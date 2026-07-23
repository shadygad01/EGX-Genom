"""The Event lifecycle: mirrors the KnowledgeStatus/GeneStatus pattern
already established elsewhere, which Epoch II's `Event` never got.

    PENDING --------> CONFIRMED -------> CORROBORATED
       |                  |                   ^  |
       |                  |                   |  v
       +---------------> DISPUTED <-----------+
       |                  |
       v                  v
   RETRACTED          RETRACTED
       |                  |
       v                  v
    ARCHIVED  <---   SUPERSEDED

A dispute can later resolve back to CORROBORATED if a subsequent source
agrees with the originally-recorded facts; it is not a dead end.
"""

from __future__ import annotations

from enum import Enum


class EventStatus(str, Enum):
    PENDING = "pending"
    CONFIRMED = "confirmed"
    CORROBORATED = "corroborated"
    DISPUTED = "disputed"
    RETRACTED = "retracted"
    SUPERSEDED = "superseded"
    ARCHIVED = "archived"


_ALLOWED_TRANSITIONS: dict[EventStatus, set[EventStatus]] = {
    EventStatus.PENDING: {
        EventStatus.CONFIRMED,
        EventStatus.CORROBORATED,
        EventStatus.DISPUTED,
        EventStatus.RETRACTED,
        EventStatus.ARCHIVED,
    },
    EventStatus.CONFIRMED: {
        EventStatus.CORROBORATED,
        EventStatus.DISPUTED,
        EventStatus.RETRACTED,
        EventStatus.SUPERSEDED,
        EventStatus.ARCHIVED,
    },
    EventStatus.CORROBORATED: {
        EventStatus.DISPUTED,
        EventStatus.RETRACTED,
        EventStatus.SUPERSEDED,
        EventStatus.ARCHIVED,
    },
    EventStatus.DISPUTED: {
        EventStatus.CORROBORATED,
        EventStatus.RETRACTED,
        EventStatus.SUPERSEDED,
        EventStatus.ARCHIVED,
    },
    EventStatus.RETRACTED: {EventStatus.ARCHIVED},
    EventStatus.SUPERSEDED: {EventStatus.ARCHIVED},
    EventStatus.ARCHIVED: set(),
}


def can_transition(current: EventStatus, target: EventStatus) -> bool:
    return target in _ALLOWED_TRANSITIONS[current]
