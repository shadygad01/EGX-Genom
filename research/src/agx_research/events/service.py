"""EventPlatform: the sole sanctioned entry point for persisting events.

Mirrors the "agents propose, the pipeline decides" pattern: adapters (and
future real data providers) only *build candidate* `Event`s; nothing writes
to `EventRepository` except through `register()` here. That is what makes
identity, deduplication, conflict resolution, and lifecycle management
guarantees actually hold — they can't be bypassed by a caller that doesn't
know about them.

- `register(candidate)` is idempotent-by-identity: the candidate's id must
  come from `identity.derive_event_id()` (adapters use
  `build_candidate_event()` below, which guarantees it). An unseen id is
  persisted as version 1, status CONFIRMED (adapters derive from observed
  data) or PENDING. A seen id is merged via the configured
  `ConflictResolutionPolicy`: agreement corroborates (confidence rises),
  disagreement marks the event DISPUTED with the conflicting keys recorded
  — never silently picking a winner.
- `supersede(event_id, corrected)` mirrors `AlphaGenome.mutate()`: the
  correction is a *new* event linked back via a SUPERSEDES relationship,
  and the original is marked SUPERSEDED. History is never rewritten.
- `retract(event_id, reason)` marks an event RETRACTED (e.g. the source
  withdrew it) without deleting anything.
"""

from __future__ import annotations

from datetime import date, datetime
from typing import Any

from agx_research.config import Horizon
from agx_research.domain.provenance import Provenance, ProvenanceRef
from agx_research.events.conflict import ConflictResolutionPolicy, ConservativeConflictPolicy
from agx_research.events.entity import EntityRef
from agx_research.events.event import (
    Event,
    EventRelationship,
    EventRelationshipType,
    EventSeverity,
    EventType,
)
from agx_research.events.identity import compute_event_fingerprint, derive_event_id
from agx_research.events.lifecycle import EventStatus, can_transition
from agx_research.events.ontology import classify_impact_horizons
from agx_research.events.repository import EventRepository
from agx_research.events.taxonomy import EventSubtype, validate_subtype


def build_candidate_event(
    *,
    event_type: EventType,
    subtype: EventSubtype,
    entities: list[EntityRef],
    event_date: date,
    source: str,
    confidence: float,
    severity: EventSeverity,
    metadata: dict[str, Any] | None = None,
    provenance: Provenance,
    timestamp: datetime | None = None,
    impact_horizons: list[Horizon] | None = None,
    discriminator: str | None = None,
) -> Event:
    """The one way adapters should construct a candidate Event.

    Guarantees the id is fingerprint-derived (so `register()` can
    deduplicate) and the impact horizons come from the ontology unless
    explicitly overridden. See `identity.compute_event_fingerprint` for
    when to pass a `discriminator`.
    """
    validate_subtype(event_type, subtype)
    fingerprint = compute_event_fingerprint(
        event_type=event_type,
        subtype=subtype,
        entities=entities,
        event_date=event_date,
        discriminator=discriminator,
    )
    return Event(
        id=derive_event_id(fingerprint),
        event_type=event_type,
        subtype=subtype.value,
        entities=entities,
        event_date=event_date,
        timestamp=timestamp or datetime.combine(event_date, datetime.min.time()),
        source=source,
        confidence=confidence,
        severity=severity,
        status=EventStatus.PENDING,
        impact_horizons=(
            impact_horizons if impact_horizons is not None else classify_impact_horizons(subtype)
        ),
        metadata=metadata or {},
        provenance=provenance,
    )


class EventPlatform:
    def __init__(
        self,
        repository: EventRepository | None = None,
        conflict_policy: ConflictResolutionPolicy | None = None,
    ):
        self.repository = repository or EventRepository()
        self.conflict_policy = conflict_policy or ConservativeConflictPolicy()

    def register(self, candidate: Event) -> Event:
        existing = self.repository.latest(candidate.id)
        if existing is None:
            first = candidate.model_copy(update={"status": EventStatus.CONFIRMED})
            return self.repository.add(first)

        if existing.status in (EventStatus.RETRACTED, EventStatus.SUPERSEDED, EventStatus.ARCHIVED):
            # A terminal event is never resurrected by re-registration; a
            # genuine correction goes through supersede().
            return existing

        if candidate.source in existing.sources:
            # Same source re-reporting the same event (e.g. an adapter
            # re-run over the same snapshot) is idempotent, not
            # corroboration — confidence must not inflate from replays.
            return existing

        resolution = self.conflict_policy.resolve(existing, candidate)
        next_status = EventStatus.DISPUTED if resolution.is_disputed else EventStatus.CORROBORATED
        if not can_transition(existing.status, next_status):
            next_status = existing.status

        relationship_type = (
            EventRelationshipType.CONTRADICTS
            if resolution.is_disputed
            else EventRelationshipType.CORROBORATES
        )
        merged = existing.model_copy(
            update={
                "version": existing.version + 1,
                "sources": [*existing.sources, candidate.source],
                "confidence": resolution.merged_confidence,
                "status": next_status,
                "metadata": resolution.merged_metadata,
                "disputed_keys": sorted(set(existing.disputed_keys) | set(resolution.disputed_keys)),
                "relationships": [
                    *existing.relationships,
                    EventRelationship(
                        related_event_id=candidate.id,
                        relationship_type=relationship_type,
                        notes=f"Report from {candidate.source}: {resolution.notes}",
                    ),
                ],
                "provenance": Provenance(
                    produced_by="event_platform.register",
                    produced_at=datetime.now(),
                    inputs=[
                        ProvenanceRef(kind="event", ref_id=existing.id, ref_version=existing.version),
                        *candidate.provenance.inputs,
                    ],
                ),
            }
        )
        return self.repository.add(merged)

    def register_all(self, candidates: list[Event]) -> list[Event]:
        return [self.register(candidate) for candidate in candidates]

    def transition_status(self, event_id: str, target: EventStatus, *, reason: str = "") -> Event:
        current = self.repository.latest(event_id)
        if current is None:
            raise KeyError(f"No event with id {event_id}")
        if not can_transition(current.status, target):
            raise ValueError(f"Cannot transition event {event_id}: {current.status} -> {target}")
        next_revision = current.model_copy(
            update={
                "version": current.version + 1,
                "status": target,
                "metadata": (
                    {**current.metadata, "status_reason": reason} if reason else current.metadata
                ),
            }
        )
        return self.repository.add(next_revision)

    def retract(self, event_id: str, reason: str) -> Event:
        return self.transition_status(event_id, EventStatus.RETRACTED, reason=reason)

    def supersede(self, event_id: str, corrected_candidate: Event) -> Event:
        """Record a factual correction as a NEW event; never edit the original.

        The corrected candidate must have a different fingerprint (its facts
        changed — that's what makes it a correction); it is registered
        normally, linked back to the original via SUPERSEDES, and the
        original is marked SUPERSEDED.
        """
        original = self.repository.latest(event_id)
        if original is None:
            raise KeyError(f"No event with id {event_id}")
        if corrected_candidate.id == event_id:
            raise ValueError(
                "A correction must change the event's identifying facts "
                "(same fingerprint means nothing was corrected); use register() "
                "for corroborating reports."
            )

        replacement = self.register(corrected_candidate)
        linked = replacement.model_copy(
            update={
                "version": replacement.version + 1,
                "relationships": [
                    *replacement.relationships,
                    EventRelationship(
                        related_event_id=original.id,
                        relationship_type=EventRelationshipType.SUPERSEDES,
                        notes="Correction of an earlier report.",
                    ),
                ],
            }
        )
        self.repository.add(linked)
        self.transition_status(original.id, EventStatus.SUPERSEDED, reason=f"Superseded by {linked.id}")
        return linked

    def events_for_entity(self, canonical_id: str) -> list[Event]:
        return [
            event
            for event in self.repository.all_latest()
            if any(entity.canonical_id == canonical_id for entity in event.entities)
        ]

    def events_for_horizon(self, horizon: Horizon) -> list[Event]:
        return [event for event in self.repository.all_latest() if horizon in event.impact_horizons]
