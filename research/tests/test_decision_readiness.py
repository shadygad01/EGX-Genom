from datetime import date
from pathlib import Path

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
