from datetime import date
from pathlib import Path

from agx_research.config import Horizon
from agx_research.data.mock_provider import MockDataProvider
from agx_research.data.snapshot import build_snapshot
from agx_research.financials.collected import CollectedFinancialStatementProvider
from agx_research.market_memory.state import MarketState, TradingSession
from agx_research.meta.readiness import ReadinessStatus, assess_decision_readiness

MOCK_ROOT = Path(__file__).resolve().parents[1] / "data" / "mock"


def test_missing_fundamentals_and_knowledge_force_explicit_abstention(tmp_path):
    snapshot = build_snapshot(
        MockDataProvider(MOCK_ROOT),
        tickers=["COMI"],
        macro_series_ids=["BRENT_USD"],
        as_of=date(2026, 6, 14),
        lookback_days=30,
    )
    state = MarketState(
        as_of=date(2026, 6, 14),
        dataset_snapshot=snapshot,
        constituents={"COMI": "Commercial International Bank"},
        sectors={"COMI": "Banks"},
        trading_session=TradingSession(session_date=date(2026, 6, 14), is_trading_day=True),
    )
    row = assess_decision_readiness(
        state, CollectedFinancialStatementProvider(tmp_path), []
    )[0]
    assert row.status == ReadinessStatus.DEGRADED
    assert row.decision == "abstain"
    assert row.price_observations > 0
    assert row.financial_periods == 0
    assert any("معرفة" in blocker for blocker in row.blockers)


def test_investment_horizon_blocked_without_currency_series(tmp_path):
    # macro_series_ids includes only BRENT_USD, never EGP_USD -- the
    # country-risk-data-presence check (Architecture Adversarial Review
    # R2) should block INVESTMENT distinctly from the generic "fewer than
    # 3 macro series" check.
    snapshot = build_snapshot(
        MockDataProvider(MOCK_ROOT),
        tickers=["COMI"],
        macro_series_ids=["BRENT_USD"],
        as_of=date(2026, 6, 14),
        lookback_days=30,
    )
    state = MarketState(
        as_of=date(2026, 6, 14),
        dataset_snapshot=snapshot,
        constituents={"COMI": "Commercial International Bank"},
        sectors={"COMI": "Banks"},
        trading_session=TradingSession(session_date=date(2026, 6, 14), is_trading_day=True),
    )
    row = assess_decision_readiness(state, CollectedFinancialStatementProvider(tmp_path), [])[0]
    assert Horizon.INVESTMENT not in row.ready_horizons
    assert any("سعر الصرف" in blocker for blocker in row.horizon_blockers[Horizon.INVESTMENT])
    assert any("سعر الصرف" in blocker for blocker in row.blockers)


def test_illiquid_ticker_blocked_across_every_horizon(tmp_path):
    # An absurdly high liquidity floor flags even COMI/MFPC's real mock
    # traded value as illiquid, proving the override reaches every
    # horizon, not just one.
    import agx_research.meta.readiness as readiness_module

    original_floor = readiness_module._LIQUIDITY_FLOOR_MIN_AVG_TRADED_VALUE
    readiness_module._LIQUIDITY_FLOOR_MIN_AVG_TRADED_VALUE = 1e18
    try:
        snapshot = build_snapshot(
            MockDataProvider(MOCK_ROOT),
            tickers=["COMI"],
            macro_series_ids=["BRENT_USD", "EGP_USD"],
            as_of=date(2026, 6, 14),
            lookback_days=30,
        )
        state = MarketState(
            as_of=date(2026, 6, 14),
            dataset_snapshot=snapshot,
            constituents={"COMI": "Commercial International Bank"},
            sectors={"COMI": "Banks"},
            trading_session=TradingSession(session_date=date(2026, 6, 14), is_trading_day=True),
        )
        row = assess_decision_readiness(state, CollectedFinancialStatementProvider(tmp_path), [])[0]
    finally:
        readiness_module._LIQUIDITY_FLOOR_MIN_AVG_TRADED_VALUE = original_floor

    assert row.ready_horizons == []
    for horizon in Horizon:
        assert any("السيولة" in blocker for blocker in row.horizon_blockers[horizon])
    assert any("السيولة" in blocker for blocker in row.blockers)


def test_no_prices_is_blocked_not_merely_degraded(tmp_path):
    snapshot = build_snapshot(
        MockDataProvider(tmp_path),
        tickers=["SWDY"],
        macro_series_ids=[],
        as_of=date(2026, 6, 14),
        lookback_days=30,
    )
    state = MarketState(
        as_of=date(2026, 6, 14),
        dataset_snapshot=snapshot,
        constituents={"SWDY": "Elsewedy Electric"},
        sectors={},
        trading_session=TradingSession(session_date=date(2026, 6, 14), is_trading_day=True),
    )
    row = assess_decision_readiness(
        state, CollectedFinancialStatementProvider(tmp_path), []
    )[0]
    assert row.status == ReadinessStatus.BLOCKED
    assert row.decision == "abstain"
    assert row.ready_horizons == []
