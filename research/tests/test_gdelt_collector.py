import json
from datetime import date

from agx_research.collectors.gdelt import GdeltDocCollector
from agx_research.production.collector_plan import MockFetcher
from agx_research.sources.catalog import seed_sources


def test_gdelt_builds_query_and_parses_deduplicated_metadata():
    spec = next(source for source in seed_sources() if source.id == "gdelt")
    payload = json.dumps(
        {
            "articles": [
                {
                    "url": "https://news.test/a",
                    "title": "COMI expands in Egypt",
                    "seendate": "20260724T101500Z",
                },
                {
                    "url": "https://news.test/a",
                    "title": "duplicate",
                    "seendate": "20260724T101600Z",
                },
                {
                    "url": "https://news.test/b",
                    "title": "Egypt inflation slows",
                    "seendate": "20260723T090000Z",
                },
            ]
        }
    )
    expected = (
        f"{spec.base_url}?query=Egypt+OR+EGX&mode=artlist&maxrecords=25&"
        "timespan=2d&sort=datedesc&format=json"
    )
    fetcher = MockFetcher({expected: payload})
    collector = GdeltDocCollector(
        spec,
        query="Egypt OR EGX",
        ticker_hints=["COMI"],
        max_records=25,
        timespan="2d",
        fetcher=fetcher,
    )
    batch = collector.parse(collector.fetch()[0])
    assert fetcher.calls == [expected]
    assert [item.headline for item in batch.news_items] == [
        "COMI expands in Egypt",
        "Egypt inflation slows",
    ]
    assert batch.news_items[0].tickers == ["COMI"]
    assert batch.news_items[0].body == "https://news.test/a"
    assert batch.parse_warnings


def test_gdelt_historical_mode_issues_one_windowed_request_per_slice():
    spec = next(source for source in seed_sources() if source.id == "gdelt")
    empty_payload = json.dumps({"articles": []})
    expected_urls = [
        f"{spec.base_url}?query=Egypt&mode=artlist&maxrecords=25&"
        "startdatetime=20260101000000&enddatetime=20260108000000&"
        "sort=datedesc&format=json",
        f"{spec.base_url}?query=Egypt&mode=artlist&maxrecords=25&"
        "startdatetime=20260108000000&enddatetime=20260115000000&"
        "sort=datedesc&format=json",
        f"{spec.base_url}?query=Egypt&mode=artlist&maxrecords=25&"
        "startdatetime=20260115000000&enddatetime=20260116000000&"
        "sort=datedesc&format=json",
    ]
    fetcher = MockFetcher({url: empty_payload for url in expected_urls})
    collector = GdeltDocCollector(
        spec,
        query="Egypt",
        max_records=25,
        start_date=date(2026, 1, 1),
        end_date=date(2026, 1, 15),
        window_days=7,
        fetcher=fetcher,
    )
    documents = collector.fetch()
    assert [doc.original_url for doc in documents] == expected_urls
    assert fetcher.calls == expected_urls
    # Every window still parses independently through the same batch shape.
    for document in documents:
        batch = collector.parse(document)
        assert batch.news_items == []
        assert not batch.parse_warnings


def test_gdelt_historical_mode_dedups_across_windows_by_url():
    spec = next(source for source in seed_sources() if source.id == "gdelt")
    window_a_url = (
        f"{spec.base_url}?query=Egypt&mode=artlist&maxrecords=25&"
        "startdatetime=20260101000000&enddatetime=20260108000000&"
        "sort=datedesc&format=json"
    )
    window_b_url = (
        f"{spec.base_url}?query=Egypt&mode=artlist&maxrecords=25&"
        "startdatetime=20260108000000&enddatetime=20260115000000&"
        "sort=datedesc&format=json"
    )
    fetcher = MockFetcher(
        {
            window_a_url: json.dumps(
                {
                    "articles": [
                        {
                            "url": "https://news.test/old",
                            "title": "Old EGX story",
                            "seendate": "20260105T090000Z",
                        }
                    ]
                }
            ),
            window_b_url: json.dumps(
                {
                    "articles": [
                        {
                            "url": "https://news.test/newer",
                            "title": "Newer EGX story",
                            "seendate": "20260110T090000Z",
                        }
                    ]
                }
            ),
        }
    )
    collector = GdeltDocCollector(
        spec,
        query="Egypt",
        max_records=25,
        start_date=date(2026, 1, 1),
        end_date=date(2026, 1, 14),
        window_days=7,
        fetcher=fetcher,
    )
    documents = collector.fetch()
    assert len(documents) == 2
    headlines = [item.headline for doc in documents for item in collector.parse(doc).news_items]
    assert headlines == ["Old EGX story", "Newer EGX story"]
