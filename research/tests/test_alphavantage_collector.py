"""AlphaVantageCollector tests: parsing exercised against a recorded-format
fixture via an injected fake fetcher. The seed catalog entry stays
NEEDS_KEY (see docs/DATA_ACQUISITION.md); these tests construct an
IMPLEMENTED copy of the spec purely to exercise the parser, exactly like
the other collector test suites do for their own fixtures.
"""

from datetime import date
from pathlib import Path

from agx_research.collectors.alphavantage import AlphaVantageCollector
from agx_research.sources.catalog import seed_sources
from agx_research.sources.spec import SourceStatus

FIXTURES = Path(__file__).parent / "fixtures"


def alphavantage_spec():
    spec = next(s for s in seed_sources() if s.id == "alphavantage")
    return spec.model_copy(update={"status": SourceStatus.IMPLEMENTED})


class FakeFetcher:
    def __init__(self, text: str):
        self.text = text

    def fetch_text(self, url, spec):
        return self.text


def test_fetch_strips_api_key_from_stored_url():
    fetcher = FakeFetcher((FIXTURES / "alphavantage_synthetic.json").read_text())
    collector = AlphaVantageCollector(alphavantage_spec(), ["COMI"], api_key="secret123", fetcher=fetcher)
    [document] = collector.fetch()
    assert "secret123" not in document.original_url
    assert "symbol=COMI" in document.original_url


def test_parse_produces_expected_price_bars():
    fetcher = FakeFetcher((FIXTURES / "alphavantage_synthetic.json").read_text())
    collector = AlphaVantageCollector(alphavantage_spec(), ["COMI"], api_key="secret123", fetcher=fetcher)
    [document] = collector.fetch()
    batch = collector.parse(document)

    assert len(batch.price_bars) == 2
    by_date = {bar.trade_date: bar for bar in batch.price_bars}
    bar = by_date[date(2026, 6, 1)]
    assert bar.ticker == "COMI"
    assert bar.close == 45.5
    assert bar.volume == 1200000


def test_parse_error_message_recorded_as_warning():
    fetcher = FakeFetcher('{"Error Message": "Invalid API call"}')
    collector = AlphaVantageCollector(alphavantage_spec(), ["COMI"], api_key="k", fetcher=fetcher)
    [document] = collector.fetch()
    batch = collector.parse(document)
    assert batch.price_bars == []
    assert "AlphaVantage error" in batch.parse_warnings[0]


def test_parse_rate_limit_note_recorded_as_warning():
    fetcher = FakeFetcher('{"Note": "Thank you for using Alpha Vantage! ..."}')
    collector = AlphaVantageCollector(alphavantage_spec(), ["COMI"], api_key="k", fetcher=fetcher)
    [document] = collector.fetch()
    batch = collector.parse(document)
    assert batch.price_bars == []
    assert "rate-limit notice" in batch.parse_warnings[0]
