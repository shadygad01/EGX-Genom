"""FmpCollector tests: parsing exercised against a recorded-format fixture
via an injected fake fetcher. Seed catalog entry stays NEEDS_KEY; see
docs/DATA_ACQUISITION.md and test_alphavantage_collector.py's header note.
"""

from datetime import date
from pathlib import Path

from agx_research.collectors.fmp import FmpCollector
from agx_research.sources.catalog import seed_sources
from agx_research.sources.spec import SourceStatus

FIXTURES = Path(__file__).parent / "fixtures"


def fmp_spec():
    spec = next(s for s in seed_sources() if s.id == "fmp")
    return spec.model_copy(update={"status": SourceStatus.IMPLEMENTED})


class FakeFetcher:
    def __init__(self, text: str):
        self.text = text

    def fetch_text(self, url, spec):
        return self.text


def test_fetch_strips_api_key_from_stored_url():
    fetcher = FakeFetcher((FIXTURES / "fmp_synthetic.json").read_text())
    collector = FmpCollector(fmp_spec(), ["COMI"], api_key="secret123", fetcher=fetcher)
    [document] = collector.fetch()
    assert "secret123" not in document.original_url
    assert "historical-price-full/COMI" in document.original_url


def test_parse_produces_expected_price_bars():
    fetcher = FakeFetcher((FIXTURES / "fmp_synthetic.json").read_text())
    collector = FmpCollector(fmp_spec(), ["COMI"], api_key="secret123", fetcher=fetcher)
    [document] = collector.fetch()
    batch = collector.parse(document)

    assert len(batch.price_bars) == 2
    by_date = {bar.trade_date: bar for bar in batch.price_bars}
    bar = by_date[date(2026, 6, 1)]
    assert bar.ticker == "COMI"
    assert bar.close == 45.5
    assert bar.volume == 1200000


def test_parse_error_message_recorded_as_warning():
    fetcher = FakeFetcher('{"Error Message": "Invalid API key"}')
    collector = FmpCollector(fmp_spec(), ["COMI"], api_key="k", fetcher=fetcher)
    [document] = collector.fetch()
    batch = collector.parse(document)
    assert batch.price_bars == []
    assert "FMP error" in batch.parse_warnings[0]


def test_parse_unexpected_shape_recorded_as_warning():
    fetcher = FakeFetcher('{"unexpected": true}')
    collector = FmpCollector(fmp_spec(), ["COMI"], api_key="k", fetcher=fetcher)
    [document] = collector.fetch()
    batch = collector.parse(document)
    assert batch.price_bars == []
    assert "Unexpected response shape" in batch.parse_warnings[0]
