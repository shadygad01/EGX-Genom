"""Populating "what historical cases are similar?" from real recorded events.

A similar historical case is, mechanically: a prior canonical Event of the
same subtype involving the same entity, drawn from the Event Platform's
repository. This answers the vision's explainability question from data
the platform actually holds — never from generated prose.
"""

from __future__ import annotations

from datetime import date

from agx_research.events.service import EventPlatform


def find_similar_cases(
    event_platform: EventPlatform,
    ticker: str,
    *,
    before: date,
    limit: int = 5,
) -> list[str]:
    events = [
        e
        for e in event_platform.events_for_entity(ticker)
        if e.event_date < before
    ]
    events.sort(key=lambda e: e.event_date, reverse=True)
    return [
        f"{e.event_date.isoformat()}: {e.event_type.value}/{e.subtype} "
        f"(severity {e.severity.value}, confidence {e.confidence:.2f})"
        for e in events[:limit]
    ]
