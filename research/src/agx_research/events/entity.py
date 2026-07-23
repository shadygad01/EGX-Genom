"""What an Event is about: a resolved reference to a real-world entity.

`EntityRef` is deliberately not a bare string — it carries the canonical
id, what kind of thing it is, and the raw mention that was resolved to it,
so a later audit can always answer "why does this event involve this
entity" instead of trusting an opaque ticker string.
"""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel


class EntityKind(str, Enum):
    COMPANY = "company"
    SECTOR = "sector"
    MACRO_SERIES = "macro_series"
    MARKET = "market"
    UNKNOWN = "unknown"


class EntityRef(BaseModel):
    kind: EntityKind
    canonical_id: str
    display_name: str | None = None
    raw_mention: str
