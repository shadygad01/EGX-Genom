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
