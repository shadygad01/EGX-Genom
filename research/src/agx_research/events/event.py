"""The canonical Event: everything entering AGX becomes one of these.

No downstream component (agents, experiments, the graph layer) should
consume raw news, corporate disclosures, or macro observations directly —
they consume `Event`s.

Design points (see docs/EVENT_PLATFORM_DESIGN.md for the full audit):

- `id` is derived from a content fingerprint (`events/identity.py`), not a
  random UUID — the same real-world occurrence always maps to the same id,
  which is what makes deduplication and cross-source corroboration
  possible at all.
- `entities` are resolved `EntityRef`s, not bare strings — each carries
  its kind, canonical id, and the raw mention it was resolved from.
- `subtype` comes from the controlled taxonomy (`events/taxonomy.py`) and
  is validated against `event_type`; `impact_horizons` is the ontology's
  triage classification of which research horizons the event is relevant
  to investigate (not a price-impact prediction).
- `relationships` are typed `EventRelationship`s (corroborates,
  supersedes, contradicts, ...), not a flat id list — this is what makes
  the event graph mean something.
- `status`/`sources` are lifecycle state managed exclusively by
  `events/service.py`'s EventPlatform; adapters only propose candidates.
- Events are immutable in the repository sense: every change is a new
  revision (version + 1) appended via the versioned repository, and a
  factual correction is a *new* event that SUPERSEDES the old one, never
  an in-place edit.
"""

from __future__ import annotations

from datetime import date, datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field, model_validator

from agx_research.config import Horizon
from agx_research.domain.provenance import Provenance
from agx_research.events.entity import EntityRef
from agx_research.events.lifecycle import EventStatus


class EventType(str, Enum):
    CORPORATE = "corporate"
    MACROECONOMIC = "macroeconomic"
    POLITICAL = "political"
    MARKET = "market"
    TECHNICAL = "technical"
    NEWS = "news"


class EventSeverity(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class EventRelationshipType(str, Enum):
    CORROBORATES = "corroborates"
    SUPERSEDES = "supersedes"
    CONTRADICTS = "contradicts"
    CAUSALLY_PRECEDES = "causally_precedes"
    PART_OF = "part_of"


class EventRelationship(BaseModel):
    related_event_id: str
    relationship_type: EventRelationshipType
    notes: str = ""


class Event(BaseModel):
    id: str
    version: int = 1
    event_type: EventType
    # str, not EventSubtype, to avoid a circular import (taxonomy imports
    # EventType from here); validated against the taxonomy below.
    subtype: str
    entities: list[EntityRef] = Field(default_factory=list)
    event_date: date
    timestamp: datetime
    source: str
    sources: list[str] = Field(default_factory=list)
    confidence: float = Field(ge=0.0, le=1.0)
    severity: EventSeverity
    status: EventStatus = EventStatus.PENDING
    impact_horizons: list[Horizon] = Field(default_factory=list)
    relationships: list[EventRelationship] = Field(default_factory=list)
    disputed_keys: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)
    provenance: Provenance

    @model_validator(mode="after")
    def _validate_subtype_and_sources(self) -> "Event":
        # Imported here, not at module top, because taxonomy imports
        # EventType from this module.
        from agx_research.events.taxonomy import EventSubtype, validate_subtype

        validate_subtype(self.event_type, EventSubtype(self.subtype))
        if not self.sources:
            self.sources = [self.source]
        return self
