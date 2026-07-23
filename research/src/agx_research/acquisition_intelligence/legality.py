"""Legality verification: is this acquisition method legally collectable?

Mirrors the same "ambiguity blocks" rule `docs/DATA_ACQUISITION.md` already
enforces for the seed catalog's `TOS_REVIEW` status -- this module just
makes the check mechanical and automatic instead of a one-off human read.
It never elevates a scraping method to `ALLOWED`: `AccessMethod.HTML_SCRAPE`
is last-resort by charter rule, and by construction this verifier can only
return `AMBIGUOUS` or `BLOCKED` for it, never `ALLOWED`. A structured method
(RSS/CSV/JSON API/PDF download) is `ALLOWED` only when robots.txt doesn't
disallow it *and* the page text carries no red-flag terms of use.
"""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, Field

from agx_research.sources.spec import AccessMethod

_RED_FLAGS = [
    "no automated access",
    "scraping is prohibited",
    "may not scrape",
    "no crawling",
    "robots are not permitted",
    "automated queries are prohibited",
    "no bots",
    "not for redistribution",
    "prior written permission",
    "prohibited without",
]
_GREEN_FLAGS = [
    "rss feed",
    "api access",
    "developer api",
    "open data",
    "public api",
    "api documentation",
    "free to download",
    "open government data",
]


class LegalityVerdict(str, Enum):
    ALLOWED = "allowed"
    AMBIGUOUS = "ambiguous"
    BLOCKED = "blocked"


class LegalityAssessment(BaseModel):
    verdict: LegalityVerdict
    robots_allows: bool | None = None  # None: robots.txt unavailable/unchecked
    red_flags_found: list[str] = Field(default_factory=list)
    green_flags_found: list[str] = Field(default_factory=list)
    evidence: str = ""


def assess_legality(
    *,
    access_method: AccessMethod,
    robots_allows: bool | None,
    page_text: str = "",
    terms_of_use_text: str = "",
) -> LegalityAssessment:
    corpus = f"{page_text}\n{terms_of_use_text}".lower()
    red = [flag for flag in _RED_FLAGS if flag in corpus]
    green = [flag for flag in _GREEN_FLAGS if flag in corpus]

    if robots_allows is False:
        return LegalityAssessment(
            verdict=LegalityVerdict.BLOCKED, robots_allows=False,
            red_flags_found=red, green_flags_found=green,
            evidence="robots.txt disallows this path.",
        )

    if red and not green:
        return LegalityAssessment(
            verdict=LegalityVerdict.BLOCKED, robots_allows=robots_allows,
            red_flags_found=red, green_flags_found=green,
            evidence=f"Terms-of-use red flag(s) found with no offsetting invitation: {red}.",
        )

    if access_method == AccessMethod.HTML_SCRAPE:
        # Charter rule: scraping is last-resort and never auto-cleared, even
        # with clean robots.txt and no red flags -- it always needs a human
        # ToS read.
        return LegalityAssessment(
            verdict=LegalityVerdict.AMBIGUOUS, robots_allows=robots_allows,
            red_flags_found=red, green_flags_found=green,
            evidence="HTML scraping never auto-clears; requires human ToS review.",
        )

    if red or robots_allows is None:
        return LegalityAssessment(
            verdict=LegalityVerdict.AMBIGUOUS, robots_allows=robots_allows,
            red_flags_found=red, green_flags_found=green,
            evidence="Mixed or unknown signals; ambiguity blocks per program policy.",
        )

    return LegalityAssessment(
        verdict=LegalityVerdict.ALLOWED, robots_allows=robots_allows,
        red_flags_found=red, green_flags_found=green,
        evidence="robots.txt permits this path; no red-flag terms found for a structured "
        "(non-scraping) access method.",
    )
