from datetime import date, datetime

from agx_research.config import Horizon
from agx_research.decision_service.country_risk import CountryRiskAssessment, CountryRiskSeverity
from agx_research.decision_service.liquidity_floor import compute_illiquid_tickers
from agx_research.decision_service.position import PositionState
from agx_research.decision_service.service import (
    DecisionService,
    PositionAction,
)
from agx_research.domain.provenance import Provenance
from agx_research.explainability import Explanation
from agx_research.horizons.base import Prediction
from agx_research.meta.decision_engine import DecisionAction, MetaDecisionEngine, PublicationStatus

NO_RISK = CountryRiskAssessment(as_of=date(2026, 6, 14), severity=CountryRiskSeverity.NORMAL)


def make_prediction(
    ticker: str,
    expected_return: float,
    expected_risk: float,
    confidence: float,
    reference_price: float | None = 100.0,
) -> Prediction:
    return Prediction(
        ticker=ticker,
        horizon=Horizon.INVESTMENT,
        as_of=date(2026, 6, 14),
        model_id="investment_alpha",
        model_version="0.1.0",
        expected_return=expected_return,
        expected_risk=expected_risk,
        confidence=confidence,
        reference_price=reference_price,
        explanation=Explanation(why_this_stock="test", why_now="test", why_not_others="test"),
        supporting_knowledge_ids=["know-1"],
        provenance=Provenance(produced_by="investment_alpha@0.1.0", produced_at=datetime.now()),
    )


def make_publication_ready_recommendation(
    ticker: str, expected_return: float = 0.10, expected_risk: float = 0.05, confidence: float = 0.8
):
    """A real Recommendation, built the same way `MetaDecisionEngine` always
    builds one (not a hand-constructed fake), with its INVESTMENT decision
    manually promoted to publication-ready -- the exact pattern
    `test_runtime_and_intelligence.py`'s own portfolio-construction test
    already uses for `PortfolioConstructor`, since a real end-to-end
    publication gate needs 30 evaluated decisions and legal approval that
    no unit test can honestly provide."""
    prediction = make_prediction(ticker, expected_return, expected_risk, confidence)
    recommendation = MetaDecisionEngine().decide(ticker, date(2026, 6, 14), {Horizon.INVESTMENT: prediction})
    assert recommendation is not None
    decision = recommendation.horizon_decisions[Horizon.INVESTMENT]
    assert decision.action == DecisionAction.BUY_CANDIDATE  # sanity: score >= 1.0 threshold cleared
    decision.publication_status = PublicationStatus.PUBLICATION_READY
    return recommendation


def make_research_only_recommendation(ticker: str):
    """A real Recommendation whose decision never clears publication --
    the default, honest state for almost everything today."""
    prediction = make_prediction(ticker, 0.10, 0.05, 0.8)
    recommendation = MetaDecisionEngine().decide(ticker, date(2026, 6, 14), {Horizon.INVESTMENT: prediction})
    assert recommendation.horizon_decisions[Horizon.INVESTMENT].publication_status == PublicationStatus.RESEARCH_ONLY
    return recommendation


def test_buy_when_no_position_and_positive_publication_ready_signal():
    rec = make_publication_ready_recommendation("COMI")
    decisions = DecisionService().decide_portfolio(
        [rec], positions={}, as_of=date(2026, 6, 14), country_risk=NO_RISK
    )
    assert len(decisions) == 1
    decision = decisions[0]
    assert decision.action == PositionAction.BUY
    assert decision.target_weight > 0
    assert not decision.abstained
    assert decision.explanation.why_this_stock


def test_research_only_recommendation_never_produces_a_position():
    rec = make_research_only_recommendation("COMI")
    decisions = DecisionService().decide_portfolio(
        [rec], positions={}, as_of=date(2026, 6, 14), country_risk=NO_RISK
    )
    assert decisions[0].action == PositionAction.NO_ACTION
    assert decisions[0].target_weight == 0.0


def test_increase_when_held_below_cap_and_signal_still_positive():
    rec = make_publication_ready_recommendation("COMI")
    position = PositionState(ticker="COMI", held=True, current_weight=0.01)
    decisions = DecisionService(max_position_weight=0.25).decide_portfolio(
        [rec], positions={"COMI": position}, as_of=date(2026, 6, 14), country_risk=NO_RISK
    )
    decision = decisions[0]
    assert decision.action == PositionAction.INCREASE_POSITION
    assert decision.target_weight > position.current_weight


def test_hold_when_held_and_target_matches_current_weight():
    rec = make_publication_ready_recommendation("COMI")
    target = rec.horizon_decisions[Horizon.INVESTMENT].max_position_pct
    # Force target_weight to equal current_weight by capping at the exact
    # score-derived weight (single ticker -> full weight, capped by
    # max_position_weight only).
    service = DecisionService(max_position_weight=target if target > 0 else 0.05)
    position = PositionState(ticker="COMI", held=True, current_weight=service.max_position_weight)
    decisions = service.decide_portfolio(
        [rec], positions={"COMI": position}, as_of=date(2026, 6, 14), country_risk=NO_RISK
    )
    assert decisions[0].action == PositionAction.HOLD


def test_exit_when_held_and_no_fresh_investment_horizon_evidence():
    position = PositionState(ticker="COMI", held=True, current_weight=0.05)
    decisions = DecisionService().decide_portfolio(
        [], positions={"COMI": position}, as_of=date(2026, 6, 14), country_risk=NO_RISK
    )
    decision = decisions[0]
    assert decision.abstained
    assert decision.action == PositionAction.HOLD  # abstain overlay while held, never a forced sell


def test_reduce_when_held_and_signal_weakens_but_stays_positive():
    strong = make_publication_ready_recommendation("COMI", expected_return=0.30, expected_risk=0.05)
    weak = make_publication_ready_recommendation("MFPC", expected_return=0.08, expected_risk=0.05)
    # Two competing tickers: COMI's larger relative score shrinks MFPC's
    # normalized share below MFPC's current (previously larger) weight.
    positions = {
        "MFPC": PositionState(ticker="MFPC", held=True, current_weight=0.24),
    }
    decisions = DecisionService(max_position_weight=0.25).decide_portfolio(
        [strong, weak], positions=positions, as_of=date(2026, 6, 14), country_risk=NO_RISK
    )
    mfpc = next(d for d in decisions if d.ticker == "MFPC")
    assert mfpc.action == PositionAction.REDUCE_POSITION
    assert 0 < mfpc.target_weight < mfpc.current_weight


def test_liquidity_floor_overrides_a_positive_signal_to_no_action():
    rec = make_publication_ready_recommendation("COMI")
    decisions = DecisionService().decide_portfolio(
        [rec],
        positions={},
        as_of=date(2026, 6, 14),
        country_risk=NO_RISK,
        illiquid_tickers={"COMI"},
    )
    decision = decisions[0]
    assert decision.action == PositionAction.NO_ACTION
    assert decision.target_weight == 0.0
    assert any("liquidity" in reason.lower() for reason in decision.reasons)


def test_liquidity_floor_forces_exit_for_a_held_illiquid_position():
    rec = make_publication_ready_recommendation("COMI")
    position = PositionState(ticker="COMI", held=True, current_weight=0.05)
    decisions = DecisionService().decide_portfolio(
        [rec],
        positions={"COMI": position},
        as_of=date(2026, 6, 14),
        country_risk=NO_RISK,
        illiquid_tickers={"COMI"},
    )
    assert decisions[0].action == PositionAction.EXIT


def test_country_risk_crisis_forces_exit_regardless_of_signal_strength():
    rec = make_publication_ready_recommendation("COMI", expected_return=0.50, expected_risk=0.01, confidence=0.99)
    position = PositionState(ticker="COMI", held=True, current_weight=0.05)
    crisis = CountryRiskAssessment(
        as_of=date(2026, 6, 14), severity=CountryRiskSeverity.CRISIS, reasons=["Moody's downgrade"]
    )
    decisions = DecisionService().decide_portfolio(
        [rec], positions={"COMI": position}, as_of=date(2026, 6, 14), country_risk=crisis
    )
    decision = decisions[0]
    assert decision.action == PositionAction.EXIT
    assert any("downgrade" in reason.lower() for reason in decision.reasons)


def test_country_risk_crisis_forces_no_action_for_unheld_ticker():
    rec = make_publication_ready_recommendation("COMI", expected_return=0.50, expected_risk=0.01, confidence=0.99)
    crisis = CountryRiskAssessment(as_of=date(2026, 6, 14), severity=CountryRiskSeverity.CRISIS)
    decisions = DecisionService().decide_portfolio(
        [rec], positions={}, as_of=date(2026, 6, 14), country_risk=crisis
    )
    assert decisions[0].action == PositionAction.NO_ACTION


def test_invalid_max_position_weight_rejected():
    import pytest

    with pytest.raises(ValueError):
        DecisionService(max_position_weight=0.0)
    with pytest.raises(ValueError):
        DecisionService(max_position_weight=1.5)


def test_liquidity_floor_helper_flags_thin_and_no_history_tickers():
    from agx_research.data.mock_provider import MockDataProvider
    from agx_research.data.snapshot import build_snapshot
    from pathlib import Path

    mock_root = Path(__file__).resolve().parents[1] / "data" / "mock"
    snapshot = build_snapshot(
        MockDataProvider(mock_root),
        tickers=["COMI", "MFPC", "NOSUCHTICKER"],
        macro_series_ids=[],
        as_of=date(2026, 6, 14),
        lookback_days=30,
    )
    illiquid = compute_illiquid_tickers(snapshot, min_average_traded_value=1e18)
    assert {"COMI", "MFPC"} <= illiquid  # threshold set absurdly high -> everything flagged
    assert "NOSUCHTICKER" in illiquid  # no price history at all -> illiquid, never assumed tradable

    permissive = compute_illiquid_tickers(snapshot, min_average_traded_value=0.0)
    assert "NOSUCHTICKER" in permissive  # still illiquid: no history, regardless of floor
    assert "COMI" not in permissive
