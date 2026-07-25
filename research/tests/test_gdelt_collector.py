import json

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
