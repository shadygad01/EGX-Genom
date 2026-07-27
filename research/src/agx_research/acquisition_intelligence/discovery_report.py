"""Standalone weekly Discovery workflow support: run the Acquisition
Intelligence Engine against every catalogued `PLANNED`/`CANDIDATE` source
that has a matching `TargetOrganization`, produce a structured, evidenced
report per source, and cache the result so an unchanged source is not
re-probed on every run.

Scope is deliberately narrow: only non-per-constituent, non-integrated-via
sources are in play here (see `plan_discovery_targets`). Per-constituent
Investor Relations discovery and provider legs already wired inside a
composite collector (`yahoo_finance`/`stockanalysis`/`mubasher`) are out of
scope for this report -- see their own docstrings for why.

Nothing here ever promotes a source to `IMPLEMENTED` by itself: a
`SourceDiscoveryOutcome` only ever *recommends* a next step for a human
maintainer (write/verify a concrete collector, or -- for the one access
method with an existing generic, already-precedented collector,
`RssNewsCollector` -- flip the status once real content is confirmed to
parse). Promotion still goes through a reviewed pull request, never a
direct commit, exactly like every other promotion in this codebase goes
through a gate rather than a shortcut.
"""

from __future__ import annotations

import hashlib
from datetime import datetime, timedelta
from pathlib import Path

from pydantic import BaseModel, Field

from agx_research.acquisition_intelligence.engine import (
    AcquisitionIntelligenceEngine,
    AcquisitionResult,
)
from agx_research.acquisition_intelligence.target import TargetOrganization
from agx_research.sources.registry import SourceRegistry
from agx_research.sources.spec import AccessMethod, SourceSpec, SourceStatus
from agx_research.storage.repository import JsonFileRepository

DEFAULT_TTL_DAYS = 30

# Access methods this codebase already has a real, tested, generic
# collector for -- the exact precedent already used for Enterprise/Al
# Borsa/Masrawy/FRA/Sky News Arabia: a verified feed URL plus this
# collector class is enough to flip PLANNED -> IMPLEMENTED without new
# parsing code, once a maintainer confirms it actually returns real items.
_READY_GENERIC_COLLECTOR_BY_ACCESS_METHOD: dict[AccessMethod, str] = {
    AccessMethod.RSS_FEED: "RssNewsCollector",
}


class EndpointCandidate(BaseModel):
    """One ranked candidate the engine considered for a target, whether or
    not it was ultimately selected -- `endpoint_candidates.json`'s row
    shape, so a maintainer can see every real alternative, not just the
    winner.
    """

    source_id: str
    discovered_url: str
    access_method_guess: str
    legality_verdict: str
    robots_allows: bool | None
    stability_score: float
    historical_score: float
    composite_score: float
    selected: bool


class SourceDiscoveryOutcome(BaseModel):
    """One row of `discovery_report.json` -- the complete, evidenced
    picture of one catalogued source's discovery attempt (or cached
    result) this run.
    """

    source_id: str
    previous_status: str
    current_status: str
    discovered_endpoints: list[str] = Field(default_factory=list)
    verification_result: str
    reason_for_failure: str | None = None
    evidence: list[str] = Field(default_factory=list)
    recommendation: str
    confidence: float = 0.0
    from_cache: bool = False
    verified_at: datetime


class DiscoveryHistoryEntry(BaseModel):
    """Persisted, incremental cache of the last real (non-cached) discovery
    attempt for one source -- what makes re-running this weekly cheap and
    non-repetitive instead of re-probing every target from scratch every
    time (see `docs/DATA_ACQUISITION.md`'s Discovery workflow section).
    """

    id: str  # == source_id
    version: int = 1
    source_id: str
    verified_at: datetime
    ttl_expires_at: datetime
    input_fingerprint: str
    outcome: SourceDiscoveryOutcome


class DiscoveryHistoryRepository(JsonFileRepository[DiscoveryHistoryEntry]):
    def __init__(self, persist_path: Path | str | None = None):
        super().__init__(DiscoveryHistoryEntry, persist_path)


def _target_fingerprint(target: TargetOrganization) -> str:
    """Changes whenever a target's own inputs change (a new domain hint
    added, priority changed, ...) -- used to force a fresh check even
    within the TTL window, since "the endpoint changed" in the requester's
    own sense starts with what we told the engine to look for.
    """
    return hashlib.sha256(target.model_dump_json(exclude={"notes"}).encode()).hexdigest()


def plan_discovery_targets(
    registry: SourceRegistry, targets: list[TargetOrganization]
) -> tuple[list[tuple[SourceSpec, TargetOrganization]], list[SourceSpec]]:
    """Split the catalog into (a) PLANNED/CANDIDATE sources with a real
    `TargetOrganization` to run discovery against, and (b) PLANNED/CANDIDATE
    sources with no target yet -- reported as `not_targeted`, never
    fabricated a domain for. Per-constituent markers (`per_constituent`)
    and sources already operating as a provider leg inside a composite
    collector (`integrated_via` set -- their real endpoint is already known
    and wired in code, discovery would be redundant) are excluded from
    both lists entirely.
    """
    targets_by_source_id = {
        t.existing_source_id: t
        for t in targets
        if t.existing_source_id and not t.per_constituent
    }
    in_scope = [
        spec
        for spec in registry.all_latest()
        if spec.status in (SourceStatus.PLANNED,) and not spec.integrated_via
    ]
    targeted = [
        (spec, targets_by_source_id[spec.id]) for spec in in_scope if spec.id in targets_by_source_id
    ]
    untargeted = [spec for spec in in_scope if spec.id not in targets_by_source_id]
    return targeted, untargeted


def _recommendation_for_result(result: AcquisitionResult) -> str:
    if not result.registered or result.selected is None or result.generated_spec is None:
        return (
            "No action -- no candidate cleared verification this run. Re-check after "
            "the next scheduled discovery run, or supply a corrected domain hint if the "
            "target organization's public domain is known to differ from what was tried."
        )
    ready_collector = _READY_GENERIC_COLLECTOR_BY_ACCESS_METHOD.get(
        result.selected.candidate.access_method_guess
    )
    if ready_collector:
        return (
            f"Endpoint verified and stable. A generic, already-tested collector "
            f"({ready_collector}) already covers this access method -- a maintainer only "
            "needs to confirm the feed actually returns real items before flipping "
            "status to IMPLEMENTED (same precedent as Enterprise/Al Borsa/Masrawy)."
        )
    return (
        "Endpoint verified and stable, but this access method has no ready generic "
        "collector yet -- a maintainer must write and test a concrete collector against "
        "this specific endpoint's real response shape before flipping status to "
        "IMPLEMENTED (see AD-16/AD-24; never flip status on discovery evidence alone)."
    )


def _outcome_for_result(spec: SourceSpec, result: AcquisitionResult) -> SourceDiscoveryOutcome:
    now = datetime.now()
    if result.registered and result.selected is not None and result.generated_spec is not None:
        evidence = [
            e for e in (
                result.selected.legality.evidence,
                *result.selected.stability.evidence,
                result.selected.historical.evidence,
            ) if e
        ]
        return SourceDiscoveryOutcome(
            source_id=spec.id,
            previous_status=spec.status.value,
            current_status=result.generated_spec.status.value,
            discovered_endpoints=[result.selected.candidate.discovered_url],
            verification_result="verified_reachable",
            reason_for_failure=None,
            evidence=evidence,
            recommendation=_recommendation_for_result(result),
            confidence=result.selected.composite_score,
            verified_at=now,
        )

    reason = result.reason or "No reason recorded."
    if reason.startswith("No reachable domain"):
        verification_result = "no_reachable_domain"
    elif "Homepage reachable but" in reason:
        verification_result = "homepage_unreachable"
    elif "No acquisition-method candidates" in reason:
        verification_result = "no_candidates_discovered"
    elif "legality gate" in reason:
        verification_result = "legality_blocked"
    else:
        verification_result = "not_verified"

    return SourceDiscoveryOutcome(
        source_id=spec.id,
        previous_status=spec.status.value,
        current_status=spec.status.value,
        discovered_endpoints=[],
        verification_result=verification_result,
        reason_for_failure=reason,
        evidence=[],
        recommendation=_recommendation_for_result(result),
        confidence=0.0,
        verified_at=now,
    )


def _not_targeted_outcome(spec: SourceSpec) -> SourceDiscoveryOutcome:
    return SourceDiscoveryOutcome(
        source_id=spec.id,
        previous_status=spec.status.value,
        current_status=spec.status.value,
        discovered_endpoints=[],
        verification_result="not_targeted",
        reason_for_failure=(
            "No TargetOrganization entry maps to this source id yet; the discovery "
            "engine has nothing to resolve/probe for it."
        ),
        evidence=[],
        recommendation=(
            "Add a TargetOrganization entry (acquisition_intelligence/target.py) with "
            "the organization's own publicly-known brand domain as a hint before this "
            "source can be verified -- never fabricate a domain for it here."
        ),
        confidence=0.0,
        verified_at=datetime.now(),
    )


def run_discovery_report(
    engine: AcquisitionIntelligenceEngine,
    registry: SourceRegistry,
    targets: list[TargetOrganization],
    history: DiscoveryHistoryRepository,
    *,
    force_ids: set[str] | None = None,
    ttl_days: float = DEFAULT_TTL_DAYS,
    now: datetime | None = None,
) -> tuple[list[SourceDiscoveryOutcome], list[EndpointCandidate]]:
    """The Discovery workflow's one entry point: for every in-scope PLANNED/
    CANDIDATE source (see `plan_discovery_targets`), reuse a fresh cached
    result or run a real, evidenced discovery attempt, and return both the
    per-source report rows and the full ranked-candidate menu (not just
    each winner) for `endpoint_candidates.json`.
    """
    force_ids = force_ids or set()
    now = now or datetime.now()
    targeted, untargeted = plan_discovery_targets(registry, targets)

    outcomes: list[SourceDiscoveryOutcome] = []
    candidates: list[EndpointCandidate] = []

    for spec, target in targeted:
        fingerprint = _target_fingerprint(target)
        cached = history.latest(spec.id)
        cache_is_fresh = (
            cached is not None
            and spec.id not in force_ids
            and cached.input_fingerprint == fingerprint
            and now < cached.ttl_expires_at
        )
        if cache_is_fresh:
            outcomes.append(cached.outcome.model_copy(update={"from_cache": True}))
            continue

        result = engine.run_for_target(target)
        outcome = _outcome_for_result(spec, result)
        outcomes.append(outcome)
        for ranked in result.ranked_methods:
            candidates.append(
                EndpointCandidate(
                    source_id=spec.id,
                    discovered_url=ranked.candidate.discovered_url,
                    access_method_guess=ranked.candidate.access_method_guess.value,
                    legality_verdict=ranked.legality.verdict.value,
                    robots_allows=ranked.legality.robots_allows,
                    stability_score=ranked.stability.score,
                    historical_score=ranked.historical.score,
                    composite_score=ranked.composite_score,
                    selected=(result.selected is ranked),
                )
            )
        previous = history.latest(spec.id)
        history.add(
            DiscoveryHistoryEntry(
                id=spec.id,
                version=(previous.version + 1) if previous else 1,
                source_id=spec.id,
                verified_at=now,
                ttl_expires_at=now + timedelta(days=ttl_days),
                input_fingerprint=fingerprint,
                outcome=outcome,
            ),
            persist=False,
        )

    for spec in untargeted:
        outcomes.append(_not_targeted_outcome(spec))

    history.flush()
    return outcomes, candidates


def build_discovery_metrics(
    outcomes: list[SourceDiscoveryOutcome], *, started_at: datetime, finished_at: datetime
) -> dict:
    """Aggregate counts for `discovery_metrics.json` -- a pure summary of
    `outcomes`, never a second source of truth about what happened.
    """
    by_result: dict[str, int] = {}
    for outcome in outcomes:
        by_result[outcome.verification_result] = by_result.get(outcome.verification_result, 0) + 1
    fresh = [o for o in outcomes if not o.from_cache]
    cached = [o for o in outcomes if o.from_cache]
    verified = [o for o in outcomes if o.verification_result == "verified_reachable"]
    return {
        "started_at": started_at.isoformat(),
        "finished_at": finished_at.isoformat(),
        "duration_seconds": (finished_at - started_at).total_seconds(),
        "sources_in_report": len(outcomes),
        "sources_checked_fresh_this_run": len(fresh),
        "sources_served_from_cache": len(cached),
        "sources_verified_reachable": len(verified),
        "by_verification_result": by_result,
        "average_confidence_verified": (
            sum(o.confidence for o in verified) / len(verified) if verified else None
        ),
    }
