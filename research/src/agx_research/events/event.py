"""The canonical Event: everything entering AGX becomes one of these.

No downstream component (agents, experiments, the graph layer) should
consume raw news, corporate disclosures, or macro observations directly —
they consume `Event`s. `relationships` (ids of other related events) is
what makes an `Event` a node in an event graph rather than an isolated
record; the Knowledge Graph layer (Phase 8) materializes these as edges
alongside everything else.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field

from agx_research.domain.provenance import Provenance


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


class Event(BaseModel):
    id: str
    version: int = 1
    event_type: EventType
    entities: list[str] = Field(default_factory=list)
    timestamp: datetime
    source: str
    confidence: float = Field(ge=0.0, le=1.0)
    severity: EventSeverity
    relationships: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)
    provenance: Provenance
