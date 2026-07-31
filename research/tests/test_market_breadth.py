from datetime import date
from pathlib import Path

from agx_research.data.mock_provider import MockDataProvider
from agx_research.market_memory.breadth import compute_market_breadth
from agx_research.market_memory.memory import MarketMemory
from agx_research.universe.provider import MappingUniverseProvider
from agx_research.universe.sector import StaticSectorProvider

MOCK_ROOT = Path(__file__).resolve().parents[1] / "data" / "mock"


def make_memory() -> MarketMemory:
    return MarketMemory(
        MockDataProvider(MOCK_ROOT),
        MappingUniverseProvider({"COMI": "COMI", "MFPC": "MFPC"}),
        StaticSectorProvider(),
        macro_series_ids=["BRENT_USD"],
        lookback_days=30,
    )


def test_breadth_counts_real_advancers_and_decliners():
    # 2026-06-09: COMI closed 69.30 -> 69.90 (up); MFPC closed 222.10 -> 220.80 (down).
    state = make_memory().reconstruct(date(2026, 6, 9))
    report = compute_market_breadth(state)

    assert report.as_of == date(2026, 6, 9)
    assert report.universe_count == 2
    assert report.tickers_with_price_data == 2
    assert report.advancers == 1
    assert report.decliners == 1
    assert report.unchanged == 0
    assert report.advance_decline_ratio == 1.0
    assert report.average_daily_return_pct is not None


def test_breadth_flags_above_and_below_average_volume():
    # COMI's 06-09 volume (1,720,000) exceeds its trailing average; MFPC's
    # (280,000) sits below its own trailing average -- hand-computed from
    # the real mock CSVs, not asserted blind.
    state = make_memory().reconstruct(date(2026, 6, 9))
    report = compute_market_breadth(state)

    assert report.tickers_with_volume_data == 2
    assert report.tickers_above_average_volume == 1
    assert report.tickers_below_average_volume == 1


def test_breadth_excludes_tickers_with_fewer_than_two_bars():
    memory = MarketMemory(
        MockDataProvider(MOCK_ROOT),
        MappingUniverseProvider({"COMI": "COMI", "MFPC": "MFPC"}),
        StaticSectorProvider(),
        macro_series_ids=["BRENT_USD"],
        lookback_days=30,
    )
    # The mock data starts 2026-06-01; requesting the very first trading day
    # leaves every ticker with at most one bar, so nothing can have a return.
    state = memory.reconstruct(date(2026, 6, 1))
    report = compute_market_breadth(state)

    assert report.tickers_with_price_data == 0
    assert report.advancers == 0
    assert report.decliners == 0
    assert report.advance_decline_ratio is None
    assert report.average_daily_return_pct is None


def test_advance_decline_ratio_is_none_with_zero_decliners():
    memory = MarketMemory(
        MockDataProvider(MOCK_ROOT),
        MappingUniverseProvider({"COMI": "COMI"}),
        StaticSectorProvider(),
        macro_series_ids=["BRENT_USD"],
        lookback_days=30,
    )
    state = memory.reconstruct(date(2026, 6, 9))
    report = compute_market_breadth(state)

    assert report.decliners == 0
    assert report.advance_decline_ratio is None
