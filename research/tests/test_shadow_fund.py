"""Tests for the Shadow Fund engine -- a persistent virtual portfolio
driven entirely by feeding the fund's own prior state back into the
existing `DecisionService.decide_portfolio()` (never a new decision
engine). Exercised with hand-built `Recommendation`s + `DatasetSnapshot`
price series, the same posture `test_decision_service.py`/
`test_decision_ledger.py` already use."""

from __future__ import annotations

from datetime import date, datetime

import pytest

from agx_research.config import Horizon
from agx_research.data.schemas import PriceBar
from agx_research.data.snapshot import DatasetSnapshot
from agx_research.decision_service.country_risk import CountryRiskAssessment, CountryRiskSeverity
from agx_research.domain.provenance import Provenance, ProvenanceRef
from agx_research.explainability import Explanation
from agx_research.horizons.base import Prediction
from agx_research.meta.decision_engine import DecisionAction, MetaDecisionEngine
from agx_research.meta.decision_quality import apply_decision_quality_gate
from agx_research.decision_service.service import PositionAction
from agx_research.shadow_fund.engine import (
    INCEPTION_NAV,
    MIN_RISK_SAMPLE_DAYS,
    advance,
)

NO_RISK = CountryRiskAssessment(as_of=date(2026, 6, 14), severity=CountryRiskSeverity.NORMAL)


def bar(day: date, close: float, ticker: str) -> PriceBar:
    return PriceBar(ticker=ticker, trade_date=day, open=close, high=close, low=close, close=close, volume=1000)


def make_recommendation(
    ticker: str,
    as_of: date,
    expected_return: float = 0.10,
    expected_risk: float = 0.05,
    confidence: float = 0.8,
    publication_ready: bool = True,
):
    prediction = Prediction(
        ticker=ticker, horizon=Horizon.INVESTMENT, as_of=as_of,
        model_id="test", model_version="1",
        expected_return=expected_return, expected_risk=expected_risk, confidence=confidence,
        reference_price=100.0,
        explanation=Explanation(
            why_this_stock="test", why_now="test", why_not_others="test",
            supporting_evidence=["test evidence"],
            evidence_refs=[ProvenanceRef(kind="knowledge", ref_id="know-1")],
            invalidation_conditions=["test invalidation condition"],
        ),
        provenance=Provenance(produced_by="test", produced_at=datetime.now()),
    )
    recommendation = MetaDecisionEngine().decide(ticker, as_of, {Horizon.INVESTMENT: prediction})
    assert recommendation is not None
    if publication_ready:
        recommendation = apply_decision_quality_gate([recommendation])[0]
    return recommendation


def snapshot_with_prices(as_of: date, prices: dict[str, list[tuple[date, float]]]) -> DatasetSnapshot:
    return DatasetSnapshot(
        id=f"snap-{as_of.isoformat()}",
        as_of=as_of,
        lookback_days=10,
        macro_lookback_days=10,
        tickers=[t for t in prices if t != "EGX30"],
        macro_series_ids=[],
        price_history={ticker: [bar(d, c, ticker) for d, c in series] for ticker, series in prices.items()},
    )


def test_inception_buys_into_a_strong_recommendation():
    as_of = date(2026, 7, 1)
    rec = make_recommendation("COMI", as_of)
    assert rec.horizon_decisions[Horizon.INVESTMENT].action == DecisionAction.BUY_CANDIDATE
    snapshot = snapshot_with_prices(as_of, {"COMI": [(as_of, 100.0)], "EGX30": [(as_of, 100.0)]})

    result = advance(None, [rec], as_of, snapshot, country_risk=NO_RISK)

    assert result.inception_date == as_of
    assert len(result.open_positions) == 1
    position = result.open_positions[0]
    assert position.ticker == "COMI"
    assert position.weight > 0
    assert position.average_cost == 100.0
    assert result.nav < INCEPTION_NAV  # transaction cost is a real, if tiny, drag on day one
    assert result.nav == position.market_value + result.cash
    assert len(result.transactions) == 1
    assert result.transactions[0].action == PositionAction.BUY
    assert result.daily_return_pct is None  # nothing to compare against yet
    assert result.risk.sample_status == "insufficient_sample"


def test_price_appreciation_grows_nav_and_marks_daily_return():
    day1, day2 = date(2026, 7, 1), date(2026, 7, 2)
    rec1 = make_recommendation("COMI", day1)
    snap1 = snapshot_with_prices(day1, {"COMI": [(day1, 100.0)], "EGX30": [(day1, 100.0)]})
    day1_state = advance(None, [rec1], day1, snap1, country_risk=NO_RISK)
    invested_value_day1 = day1_state.open_positions[0].market_value

    rec2 = make_recommendation("COMI", day2)
    snap2 = snapshot_with_prices(
        day2, {"COMI": [(day1, 100.0), (day2, 110.0)], "EGX30": [(day1, 100.0), (day2, 100.0)]}
    )
    day2_state = advance(day1_state, [rec2], day2, snap2, country_risk=NO_RISK)

    expected_drift_value = invested_value_day1 * 1.10
    assert day2_state.transactions == []  # too small a weight move to cross the rebalance threshold
    assert day2_state.open_positions[0].market_value == pytest.approx(expected_drift_value, rel=1e-2)
    assert day2_state.daily_return_pct is not None
    assert day2_state.daily_return_pct > 0  # the held position genuinely gained value
    assert day2_state.nav > day1_state.nav
    assert day2_state.benchmark_cumulative_return_pct == 0.0  # EGX30 was flat


def test_small_drift_below_threshold_does_not_trade():
    day1, day2 = date(2026, 7, 1), date(2026, 7, 2)
    rec1 = make_recommendation("COMI", day1)
    snap1 = snapshot_with_prices(day1, {"COMI": [(day1, 100.0)], "EGX30": [(day1, 100.0)]})
    day1_state = advance(None, [rec1], day1, snap1, country_risk=NO_RISK)

    # Same recommendation again -- decide_portfolio recomputes essentially
    # the same target weight, so any drift is well under the threshold.
    rec2 = make_recommendation("COMI", day2)
    snap2 = snapshot_with_prices(
        day2, {"COMI": [(day1, 100.0), (day2, 100.05)], "EGX30": [(day1, 100.0), (day2, 100.0)]}
    )
    day2_state = advance(day1_state, [rec2], day2, snap2, country_risk=NO_RISK)

    assert day2_state.transactions == []
    assert len(day2_state.open_positions) == 1


def test_exit_closes_the_position_and_records_realized_pnl():
    day1, day2 = date(2026, 7, 1), date(2026, 7, 2)
    rec1 = make_recommendation("COMI", day1)
    snap1 = snapshot_with_prices(day1, {"COMI": [(day1, 100.0)], "EGX30": [(day1, 100.0)]})
    day1_state = advance(None, [rec1], day1, snap1, country_risk=NO_RISK)
    assert day1_state.open_positions

    # A genuine, evidenced AVOID (not an evidence gap) -- this is a real
    # sell signal, unlike the abstained case below.
    rec2 = make_recommendation("COMI", day2, expected_return=-0.10)
    snap2 = snapshot_with_prices(
        day2, {"COMI": [(day1, 100.0), (day2, 120.0)], "EGX30": [(day1, 100.0), (day2, 100.0)]}
    )
    day2_state = advance(day1_state, [rec2], day2, snap2, country_risk=NO_RISK)

    assert day2_state.open_positions == []
    assert len(day2_state.closed_positions_today) == 1
    closed = day2_state.closed_positions_today[0]
    assert closed.ticker == "COMI"
    assert closed.realized_pnl_pct > 0  # exited at 120 against a 100 cost basis
    exit_transaction = next(t for t in day2_state.transactions if t.ticker == "COMI")
    assert exit_transaction.action == PositionAction.EXIT
    assert day2_state.cash == day2_state.nav  # fully in cash after the only holding exits


def test_abstained_held_ticker_is_preserved_not_liquidated():
    """CLAUDE.md's capital_allocation rule: an abstained held ticker's
    target_weight=0.0 is an evidence gap, never a real sell signal --
    treating it as one would fabricate a liquidation nothing recommended.
    The Shadow Fund must honor the same rule `CapitalAllocationEngine`
    already does."""
    day1, day2 = date(2026, 7, 1), date(2026, 7, 2)
    rec1 = make_recommendation("COMI", day1)
    snap1 = snapshot_with_prices(day1, {"COMI": [(day1, 100.0)], "EGX30": [(day1, 100.0)]})
    day1_state = advance(None, [rec1], day1, snap1, country_risk=NO_RISK)
    assert day1_state.open_positions

    # No recommendation at all on day 2 -- this is an evidence gap
    # (abstained), not a real signal to exit.
    snap2 = snapshot_with_prices(
        day2, {"COMI": [(day1, 100.0), (day2, 120.0)], "EGX30": [(day1, 100.0), (day2, 100.0)]}
    )
    day2_state = advance(day1_state, [], day2, snap2, country_risk=NO_RISK)

    assert len(day2_state.open_positions) == 1
    assert day2_state.open_positions[0].ticker == "COMI"
    assert day2_state.transactions == []
    assert day2_state.closed_positions_today == []


def test_capital_allocation_plan_is_reused_not_recomputed():
    as_of = date(2026, 7, 1)
    rec = make_recommendation("COMI", as_of)
    snapshot = snapshot_with_prices(as_of, {"COMI": [(as_of, 100.0)], "EGX30": [(as_of, 100.0)]})

    result = advance(None, [rec], as_of, snapshot, country_risk=NO_RISK)

    assert result.capital_allocation_plan is not None
    assert {r.ticker for r in result.capital_allocation_plan.ranking} == {"COMI"}


def test_risk_metrics_stay_honest_below_minimum_sample():
    as_of = date(2026, 7, 1)
    rec = make_recommendation("COMI", as_of)
    snapshot = snapshot_with_prices(as_of, {"COMI": [(as_of, 100.0)], "EGX30": [(as_of, 100.0)]})
    result = advance(
        None, [rec], as_of, snapshot, country_risk=NO_RISK,
        prior_daily_returns=[0.1] * (MIN_RISK_SAMPLE_DAYS - 2),
    )
    assert result.risk.sample_status == "insufficient_sample"
    assert result.risk.volatility_annualized_pct is None
    assert result.risk.sharpe_like_ratio is None


def test_risk_metrics_populate_once_sample_is_sufficient():
    as_of = date(2026, 7, 1)
    rec = make_recommendation("COMI", as_of)
    snapshot = snapshot_with_prices(as_of, {"COMI": [(as_of, 100.0)], "EGX30": [(as_of, 100.0)]})
    result = advance(
        None, [rec], as_of, snapshot, country_risk=NO_RISK,
        prior_daily_returns=[0.1, -0.2, 0.15, 0.05] * MIN_RISK_SAMPLE_DAYS,
        prior_nav_series=[100.0 + i for i in range(MIN_RISK_SAMPLE_DAYS)],
    )
    assert result.risk.sample_status == "sufficient"
    assert result.risk.volatility_annualized_pct is not None
    assert result.risk.max_drawdown_pct is not None


def test_attribution_sums_toward_total_gain_for_a_single_holding():
    day1, day2 = date(2026, 7, 1), date(2026, 7, 2)
    rec1 = make_recommendation("COMI", day1)
    snap1 = snapshot_with_prices(day1, {"COMI": [(day1, 100.0)], "EGX30": [(day1, 100.0)]})
    day1_state = advance(None, [rec1], day1, snap1, country_risk=NO_RISK)

    rec2 = make_recommendation("COMI", day2)
    snap2 = snapshot_with_prices(
        day2, {"COMI": [(day1, 100.0), (day2, 110.0)], "EGX30": [(day1, 100.0), (day2, 100.0)]}
    )
    day2_state = advance(day1_state, [rec2], day2, snap2, country_risk=NO_RISK)

    assert len(day2_state.attribution) == 1
    entry = day2_state.attribution[0]
    assert entry.ticker == "COMI"
    assert entry.status == "open"
    # COMI is the only holding; its contribution should fully explain the
    # fund's total gain (a fraction of 1.0, within floating-point tolerance --
    # `_pct` fields are fractions in this codebase, e.g. MAX_PRICE_ABOVE_FAIR_VALUE_PCT).
    assert entry.contribution_pct_of_total_gain == pytest.approx(1.0, rel=1e-3)
