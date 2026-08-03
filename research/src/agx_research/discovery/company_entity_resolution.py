"""EntityResolutionEngine: the discovery problem, solved as its own
independent system, before any collector/parser work resumes.

Existing website-hint sources (`wikidata_lookup.WikidataOfficialWebsiteClient`,
`web_search_hints.load_web_search_domain_hints`, and
`discovery.engine.discover_company_directory_links`'s directory-chaining)
already each independently resolve at most a *website* hint per company.
Two real, structural gaps this module closes, neither by adding a fabricated
signal, both by making better use of signals this codebase already has or
can honestly obtain for free:

1. **Single-strategy-wins, not multi-strategy.** `cli.py`'s `discover-sources`
   command (and `scripts/build_financial_source_registry.py`, which never
   called Wikidata at all) each pick *one* hint per company by priority and
   discard the rest -- even though `TargetOrganization.domain_hints` is
   already a `list[str]` and `HeuristicDomainResolver.candidate_domains()`
   already tries every hint in order before falling back to a heuristic
   guess (see `domain_resolution.py`). A company whose top-priority hint
   turns out unreachable never gets a fallback try at a second, independent
   hint for the *same* company -- pure information loss, not a deliberate
   choice. `EntityResolutionEngine.resolve_website_candidates()` collects
   every strategy's result for a company into one ordered `domain_hints`
   list instead of picking a single winner up front, so
   `HeuristicDomainResolver` (unchanged) gets a real chance at all of them.

2. **No canonical-legal-entity or alias resolution existed at all.**
   Every existing strategy only ever answers "what's this company's
   website" -- nothing in this codebase resolved a company's registered
   legal name or its known aliases. `discovery.gleif_lookup
   .GleifLegalEntityClient` is a new, independent, free, no-key strategy
   for exactly that (the Global LEI Foundation's public registry), wired
   in here as `resolve_legal_entities()`.

Everything downstream of a resolved website is untouched: once
`HeuristicDomainResolver` confirms a real homepage,
`discovery.company_financial_discovery.discover_company_financial_sources`
(unchanged) still does all the real work of finding the Investor Relations
entry point, financial-report repository, and PDF locations. This module
is the discovery/resolution layer specifically, not a second copy of that
document-discovery logic.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol

from agx_research.acquisition_intelligence.domain_resolution import (
    DomainProbeAttempt,
    HeuristicDomainResolver,
    ProbeResult,
    ResolvedDomain,
)
from agx_research.acquisition_intelligence.target import TargetOrganization
from agx_research.collectors.fetcher import HttpFetcher
from agx_research.discovery.company_financial_discovery import discover_company_financial_sources
from agx_research.discovery.company_financial_registry import (
    CompanyFinancialSourceRecord,
    CompanyRegistryStatus,
)
from agx_research.discovery.gleif_lookup import GleifLegalEntityClient, GleifLookupAttempt, LegalEntityMatch
from agx_research.discovery.resolution_memory import (
    Claim,
    ClaimAttribute,
    ClaimStatus,
    Observation,
    ObservationOutcome,
    ResolutionMemoryRecord,
)
from agx_research.sources.spec import SourceCategory

_HEURISTIC_NAME_GUESS_SOURCE = "heuristic_name_guess"


class WebsiteHintStrategy(Protocol):
    """Anything with this shape can be plugged into `EntityResolutionEngine`
    as a website-hint source -- `WikidataOfficialWebsiteClient` and a thin
    wrapper around `load_web_search_domain_hints` both already match it
    without modification."""

    name: str

    def lookup(self, companies: dict[str, str]) -> dict[str, str]: ...


@dataclass
class HintCandidate:
    hostname: str
    source: str  # e.g. "wikidata" | "web_search" | "directory:egx_official"
    confidence: float


@dataclass
class EntityResolutionRecord:
    """One company's full resolution result across all six mission items,
    each with its own confidence/evidence/provenance -- a field left
    unresolved stays `None`/empty, never filled with a guess."""

    ticker: str
    company_name: str

    # 1-2: canonical legal entity + aliases
    legal_name: str | None = None
    legal_name_confidence: float = 0.0
    legal_name_evidence: str = ""
    legal_name_source: str | None = None
    aliases: list[str] = field(default_factory=list)
    lei: str | None = None

    # 3: official corporate website
    website_candidates: list[HintCandidate] = field(default_factory=list)
    resolved_domain: ResolvedDomain | None = None

    # 4-6: IR entry point, financial-report repository, PDF locations --
    # delegated entirely to the existing, unmodified
    # discover_company_financial_sources() once a website is resolved.
    financial_record: CompanyFinancialSourceRecord | None = None

    # Permanent, cumulative record of this attempt regardless of outcome --
    # see discovery.resolution_memory's module docstring for why this
    # exists alongside financial_record rather than folded into it.
    resolution_memory: ResolutionMemoryRecord | None = None

    @property
    def website_resolved(self) -> bool:
        return self.resolved_domain is not None

    @property
    def ir_entry_point_resolved(self) -> bool:
        return bool(self.financial_record and self.financial_record.documents)


@dataclass
class EntityResolutionReport:
    records: list[EntityResolutionRecord]

    @property
    def total(self) -> int:
        return len(self.records)

    def _rate(self, predicate) -> float:
        return (sum(1 for r in self.records if predicate(r)) / self.total) if self.total else 0.0

    @property
    def legal_name_resolution_rate(self) -> float:
        return self._rate(lambda r: r.legal_name is not None)

    @property
    def website_resolution_rate(self) -> float:
        return self._rate(lambda r: r.website_resolved)

    @property
    def ir_entry_point_resolution_rate(self) -> float:
        return self._rate(lambda r: r.ir_entry_point_resolved)

    def website_resolutions_by_source(self) -> dict[str, int]:
        """How many companies each website-hint strategy is actually
        responsible for resolving -- i.e. whose *winning* candidate (the
        one `HeuristicDomainResolver` actually confirmed reachable) came
        from that strategy. Answers "which strategy is pulling its
        weight" without double-counting a company under every strategy
        that merely proposed a hint for it."""
        counts: dict[str, int] = {}
        for record in self.records:
            if record.resolved_domain is None:
                continue
            winning = next(
                (c for c in record.website_candidates if c.hostname == record.resolved_domain.domain),
                None,
            )
            source = winning.source if winning else record.resolved_domain.origin
            counts[source] = counts.get(source, 0) + 1
        return counts


class EntityResolutionEngine:
    def __init__(
        self,
        *,
        website_strategies: list[WebsiteHintStrategy],
        legal_entity_client: GleifLegalEntityClient | None = None,
        domain_resolver: HeuristicDomainResolver,
        fetcher: HttpFetcher,
    ):
        self.website_strategies = website_strategies
        self.legal_entity_client = legal_entity_client
        self.domain_resolver = domain_resolver
        self.fetcher = fetcher

    def resolve_website_candidates(
        self, companies: dict[str, str]
    ) -> dict[str, list[HintCandidate]]:
        """Runs every configured strategy and keeps every result -- never
        stops at the first strategy that resolves a company, so a second,
        independent hint is still available if the first turns out
        unreachable. Order of `website_strategies` is the confidence
        order: earlier strategies' candidates are tried first by
        `HeuristicDomainResolver`."""
        candidates, _absent = self._resolve_website_candidates_and_absent_sources(companies)
        return candidates

    def _resolve_website_candidates_and_absent_sources(
        self, companies: dict[str, str]
    ) -> tuple[dict[str, list[HintCandidate]], dict[str, list[tuple[str, str | None]]]]:
        """Same resolution as `resolve_website_candidates`, plus a per-ticker
        list of `(source, rejection_reason)` for every strategy that
        proposed *nothing at all* this run, for strategies that expose
        `lookup_with_trace` -- currently
        `wikidata_lookup.WikidataOfficialWebsiteClient`. Calling
        `lookup_with_trace` once here (instead of `lookup` here and
        `lookup_with_trace` again elsewhere) is what keeps this a single
        network round-trip per strategy per run, not two. A source that
        *did* propose a value needs no separate entry here -- its proposal
        becomes a `resolution_memory.Observation` directly from the
        returned `HintCandidate`."""
        candidates: dict[str, list[HintCandidate]] = {ticker: [] for ticker in companies}
        absent_sources: dict[str, list[tuple[str, str | None]]] = {ticker: [] for ticker in companies}
        strategy_count = len(self.website_strategies) or 1
        for rank, strategy in enumerate(self.website_strategies):
            confidence = round(1.0 - (rank / strategy_count) * 0.5, 4)
            lookup_with_trace = getattr(strategy, "lookup_with_trace", None)
            if lookup_with_trace is not None:
                for ticker, attempt in lookup_with_trace(companies).items():
                    if ticker not in candidates:
                        continue
                    if attempt.matched and attempt.hostname:
                        candidates[ticker].append(
                            HintCandidate(hostname=attempt.hostname, source=strategy.name, confidence=confidence)
                        )
                    else:
                        absent_sources[ticker].append((strategy.name, attempt.rejection_reason))
            else:
                hints = strategy.lookup(companies)
                for ticker, hostname in hints.items():
                    if ticker in candidates:
                        candidates[ticker].append(
                            HintCandidate(hostname=hostname, source=strategy.name, confidence=confidence)
                        )
        return candidates, absent_sources

    def resolve_legal_entities(self, companies: dict[str, str]) -> dict[str, LegalEntityMatch]:
        matches, _attempts = self._resolve_legal_entities_and_attempts(companies)
        return matches

    def _resolve_legal_entities_and_attempts(
        self, companies: dict[str, str]
    ) -> tuple[dict[str, LegalEntityMatch], dict[str, GleifLookupAttempt]]:
        if self.legal_entity_client is None:
            return {}, {}
        attempts = self.legal_entity_client.lookup_with_trace(companies)
        matches = {t: a.match for t, a in attempts.items() if a.matched and a.match is not None}
        return matches, attempts

    def resolve(
        self,
        companies: dict[str, str],
        *,
        existing_records: dict[str, CompanyFinancialSourceRecord] | None = None,
    ) -> EntityResolutionReport:
        """Runs every resolution step for every company in `companies`
        (ticker -> display name) and returns one report. `existing_records`
        (ticker -> its current `CompanyFinancialSourceRecord`, if any) lets
        a caller preserve index membership / avoid re-discovering an
        already-`VALIDATED` company -- the same resumability contract
        `CompanyFinancialSourceRegistry.is_resumable_skip` already
        enforces; this method itself never mutates a stored registry."""
        existing_records = existing_records or {}
        website_candidates, absent_website_sources = self._resolve_website_candidates_and_absent_sources(
            companies
        )
        legal_entities, legal_entity_attempts = self._resolve_legal_entities_and_attempts(companies)

        records: list[EntityResolutionRecord] = []
        for ticker, name in companies.items():
            existing = existing_records.get(ticker)
            if existing is not None and existing.status == CompanyRegistryStatus.VALIDATED:
                continue

            record = EntityResolutionRecord(ticker=ticker, company_name=name)
            record.website_candidates = sorted(
                website_candidates.get(ticker, []), key=lambda c: -c.confidence
            )

            match = legal_entities.get(ticker)
            if match is not None:
                record.legal_name = match.legal_name
                record.legal_name_confidence = match.match_confidence
                record.legal_name_evidence = match.evidence
                record.legal_name_source = "gleif"
                record.aliases = match.aliases
                record.lei = match.lei

            target = TargetOrganization(
                id=f"entity_resolution_{ticker.lower()}",
                name=name,
                category=SourceCategory.COMPANY,
                domain_hints=[c.hostname for c in record.website_candidates],
                company_ticker=ticker,
            )
            record.resolved_domain, domain_probe_attempts = self.domain_resolver.resolve_with_trace(target)

            base_record = existing or CompanyFinancialSourceRecord(
                id=ticker, ticker=ticker, company_name=name,
            )
            if record.resolved_domain is not None:
                result = discover_company_financial_sources(
                    self.fetcher, base_record, record.resolved_domain.homepage_url
                )
                winning = next(
                    (c for c in record.website_candidates if c.hostname == record.resolved_domain.domain),
                    None,
                )
                record.financial_record = result.model_copy(
                    update={"homepage_hint_source": winning.source if winning else record.resolved_domain.origin}
                )
            else:
                record.financial_record = base_record.model_copy(
                    update={
                        "status": CompanyRegistryStatus.HOMEPAGE_UNRESOLVED,
                        "blocked_reason": "No website-hint strategy produced a reachable domain this run.",
                    }
                )

            record.resolution_memory = _build_resolution_memory_record(
                ticker=ticker,
                company_name=name,
                website_candidates=record.website_candidates,
                absent_website_sources=absent_website_sources.get(ticker, []),
                domain_probe_attempts=domain_probe_attempts,
                resolved_domain=record.resolved_domain,
                legal_entity_attempt=legal_entity_attempts.get(ticker),
                legal_name=record.legal_name,
                aliases=record.aliases,
                lei=record.lei,
            )

            records.append(record)

        return EntityResolutionReport(records=records)


def _probe_evidence(probe: ProbeResult) -> str:
    if probe.status_code is not None:
        return f"HTTP {probe.status_code}"
    return probe.error or ""


def _probe_rejection_reason(probe: ProbeResult) -> str | None:
    if probe.reachable:
        return None
    return probe.error or f"Homepage probe returned HTTP {probe.status_code}."


def _build_resolution_memory_record(
    *,
    ticker: str,
    company_name: str,
    website_candidates: list[HintCandidate],
    absent_website_sources: list[tuple[str, str | None]],
    domain_probe_attempts: list[DomainProbeAttempt],
    resolved_domain: ResolvedDomain | None,
    legal_entity_attempt: GleifLookupAttempt | None,
    legal_name: str | None,
    aliases: list[str],
    lei: str | None,
) -> ResolutionMemoryRecord:
    """Assembles this run's immutable `Observation`s and the `Claim`s
    synthesized from them into one permanent record -- see
    `discovery.resolution_memory`'s module docstring for why the two are
    kept separate and what real signal each field traces back to."""
    observations: list[Observation] = []
    claims: list[Claim] = []

    # A website-hint strategy that proposed nothing at all this run is its
    # own observation and its own NOT_FOUND claim -- there is no candidate
    # value to later attach a probe observation to.
    for source, reason in absent_website_sources:
        observations.append(
            Observation(
                attribute=ClaimAttribute.WEBSITE, source=source,
                outcome=ObservationOutcome.ABSENT, rejection_reason=reason,
            )
        )
        claims.append(
            Claim(
                attribute=ClaimAttribute.WEBSITE, status=ClaimStatus.NOT_FOUND,
                rejection_reason=reason, supporting_observations=[len(observations) - 1],
            )
        )

    # Every strategy's proposed hostname is a PROPOSED observation, whether
    # or not it ever gets probed.
    proposal_index_by_hostname: dict[str, int] = {}
    source_by_hostname: dict[str, str] = {}
    for candidate in website_candidates:
        observations.append(
            Observation(
                attribute=ClaimAttribute.WEBSITE, source=candidate.source,
                value=candidate.hostname, outcome=ObservationOutcome.PROPOSED,
            )
        )
        proposal_index_by_hostname[candidate.hostname] = len(observations) - 1
        source_by_hostname[candidate.hostname] = candidate.source

    # Every domain actually probed is a VERIFIED/REFUTED observation --
    # attributed to whichever strategy proposed it, or to the heuristic
    # name-guess source when no strategy proposed it at all (only possible
    # when the candidate list was empty to begin with).
    probe_index_by_domain: dict[str, int] = {}
    for attempt in domain_probe_attempts:
        reachable = attempt.probe.reachable
        source = source_by_hostname.get(attempt.domain, _HEURISTIC_NAME_GUESS_SOURCE)
        observations.append(
            Observation(
                attribute=ClaimAttribute.WEBSITE, source=source, value=attempt.domain,
                outcome=ObservationOutcome.VERIFIED if reachable else ObservationOutcome.REFUTED,
                evidence=_probe_evidence(attempt.probe),
                rejection_reason=_probe_rejection_reason(attempt.probe),
            )
        )
        probe_index_by_domain[attempt.domain] = len(observations) - 1

    # Synthesize one WEBSITE claim per proposed hostname: CONFIRMED/REFUTED
    # if it was probed, UNVERIFIED if a higher-priority candidate already
    # won and this one was never reached.
    for candidate in website_candidates:
        proposal_idx = proposal_index_by_hostname[candidate.hostname]
        probe_idx = probe_index_by_domain.get(candidate.hostname)
        if probe_idx is None:
            claims.append(
                Claim(
                    attribute=ClaimAttribute.WEBSITE, value=candidate.hostname,
                    status=ClaimStatus.UNVERIFIED, confidence=candidate.confidence,
                    supporting_observations=[proposal_idx],
                )
            )
        else:
            confirmed = observations[probe_idx].outcome == ObservationOutcome.VERIFIED
            claims.append(
                Claim(
                    attribute=ClaimAttribute.WEBSITE, value=candidate.hostname,
                    status=ClaimStatus.CONFIRMED if confirmed else ClaimStatus.REFUTED,
                    confidence=candidate.confidence,
                    rejection_reason=observations[probe_idx].rejection_reason,
                    supporting_observations=[proposal_idx, probe_idx],
                )
            )

    # A heuristic name-guess has no strategy proposal to pair with -- its
    # probe observation is its own, single-observation claim.
    for attempt in domain_probe_attempts:
        if attempt.domain in proposal_index_by_hostname:
            continue
        probe_idx = probe_index_by_domain[attempt.domain]
        confirmed = observations[probe_idx].outcome == ObservationOutcome.VERIFIED
        claims.append(
            Claim(
                attribute=ClaimAttribute.WEBSITE, value=attempt.domain,
                status=ClaimStatus.CONFIRMED if confirmed else ClaimStatus.REFUTED,
                rejection_reason=observations[probe_idx].rejection_reason,
                supporting_observations=[probe_idx],
            )
        )

    if legal_entity_attempt is not None:
        if legal_entity_attempt.matched and legal_entity_attempt.match is not None:
            match = legal_entity_attempt.match
            observations.append(
                Observation(
                    attribute=ClaimAttribute.LEGAL_NAME, source="gleif", value=match.legal_name,
                    outcome=ObservationOutcome.VERIFIED,
                    identifier=match.lei, identifier_scheme="LEI", evidence=match.evidence,
                )
            )
            claims.append(
                Claim(
                    attribute=ClaimAttribute.LEGAL_NAME, value=match.legal_name,
                    status=ClaimStatus.CONFIRMED, confidence=match.match_confidence,
                    identifier=match.lei, identifier_scheme="LEI",
                    supporting_observations=[len(observations) - 1],
                )
            )
            for alias in match.aliases:
                observations.append(
                    Observation(
                        attribute=ClaimAttribute.ALIAS, source="gleif", value=alias,
                        outcome=ObservationOutcome.VERIFIED,
                        identifier=match.lei, identifier_scheme="LEI", evidence=match.evidence,
                    )
                )
                claims.append(
                    Claim(
                        attribute=ClaimAttribute.ALIAS, value=alias,
                        status=ClaimStatus.CONFIRMED, confidence=match.match_confidence,
                        identifier=match.lei, identifier_scheme="LEI",
                        supporting_observations=[len(observations) - 1],
                    )
                )
        else:
            observations.append(
                Observation(
                    attribute=ClaimAttribute.LEGAL_NAME, source="gleif",
                    outcome=ObservationOutcome.ABSENT,
                    rejection_reason=legal_entity_attempt.rejection_reason,
                )
            )
            claims.append(
                Claim(
                    attribute=ClaimAttribute.LEGAL_NAME, status=ClaimStatus.NOT_FOUND,
                    rejection_reason=legal_entity_attempt.rejection_reason,
                    supporting_observations=[len(observations) - 1],
                )
            )

    return ResolutionMemoryRecord(
        id=ticker,
        ticker=ticker,
        company_name=company_name,
        observations=observations,
        claims=claims,
        resolved_hostname=resolved_domain.domain if resolved_domain else None,
        legal_name=legal_name,
        aliases=aliases,
        lei=lei,
    )
