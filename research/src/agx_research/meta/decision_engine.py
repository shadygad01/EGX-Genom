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

from datetime import date, datetime

from pydantic import BaseModel, Field

from agx_research.config import Horizon
from agx_research.domain.provenance import Provenance, ProvenanceRef
from agx_research.explainability import Explanation
from agx_research.horizons.base import Prediction


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
                f"{len(predictions)} horizon model(s) "
                f"({', '.join(h.value for h in predictions)}) found supporting evidence for {ticker}."
            ),
            why_now=f"Based on knowledge and market data available as of {as_of.isoformat()}.",
            why_not_others=(
                "This engine only combines predictions it was given; it does not "
                "rank against other tickers by itself — that comparison happens "
                "upstream, across every ticker's Recommendation."
            ),
            supporting_evidence=[
                f"{h.value}: expected_return={p.expected_return:.4f}, "
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
                "Underlying knowledge is retired or its performance history degrades below threshold."
            ],
        )

        return Recommendation(
            ticker=ticker,
            as_of=as_of,
            combined_expected_return=combined_return,
            combined_expected_risk=combined_risk,
            confidence=combined_confidence,
            horizon_predictions=predictions,
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
