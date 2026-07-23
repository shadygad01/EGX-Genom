from datetime import date, datetime

import pytest

from agx_research.config import Horizon
from agx_research.domain.provenance import Provenance
from agx_research.events.conflict import ConservativeConflictPolicy
from agx_research.events.entity import EntityKind, EntityRef
from agx_research.events.event import EventRelationshipType, EventSeverity, EventType
from agx_research.events.identity import compute_event_fingerprint
from agx_research.events.lifecycle import EventStatus
from agx_research.events.service import EventPlatform, build_candidate_event
from agx_research.events.taxonomy import EventSubtype


def entity(canonical_id="COMI") -> EntityRef:
    return EntityRef(kind=EntityKind.COMPANY, canonical_id=canonical_id, raw_mention=canonical_id)


def candidate(
    *,
    source="source_a",
    metadata=None,
    subtype=EventSubtype.DIVIDEND,
    event_date=date(2026, 6, 4),
    canonical_id="COMI",
):
    return build_candidate_event(
        event_type=EventType.CORPORATE,
        subtype=subtype,
        entities=[entity(canonical_id)],
        event_date=event_date,
        source=source,
        confidence=0.8,
        severity=EventSeverity.MEDIUM,
        metadata=metadata or {"dividend_amount": 3.5},
        provenance=Provenance(produced_by="test", produced_at=datetime.now()),
    )


# --- identity ---


def test_same_facts_produce_same_id_regardless_of_source():
    a = candidate(source="source_a")
    b = candidate(source="source_b")
    assert a.id == b.id


def test_different_facts_produce_different_ids():
    a = candidate(event_date=date(2026, 6, 4))
    b = candidate(event_date=date(2026, 6, 5))
    assert a.id != b.id


def test_entity_order_does_not_change_fingerprint():
    fp1 = compute_event_fingerprint(
        event_type=EventType.CORPORATE,
        subtype=EventSubtype.MERGER_ACQUISITION,
        entities=[entity("COMI"), entity("MFPC")],
        event_date=date(2026, 6, 4),
    )
    fp2 = compute_event_fingerprint(
        event_type=EventType.CORPORATE,
        subtype=EventSubtype.MERGER_ACQUISITION,
        entities=[entity("MFPC"), entity("COMI")],
        event_date=date(2026, 6, 4),
    )
    assert fp1 == fp2


def test_discriminator_separates_same_day_news():
    fp1 = compute_event_fingerprint(
        event_type=EventType.NEWS,
        subtype=EventSubtype.COMPANY_NEWS,
        entities=[entity("COMI")],
        event_date=date(2026, 6, 9),
        discriminator="headline one",
    )
    fp2 = compute_event_fingerprint(
        event_type=EventType.NEWS,
        subtype=EventSubtype.COMPANY_NEWS,
        entities=[entity("COMI")],
        event_date=date(2026, 6, 9),
        discriminator="headline two",
    )
    assert fp1 != fp2


# --- registration, dedup, corroboration, dispute ---


def test_first_registration_confirms_the_event():
    platform = EventPlatform()
    registered = platform.register(candidate())
    assert registered.status == EventStatus.CONFIRMED
    assert registered.version == 1


def test_same_source_replay_is_idempotent_and_does_not_inflate_confidence():
    platform = EventPlatform()
    first = platform.register(candidate(source="source_a"))
    replay = platform.register(candidate(source="source_a"))
    assert replay.version == first.version
    assert replay.confidence == first.confidence


def test_agreeing_second_source_corroborates_and_raises_confidence():
    platform = EventPlatform()
    first = platform.register(candidate(source="source_a"))
    merged = platform.register(candidate(source="source_b"))

    assert merged.status == EventStatus.CORROBORATED
    assert merged.confidence > first.confidence
    assert merged.sources == ["source_a", "source_b"]
    assert merged.version == 2
    assert merged.relationships[-1].relationship_type == EventRelationshipType.CORROBORATES


def test_disagreeing_second_source_disputes_and_lowers_confidence():
    platform = EventPlatform()
    first = platform.register(candidate(source="source_a", metadata={"dividend_amount": 3.5}))
    merged = platform.register(candidate(source="source_b", metadata={"dividend_amount": 4.0}))

    assert merged.status == EventStatus.DISPUTED
    assert merged.confidence < first.confidence
    assert merged.disputed_keys == ["dividend_amount"]
    # The existing value is kept, never silently replaced by the newcomer's.
    assert merged.metadata["dividend_amount"] == 3.5
    assert merged.relationships[-1].relationship_type == EventRelationshipType.CONTRADICTS


def test_new_metadata_keys_are_additive_not_conflicting():
    platform = EventPlatform()
    platform.register(candidate(source="source_a", metadata={"dividend_amount": 3.5}))
    merged = platform.register(
        candidate(source="source_b", metadata={"dividend_amount": 3.5, "currency": "EGP"})
    )
    assert merged.status == EventStatus.CORROBORATED
    assert merged.metadata["currency"] == "EGP"


def test_dispute_can_resolve_back_to_corroborated():
    platform = EventPlatform()
    platform.register(candidate(source="source_a", metadata={"dividend_amount": 3.5}))
    platform.register(candidate(source="source_b", metadata={"dividend_amount": 4.0}))
    resolved = platform.register(candidate(source="source_c", metadata={"dividend_amount": 3.5}))
    assert resolved.status == EventStatus.CORROBORATED


# --- lifecycle: retraction and supersession ---


def test_retract_marks_event_and_preserves_history():
    platform = EventPlatform()
    registered = platform.register(candidate())
    retracted = platform.retract(registered.id, "source withdrew the announcement")

    assert retracted.status == EventStatus.RETRACTED
    assert retracted.metadata["status_reason"] == "source withdrew the announcement"
    history = platform.repository.history(registered.id)
    assert history[0].status == EventStatus.CONFIRMED  # original revision untouched


def test_registration_after_retraction_does_not_resurrect():
    platform = EventPlatform()
    registered = platform.register(candidate(source="source_a"))
    platform.retract(registered.id, "withdrawn")
    result = platform.register(candidate(source="source_b"))
    assert result.status == EventStatus.RETRACTED


def test_supersede_creates_new_event_and_marks_original():
    platform = EventPlatform()
    original = platform.register(candidate(event_date=date(2026, 6, 4)))
    # The correction changes an identifying fact (the actual ex-date).
    corrected = platform.supersede(original.id, candidate(event_date=date(2026, 6, 5)))

    assert corrected.id != original.id
    assert any(
        r.relationship_type == EventRelationshipType.SUPERSEDES and r.related_event_id == original.id
        for r in corrected.relationships
    )
    assert platform.repository.latest(original.id).status == EventStatus.SUPERSEDED


def test_supersede_rejects_identical_facts():
    platform = EventPlatform()
    original = platform.register(candidate())
    with pytest.raises(ValueError):
        platform.supersede(original.id, candidate())


# --- taxonomy / ontology enforcement on the schema itself ---


def test_subtype_must_belong_to_event_type():
    with pytest.raises(ValueError):
        build_candidate_event(
            event_type=EventType.MARKET,
            subtype=EventSubtype.DIVIDEND,  # a corporate subtype
            entities=[entity()],
            event_date=date(2026, 6, 4),
            source="s",
            confidence=1.0,
            severity=EventSeverity.LOW,
            provenance=Provenance(produced_by="test", produced_at=datetime.now()),
        )


def test_impact_horizons_come_from_the_ontology():
    event = candidate(subtype=EventSubtype.DIVIDEND)
    assert event.impact_horizons == [Horizon.MICRO]


# --- queries ---


def test_events_for_entity_and_horizon():
    platform = EventPlatform()
    platform.register(candidate(canonical_id="COMI", subtype=EventSubtype.DIVIDEND))
    platform.register(
        candidate(canonical_id="MFPC", subtype=EventSubtype.EARNINGS, metadata={"eps": 1.2})
    )

    comi_events = platform.events_for_entity("COMI")
    assert len(comi_events) == 1
    assert comi_events[0].subtype == EventSubtype.DIVIDEND.value

    micro_events = platform.events_for_horizon(Horizon.MICRO)
    assert len(micro_events) == 2  # both dividend and earnings triage to MICRO


def test_confidence_never_exceeds_one():
    platform = EventPlatform(conflict_policy=ConservativeConflictPolicy(corroboration_boost=1.0))
    platform.register(candidate(source="a"))
    merged = platform.register(candidate(source="b"))
    assert merged.confidence <= 1.0
