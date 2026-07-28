"""RssNewsCollector tests against recorded-format RSS and Atom fixtures.
No live network."""

from datetime import date
from pathlib import Path

from agx_research.collectors.rss import RssNewsCollector
from agx_research.sources.catalog import seed_sources

FIXTURES = Path(__file__).parent / "fixtures"


def rss_spec():
    return next(s for s in seed_sources() if s.id == "rss_generic")


class FakeFetcher:
    def __init__(self, text: str):
        self.text = text

    def fetch_text(self, url, spec):
        return self.text


def test_parse_rss2_items():
    fetcher = FakeFetcher((FIXTURES / "rss_synthetic.xml").read_text())
    collector = RssNewsCollector(
        rss_spec(), feed_url="https://example.test/feed.xml", ticker_hints=["COMI"], fetcher=fetcher
    )
    [document] = collector.fetch()
    batch = collector.parse(document)
    # 3 items in fixture; one has no date and is skipped with a warning
    assert len(batch.news_items) == 2
    assert len(batch.parse_warnings) == 1
    assert "missing title or date" in batch.parse_warnings[0]


def test_ticker_hint_matching_is_case_insensitive_and_preserves_link_as_body():
    fetcher = FakeFetcher((FIXTURES / "rss_synthetic.xml").read_text())
    collector = RssNewsCollector(
        rss_spec(), feed_url="https://example.test/feed.xml", ticker_hints=["comi"], fetcher=fetcher
    )
    [document] = collector.fetch()
    batch = collector.parse(document)
    matched = next(i for i in batch.news_items if i.headline.startswith("COMI"))
    assert matched.tickers == ["comi"]
    assert matched.body == "https://example.test/news/comi-q2"
    assert matched.published_at == date(2026, 6, 1)


def test_parse_atom_entries():
    fetcher = FakeFetcher((FIXTURES / "atom_synthetic.xml").read_text())
    collector = RssNewsCollector(
        rss_spec(), feed_url="https://example.test/atom.xml", ticker_hints=["MFPC"], fetcher=fetcher
    )
    [document] = collector.fetch()
    batch = collector.parse(document)
    assert len(batch.news_items) == 1
    item = batch.news_items[0]
    assert item.published_at == date(2026, 6, 3)
    assert item.body == "https://example.test/news/mfpc-facility"
    assert item.tickers == ["MFPC"]


def test_parse_month_day_year_timestamp_used_by_arabic_feed():
    feed = """<?xml version="1.0" encoding="utf-8"?>
    <rss version="2.0"><channel><item>
      <title>خبر اقتصادي مصري</title>
      <link>https://example.test/economy/1</link>
      <pubDate>7/26/2026 4:49:21 AM</pubDate>
    </item></channel></rss>"""
    collector = RssNewsCollector(
        rss_spec(), feed_url="https://example.test/economy.xml", fetcher=FakeFetcher(feed)
    )

    [document] = collector.fetch()
    batch = collector.parse(document)

    assert batch.parse_warnings == []
    assert batch.news_items[0].published_at == date(2026, 7, 26)


def test_ticker_hint_no_longer_matches_as_substring_of_a_longer_ticker():
    # The real near-miss named in the project owner's completion plan:
    # a "VLMR" hint must not match a headline about "VLMRA".
    feed = """<?xml version="1.0" encoding="utf-8"?>
    <rss version="2.0"><channel><item>
      <title>VLMRA reports quarterly results</title>
      <link>https://example.test/news/vlmra-q</link>
      <pubDate>Mon, 01 Jun 2026 00:00:00 GMT</pubDate>
    </item></channel></rss>"""
    collector = RssNewsCollector(
        rss_spec(), feed_url="https://example.test/feed.xml", ticker_hints=["VLMR"], fetcher=FakeFetcher(feed)
    )
    [document] = collector.fetch()
    batch = collector.parse(document)
    assert batch.news_items[0].tickers == []


def test_ticker_hints_as_dict_matches_by_real_company_name_too():
    feed = """<?xml version="1.0" encoding="utf-8"?>
    <rss version="2.0"><channel><item>
      <title>Commercial International Bank CIB posts record earnings</title>
      <link>https://example.test/news/cib-earnings</link>
      <pubDate>Mon, 01 Jun 2026 00:00:00 GMT</pubDate>
    </item></channel></rss>"""
    collector = RssNewsCollector(
        rss_spec(),
        feed_url="https://example.test/feed.xml",
        ticker_hints={"COMI": "Commercial International Bank-Egypt (CIB)"},
        fetcher=FakeFetcher(feed),
    )
    [document] = collector.fetch()
    batch = collector.parse(document)
    assert batch.news_items[0].tickers == ["COMI"]


def test_no_ticker_hint_match_leaves_tickers_empty():
    fetcher = FakeFetcher((FIXTURES / "atom_synthetic.xml").read_text())
    collector = RssNewsCollector(
        rss_spec(), feed_url="https://example.test/atom.xml", ticker_hints=["COMI"], fetcher=fetcher
    )
    [document] = collector.fetch()
    batch = collector.parse(document)
    assert batch.news_items[0].tickers == []


def test_malformed_xml_recorded_as_warning_not_raised():
    fetcher = FakeFetcher("<rss><channel><item><title>Broken")
    collector = RssNewsCollector(rss_spec(), feed_url="https://example.test/feed.xml", fetcher=fetcher)
    [document] = collector.fetch()
    batch = collector.parse(document)
    assert batch.news_items == []
    assert len(batch.parse_warnings) == 1


def test_feed_with_no_entries_recorded_as_warning():
    fetcher = FakeFetcher("<rss><channel><title>Empty</title></channel></rss>")
    collector = RssNewsCollector(rss_spec(), feed_url="https://example.test/feed.xml", fetcher=fetcher)
    [document] = collector.fetch()
    batch = collector.parse(document)
    assert batch.news_items == []
    assert "No <item>/<entry>" in batch.parse_warnings[0]


def test_classify_corporate_events_off_by_default():
    fetcher = FakeFetcher((FIXTURES / "rss_synthetic.xml").read_text())
    collector = RssNewsCollector(
        rss_spec(), feed_url="https://example.test/feed.xml", ticker_hints=["COMI"], fetcher=fetcher
    )
    [document] = collector.fetch()
    batch = collector.parse(document)
    assert batch.corporate_events == []


def test_classify_corporate_events_populates_batch_alongside_news_item():
    fetcher = FakeFetcher((FIXTURES / "rss_synthetic.xml").read_text())
    collector = RssNewsCollector(
        rss_spec(), feed_url="https://example.test/feed.xml", ticker_hints=["COMI"],
        classify_corporate_events=True, fetcher=fetcher,
    )
    [document] = collector.fetch()
    batch = collector.parse(document)

    # "COMI reports quarterly results" -> EARNINGS; the CBE-rates and
    # no-date entries have no ticker match / are skipped, so no event.
    assert len(batch.corporate_events) == 1
    event = batch.corporate_events[0]
    assert event.ticker == "COMI"
    assert event.event_type == "EARNINGS"
    assert event.event_date == date(2026, 6, 1)
    assert event.details == {}
    # Still a news item too -- classification adds a view, doesn't replace one.
    assert any(item.headline.startswith("COMI") for item in batch.news_items)


def test_classify_corporate_events_skips_entries_with_no_or_multiple_ticker_matches():
    fetcher = FakeFetcher((FIXTURES / "rss_synthetic.xml").read_text())
    collector = RssNewsCollector(
        rss_spec(), feed_url="https://example.test/feed.xml", ticker_hints=["COMI", "quarterly"],
        classify_corporate_events=True, fetcher=fetcher,
    )
    [document] = collector.fetch()
    batch = collector.parse(document)
    # "quarterly" also appears in the COMI headline, so two hints match --
    # a CorporateEvent needs exactly one ticker, so nothing is classified.
    assert batch.corporate_events == []


def test_classify_corporate_events_skips_headlines_matching_no_keyword():
    fetcher = FakeFetcher((FIXTURES / "rss_synthetic.xml").read_text())
    collector = RssNewsCollector(
        rss_spec(), feed_url="https://example.test/feed.xml", ticker_hints=["Egypt"],
        classify_corporate_events=True, fetcher=fetcher,
    )
    [document] = collector.fetch()
    batch = collector.parse(document)
    # "Egypt central bank holds rates" matches no corporate-event keyword.
    assert batch.corporate_events == []
