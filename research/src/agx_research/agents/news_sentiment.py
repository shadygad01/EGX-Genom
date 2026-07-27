"""Headline-level sentiment classification: a declared keyword heuristic,
same posture as `collectors.corporate_event_classifier`'s event-type
mapping and `acquisition_intelligence.legality`'s red/green ToS flag
lists -- a starting policy, not calibrated against a real corpus, and
honestly documented as such (TD-35).

Deliberately headline-only, matching `NewsItem`'s own real coverage (RSS
feeds give headline/link/date, not full article text -- TD-12): no claim
is made about sentiment expressed in a news item's body.
"""

from __future__ import annotations

_POSITIVE_PHRASES: tuple[str, ...] = (
    "net income growth",
    "profit surge",
    "profit growth",
    "record profit",
    "strong growth",
    "strong results",
    "beats estimates",
    "beat estimates",
    "raises guidance",
    "raised guidance",
    "upgrade",
    "outperform",
    "expansion",
    "expands",
    "declares dividend",
    "special dividend",
    "surge",
    "rally",
    "climbs",
    "rises",
    "jumps",
    "gains",
)

_NEGATIVE_PHRASES: tuple[str, ...] = (
    "net loss",
    "profit decline",
    "profit warning",
    "misses estimates",
    "missed estimates",
    "cuts guidance",
    "cut guidance",
    "downgrade",
    "underperform",
    "plunge",
    "plunges",
    "slump",
    "slumps",
    "tumbles",
    "falls",
    "declines",
    "investigation",
    "lawsuit",
    "fraud",
    "fine",
    "penalty",
    "default",
    "delisting",
    "delisted",
)


def classify_headline_sentiment(headline: str) -> str | None:
    """Return `"positive"`/`"negative"` if `headline` matches a declared
    phrase, else `None` -- never a guess when nothing matches. Negative
    phrases are checked first so a headline containing both ("shares fall
    despite dividend declaration") is not misclassified positive by
    whichever list happens to be scanned first.
    """
    normalized = headline.lower()
    for phrase in _NEGATIVE_PHRASES:
        if phrase in normalized:
            return "negative"
    for phrase in _POSITIVE_PHRASES:
        if phrase in normalized:
            return "positive"
    return None
