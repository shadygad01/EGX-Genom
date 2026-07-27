"""Knowledge-weighted horizon models: predictions derived exclusively from
validated, promoted knowledge.

`predict()` aggregates every non-retired `KnowledgeObject` for the ticker
and horizon, weighting each by its (evidence-derived, adversarially
adjusted) confidence. No knowledge means no prediction — the model returns
None rather than guessing, which is Principle 1 ("no recommendation
without evidence") executing at the model layer.

This is deliberately not a trained statistical model. Training one needs
years of real market data (a business-blocked dependency); until then this
is the honest v1: it adds no information of its own, it only aggregates
what survived the full validation pipeline. The Epoch I stubs
(`MicroAlphaModel` etc.) remain reserved for future trained models.
"""

from __future__ import annotations

from datetime import date, datetime

from agx_research.config import Horizon
from agx_research.domain.provenance import Provenance, ProvenanceRef
from agx_research.events.event import Event, EventSeverity
from agx_research.events.lifecycle import EventStatus
from agx_research.events.service import EventPlatform
from agx_research.explainability import Explanation
from agx_research.explainability.historical_cases import find_similar_cases
from agx_research.horizons.base import HorizonModel, Prediction
from agx_research.knowledge import KnowledgeObject
from agx_research.knowledge.lifecycle import KnowledgeStatus

_EGX_MARKET_ENTITY_ID = "EGX"


def _event_headline(event: Event) -> str:
    """A quoted headline prefix for a supporting-evidence line, or "" if the
    event carries none. Without this, an event's line in `supporting_evidence`
    was only its opaque id + category/severity/confidence -- real, but
    unreadable to a human deciding whether the evidence is actually relevant.
    The headline itself already exists on news-derived events
    (`events.adapters` sets `metadata["headline"]`); this only surfaces it,
    it never invents one for an event that doesn't carry it.
    """
    headline = event.metadata.get("headline")
    return f'"{headline}" ' if headline else ""


class KnowledgeWeightedHorizonModel(HorizonModel):
    model_id = "knowledge_weighted"
    model_version = "1.0.0"

    def __init__(self, horizon: Horizon, *, event_platform: EventPlatform | None = None):
        self.horizon = horizon
        self.event_platform = event_platform

    def predict(
        self, ticker: str, as_of: date, knowledge: list[KnowledgeObject]
    ) -> Prediction | None:
        relevant = [
            k
            for k in knowledge
            if k.horizon == self.horizon
            and ticker in k.affected_assets
            and k.status != KnowledgeStatus.RETIRED
            and k.confidence > 0
        ]
        if not relevant:
            return None  # no evidence, no prediction -- never guess

        total_weight = sum(k.confidence for k in relevant)
        expected_return = sum(k.confidence * k.expected_return for k in relevant) / total_weight
        expected_risk = sum(k.confidence * k.expected_risk for k in relevant) / total_weight
        # Aggregate confidence is the weighted mean, never more than the
        # strongest single piece of knowledge -- combining evidence must
        # not fabricate certainty beyond what any source claimed.
        confidence = min(total_weight / len(relevant), max(k.confidence for k in relevant))

        similar_cases = (
            find_similar_cases(self.event_platform, ticker, before=as_of)
            if self.event_platform is not None
            else []
        )
        active_events = []
        if self.event_platform is not None:
            candidate_events = {
                event.id: event
                for canonical_id in (ticker, _EGX_MARKET_ENTITY_ID)
                for event in self.event_platform.events_for_entity(canonical_id)
            }.values()
            active_events = [
                event
                for event in candidate_events
                if event.event_date <= as_of
                and (as_of - event.event_date).days <= 30
                and self.horizon in event.impact_horizons
                and event.status in (EventStatus.CONFIRMED, EventStatus.CORROBORATED)
            ]
        severity_penalty = {
            EventSeverity.LOW: 0.02,
            EventSeverity.MEDIUM: 0.05,
            EventSeverity.HIGH: 0.12,
            EventSeverity.CRITICAL: 0.25,
        }
        event_risk = min(
            0.50,
            sum(severity_penalty[event.severity] * event.confidence for event in active_events),
        )
        expected_risk *= 1.0 + event_risk
        confidence *= 1.0 - event_risk
        explanation = Explanation(
            why_this_stock=(
                f"{len(relevant)} validated knowledge object(s) cover {ticker} on the "
                f"{self.horizon.value} horizon: "
                + "; ".join(k.economic_explanation for k in relevant)
            ),
            why_now=f"Knowledge active and unretired as of {as_of.isoformat()}.",
            why_not_others=(
                "This model only aggregates promoted knowledge; tickers without "
                "surviving knowledge get no prediction at all rather than a weaker one."
            ),
            supporting_evidence=[
                f"{k.id} v{k.version}: confidence={k.confidence:.2f}, "
                f"expected_return={k.expected_return:.4f}, "
                f"p_value={k.statistical_evidence.p_value:.4g}"
                for k in relevant
            ]
            + [
                f"event {event.id}: {_event_headline(event)}{event.subtype}, "
                f"severity={event.severity.value}, confidence={event.confidence:.2f}, "
                f"sources={','.join(event.sources)}"
                for event in active_events
            ],
            evidence_refs=[
                ProvenanceRef(kind="knowledge", ref_id=k.id, ref_version=k.version)
                for k in relevant
            ]
            + [
                ProvenanceRef(kind="event", ref_id=event.id, ref_version=event.version)
                for event in active_events
            ],
            similar_historical_cases=similar_cases,
            invalidation_conditions=[
                "Any supporting knowledge object is retired or its monitored "
                "performance degrades below its retirement threshold.",
                "A new high-severity source event can raise expected risk and reduce confidence.",
            ],
        )
        return Prediction(
            ticker=ticker,
            horizon=self.horizon,
            as_of=as_of,
            model_id=self.model_id,
            model_version=self.model_version,
            expected_return=expected_return,
            expected_risk=expected_risk,
            confidence=confidence,
            explanation=explanation,
            supporting_knowledge_ids=[k.id for k in relevant],
            provenance=Provenance(
                produced_by=f"{self.model_id}@{self.model_version}",
                produced_at=datetime.now(),
                inputs=[
                    ProvenanceRef(kind="knowledge", ref_id=k.id, ref_version=k.version)
                    for k in relevant
                ]
                + [
                    ProvenanceRef(kind="event", ref_id=event.id, ref_version=event.version)
                    for event in active_events
                ],
            ),
        )
