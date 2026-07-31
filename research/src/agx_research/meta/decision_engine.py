"""The Meta Decision Engine: the only component allowed to combine outputs
from the three independent horizon models into a single recommendation.

The combination strategy here (a confidence-weighted average per horizon
weight) is a placeholder — a simple, transparent starting point, not a
validated decision rule. Principle 6 ("AI proposes, evidence approves")
means whatever combination logic replaces this should itself be backed by
evidence that it improves outcomes versus simpler alternatives, not just
intuition about what weights "feel right."
"""

from __future__ import annotations

from datetime import date, datetime, timedelta
from enum import Enum

from pydantic import BaseModel, Field

from agx_research.config import HORIZON_WINDOWS, Horizon
from agx_research.domain.provenance import Provenance, ProvenanceRef
from agx_research.explainability import Explanation
from agx_research.horizons.base import Prediction


class DecisionAction(str, Enum):
    """Research actions, deliberately distinct from personalized advice."""

    BUY_CANDIDATE = "buy_candidate"
    WATCH = "watch"
    AVOID = "avoid"
    ABSTAIN = "abstain"


class PublicationStatus(str, Enum):
    RESEARCH_ONLY = "research_only"
    PUBLICATION_READY = "publication_ready"


class PriceConditionOperator(str, Enum):
    AT_OR_BELOW = "at_or_below"
    BELOW = "below"
    NOT_APPLICABLE = "not_applicable"


class HorizonDecision(BaseModel):
    """One executable-looking but research-only decision for exactly one horizon.

    Horizons are never blended here: return, risk, validity and invalidation
    retain the unit and window of their originating prediction.
    """

    horizon: Horizon
    horizon_window: str
    action: DecisionAction
    expected_return: float
    expected_risk: float
    risk_metric: str = "model_expected_risk_for_horizon"
    confidence: float
    risk_adjusted_score: float
    valid_until: date
    entry_condition: str
    reference_price: float | None = Field(default=None, gt=0)
    entry_operator: PriceConditionOperator = PriceConditionOperator.NOT_APPLICABLE
    entry_value: float | None = Field(default=None, gt=0)
    invalidation_operator: PriceConditionOperator = PriceConditionOperator.NOT_APPLICABLE
    invalidation_value: float | None = Field(default=None, gt=0)
    review_condition: str
    invalidation_conditions: list[str] = Field(default_factory=list)
    max_position_pct: float = 0.0
    publication_status: PublicationStatus = PublicationStatus.RESEARCH_ONLY
    abstention_reasons: list[str] = Field(default_factory=list)
    evidence_refs: list[ProvenanceRef] = Field(default_factory=list)


class Recommendation(BaseModel):
    """A final, explainable output combining every available horizon's prediction.

    Never constructed without an Explanation — see Principle 3. `provenance`
    links back to every contributing prediction's model and to every
    supporting knowledge object, so the full chain from recommendation back
    to raw data is walkable via repository lookups.
    """

    ticker: str
    as_of: date
    combined_expected_return: float
    combined_expected_risk: float
    confidence: float
    horizon_predictions: dict[Horizon, Prediction]
    horizon_decisions: dict[Horizon, HorizonDecision]
    supporting_knowledge_ids: list[str] = Field(default_factory=list)
    explanation: Explanation
    provenance: Provenance


DEFAULT_HORIZON_WEIGHTS: dict[Horizon, float] = {
    Horizon.MICRO: 1.0,
    Horizon.SWING: 1.0,
    Horizon.INVESTMENT: 1.0,
}


class MetaDecisionEngine:
    """Combines per-horizon predictions into one explainable recommendation."""

    def __init__(self, horizon_weights: dict[Horizon, float] | None = None):
        self.horizon_weights = horizon_weights or DEFAULT_HORIZON_WEIGHTS

    def decide(
        self, ticker: str, as_of: date, predictions: dict[Horizon, Prediction]
    ) -> Recommendation | None:
        """Combine whichever horizon predictions are available for `ticker`.

        Returns None if there are no predictions to combine — the engine
        never fabricates a recommendation from nothing.
        """
        if not predictions:
            return None

        total_weight = 0.0
        weighted_return = 0.0
        weighted_risk = 0.0
        weighted_confidence = 0.0
        knowledge_ids: list[str] = []

        horizon_decisions = {
            horizon: self._decision_for_prediction(prediction)
            for horizon, prediction in predictions.items()
        }

        for horizon, prediction in predictions.items():
            weight = self.horizon_weights.get(horizon, 0.0) * prediction.confidence
            total_weight += weight
            weighted_return += weight * prediction.expected_return
            weighted_risk += weight * prediction.expected_risk
            weighted_confidence += weight * prediction.confidence
            knowledge_ids.extend(prediction.supporting_knowledge_ids)

        if total_weight == 0:
            return None

        combined_return = weighted_return / total_weight
        combined_risk = weighted_risk / total_weight
        combined_confidence = weighted_confidence / total_weight

        explanation = Explanation(
            why_this_stock=(
                f"Models across {len(predictions)} horizon(s) "
                f"({', '.join(_horizon_label(h) for h in predictions)}) found supporting evidence for {ticker}."
            ),
            why_now=f"Based on knowledge and market data available through {as_of.isoformat()}.",
            why_not_others=(
                "This engine only combines available predictions; comparison against other "
                "stocks happens at the market-wide ranking stage."
            ),
            supporting_evidence=[
                f"{_horizon_label(h)}: expected_return={p.expected_return:.4f}, "
                f"expected_risk={p.expected_risk:.4f}, confidence={p.confidence:.2f}"
                for h, p in predictions.items()
            ]
            + [
                evidence
                for prediction in predictions.values()
                for evidence in prediction.explanation.supporting_evidence
            ],
            evidence_refs=[
                ProvenanceRef(kind="knowledge", ref_id=knowledge_id)
                for knowledge_id in sorted(set(knowledge_ids))
            ]
            + [
                ref
                for prediction in predictions.values()
                for ref in prediction.explanation.evidence_refs
                if ref.kind != "knowledge"
            ],
            similar_historical_cases=[],
            invalidation_conditions=[
                "The underlying knowledge is retired, or its performance record falls below the acceptance threshold."
            ],
        )

        return Recommendation(
            ticker=ticker,
            as_of=as_of,
            combined_expected_return=combined_return,
            combined_expected_risk=combined_risk,
            confidence=combined_confidence,
            horizon_predictions=predictions,
            horizon_decisions=horizon_decisions,
            supporting_knowledge_ids=sorted(set(knowledge_ids)),
            explanation=explanation,
            provenance=Provenance(
                produced_by="meta_decision_engine",
                produced_at=datetime.now(),
                inputs=[
                    ProvenanceRef(
                        kind="prediction", ref_id=f"{p.model_id}@{p.model_version}:{h.value}"
                    )
                    for h, p in predictions.items()
                ]
                + [
                    ProvenanceRef(kind="knowledge", ref_id=kid)
                    for kid in sorted(set(knowledge_ids))
                ]
                + [
                    ref
                    for prediction in predictions.values()
                    for ref in prediction.provenance.inputs
                    if ref.kind != "knowledge"
                ],
            ),
        )

    @staticmethod
    def _decision_for_prediction(prediction: Prediction) -> HorizonDecision:
        """Translate one prediction into a transparent research action.

        This is intentionally conservative. It never emits personalized advice
        and keeps publication blocked until legal review and validated live data
        are represented by an explicit future publication gate.
        """
        risk = max(prediction.expected_risk, 1e-9)
        score = prediction.expected_return * prediction.confidence / risk
        abstention_reasons: list[str] = []
        if prediction.confidence < 0.60:
            action = DecisionAction.ABSTAIN
            abstention_reasons.append("Confidence is below the research threshold of 60%.")
        elif prediction.expected_return <= 0:
            action = DecisionAction.AVOID
        elif score >= 1.0:
            action = DecisionAction.BUY_CANDIDATE
        else:
            action = DecisionAction.WATCH

        if action == DecisionAction.BUY_CANDIDATE and prediction.reference_price is None:
            action = DecisionAction.ABSTAIN
            abstention_reasons.append(
                "No recent, positive reference price is attached to this prediction."
            )

        reference_price = prediction.reference_price
        entry_value = reference_price if action == DecisionAction.BUY_CANDIDATE else None
        risk_buffer = min(0.25, max(0.02, prediction.expected_risk))
        invalidation_value = (
            reference_price * (1.0 - risk_buffer)
            if action == DecisionAction.BUY_CANDIDATE and reference_price is not None
            else None
        )
        if action == DecisionAction.BUY_CANDIDATE:
            entry_condition = (
                f"Average close at or below EGP {entry_value:.2f}, while the evidence "
                "and publication gate remain valid."
            )
            review_condition = (
                f"Reviewed at EGP {reference_price * (1 + max(0.0, prediction.expected_return)):.2f} "
                "or upon expiry, whichever comes first."
            )
        else:
            entry_condition = "No executable entry while the decision is not a buy candidate."
            review_condition = "Reviewed when new evidence emerges or upon expiry."

        validity_days = {
            Horizon.MICRO: 3,
            Horizon.SWING: 28,
            Horizon.INVESTMENT: 183,
        }[prediction.horizon]
        return HorizonDecision(
            horizon=prediction.horizon,
            horizon_window=HORIZON_WINDOWS[prediction.horizon],
            action=action,
            expected_return=prediction.expected_return,
            expected_risk=prediction.expected_risk,
            confidence=prediction.confidence,
            risk_adjusted_score=score,
            valid_until=prediction.as_of + timedelta(days=validity_days),
            entry_condition=entry_condition,
            reference_price=reference_price,
            entry_operator=(
                PriceConditionOperator.AT_OR_BELOW
                if entry_value is not None else PriceConditionOperator.NOT_APPLICABLE
            ),
            entry_value=entry_value,
            invalidation_operator=(
                PriceConditionOperator.BELOW
                if invalidation_value is not None else PriceConditionOperator.NOT_APPLICABLE
            ),
            invalidation_value=invalidation_value,
            review_condition=review_condition,
            invalidation_conditions=list(prediction.explanation.invalidation_conditions)
            + ([f"Average close below EGP {invalidation_value:.2f}."] if invalidation_value else []),
            max_position_pct=0.0,
            abstention_reasons=abstention_reasons,
            evidence_refs=list(prediction.explanation.evidence_refs),
        )


def _horizon_label(horizon: Horizon) -> str:
    return {
        Horizon.MICRO: "Micro",
        Horizon.SWING: "Swing",
        Horizon.INVESTMENT: "Investment",
    }[horizon]
