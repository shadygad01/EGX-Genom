from datetime import date

from agx_research.config import HORIZON_WINDOWS, Horizon
from agx_research.domain.provenance import Provenance, ProvenanceRef
from agx_research.explainability import Explanation
from agx_research.horizons.base import Prediction
from agx_research.meta.decision_engine import (
    DecisionAction,
    HorizonDecision,
    PriceConditionOperator,
    PublicationStatus,
    Recommendation,
)
from agx_research.meta.decision_quality import apply_decision_quality_gate, evaluate_decision_quality

AS_OF = date(2026, 6, 14)


def complete_explanation(**overrides) -> Explanation:
    defaults = dict(
        why_this_stock="Real evidence supports this ticker.",
        why_now="Fresh evidence as of today.",
        why_not_others="Ranked against the rest of the universe elsewhere.",
        supporting_evidence=["revenue grew 12% YoY"],
        evidence_refs=[ProvenanceRef(kind="knowledge", ref_id="know-1")],
        invalidation_conditions=["Revenue growth reverses for two consecutive quarters."],
    )
    defaults.update(overrides)
    return Explanation(**defaults)


def buy_decision(**overrides) -> HorizonDecision:
    defaults = dict(
        horizon=Horizon.INVESTMENT,
        horizon_window=HORIZON_WINDOWS[Horizon.INVESTMENT],
        action=DecisionAction.BUY_CANDIDATE,
        expected_return=0.10,
        expected_risk=0.05,
        confidence=0.8,
        risk_adjusted_score=1.6,
        valid_until=date(2026, 12, 1),
        entry_condition="Average close at or below EGP 100.00.",
        reference_price=100.0,
        entry_operator=PriceConditionOperator.AT_OR_BELOW,
        entry_value=100.0,
        invalidation_operator=PriceConditionOperator.BELOW,
        invalidation_value=95.0,
        review_condition="Reviewed at EGP 110.00 or upon expiry.",
        invalidation_conditions=["Average close below EGP 95.00."],
    )
    defaults.update(overrides)
    return HorizonDecision(**defaults)


def test_complete_evidenced_decision_passes_every_check():
    report = evaluate_decision_quality("COMI", buy_decision(), complete_explanation())
    assert report.passed is True
    assert all(check.passed for check in report.checks)


def test_missing_evidence_fails_the_gate():
    explanation = complete_explanation(supporting_evidence=[], evidence_refs=[])
    report = evaluate_decision_quality("COMI", buy_decision(), explanation)
    assert report.passed is False
    assert next(c for c in report.checks if c.id == "evidence_present").passed is False


def test_incomplete_thesis_fails_the_gate():
    explanation = complete_explanation(why_now="")
    report = evaluate_decision_quality("COMI", buy_decision(), explanation)
    assert report.passed is False
    assert next(c for c in report.checks if c.id == "thesis_complete").passed is False


def test_no_invalidation_condition_fails_the_gate():
    decision = buy_decision(invalidation_conditions=[])
    report = evaluate_decision_quality("COMI", decision, complete_explanation())
    assert report.passed is False
    assert next(c for c in report.checks if c.id == "invalidation_defined").passed is False


def test_blank_monitoring_conditions_fail_the_gate():
    decision = buy_decision(review_condition="")
    report = evaluate_decision_quality("COMI", decision, complete_explanation())
    assert report.passed is False
    assert next(c for c in report.checks if c.id == "monitoring_defined").passed is False


def test_buy_candidate_without_numeric_levels_is_internally_inconsistent():
    decision = buy_decision(
        entry_value=None, invalidation_value=None,
        entry_operator=PriceConditionOperator.NOT_APPLICABLE,
        invalidation_operator=PriceConditionOperator.NOT_APPLICABLE,
    )
    report = evaluate_decision_quality("COMI", decision, complete_explanation())
    assert report.passed is False
    assert next(c for c in report.checks if c.id == "internal_consistency").passed is False


def test_non_buy_action_never_needs_numeric_levels():
    decision = buy_decision(
        action=DecisionAction.WATCH, entry_value=None, invalidation_value=None,
        entry_operator=PriceConditionOperator.NOT_APPLICABLE,
        invalidation_operator=PriceConditionOperator.NOT_APPLICABLE,
    )
    report = evaluate_decision_quality("COMI", decision, complete_explanation())
    assert next(c for c in report.checks if c.id == "internal_consistency").passed is True


def _recommendation(action: DecisionAction, explanation: Explanation) -> Recommendation:
    decision = buy_decision(action=action)
    prediction = Prediction(
        ticker="COMI", horizon=Horizon.INVESTMENT, as_of=AS_OF,
        model_id="test", model_version="1",
        expected_return=0.10, expected_risk=0.05, confidence=0.8,
        reference_price=100.0, explanation=explanation,
        provenance=Provenance(produced_by="test", produced_at=AS_OF.isoformat()),
    )
    return Recommendation(
        ticker="COMI", as_of=AS_OF, combined_expected_return=0.10, combined_expected_risk=0.05,
        confidence=0.8, horizon_predictions={Horizon.INVESTMENT: prediction},
        horizon_decisions={Horizon.INVESTMENT: decision},
        explanation=explanation,
        provenance=Provenance(produced_by="test", produced_at=AS_OF.isoformat()),
    )


def test_apply_decision_quality_gate_marks_a_complete_buy_publication_ready():
    recommendation = _recommendation(DecisionAction.BUY_CANDIDATE, complete_explanation())
    [gated] = apply_decision_quality_gate([recommendation])
    decision = gated.horizon_decisions[Horizon.INVESTMENT]
    assert decision.publication_status == PublicationStatus.PUBLICATION_READY
    assert decision.max_position_pct > 0.0


def test_apply_decision_quality_gate_never_publishes_an_incomplete_decision():
    # No evidence at all -- the exact real gap that used to slip through
    # when only a system-wide track-record/legal switch gated everything.
    incomplete = complete_explanation(supporting_evidence=[], evidence_refs=[])
    recommendation = _recommendation(DecisionAction.BUY_CANDIDATE, incomplete)
    [gated] = apply_decision_quality_gate([recommendation])
    decision = gated.horizon_decisions[Horizon.INVESTMENT]
    assert decision.publication_status == PublicationStatus.RESEARCH_ONLY
    assert decision.max_position_pct == 0.0
    assert decision.abstention_reasons  # names the real reason, never silent


def test_apply_decision_quality_gate_never_publishes_an_abstain():
    recommendation = _recommendation(DecisionAction.ABSTAIN, complete_explanation())
    [gated] = apply_decision_quality_gate([recommendation])
    decision = gated.horizon_decisions[Horizon.INVESTMENT]
    assert decision.publication_status == PublicationStatus.RESEARCH_ONLY


def test_quality_is_evaluated_independently_per_horizon():
    """One horizon's complete evidence never rescues a sibling horizon's
    incomplete one -- the entire point of moving from one system-wide
    switch to a per-decision gate."""
    good = complete_explanation()
    bad = complete_explanation(supporting_evidence=[], evidence_refs=[])
    micro_decision = buy_decision(horizon=Horizon.MICRO, horizon_window=HORIZON_WINDOWS[Horizon.MICRO])
    swing_decision = buy_decision(horizon=Horizon.SWING, horizon_window=HORIZON_WINDOWS[Horizon.SWING])
    micro_prediction = Prediction(
        ticker="COMI", horizon=Horizon.MICRO, as_of=AS_OF, model_id="test", model_version="1",
        expected_return=0.10, expected_risk=0.05, confidence=0.8, reference_price=100.0,
        explanation=good, provenance=Provenance(produced_by="test", produced_at=AS_OF.isoformat()),
    )
    swing_prediction = Prediction(
        ticker="COMI", horizon=Horizon.SWING, as_of=AS_OF, model_id="test", model_version="1",
        expected_return=0.10, expected_risk=0.05, confidence=0.8, reference_price=100.0,
        explanation=bad, provenance=Provenance(produced_by="test", produced_at=AS_OF.isoformat()),
    )
    recommendation = Recommendation(
        ticker="COMI", as_of=AS_OF, combined_expected_return=0.10, combined_expected_risk=0.05,
        confidence=0.8,
        horizon_predictions={Horizon.MICRO: micro_prediction, Horizon.SWING: swing_prediction},
        horizon_decisions={Horizon.MICRO: micro_decision, Horizon.SWING: swing_decision},
        explanation=good,
        provenance=Provenance(produced_by="test", produced_at=AS_OF.isoformat()),
    )
    [gated] = apply_decision_quality_gate([recommendation])
    assert gated.horizon_decisions[Horizon.MICRO].publication_status == PublicationStatus.PUBLICATION_READY
    assert gated.horizon_decisions[Horizon.SWING].publication_status == PublicationStatus.RESEARCH_ONLY
