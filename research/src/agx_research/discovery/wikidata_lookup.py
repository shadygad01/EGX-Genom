"""Wikidata official-website lookup: a free, structured, no-key alternative
path to a real EGX30/EGX70 constituent's own homepage that does not depend
on `egx_official` being reachable.

`acquisition_intelligence.target.generate_company_ir_targets`'s docstring
names two honest paths to a real per-company domain hint: the company's
own public disclosure, or `discover_company_directory_links` reading an
already-resolved directory homepage (e.g. EGX's own listed-companies page).
This module is a third, independent path: Wikidata's own declared `P856`
("official website") property for an entity, read through its public,
documented, no-key action API -- the same confidence tier as the Wayback
Machine APIs `acquisition_intelligence.historical` already uses for
verification, and reusable even while `egx_official` itself stays
unreachable, since it never depends on the exchange's own site at all.

Per-company search (`wbsearchentities` + `wbgetclaims`), not one bulk
query: an earlier design queried everything Wikidata tags `P17` (country)
= Egypt in one SPARQL call. That query demonstrably worked (a live run
returned 2404 real results) but missed real, well-documented companies --
Telecom Egypt among them -- outright, because `P17` is not reliably set on
individual company items; organizations more often carry a headquarters
location than a direct country statement. Searching by the company's own
display name sidesteps that gap entirely: it asks Wikidata "what entity is
this name", not "what entities are tagged Egypt", so it works whether or
not `P17` happens to be set on that particular item.

Matching reuses `discovery.engine.significant_tokens`'s exact name-token-
overlap discipline (no duplicated matching logic, same rule everywhere): a
match still requires every significant token of a company's known display
name to appear in a label Wikidata itself returned for a real search hit.
A result here still only becomes a `domain_hints` entry -- it is always
re-probed independently by
`acquisition_intelligence.domain_resolution.HeuristicDomainResolver` before
anything is trusted (AD-24 holds unchanged); this module never asserts a
company's domain, only reports what a real, already-fetched Wikidata
response actually contained.
"""

from __future__ import annotations

from typing import Callable
from urllib.parse import quote, urlsplit

from pydantic import BaseModel

from agx_research.discovery.engine import significant_tokens

FetchJson = Callable[[str], object]

WIKIDATA_API_ENDPOINT = "https://www.wikidata.org/w/api.php"

_OFFICIAL_WEBSITE_PROPERTY = "P856"
_SEARCH_RESULT_LIMIT = 5


def build_wikidata_search_url(name: str) -> str:
    return (
        f"{WIKIDATA_API_ENDPOINT}?action=wbsearchentities&search={quote(name)}"
        f"&language=en&type=item&format=json&limit={_SEARCH_RESULT_LIMIT}"
    )


def parse_wikidata_search_results(payload: dict) -> list[tuple[str, str]]:
    """`payload` is a real `wbsearchentities` response (`search` -> list of
    `{"id": ..., "label": ..., ...}` dicts). An entry missing either field
    is skipped -- nothing to match against, not a guess.
    """
    results: list[tuple[str, str]] = []
    for entry in payload.get("search") or []:
        entity_id = entry.get("id")
        label = entry.get("label")
        if entity_id and label:
            results.append((entity_id, label))
    return results


def build_wikidata_claims_url(entity_id: str) -> str:
    return (
        f"{WIKIDATA_API_ENDPOINT}?action=wbgetclaims&entity={quote(entity_id)}"
        f"&property={_OFFICIAL_WEBSITE_PROPERTY}&format=json"
    )


def parse_wikidata_official_website(payload: dict) -> str | None:
    """`payload` is a real `wbgetclaims` response restricted to `P856`.
    Returns the first claim's string value if present, else `None` -- a
    claim with no `datavalue` (a "no value"/"unknown value" snak) or a
    non-string value is treated as absent, never guessed at.
    """
    for claim in (payload.get("claims") or {}).get(_OFFICIAL_WEBSITE_PROPERTY, []):
        value = ((claim.get("mainsnak") or {}).get("datavalue") or {}).get("value")
        if isinstance(value, str) and value:
            return value
    return None


def _find_matching_entity(candidates: list[tuple[str, str]], name: str) -> str | None:
    tokens = significant_tokens(name)
    if not tokens:
        return None
    for entity_id, label in candidates:
        if tokens.issubset(significant_tokens(label)):
            return entity_id
    return None


class WikidataLookupAttempt(BaseModel):
    """One company's Wikidata lookup attempt this run, whatever the outcome
    -- the raw material `discovery.resolution_memory` persists so a later
    run (or a human debugging low coverage) can see *why* a ticker has no
    Wikidata hint instead of just that it doesn't: "no search hit at all"
    is a structurally different gap from "matched an entity with no P856
    website claim," and neither should be silently collapsed into the
    other."""

    ticker: str
    matched: bool
    hostname: str | None = None
    matched_entity_id: str | None = None
    matched_label: str | None = None
    rejection_reason: str | None = None  # populated only when matched=False


class WikidataOfficialWebsiteClient:
    name = "wikidata"

    def __init__(self, fetch_json: FetchJson):
        self.fetch_json = fetch_json

    def lookup(self, companies: dict[str, str]) -> dict[str, str]:
        """Ticker -> hostname for every company in `companies` (ticker ->
        display name) that a real Wikidata name search finds a matching
        entity for, and whose entity has a real `P856` claim. One
        company's lookup failing (unreachable endpoint, no match, no
        claim) never blocks the rest -- each is independently degraded to
        "no hint", the same honest fallback every other network-dependent
        step in this package uses.
        """
        return {
            ticker: attempt.hostname
            for ticker, attempt in self.lookup_with_trace(companies).items()
            if attempt.matched and attempt.hostname
        }

    def lookup_with_trace(self, companies: dict[str, str]) -> dict[str, WikidataLookupAttempt]:
        """Same lookups as `lookup()`, but returns one `WikidataLookupAttempt`
        per company regardless of outcome -- a miss is recorded with a real
        rejection reason instead of silently vanishing from the result."""
        return {ticker: self._lookup_one(ticker, name) for ticker, name in companies.items()}

    def _lookup_one(self, ticker: str, name: str) -> WikidataLookupAttempt:
        search_payload = self.fetch_json(build_wikidata_search_url(name))
        if not isinstance(search_payload, dict):
            return WikidataLookupAttempt(
                ticker=ticker, matched=False,
                rejection_reason="Wikidata search request failed or returned a malformed response.",
            )
        search_results = parse_wikidata_search_results(search_payload)
        if not search_results:
            return WikidataLookupAttempt(
                ticker=ticker, matched=False,
                rejection_reason="Wikidata name search returned no candidate entities.",
            )
        entity_id = _find_matching_entity(search_results, name)
        if entity_id is None:
            return WikidataLookupAttempt(
                ticker=ticker, matched=False,
                rejection_reason=(
                    "Wikidata search returned candidates, but none shared every "
                    "significant token of the company's display name."
                ),
            )
        matched_label = next((label for eid, label in search_results if eid == entity_id), None)

        claims_payload = self.fetch_json(build_wikidata_claims_url(entity_id))
        if not isinstance(claims_payload, dict):
            return WikidataLookupAttempt(
                ticker=ticker, matched=False, matched_entity_id=entity_id, matched_label=matched_label,
                rejection_reason="Wikidata claims request failed or returned a malformed response.",
            )
        website = parse_wikidata_official_website(claims_payload)
        if website is None:
            return WikidataLookupAttempt(
                ticker=ticker, matched=False, matched_entity_id=entity_id, matched_label=matched_label,
                rejection_reason=f"Matched entity {entity_id} has no P856 (official website) claim.",
            )
        hostname = urlsplit(website).netloc
        if not hostname:
            return WikidataLookupAttempt(
                ticker=ticker, matched=False, matched_entity_id=entity_id, matched_label=matched_label,
                rejection_reason=f"Matched entity {entity_id}'s P856 claim {website!r} has no parseable hostname.",
            )
        return WikidataLookupAttempt(
            ticker=ticker, matched=True, hostname=hostname,
            matched_entity_id=entity_id, matched_label=matched_label,
        )
