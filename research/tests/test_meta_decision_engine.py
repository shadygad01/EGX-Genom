from datetime import date

from agx_research.config import Horizon
from agx_research.explainability import Explanation
from agx_research.horizons.base import Prediction
from agx_research.meta.decision_engine import MetaDecisionEngine


def make_prediction(horizon: Horizon, expected_return: float, expected_risk: float,
                     confidence: float, knowledge_id: str) -> Prediction:
    return Prediction(
        ticker="COMI",
        horizon=horizon,
        as_of=date(2026, 6, 14),
        expected_return=expected_return,
        expected_risk=expected_risk,
        confidence=confidence,
        explanation=Explanation(
            why_this_stock="test",
            why_now="test",
            why_not_others="test",
        ),
        supporting_knowledge_ids=[knowledge_id],
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
