from datetime import date, timedelta
from pathlib import Path

from agx_research.data.mock_provider import MockDataProvider
from agx_research.data.schemas import PriceBar
from agx_research.data.snapshot import DatasetSnapshot
from agx_research.market_memory.memory import MarketMemory
from agx_research.market_memory.regime import (
    BEARISH_CUMULATIVE_RETURN_THRESHOLD,
    BULLISH_CUMULATIVE_RETURN_THRESHOLD,
    MarketTrend,
    VolatilityLevel,
    compute_market_regime,
)
from agx_research.market_memory.state import MarketState, TradingSession
from agx_research.universe.provider import MappingUniverseProvider
from agx_research.universe.sector import StaticSectorProvider

MOCK_ROOT = Path(__file__).resolve().parents[1] / "data" / "mock"


def make_bars(ticker: str, closes: list[float], start: date) -> list[PriceBar]:
    return [
        PriceBar(
            ticker=ticker,
            trade_date=start + timedelta(days=i),
            open=close,
            high=close,
            low=close,
            close=close,
            volume=100_000,
        )
        for i, close in enumerate(closes)
    ]


def make_state(price_history: dict[str, list[PriceBar]], as_of: date) -> MarketState:
    snapshot = DatasetSnapshot(
        id="test-snapshot",
        as_of=as_of,
        lookback_days=30,
        macro_lookback_days=30,
        tickers=sorted(price_history),
        macro_series_ids=[],
        price_history=price_history,
    )
    return MarketState(
        as_of=as_of,
        dataset_snapshot=snapshot,
        constituents={t: t for t in price_history},
        trading_session=TradingSession(session_date=as_of, is_trading_day=True),
    )


def test_regime_classifies_bullish_trend_from_a_real_uptrend():
    start = date(2026, 6, 1)
    # Steady +1%/day for 10 days -> well above the bullish floor, and
    # smooth enough to stay out of the elevated/high volatility bands.
    closes = [100.0]
    for _ in range(9):
        closes.append(closes[-1] * 1.01)
    state = make_state({"AAA": make_bars("AAA", closes, start)}, start + timedelta(days=9))

    report = compute_market_regime(state)

    assert report.trend == MarketTrend.BULLISH
    assert report.cumulative_return_pct is not None
    assert report.cumulative_return_pct > BULLISH_CUMULATIVE_RETURN_THRESHOLD * 100
    assert report.volatility == VolatilityLevel.LOW
    assert report.tickers_with_sufficient_data == 1
    assert report.trading_days_observed == 9
    assert any("bullish" in r.lower() for r in report.reasons)


def test_regime_classifies_bearish_trend_from_a_real_downtrend():
    start = date(2026, 6, 1)
    closes = [100.0]
    for _ in range(9):
        closes.append(closes[-1] * 0.99)
    state = make_state({"AAA": make_bars("AAA", closes, start)}, start + timedelta(days=9))

    report = compute_market_regime(state)

    assert report.trend == MarketTrend.BEARISH
    assert report.cumulative_return_pct is not None
    assert report.cumulative_return_pct < BEARISH_CUMULATIVE_RETURN_THRESHOLD * 100


def test_regime_classifies_neutral_trend_inside_the_band():
    start = date(2026, 6, 1)
    # Tiny back-and-forth moves that never accumulate past either threshold.
    closes = [100.0, 100.2, 100.0, 100.1, 100.0, 100.1, 99.9, 100.0]
    state = make_state({"AAA": make_bars("AAA", closes, start)}, start + timedelta(days=7))

    report = compute_market_regime(state)

    assert report.trend == MarketTrend.NEUTRAL


def test_regime_classifies_high_volatility_even_with_a_near_zero_trend():
    start = date(2026, 6, 1)
    # Large swings that start and end at exactly the same price (0%
    # cumulative return, safely inside the neutral band) but with a large
    # realized daily standard deviation along the way.
    closes = [100.0, 108.0, 95.0, 110.0, 92.0, 108.0, 96.0, 106.0, 98.0, 100.0]
    state = make_state({"AAA": make_bars("AAA", closes, start)}, start + timedelta(days=9))

    report = compute_market_regime(state)

    assert report.volatility == VolatilityLevel.HIGH
    assert report.trend == MarketTrend.NEUTRAL


def test_regime_reports_insufficient_data_honestly_rather_than_a_fabricated_trend():
    state = make_state({}, date(2026, 6, 1))
    report = compute_market_regime(state)

    assert report.trend == MarketTrend.NEUTRAL
    assert report.volatility == VolatilityLevel.LOW
    assert report.cumulative_return_pct is None
    assert report.trading_days_observed == 0
    assert "insufficient" in report.reasons[0].lower()


def test_regime_never_looks_past_a_declared_lookback_window():
    start = date(2026, 1, 1)
    # 40 trading days of a steady uptrend, but only the trailing 5 requested
    # -- confirms the window is honored, not silently using everything.
    closes = [100.0]
    for _ in range(39):
        closes.append(closes[-1] * 1.01)
    state = make_state({"AAA": make_bars("AAA", closes, start)}, start + timedelta(days=39))

    report = compute_market_regime(state, lookback_days=5)

    assert report.trading_days_observed == 5


def test_regime_end_to_end_against_real_mock_data_runs_without_error():
    memory = MarketMemory(
        MockDataProvider(MOCK_ROOT),
        MappingUniverseProvider({"COMI": "COMI", "MFPC": "MFPC"}),
        StaticSectorProvider(),
        macro_series_ids=["BRENT_USD"],
        lookback_days=30,
    )
    state = memory.reconstruct(date(2026, 6, 14))
    report = compute_market_regime(state)

    assert report.as_of == date(2026, 6, 14)
    assert report.trend in set(MarketTrend)
    assert report.volatility in set(VolatilityLevel)
