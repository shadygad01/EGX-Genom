from datetime import date, datetime

from agx_research.config import Horizon
from agx_research.domain.provenance import Provenance
from agx_research.explainability import Explanation
from agx_research.horizons.base import Prediction
from agx_research.meta.decision_engine import (
    DecisionAction,
    MetaDecisionEngine,
    PublicationStatus,
)


def make_prediction(horizon: Horizon, expected_return: float, expected_risk: float,
                     confidence: float, knowledge_id: str) -> Prediction:
    return Prediction(
        ticker="COMI",
        horizon=horizon,
        as_of=date(2026, 6, 14),
        model_id=f"{horizon.value}_alpha",
        model_version="0.1.0",
        expected_return=expected_return,
        expected_risk=expected_risk,
        confidence=confidence,
        reference_price=100.0,
        explanation=Explanation(
            why_this_stock="test",
            why_now="test",
            why_not_others="test",
        ),
        supporting_knowledge_ids=[knowledge_id],
        provenance=Provenance(produced_by=f"{horizon.value}_alpha@0.1.0", produced_at=datetime.now()),
    )


def test_returns_none_with_no_predictions():
    engine = MetaDecisionEngine()
    assert engine.decide("COMI", date(2026, 6, 14), {}) is None


def test_combines_single_horizon_prediction():
    engine = MetaDecisionEngine()
    prediction = make_prediction(Horizon.MICRO, 0.02, 0.01, 0.8, "know-1")

    recommendation = engine.decide("COMI", date(2026, 6, 14), {Horizon.MICRO: prediction})

    assert recommendation is not None
    assert recommendation.combined_expected_return == 0.02
    assert recommendation.supporting_knowledge_ids == ["know-1"]
    assert recommendation.explanation.why_this_stock
    assert recommendation.explanation.evidence_refs == [
        recommendation.explanation.evidence_refs[0]
    ]
    assert recommendation.explanation.evidence_refs[0].ref_id == "know-1"
    assert recommendation.provenance.produced_by == "meta_decision_engine"
    decision = recommendation.horizon_decisions[Horizon.MICRO]
    assert decision.action == DecisionAction.BUY_CANDIDATE
    assert decision.horizon_window == "1-3 trading days"
    assert decision.publication_status == PublicationStatus.RESEARCH_ONLY
    assert decision.valid_until == date(2026, 6, 17)
    assert decision.entry_operator.value == "at_or_below"
    assert decision.entry_value == 100.0
    assert decision.invalidation_value == 98.0


def test_buy_signal_without_reference_price_abstains():
    prediction = make_prediction(Horizon.MICRO, 0.02, 0.01, 0.8, "know-1")
    prediction.reference_price = None
    recommendation = MetaDecisionEngine().decide(
        "COMI", date(2026, 6, 14), {Horizon.MICRO: prediction}
    )
    assert recommendation is not None
    decision = recommendation.horizon_decisions[Horizon.MICRO]
    assert decision.action == DecisionAction.ABSTAIN
    assert decision.entry_value is None
    assert "سعر مرجعي" in " ".join(decision.abstention_reasons)


def test_executable_decision_language_is_arabic():
    prediction = make_prediction(Horizon.MICRO, 0.02, 0.01, 0.8, "know-1")
    recommendation = MetaDecisionEngine().decide(
        "COMI", date(2026, 6, 14), {Horizon.MICRO: prediction}
    )
    assert recommendation is not None
    decision = recommendation.horizon_decisions[Horizon.MICRO]
    assert "جنيه" in decision.entry_condition
    assert "تُراجع" in decision.review_condition
    assert "استنادًا" in recommendation.explanation.why_now
    assert "العائد المتوقع" in recommendation.explanation.supporting_evidence[0]


def test_combines_multiple_horizons_weighted_by_confidence():
    engine = MetaDecisionEngine()
    predictions = {
        Horizon.MICRO: make_prediction(Horizon.MICRO, 0.02, 0.01, 1.0, "know-1"),
        Horizon.SWING: make_prediction(Horizon.SWING, 0.10, 0.05, 0.0, "know-2"),
    }

    recommendation = engine.decide("COMI", date(2026, 6, 14), predictions)

    # SWING has zero confidence so its weight is zero -> result should equal MICRO alone.
    assert recommendation is not None
    assert round(recommendation.combined_expected_return, 6) == 0.02
    assert set(recommendation.supporting_knowledge_ids) == {"know-1", "know-2"}
    assert len(recommendation.provenance.inputs) == 4  # 2 predictions + 2 knowledge refs


def test_low_confidence_horizon_abstains_without_affecting_other_horizons():
    engine = MetaDecisionEngine()
    predictions = {
        Horizon.MICRO: make_prediction(Horizon.MICRO, 0.03, 0.01, 0.80, "know-1"),
        Horizon.INVESTMENT: make_prediction(
            Horizon.INVESTMENT, 0.20, 0.10, 0.40, "know-2"
        ),
    }

    recommendation = engine.decide("COMI", date(2026, 6, 14), predictions)

    assert recommendation is not None
    assert recommendation.horizon_decisions[Horizon.MICRO].action == DecisionAction.BUY_CANDIDATE
    assert recommendation.horizon_decisions[Horizon.MICRO].max_position_pct == 0
    assert recommendation.horizon_decisions[Horizon.MICRO].publication_status.value == "research_only"
    long_decision = recommendation.horizon_decisions[Horizon.INVESTMENT]
    assert long_decision.action == DecisionAction.ABSTAIN
    assert long_decision.max_position_pct == 0
    assert long_decision.abstention_reasons
