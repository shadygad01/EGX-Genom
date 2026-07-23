"""Event identity: a content fingerprint, not a random id.

The root design fix this audit made: a random `new_id("event")` meant
re-deriving the same real-world event from the same (or a different)
source produced a *different* record every time, with no way to recognize
them as the same occurrence. `compute_event_fingerprint()` hashes what
actually identifies "this happened, to these entities, on this date" —
deliberately excluding `source`, `confidence`, and `metadata`, so that two
different sources reporting the same real-world event collide onto the
same id and can corroborate each other instead of being treated as
unrelated events.
"""

from __future__ import annotations

import hashlib
import json
from datetime import date

from agx_research.events.entity import EntityRef
from agx_research.events.event import EventType
from agx_research.events.taxonomy import EventSubtype


def compute_event_fingerprint(
    *,
    event_type: EventType,
    subtype: EventSubtype,
    entities: list[EntityRef],
    event_date: date,
    discriminator: str | None = None,
) -> str:
    """`discriminator` is for event kinds whose natural key needs extra
    content to be distinct — e.g. two different news stories about the same
    company on the same day are two events, so news adapters pass the
    headline. A dividend announced for the same ticker on the same date,
    by contrast, IS the same event no matter who reports it, so structured
    corporate/macro/market events pass no discriminator.
    """
    payload = {
        "event_type": event_type.value,
        "subtype": subtype.value,
        "entities": sorted({entity.canonical_id for entity in entities}),
        "date": event_date.isoformat(),
    }
    if discriminator is not None:
        payload["discriminator"] = discriminator
    canonical = json.dumps(payload, sort_keys=True)
    return hashlib.sha256(canonical.encode()).hexdigest()[:20]


def derive_event_id(fingerprint: str) -> str:
    return f"event_{fingerprint}"
