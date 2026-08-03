"""ResolutionMemory: permanent, cumulative institutional knowledge about
every company's identity -- website, legal name, aliases, brand names,
parent company -- independent of which strategy or verification mechanism
produced it, today or in the future.

Before this module, a resolution run's by-products only ever survived if
they won: `HeuristicDomainResolver.resolve()` returned the first reachable
domain and silently dropped every candidate it tried and rejected along the
way; `WikidataOfficialWebsiteClient.lookup()` and
`GleifLegalEntityClient.lookup()` returned only their hits, degrading every
miss to "absent from the dict" with no record of *why* it missed.

**Observation vs. Claim -- two layers, not one.** An earlier version of
this module collapsed "what a source directly reported" and "what we
believe about the company" into one mutable record shape, itself a direct
reification of today's three-stage pipeline (propose -> strategy trace ->
probe) rather than a stable domain concept. This version separates them,
the same way `Hypothesis` (accumulating evidence) sits below `KnowledgeObject`
(the accepted synthesis) elsewhere in this codebase -- "agents propose, only
synthesis is authoritative" applied one layer down, to raw discovery
signals instead of research findings:

- An `Observation` is a directly-observed, **immutable** fact from one
  source at one point in time -- "Wikidata's P856 claim for entity Q123 was
  https://x.example", "an HTTP GET to https://x.example returned 200",
  "GLEIF's fuzzy-completions search for this name returned nothing". It
  never encodes a verdict about the company's identity as a whole, only
  what was literally seen. Once recorded, an Observation is never edited
  or reinterpreted -- a later run that learns more *adds* a new
  Observation, it never rewrites an old one.
- A `Claim` is a **synthesized** statement about a company's identity --
  "COMI's official website is cibeg.com" -- built from one or more
  supporting Observations (`Claim.supporting_observations`, indices into
  the record's own `observations` list, so every synthesis is traceable
  back to real evidence rather than asserted independently of it). Unlike
  an Observation, a Claim may evolve: a synthesis pass over a larger
  observation set can raise it from `UNVERIFIED` to `CONFIRMED`, or
  downgrade a previously `CONFIRMED` claim if a later observation
  disagrees.

The discovery layer (`company_entity_resolution.EntityResolutionEngine`)
persists Observations as a direct by-product of running its strategies; the
same engine's synthesis step (still today's unchanged strategy-priority/
first-match-wins/confidence-scoring logic -- see AD-63) is what produces
Claims from them. Anything consuming resolved identity -- a future decision
engine, a future discovery strategy deciding whether a ticker is worth
re-attempting -- should read `claims`, never `observations` directly: the
same reason nothing in this codebase reads a `Hypothesis`'s raw stage
evidence when a `KnowledgeObject` already exists.

Protocol-specific detail (an HTTP status code, a GLEIF record id) is never
a typed field of its own on either model -- it is folded into `evidence`
(free text, matching `gleif_lookup.LegalEntityMatch.evidence`/
`company_financial_registry.FinancialDocumentEntry.evidence` elsewhere in
this codebase) or, when it is itself a durable external identifier reusable
across sources (an LEI today, perhaps a national companies-registry number
tomorrow), `identifier`/`identifier_scheme`. Nothing here assumes today's
resolver implementations: a future strategy that observes facts via an
entirely different mechanism (a registry API, a human review step) plugs
into the exact same two shapes.

`resolved_hostname`/`legal_name`/`aliases`/`lei`/`brand_names`/
`parent_company` are this run's *currently accepted* values -- a
denormalized summary always reconstructible from `claims`' highest-
confidence `CONFIRMED` entries per attribute, kept alongside `claims`
purely for ergonomics. `brand_names`/`parent_company` stay honestly
`None`/`[]` until a real strategy exists to populate them -- no strategy in
this codebase resolves a brand name distinct from a legal name, or a
parent-company relationship, today. Same posture as `patterns.json`
staying `[]` until a dedicated `Pattern` model exists (TD-15): reserved for
a real future source, never filled with a guess.

Cross-run accumulation of `observations` (carrying prior runs' immutable
observations forward so a later synthesis pass sees the full history, not
just this run's) is a deliberate follow-up, not yet wired in here -- see
TD-67. Each `ResolutionMemoryRecord` version today holds only the
observations its own run produced; `claims` are synthesized from that
same-run set. The model already supports accumulating observations across
versions without a schema change once that follow-up lands.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from pathlib import Path

from pydantic import BaseModel, Field

from agx_research.storage.repository import JsonFileRepository


class ClaimAttribute(str, Enum):
    """What kind of identity fact an `Observation`/`Claim` is about -- a
    stable, closed set of *concepts*, not implementation names. Every
    attribute this codebase resolves today (website, legal name, alias) or
    reserves for a future source (brand name, parent company) shares this
    same enum, so a new attribute a future strategy resolves is a new enum
    member, never a new record shape."""

    WEBSITE = "website"
    LEGAL_NAME = "legal_name"
    ALIAS = "alias"
    BRAND_NAME = "brand_name"
    PARENT_COMPANY = "parent_company"


class ObservationOutcome(str, Enum):
    """What this one observation itself directly established -- a fact
    about the observation, never a verdict about the company's identity as
    a whole (that synthesis belongs to `Claim`)."""

    PROPOSED = "proposed"  # a source asserted this value; not itself a check
    VERIFIED = "verified"  # this observation itself confirms the value holds
    REFUTED = "refuted"  # this observation itself confirms the value does not hold
    ABSENT = "absent"  # the source was consulted and reported nothing for this attribute


class Observation(BaseModel):
    """One directly-observed, immutable fact from one source at one point
    in time. See module docstring for why this is kept separate from, and
    below, `Claim`."""

    attribute: ClaimAttribute
    source: str  # free-form provenance: "wikidata" | "web_search" | "gleif" | "heuristic_name_guess"
    observed_at: datetime = Field(default_factory=datetime.now)
    value: str | None = None  # None only when outcome is ABSENT
    outcome: ObservationOutcome
    identifier: str | None = None
    identifier_scheme: str | None = None
    evidence: str = ""
    rejection_reason: str | None = None  # populated only when outcome is REFUTED or ABSENT


class ClaimStatus(str, Enum):
    """The current synthesized verdict for a `Claim` -- protocol-agnostic
    on purpose. `CONFIRMED`/`REFUTED` replace what an HTTP-specific
    "reachable: bool" would only ever mean for web probing; the same two
    outcomes apply just as well to a future non-HTTP verification
    mechanism. `UNVERIFIED` is for a value a source proposed but that has
    no supporting verification observation yet (e.g. a lower-priority
    website candidate the resolver never reached because an earlier one
    already won) -- kept distinct from `REFUTED` so "never checked" is
    never fabricated into "checked and rejected". `NOT_FOUND` is for an
    attribute a source was consulted about but proposed no value for at
    all."""

    UNVERIFIED = "unverified"
    CONFIRMED = "confirmed"
    REFUTED = "refuted"
    NOT_FOUND = "not_found"


class Claim(BaseModel):
    """A synthesized statement about a company's identity, built from one
    or more supporting `Observation`s -- the unit a decision engine or a
    future discovery strategy should consume. See module docstring for why
    this is kept separate from, and above, `Observation`."""

    attribute: ClaimAttribute
    value: str | None = None  # None only when status is NOT_FOUND
    status: ClaimStatus
    confidence: float = 0.0
    identifier: str | None = None
    identifier_scheme: str | None = None
    rejection_reason: str | None = None
    # Indices into this same record's `observations` list -- every claim's
    # synthesis is traceable back to real, immutable evidence, never
    # asserted independently of it.
    supporting_observations: list[int] = Field(default_factory=list)


class ResolutionMemoryRecord(BaseModel):
    """One company's full entity-resolution memory as of one run. Versioned
    like every other entity in this codebase (`storage.JsonFileRepository`):
    `history(ticker)` reconstructs every past run's observations and
    claims, never just the latest, so a rejected domain from three runs ago
    is still readable, not overwritten."""

    id: str  # ticker
    version: int = 1
    ticker: str
    company_name: str
    attempted_at: datetime = Field(default_factory=datetime.now)

    # The immutable sensor readings this run produced.
    observations: list[Observation] = Field(default_factory=list)
    # This run's synthesis over those observations -- what a consumer
    # should actually read.
    claims: list[Claim] = Field(default_factory=list)

    # This run's currently-accepted values -- a denormalized summary always
    # reconstructible from `claims`' highest-confidence CONFIRMED entries
    # per attribute, kept for ergonomics only (see module docstring).
    resolved_hostname: str | None = None
    legal_name: str | None = None
    aliases: list[str] = Field(default_factory=list)
    lei: str | None = None

    # Reserved: no strategy in this codebase resolves these yet. Left
    # honestly empty rather than guessed -- see module docstring. Populated
    # the same way as every other attribute above the moment a real source
    # exists: as CONFIRMED `Claim`s with attribute=BRAND_NAME/PARENT_COMPANY,
    # no schema change required.
    brand_names: list[str] = Field(default_factory=list)
    parent_company: str | None = None


class ResolutionMemory(JsonFileRepository[ResolutionMemoryRecord]):
    def __init__(self, persist_path: Path | str | None = None):
        super().__init__(ResolutionMemoryRecord, persist_path)

    def record(self, entry: ResolutionMemoryRecord) -> ResolutionMemoryRecord:
        current = self.latest(entry.id)
        version = (current.version + 1) if current else 1
        return self.add(entry.model_copy(update={"version": version}))
