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
