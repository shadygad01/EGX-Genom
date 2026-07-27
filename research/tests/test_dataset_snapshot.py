from datetime import date
from pathlib import Path

from agx_research.data.mock_provider import MockDataProvider
from agx_research.data.snapshot import build_snapshot

MOCK_ROOT = Path(__file__).resolve().parents[1] / "data" / "mock"


def provider() -> MockDataProvider:
    return MockDataProvider(MOCK_ROOT)


def test_same_query_produces_same_id():
    snap_a = build_snapshot(
        provider(), tickers=["COMI"], macro_series_ids=["BRENT_USD"],
        as_of=date(2026, 6, 14), lookback_days=30,
    )
    snap_b = build_snapshot(
        provider(), tickers=["COMI"], macro_series_ids=["BRENT_USD"],
        as_of=date(2026, 6, 14), lookback_days=30,
    )
    assert snap_a.id == snap_b.id


def test_different_as_of_produces_different_id():
    snap_a = build_snapshot(
        provider(), tickers=["COMI"], macro_series_ids=[], as_of=date(2026, 6, 14), lookback_days=30
    )
    snap_b = build_snapshot(
        provider(), tickers=["COMI"], macro_series_ids=[], as_of=date(2026, 6, 10), lookback_days=30
    )
    assert snap_a.id != snap_b.id


def test_no_data_after_as_of():
    snapshot = build_snapshot(
        provider(), tickers=["COMI"], macro_series_ids=[], as_of=date(2026, 6, 9), lookback_days=30
    )
    assert all(bar.trade_date <= date(2026, 6, 9) for bar in snapshot.price_history["COMI"])


def test_bundles_corporate_events_and_macro_and_news():
    snapshot = build_snapshot(
        provider(),
        tickers=["COMI", "MFPC"],
        macro_series_ids=["BRENT_USD", "EGP_USD"],
        as_of=date(2026, 6, 14),
        lookback_days=30,
    )
    assert len(snapshot.corporate_events["MFPC"]) == 1
    assert len(snapshot.macro_series["BRENT_USD"]) > 0
    assert len(snapshot.news) > 0


def test_macro_lookback_days_defaults_to_lookback_days():
    snapshot = build_snapshot(
        provider(), tickers=["COMI"], macro_series_ids=["BRENT_USD"],
        as_of=date(2026, 6, 14), lookback_days=30,
    )
    assert snapshot.macro_lookback_days == 30


def test_macro_lookback_days_windows_macro_series_independently_of_price_history():
    # Mock BRENT_USD/COMI both start 2026-06-01 -- a 5-day price window (start
    # 2026-06-09) drops the early bars, but a 30-day macro window still
    # covers the whole mock fixture. This is the exact independence that a
    # single shared window doesn't give annual/quarterly macro sources.
    snapshot = build_snapshot(
        provider(),
        tickers=["COMI"],
        macro_series_ids=["BRENT_USD"],
        as_of=date(2026, 6, 14),
        lookback_days=5,
        macro_lookback_days=30,
    )
    assert all(bar.trade_date >= date(2026, 6, 9) for bar in snapshot.price_history["COMI"])
    assert any(
        obs.observation_date < date(2026, 6, 9) for obs in snapshot.macro_series["BRENT_USD"]
    )
