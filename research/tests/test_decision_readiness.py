from datetime import date
from pathlib import Path

from agx_research.config import Horizon
from agx_research.data.mock_provider import MockDataProvider
from agx_research.data.schemas import MacroObservation
from agx_research.data.snapshot import build_snapshot
from agx_research.decision_service.country_risk import REAL_CURRENCY_SERIES_ID
from agx_research.financials.collected import CollectedFinancialStatementProvider
from agx_research.financials.schema import FinancialStatementLineItem
from agx_research.market_memory.state import MarketState, TradingSession
from agx_research.meta.readiness import (
    MAX_PRICE_ABOVE_FAIR_VALUE_PCT,
    ReadinessStatus,
    assess_decision_readiness,
)
from agx_research.valuation import FairValueEngine

MOCK_ROOT = Path(__file__).resolve().parents[1] / "data" / "mock"


class _FairValueFinancialsProvider:
    """A fake `FinancialStatementProvider` supplying enough real line items
    for `FairValueEngine` to compute a value (mirrors
    `test_fair_value_engine.py`'s fixture, scaled to land near/far from
    COMI's real mock closing price so both sides of the price-quality
    criterion can be exercised)."""

    def __init__(self, ticker: str, scale: float):
        values = {
            2023: {"revenue": 1000, "operating_income": 220, "net_income": 150, "free_cash_flow": 130, "ebitda": 260, "total_equity": 700, "cash_and_equivalents": 150, "total_debt": 100, "shares_outstanding": 100, "eps_diluted": 1.5, "dividend_per_share": .5},
            2024: {"revenue": 1100, "operating_income": 240, "net_income": 165, "free_cash_flow": 140, "ebitda": 280, "total_equity": 780, "cash_and_equivalents": 170, "total_debt": 100, "shares_outstanding": 100, "eps_diluted": 1.65, "dividend_per_share": .55},
            2025: {"revenue": 1200, "operating_income": 260, "net_income": 180, "free_cash_flow": 150, "ebitda": 300, "total_equity": 860, "cash_and_equivalents": 190, "total_debt": 100, "shares_outstanding": 100, "eps_diluted": 1.8, "dividend_per_share": .6},
        }
        self.items = [
            FinancialStatementLineItem(
                ticker=ticker, period_end_date=date(year, 12, 31), period_type="ANNUAL",
                statement_type="TEST", line_item=name,
                value=value if name == "shares_outstanding" else value * scale,
            )
            for year, row in values.items() for name, value in row.items()
        ]

    def get_line_items(self, ticker, start, end, *, statement_type=None):
        return [item for item in self.items if start <= item.period_end_date <= end]


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
    assert any("knowledge" in blocker for blocker in row.blockers)


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
    assert any("exchange-rate" in blocker for blocker in row.horizon_blockers[Horizon.INVESTMENT])
    assert any("exchange-rate" in blocker for blocker in row.blockers)


def test_investment_horizon_recognizes_real_production_currency_series_id(tmp_path):
    # Regression test (2026-07-31): a real LIVE run's snapshot carries
    # EGP/USD under the real World Bank id (`egypt_official_fx_egp_per_usd`,
    # production/collector_plan.py's LIVE_WORLDBANK_INDICATORS), never the
    # mock fixture's `EGP_USD` -- this must satisfy the country-risk-data-
    # presence check exactly like the mock id does, not report "missing"
    # for real, successfully-collected data.
    snapshot = build_snapshot(
        MockDataProvider(MOCK_ROOT),
        tickers=["COMI"],
        macro_series_ids=["BRENT_USD"],
        as_of=date(2026, 6, 14),
        lookback_days=30,
    )
    snapshot = snapshot.model_copy(
        update={
            "macro_series": {
                **snapshot.macro_series,
                REAL_CURRENCY_SERIES_ID: [
                    MacroObservation(
                        series_id=REAL_CURRENCY_SERIES_ID,
                        observation_date=date(2026, 1, 1),
                        value=49.0,
                    ),
                    MacroObservation(
                        series_id=REAL_CURRENCY_SERIES_ID,
                        observation_date=date(2026, 6, 1),
                        value=49.5,
                    ),
                ],
            }
        }
    )
    state = MarketState(
        as_of=date(2026, 6, 14),
        dataset_snapshot=snapshot,
        constituents={"COMI": "Commercial International Bank"},
        sectors={"COMI": "Banks"},
        trading_session=TradingSession(session_date=date(2026, 6, 14), is_trading_day=True),
    )
    row = assess_decision_readiness(state, CollectedFinancialStatementProvider(tmp_path), [])[0]
    assert not any("exchange-rate" in blocker for blocker in row.horizon_blockers[Horizon.INVESTMENT])


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
        assert any("Liquidity" in blocker for blocker in row.horizon_blockers[horizon])
    assert any("Liquidity" in blocker for blocker in row.blockers)


def test_investment_horizon_blocked_when_price_far_above_fair_value(tmp_path):
    # COMI's real mock close on 2026-06-14 is 68.40; this financials
    # fixture (unscaled) yields a weighted fair value of ~13.48 -- a price
    # over 4x the calculated fair value should flag as a weak entry, not
    # just get silently blended into the expected return.
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
    fair_value_engine = FairValueEngine(_FairValueFinancialsProvider("COMI", scale=1))
    row = assess_decision_readiness(
        state, CollectedFinancialStatementProvider(tmp_path), [], fair_value_engine
    )[0]
    assert row.price_vs_fair_value_pct is not None
    assert row.price_vs_fair_value_pct > MAX_PRICE_ABOVE_FAIR_VALUE_PCT
    assert Horizon.INVESTMENT not in row.ready_horizons
    assert any(
        "vs. the calculated fair value" in blocker
        for blocker in row.horizon_blockers[Horizon.INVESTMENT]
    )
    assert any("above the calculated fair value" in blocker for blocker in row.blockers)


def test_investment_horizon_not_blocked_when_price_near_fair_value(tmp_path):
    # Same fixture scaled 5x lands the weighted fair value at ~67.41,
    # within MAX_PRICE_ABOVE_FAIR_VALUE_PCT of COMI's real 68.40 mock
    # close -- the price-quality criterion must not fire on a fair entry.
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
    fair_value_engine = FairValueEngine(_FairValueFinancialsProvider("COMI", scale=5))
    row = assess_decision_readiness(
        state, CollectedFinancialStatementProvider(tmp_path), [], fair_value_engine
    )[0]
    assert row.price_vs_fair_value_pct is not None
    assert row.price_vs_fair_value_pct <= MAX_PRICE_ABOVE_FAIR_VALUE_PCT
    assert not any(
        "vs. the calculated fair value" in blocker
        for blocker in row.horizon_blockers[Horizon.INVESTMENT]
    )


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
