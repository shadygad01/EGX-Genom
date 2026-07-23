from datetime import date
from pathlib import Path

from agx_research.data.adjustments import (
    adjusted_daily_returns,
    adjusted_returns_for_ticker,
    compute_adjusted_closes,
)
from agx_research.data.mock_provider import MockDataProvider
from agx_research.data.schemas import CorporateEvent, PriceBar
from agx_research.data.snapshot import build_snapshot

MOCK_ROOT = Path(__file__).resolve().parents[1] / "data" / "mock"


def bar(trade_date, close) -> PriceBar:
    return PriceBar(
        ticker="TEST", trade_date=trade_date, open=close, high=close, low=close, close=close, volume=1000
    )


def test_no_adjustable_events_leaves_closes_unchanged():
    bars = [bar(date(2026, 6, 1), 100.0), bar(date(2026, 6, 2), 101.0)]
    events = [
        CorporateEvent(
            ticker="TEST", event_date=date(2026, 6, 1), event_type="EARNINGS", description="n/a"
        )
    ]
    adjusted = compute_adjusted_closes(bars, events)
    assert adjusted == {date(2026, 6, 1): 100.0, date(2026, 6, 2): 101.0}


def test_split_halves_all_prior_closes():
    bars = [
        bar(date(2026, 6, 1), 200.0),
        bar(date(2026, 6, 2), 210.0),
        bar(date(2026, 6, 3), 100.0),  # the mechanical post-split price
    ]
    events = [
        CorporateEvent(
            ticker="TEST",
            event_date=date(2026, 6, 3),
            event_type="SPLIT",
            description="2-for-1 split",
            details={"split_ratio": 2.0},
        )
    ]
    adjusted = compute_adjusted_closes(bars, events)
    assert adjusted[date(2026, 6, 1)] == 100.0
    assert adjusted[date(2026, 6, 2)] == 105.0
    assert adjusted[date(2026, 6, 3)] == 100.0  # on/after the ex-date: untouched


def test_dividend_scales_prior_closes_by_the_correct_factor():
    bars = [bar(date(2026, 6, 1), 100.0), bar(date(2026, 6, 2), 95.0)]
    events = [
        CorporateEvent(
            ticker="TEST",
            event_date=date(2026, 6, 2),
            event_type="DIVIDEND",
            description="cash dividend",
            details={"dividend_amount": 5.0},
        )
    ]
    adjusted = compute_adjusted_closes(bars, events)
    # factor = (100 - 5) / 100 = 0.95
    assert adjusted[date(2026, 6, 1)] == 95.0
    assert adjusted[date(2026, 6, 2)] == 95.0  # on/after the ex-date: untouched


def test_adjusted_daily_returns_reflects_the_true_economic_return_across_a_split():
    bars = [
        bar(date(2026, 6, 1), 200.0),
        bar(date(2026, 6, 2), 100.0),  # a 2-for-1 split happened; no real loss occurred
    ]
    events = [
        CorporateEvent(
            ticker="TEST",
            event_date=date(2026, 6, 2),
            event_type="SPLIT",
            description="2-for-1 split",
            details={"split_ratio": 2.0},
        )
    ]
    returns = adjusted_daily_returns(bars, events)
    assert len(returns) == 1
    assert abs(returns[0]) < 1e-9  # ~0% true return, not the fake -50% the raw close implies


def test_adjusted_returns_for_ticker_uses_real_mock_dividend_event():
    provider = MockDataProvider(MOCK_ROOT)
    snapshot = build_snapshot(
        provider, tickers=["MFPC"], macro_series_ids=[], as_of=date(2026, 6, 14), lookback_days=30
    )
    from agx_research.features.correlation import daily_returns

    raw = daily_returns([b.close for b in snapshot.price_history["MFPC"]])
    adjusted = adjusted_returns_for_ticker(snapshot, "MFPC")

    assert len(adjusted) == len(raw)
    assert adjusted != raw  # the mock MFPC dividend event genuinely changes the series
