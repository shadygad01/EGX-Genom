"""Headline-level corporate-event classification: a declared keyword
heuristic, same posture as `acquisition_intelligence.legality`'s red/green
flag lists and `discovery.discover_company_directory_links`'s anchor-text
matching -- a starting policy, not calibrated against a real corpus, and
honestly documented as such (TD-29).

Deliberately headline-only: no full-text extraction happens here (RSS/ToS
terms limit collectors to headline/link/date, see TD-12), so a classified
event's `details` is always `{}` -- a numeric split ratio or dividend
amount cannot be reliably read off a headline, and guessing one would be
exactly the kind of fabrication this platform forbids. `data.adjustments`
only acts on events that carry those details, so a headline-classified
event stays correctly informational-only until a fuller-text source (e.g.
an IR disclosure PDF) enriches it.

Returns one of `events.adapters._CORPORATE_SUBTYPES`'s raw keys so a
classified `CorporateEvent.event_type` maps into the existing taxonomy
with no changes needed there -- extending an existing adapter, not
building a parallel one.
"""

from __future__ import annotations

# Longer/more specific phrases first: matching stops at the first hit, so a
# more specific phrase (e.g. "stock split") must be checked before a looser
# one that could coincidentally appear in the same headline.
_KEYWORD_TO_EVENT_TYPE: tuple[tuple[str, str], ...] = (
    ("stock split", "STOCK_SPLIT"),
    ("share split", "STOCK_SPLIT"),
    ("capital increase", "CAPITAL_INCREASE"),
    ("rights issue", "CAPITAL_INCREASE"),
    ("share buyback", "BUYBACK"),
    ("stock buyback", "BUYBACK"),
    ("treasury shares", "BUYBACK"),
    ("buyback", "BUYBACK"),
    ("management change", "MANAGEMENT_CHANGE"),
    ("board appoints", "MANAGEMENT_CHANGE"),
    ("appoints new ceo", "MANAGEMENT_CHANGE"),
    ("resignation", "MANAGEMENT_CHANGE"),
    ("delisting", "DELISTING"),
    ("delisted", "DELISTING"),
    ("merge", "MERGER"),  # covers "merge"/"merger"/"merging"
    ("acquisition", "ACQUISITION"),
    ("to acquire", "ACQUISITION"),
    ("dividend", "DIVIDEND"),
    ("guidance", "GUIDANCE"),
    ("quarterly results", "EARNINGS"),
    ("annual results", "EARNINGS"),
    ("financial results", "EARNINGS"),
    ("net income", "EARNINGS"),
    ("earnings", "EARNINGS"),
)


def classify_corporate_event_type(headline: str) -> str | None:
    """Return a raw `CorporateEvent.event_type` (an `events.adapters.
    _CORPORATE_SUBTYPES` key) if `headline` matches a declared keyword, else
    `None` -- never a guess when nothing matches.
    """
    normalized = headline.lower()
    for phrase, event_type in _KEYWORD_TO_EVENT_TYPE:
        if phrase in normalized:
            return event_type
    return None
