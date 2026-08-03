"""GLEIF Legal Entity Identifier (LEI) lookup: a free, structured, no-key
path to a company's **canonical legal entity name and known aliases** --
a capability nothing in this package had before (`wikidata_lookup.py` and
`web_search_hints.py` only ever resolve a *website*, never a legal name).

GLEIF (the Global Legal Entity Identifier Foundation) operates the
public registry behind the ISO 17442 LEI standard; its REST API
(`https://api.gleif.org/api/v1/`) is free, documented, and requires no
API key -- the same confidence tier as Wikidata's action API. Every LEI
record's `entity.legalName` is the registered legal name a company itself
filed with its Local Operating Unit, and `entity.otherNames`/
`entity.transliteratedOtherNames` are real, declared trading names/
alternate-language names -- i.e. real aliases, not a guess at what a
company might also be called.

Per-company name search via the fuzzy-completions endpoint (not an exact
`filter[entity.legalName]=` match): a listed company's commonly-known
display name (e.g. "Juhayna Food Industries") rarely matches its exact
registered legal name string (e.g. "JUHAYNA FOOD INDUSTRIES S.A.E."), so
an exact filter would systematically under-match. The fuzzy-completions
endpoint is GLEIF's own documented mechanism for exactly this "find the
LEI record for a company I know by a close but not exact name" case.

Matching reuses `discovery.engine.significant_tokens`'s exact name-token-
overlap discipline used everywhere else in this package (Wikidata,
company-directory links) -- no new matching rule invented here.

Honesty note (same posture as every other network-dependent module in
this package): the exact GLEIF response shape below is this module's
best-documented understanding of GLEIF's public, versioned JSON:API
contract, not something fetched live from within this development
sandbox (no outbound egress here -- see `acquisition_intelligence.live`'s
own module docstring). Like every hint source in this package, a result
here is never trusted directly: it must be independently verified by a
real, live-network run before being treated as confirmed (AD-16/AD-24)
-- see `docs/ARCHITECTURE_DECISIONS.md`'s entity-resolution entry for
exactly how that verification was done.
"""

from __future__ import annotations

from typing import Callable
from urllib.parse import quote

from pydantic import BaseModel, Field

from agx_research.discovery.engine import significant_tokens

FetchJson = Callable[[str], object]

GLEIF_API_BASE = "https://api.gleif.org/api/v1"
_FUZZY_COMPLETIONS_FIELD = "entity.legalName"
_FUZZY_RESULT_LIMIT = 5


class LegalEntityMatch(BaseModel):
    """One real, matched GLEIF LEI record for a company -- every field
    traces to that record; nothing here is inferred or filled in."""

    lei: str
    legal_name: str
    aliases: list[str] = Field(default_factory=list)
    jurisdiction_country: str | None = None
    registration_status: str | None = None
    match_confidence: float = Field(ge=0.0, le=1.0)
    evidence: str


def build_fuzzy_completions_url(name: str) -> str:
    return (
        f"{GLEIF_API_BASE}/fuzzycompletions"
        f"?field={_FUZZY_COMPLETIONS_FIELD}&q={quote(name)}"
    )


def build_lei_record_url(lei: str) -> str:
    return f"{GLEIF_API_BASE}/lei-records/{quote(lei)}"


def parse_fuzzy_completions(payload: dict) -> list[tuple[str, str]]:
    """`payload` is a real GLEIF `/fuzzycompletions` response: a JSON:API
    document whose `data` entries carry `attributes.value` (the matched
    legal name string) and a relationship to the matching LEI record
    (`relationships.lei-records.data.id`). An entry missing either is
    skipped -- nothing to match against, not a guess.
    """
    results: list[tuple[str, str]] = []
    for entry in payload.get("data") or []:
        attributes = entry.get("attributes") or {}
        legal_name = attributes.get("value")
        lei = (
            ((entry.get("relationships") or {}).get("lei-records") or {}).get("data") or {}
        ).get("id")
        if legal_name and lei:
            results.append((lei, legal_name))
    return results


def parse_lei_record(payload: dict) -> LegalEntityMatch | None:
    """`payload` is a real GLEIF `/lei-records/{lei}` response. Returns
    `None` if the expected `data.attributes.entity` shape isn't present --
    never a partially-filled guess.
    """
    data = payload.get("data")
    if not isinstance(data, dict):
        return None
    attributes = data.get("attributes") or {}
    lei = attributes.get("lei")
    entity = attributes.get("entity") or {}
    legal_name = (entity.get("legalName") or {}).get("name")
    if not lei or not legal_name:
        return None

    aliases = [
        name.get("name")
        for name in (entity.get("otherNames") or []) + (entity.get("transliteratedOtherNames") or [])
        if isinstance(name, dict) and name.get("name")
    ]
    return LegalEntityMatch(
        lei=lei,
        legal_name=legal_name,
        aliases=sorted(set(aliases)),
        jurisdiction_country=(entity.get("legalAddress") or {}).get("country"),
        registration_status=(attributes.get("registration") or {}).get("status"),
        match_confidence=0.0,  # set by the caller once matched against the queried name
        evidence=f"GLEIF LEI record {lei}: legalName={legal_name!r}",
    )


def _best_match(candidates: list[tuple[str, str]], name: str) -> tuple[str, str, float] | None:
    """Token-overlap scoring, same discipline as `wikidata_lookup
    ._find_matching_entity`: the queried name's significant tokens must be
    a subset of the candidate legal name's tokens for it to count as a
    real match at all. Confidence is the fraction of the candidate's own
    tokens the query also names, so an exact "Juhayna Food Industries" ==
    "Juhayna Food Industries S.A.E." match scores higher than a query that
    matches only a generic word.
    """
    query_tokens = significant_tokens(name)
    if not query_tokens:
        return None
    best: tuple[str, str, float] | None = None
    for lei, legal_name in candidates:
        candidate_tokens = significant_tokens(legal_name)
        if not query_tokens.issubset(candidate_tokens):
            continue
        confidence = len(query_tokens) / len(candidate_tokens) if candidate_tokens else 0.0
        if best is None or confidence > best[2]:
            best = (lei, legal_name, confidence)
    return best


class GleifLegalEntityClient:
    name = "gleif"

    def __init__(self, fetch_json: FetchJson):
        self.fetch_json = fetch_json

    def lookup(self, companies: dict[str, str]) -> dict[str, LegalEntityMatch]:
        """Ticker -> `LegalEntityMatch` for every company a real GLEIF
        fuzzy-completions search finds a token-overlap match for, and
        whose matched LEI record fetch succeeds. One company failing
        (unreachable endpoint, no match, malformed record) never blocks
        the rest -- same honest per-company degradation as
        `WikidataOfficialWebsiteClient.lookup`.
        """
        found: dict[str, LegalEntityMatch] = {}
        for ticker, name in companies.items():
            match = self._lookup_one(name)
            if match is not None:
                found[ticker] = match
        return found

    def _lookup_one(self, name: str) -> LegalEntityMatch | None:
        completions_payload = self.fetch_json(build_fuzzy_completions_url(name))
        if not isinstance(completions_payload, dict):
            return None
        candidates = parse_fuzzy_completions(completions_payload)
        best = _best_match(candidates, name)
        if best is None:
            return None
        lei, _legal_name, confidence = best

        record_payload = self.fetch_json(build_lei_record_url(lei))
        if not isinstance(record_payload, dict):
            return None
        match = parse_lei_record(record_payload)
        if match is None:
            return None
        return match.model_copy(update={"match_confidence": round(confidence, 4)})
