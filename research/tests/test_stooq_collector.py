"""StooqPriceCollector tests: parsing exercised against a recorded-format
fixture via an injected fake fetcher. No live network involved.
"""

from datetime import date
from pathlib import Path

import pytest

from agx_research.collectors.stooq import StooqPriceCollector
from agx_research.sources.catalog import seed_sources
from agx_research.sources.spec import SourceStatus

FIXTURES = Path(__file__).parent / "fixtures"


def stooq_spec():
    return next(s for s in seed_sources() if s.id == "stooq")


class FakeFetcher:
    def __init__(self, text: str):
        self.text = text
        self.calls: list[str] = []

    def fetch_text(self, url, spec):
        self.calls.append(url)
        return self.text


def test_fetch_produces_one_document_per_symbol_with_ticker_in_url():
    fetcher = FakeFetcher((FIXTURES / "stooq_synthetic.csv").read_text())
    collector = StooqPriceCollector(
        stooq_spec(), symbols={"COMI": "comi.eg", "MFPC": "mfpc.eg"}, fetcher=fetcher
    )
    documents = collector.fetch()
    assert len(documents) == 2
    tickers = {StooqPriceCollector._ticker_from_url(d.original_url) for d in documents}
    assert tickers == {"COMI", "MFPC"}
    assert len(fetcher.calls) == 2


def test_parse_produces_expected_price_bars():
    fetcher = FakeFetcher((FIXTURES / "stooq_synthetic.csv").read_text())
    collector = StooqPriceCollector(stooq_spec(), symbols={"COMI": "comi.eg"}, fetcher=fetcher)
    [document] = collector.fetch()
    batch = collector.parse(document)
    assert len(batch.price_bars) == 3
    assert batch.parse_warnings == []
    first = batch.price_bars[0]
    assert first.ticker == "COMI"
    assert first.trade_date == date(2026, 6, 1)
    assert first.close == 45.50
    assert first.volume == 1200000


def test_parse_missing_volume_recorded_as_zero_with_warning():
    text = "Date,Open,High,Low,Close,Volume\n2026-06-01,10,11,9,10.5,\n"
    fetcher = FakeFetcher(text)
    collector = StooqPriceCollector(stooq_spec(), symbols={"IDX": "^spx"}, fetcher=fetcher)
    [document] = collector.fetch()
    batch = collector.parse(document)
    assert len(batch.price_bars) == 1
    assert batch.price_bars[0].volume == 0
    assert any("volume" in w for w in batch.parse_warnings)


def test_parse_unparseable_row_recorded_as_warning_not_dropped_silently():
    text = "Date,Open,High,Low,Close,Volume\nnot-a-date,1,1,1,1,1\n"
    fetcher = FakeFetcher(text)
    collector = StooqPriceCollector(stooq_spec(), symbols={"COMI": "comi.eg"}, fetcher=fetcher)
    [document] = collector.fetch()
    batch = collector.parse(document)
    assert batch.price_bars == []
    assert len(batch.parse_warnings) == 1


def test_parse_unexpected_header_recorded_as_warning():
    text = "Foo,Bar\n1,2\n"
    fetcher = FakeFetcher(text)
    collector = StooqPriceCollector(stooq_spec(), symbols={"COMI": "comi.eg"}, fetcher=fetcher)
    [document] = collector.fetch()
    batch = collector.parse(document)
    assert batch.price_bars == []
    assert "Unexpected header" in batch.parse_warnings[0]


def test_collector_rejects_non_implemented_source():
    spec = stooq_spec().model_copy(update={"status": SourceStatus.PLANNED})
    with pytest.raises(ValueError):
        StooqPriceCollector(spec, symbols={"COMI": "comi.eg"})
