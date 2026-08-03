"""ResolutionMemory: permanent, cumulative record of every entity-resolution
attempt `discovery.company_entity_resolution.EntityResolutionEngine` has ever
made for a company -- independent of whether that attempt succeeded.

Before this module, a resolution run's by-products only ever survived if they
won: `HeuristicDomainResolver.resolve()` returned the first reachable domain
and silently dropped every candidate it tried and rejected along the way;
`WikidataOfficialWebsiteClient.lookup()` and `GleifLegalEntityClient.lookup()`
returned only their hits, degrading every miss to "absent from the dict" with
no record of *why* it missed. Re-running discovery therefore re-derived the
same rejected domains and the same "no match" verdicts from scratch every
time, and a human auditing low coverage (e.g. "why are 61 EGX30/EGX70
companies still unresolved") had to reconstruct the reasoning by reading code
and cross-referencing external files rather than reading a persisted record.

This module is the fix: it never re-decides anything
(`company_entity_resolution.EntityResolutionEngine`'s resolution logic --
strategy order, first-match-wins, confidence scoring -- is completely
unchanged) -- it only makes sure every attempt that logic already makes is
written down, win or lose, exactly once per run, so discovery becomes a
cumulative knowledge system instead of a stateless search that forgets its
own history the moment the process exits. Same "index over evidence, not a
parallel source of truth" discipline as `graph.KnowledgeGraph` and
`discovery.company_financial_registry`: every field here traces back to a
real probe, a real API response, or a real match/rejection decision already
made by an existing strategy -- nothing is inferred or guessed to fill in a
gap.

`brand_names`/`parent_company` stay honestly `None`/`[]` until a real
strategy exists to populate them -- no strategy in this codebase resolves a
brand name distinct from a legal name, or a parent-company relationship,
today. Same posture as `patterns.json` staying `[]` until a dedicated
`Pattern` model exists (TD-15): the field is reserved so a future real
source has somewhere honest to write to, not filled with a guess now.
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

from pydantic import BaseModel, Field

from agx_research.storage.repository import JsonFileRepository


class ProposedWebsiteCandidate(BaseModel):
    """One website-hint strategy's proposed hostname for a company this run
    -- every strategy's proposal, not just the one `HeuristicDomainResolver`
    eventually confirmed reachable (see
    `company_entity_resolution.EntityResolutionEngine.resolve_website_candidates`,
    which already collects every strategy's result before this module
    existed; the gap this closes is that nothing downstream persisted it)."""

    hostname: str
    source: str  # e.g. "wikidata" | "web_search"
    confidence: float


class WebsiteSourceAttempt(BaseModel):
    """One website-hint *strategy's* own attempt for a company, independent
    of whether its proposed hostname (if any) was ever probed -- e.g.
    `wikidata_lookup.WikidataLookupAttempt` degrading to "no P856 claim" or
    "no matching entity" without ever reaching `HeuristicDomainResolver` at
    all. Only recorded for strategies that expose `lookup_with_trace`
    (currently Wikidata); a strategy with no such reasoning to report
    (e.g. the static, deterministic web-search snapshot) is fully captured
    already by `ProposedWebsiteCandidate`/`WebsiteProbeAttempt`."""

    source: str
    matched: bool
    hostname: str | None = None
    rejection_reason: str | None = None  # populated only when matched is False


class WebsiteProbeAttempt(BaseModel):
    """One candidate domain actually probed over the network this run, from
    `acquisition_intelligence.domain_resolution.HeuristicDomainResolver
    .resolve_with_trace`. A domain that was never reached (because an
    earlier, higher-confidence candidate already won) never appears here --
    "never attempted" and "attempted and rejected" are kept distinct on
    purpose, never collapsed."""

    domain: str
    origin: str  # "hint" | "heuristic"
    reachable: bool
    status_code: int | None = None
    error: str | None = None
    rejection_reason: str | None = None  # populated only when reachable is False


class LegalEntityAttempt(BaseModel):
    """One legal-entity-resolution attempt this run (currently GLEIF only --
    see `gleif_lookup.GleifLookupAttempt`), whatever the outcome."""

    source: str  # "gleif"
    matched: bool
    lei: str | None = None
    legal_name: str | None = None
    aliases: list[str] = Field(default_factory=list)
    match_confidence: float | None = None
    evidence: str | None = None
    rejection_reason: str | None = None  # populated only when matched is False


class ResolutionMemoryRecord(BaseModel):
    """One company's full entity-resolution memory as of one run. Versioned
    like every other entity in this codebase (`storage.JsonFileRepository`):
    `history(ticker)` reconstructs every past run's attempts, never just the
    latest, so a rejected domain from three runs ago is still readable, not
    overwritten."""

    id: str  # ticker
    version: int = 1
    ticker: str
    company_name: str
    attempted_at: datetime = Field(default_factory=datetime.now)

    # Every website candidate any strategy proposed this run, and every
    # domain actually probed as a result (the reachable one, if any, plus
    # every rejected one tried before it).
    website_candidates_proposed: list[ProposedWebsiteCandidate] = Field(default_factory=list)
    website_source_attempts: list[WebsiteSourceAttempt] = Field(default_factory=list)
    website_probe_attempts: list[WebsiteProbeAttempt] = Field(default_factory=list)
    resolved_hostname: str | None = None

    # Every legal-entity-resolution attempt this run, matched or not.
    legal_entity_attempts: list[LegalEntityAttempt] = Field(default_factory=list)
    legal_name: str | None = None
    aliases: list[str] = Field(default_factory=list)
    lei: str | None = None

    # Reserved: no strategy in this codebase resolves these yet. Left
    # honestly empty rather than guessed -- see module docstring.
    brand_names: list[str] = Field(default_factory=list)
    parent_company: str | None = None
    parent_company_source: str | None = None
    parent_company_evidence: str | None = None


class ResolutionMemory(JsonFileRepository[ResolutionMemoryRecord]):
    def __init__(self, persist_path: Path | str | None = None):
        super().__init__(ResolutionMemoryRecord, persist_path)

    def record(self, entry: ResolutionMemoryRecord) -> ResolutionMemoryRecord:
        current = self.latest(entry.id)
        version = (current.version + 1) if current else 1
        return self.add(entry.model_copy(update={"version": version}))
