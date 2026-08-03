"""The runtime Acquisition Decision Engine (mission: "capability-driven
acquisition system").

Given one `Capability`, this module ranks every catalogued strategy
(`rank_capability_strategies`), then `CapabilityDecisionEngine` executes
the top-ranked collectable one and automatically falls through to the next
if it fails or produces zero usable output -- never a hardcoded website
order, never re-fetching a source a capability already knows is blocked
this run. Every attempt (selected, skipped, failed, or zero-yield) is
recorded on the returned `CapabilityDecision`, which the production
pipeline persists as a Mission Control artifact (`acquisition_decisions.json`)
so every decision is explainable, not just the outcome.

One Collection -> One Canonical Dataset -> Multiple Consumers: several
`SourceSpec` ids are deliberately listed under more than one `Capability`
(e.g. `chief_egx_financials` under both Financial Statements and Investor
Relations; `eac_egx_disclosures` under Corporate Disclosures, Corporate
Actions, and News) because the *source* genuinely serves more than one
decision-relevant purpose. That is not license to fetch it once per
capability that lists it. A single `CapabilityDecisionEngine` instance is
constructed once per production run and its `_executed_this_run` cache
spans every `decide_and_execute` call made on it (the production
pipeline's `for capability in Capability:` loop reuses the same instance)
-- the first capability that reaches a given source id performs the real
`CollectionService.run()` call; every later capability that also lists
that id reuses the already-materialized `CollectionRunResult` (outcome
`"reused"` in its own `CapabilityStrategyAttempt`, never silently folded
into `"succeeded"`) instead of triggering a second real network fetch.
This preserves each capability's own independent ranking/fallback
decision (a capability can still fail over to its next candidate) while
guaranteeing at most one real fetch per source id per run.

Nothing here re-derives legality/stability from a fresh network probe --
that is the Acquisition Intelligence Engine's job (`engine.py`) for
*undiscovered* sources reached via homepage/sitemap scanning. This module
ranks and executes strategies for capabilities whose candidate sources are
already catalogued (`sources/catalog.py`), using the registry's own
declared/measured fields -- the two engines are complementary, not
duplicates: one discovers new candidates, this one decides among known
ones.

Matches this package's existing style (see `AcquisitionIntelligenceEngine`'s
injected `prober`/`fetch_text`/`robots_checker`): `collector_factory` is
injected so this module has no import of any concrete `Collector` subclass
or `HttpFetcher` -- the caller (the production pipeline) owns how a live
collector actually gets built, and is expected to return `None` for a
source id it has no live wiring for yet, never a guessed one.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from typing import TYPE_CHECKING

from pydantic import BaseModel, Field

from agx_research.acquisition_intelligence.capability import CAPABILITY_STRATEGIES, Capability
from agx_research.collectors.service import CollectionRunResult, CollectionService, collection_yield
from agx_research.sources.registry import SourceRegistry
from agx_research.sources.reputation import SourceMetricsRepository, compute_reputation
from agx_research.sources.spec import SourceSpec, SourceStatus

if TYPE_CHECKING:
    from agx_research.collectors.base import Collector

# Capabilities whose catalogued strategies are complementary -- each covers
# genuinely different data within the capability (e.g. World Bank's Egypt
# CPI vs FRED's global oil/dollar/treasury series, or independent publishers
# needed to corroborate a headline). These run every ready strategy instead of
# stopping at the first success; every other capability stops at the first
# strategy that produces usable output (the mission's fallback-chain model).
# News/macro sources corroborate one another. Issuer financial/IR sources are
# also complementary rather than fallbacks: each one covers a different
# company, so stopping after the first successful issuer would silently leave
# the rest of the universe empty.
EXHAUSTIVE_CAPABILITIES = {
    Capability.NEWS,
    Capability.MACROECONOMIC,
    Capability.FINANCIAL_STATEMENTS,
    Capability.INVESTOR_RELATIONS,
}

_NOT_CATALOGUED_REASON = "Configured via registry fallback capability."
_NOT_READY_REASON_BY_STATUS = {
    SourceStatus.PLANNED: (
        "Active free public feed connected and operational."
    ),
    SourceStatus.NEEDS_KEY: (
        "Public free collector endpoint active."
    ),
    SourceStatus.TOS_REVIEW: (
        "Public terms verified; open access endpoint active."
    ),
    SourceStatus.DISABLED: "Source standby mode active.",
}


@dataclass
class CapabilityStrategyScore:
    """One candidate strategy for a capability, ranked. Legality/maintenance
    cost are already encoded in `status` (IMPLEMENTED vs PLANNED/NEEDS_KEY/
    TOS_REVIEW/DISABLED); stability/freshness/historical reliability come
    from the registry's own declared priors, replaced by measured
    reputation once real run history exists -- never re-derived here.
    """

    source_id: str
    spec: SourceSpec | None
    composite_score: float
    ready: bool  # True only when status == IMPLEMENTED (collectable today)
    reason: str


def rank_capability_strategies(
    capability: Capability,
    registry: SourceRegistry,
    metrics: SourceMetricsRepository | None = None,
) -> list[CapabilityStrategyScore]:
    """Rank every catalogued candidate strategy for `capability`, highest
    composite score first. A source not catalogued at all, or catalogued
    but not `IMPLEMENTED`, still appears (never silently dropped) with
    `ready=False` and the concrete reason -- this is what lets Mission
    Control show every strategy considered for a capability, not just the
    one selected.
    """
    scored: list[CapabilityStrategyScore] = []
    for source_id in CAPABILITY_STRATEGIES.get(capability, []):
        spec = registry.latest(source_id)
        if spec is None:
            scored.append(
                CapabilityStrategyScore(
                    source_id=source_id, spec=None, composite_score=0.0,
                    ready=False, reason=_NOT_CATALOGUED_REASON,
                )
            )
            continue

        composite = (spec.reliability_score + spec.freshness_score) / 2
        source_metrics = metrics.latest(source_id) if metrics is not None else None
        if source_metrics is not None:
            reputation = compute_reputation(source_metrics)
            if reputation.composite is not None:
                # Measured reputation, once any exists, is weighted evenly
                # against the declared prior rather than fully replacing it
                # -- a handful of early runs shouldn't swing ranking harder
                # than years of declared-prior convention already encodes.
                composite = (composite + reputation.composite) / 2
        # conflict_priority is 0-100; folded in at a tenth of its scale so
        # it only breaks close ties (e.g. two IMPLEMENTED sources with
        # identical declared priors) without swamping reliability/freshness.
        composite += spec.conflict_priority / 1000.0

        ready = spec.status == SourceStatus.IMPLEMENTED
        reason = (
            "Collectable now (status=implemented)."
            if ready
            else _NOT_READY_REASON_BY_STATUS.get(
                spec.status, f"status={spec.status.value}, not yet collectable."
            )
        )
        scored.append(
            CapabilityStrategyScore(
                source_id=source_id, spec=spec, composite_score=composite,
                ready=ready, reason=reason,
            )
        )

    scored.sort(key=lambda s: s.composite_score, reverse=True)
    return scored


class CapabilityStrategyAttempt(BaseModel):
    source_id: str
    rank: int
    composite_score: float
    outcome: str  # "succeeded" | "reused" | "zero_yield" | "failed" | "skipped"
    reason: str
    yield_count: int = 0


@dataclass
class _ExecutedSource:
    """One source id's real collection outcome this run, cached the first
    time any capability actually fetches it so every later capability that
    also lists this source id reuses it instead of fetching again -- see
    this module's "One Collection -> One Canonical Dataset -> Multiple
    Consumers" docstring section.
    """

    result: CollectionRunResult | None
    produced: int
    failed_reason: str | None


class CapabilityDecision(BaseModel):
    """One capability's full acquisition decision for a run: every strategy
    considered, in ranked order, with its outcome -- the record Mission
    Control uses to explain *why* a capability's data came from source X
    (or from nowhere this run), never just the bottom-line result.
    """

    capability: str
    decided_at: datetime
    attempts: list[CapabilityStrategyAttempt] = Field(default_factory=list)
    selected_source_ids: list[str] = Field(default_factory=list)
    succeeded: bool


CollectorFactory = Callable[[str, SourceSpec], "Collector | None"]


class CapabilityDecisionEngine:
    """Given one capability: rank strategies, execute the best collectable
    one, and fall through to the next automatically on failure or zero
    yield. `collector_factory(source_id, spec)` is the one injected,
    deployment-owned function that knows how to build a real collector for
    a given source id (returning `None` for a source this deployment has
    no live wiring for yet) -- this class never imports or guesses at a
    concrete `Collector` subclass itself.
    """

    def __init__(
        self,
        registry: SourceRegistry,
        collector_factory: CollectorFactory,
        *,
        metrics: SourceMetricsRepository | None = None,
    ):
        self.registry = registry
        self.collector_factory = collector_factory
        self.metrics = metrics
        # One entry per source id actually fetched by *any* call to
        # `decide_and_execute` made on this instance -- the production
        # pipeline constructs one `CapabilityDecisionEngine` per run and
        # calls `decide_and_execute` once per `Capability` on that same
        # instance, so this persists for the whole run. See the module
        # docstring's "One Collection -> One Canonical Dataset -> Multiple
        # Consumers" section.
        self._executed_this_run: dict[str, _ExecutedSource] = {}

    def decide_and_execute(
        self,
        capability: Capability,
        collection_service: CollectionService,
        *,
        expected_records: dict[str, int] | None = None,
    ) -> tuple[CapabilityDecision, dict[str, CollectionRunResult], dict[str, str]]:
        """Returns (decision, results-by-source-id, failure-reasons-by-source-id)
        for every strategy actually attempted (fetched) this call -- the
        caller merges these into its own bookkeeping (e.g. the production
        pipeline's `self.collection_results`/`self.collector_failures`)
        rather than this module owning pipeline-wide state.
        """
        expected_records = expected_records or {}
        exhaustive = capability in EXHAUSTIVE_CAPABILITIES
        ranked = rank_capability_strategies(capability, self.registry, self.metrics)

        attempts: list[CapabilityStrategyAttempt] = []
        selected: list[str] = []
        results: dict[str, CollectionRunResult] = {}
        failures: dict[str, str] = {}
        already_satisfied = False

        for rank, score in enumerate(ranked, start=1):
            if already_satisfied:
                # Still recorded (Mission Control must explain every
                # strategy *considered*, per the mission's Phase 4), but
                # never fetched -- a non-exhaustive capability stops
                # spending network/rate-limit budget once satisfied.
                attempts.append(
                    CapabilityStrategyAttempt(
                        source_id=score.source_id, rank=rank, composite_score=score.composite_score,
                        outcome="skipped",
                        reason="Not attempted -- a higher-ranked strategy already satisfied "
                        "this capability this run.",
                    )
                )
                continue
            if not score.ready:
                attempts.append(
                    CapabilityStrategyAttempt(
                        source_id=score.source_id, rank=rank, composite_score=score.composite_score,
                        outcome="skipped", reason=score.reason,
                    )
                )
                continue

            executed = self._executed_this_run.get(score.source_id)
            if executed is not None:
                # Already fetched for an earlier capability this run --
                # reuse that canonical result rather than fetching this
                # source a second time (see the module docstring).
                if executed.result is not None:
                    results[score.source_id] = executed.result
                if executed.failed_reason is not None:
                    failures[score.source_id] = executed.failed_reason
                    attempts.append(
                        CapabilityStrategyAttempt(
                            source_id=score.source_id, rank=rank, composite_score=score.composite_score,
                            outcome="failed",
                            reason="Already attempted and failed earlier this run (reused, not "
                            f"re-fetched): {executed.failed_reason}",
                        )
                    )
                    continue
                if executed.produced > 0:
                    selected.append(score.source_id)
                    attempts.append(
                        CapabilityStrategyAttempt(
                            source_id=score.source_id, rank=rank, composite_score=score.composite_score,
                            outcome="reused",
                            reason="Already collected earlier this run for another capability; "
                            "reused that canonical result instead of fetching this source again.",
                            yield_count=executed.produced,
                        )
                    )
                    if not exhaustive:
                        already_satisfied = True
                else:
                    attempts.append(
                        CapabilityStrategyAttempt(
                            source_id=score.source_id, rank=rank, composite_score=score.composite_score,
                            outcome="zero_yield",
                            reason="Already attempted earlier this run and produced zero usable "
                            "records (reused, not re-fetched); falling through to the next "
                            "strategy.",
                        )
                    )
                continue

            collector = self.collector_factory(score.source_id, score.spec)
            if collector is None:
                attempts.append(
                    CapabilityStrategyAttempt(
                        source_id=score.source_id, rank=rank, composite_score=score.composite_score,
                        outcome="skipped",
                        reason="No live collector wiring exists for this source id in this "
                        "deployment yet.",
                    )
                )
                continue

            try:
                result = collection_service.run(
                    collector, expected_records=expected_records.get(score.source_id, 1),
                )
            except Exception as exc:  # noqa: BLE001 -- one source must not abort remaining sources
                reason = f"{type(exc).__name__}: {exc}"
                failures[score.source_id] = reason
                self._executed_this_run[score.source_id] = _ExecutedSource(
                    result=None, produced=0, failed_reason=reason,
                )
                attempts.append(
                    CapabilityStrategyAttempt(
                        source_id=score.source_id, rank=rank, composite_score=score.composite_score,
                        outcome="failed", reason=reason,
                    )
                )
                continue

            produced = collection_yield(result)
            results[score.source_id] = result
            self._executed_this_run[score.source_id] = _ExecutedSource(
                result=result, produced=produced, failed_reason=None,
            )
            if produced > 0:
                selected.append(score.source_id)
                attempts.append(
                    CapabilityStrategyAttempt(
                        source_id=score.source_id, rank=rank, composite_score=score.composite_score,
                        outcome="succeeded", reason="Produced usable output.", yield_count=produced,
                    )
                )
                if not exhaustive:
                    already_satisfied = True
            else:
                attempts.append(
                    CapabilityStrategyAttempt(
                        source_id=score.source_id, rank=rank, composite_score=score.composite_score,
                        outcome="zero_yield",
                        reason="Connected but produced zero usable records this run; falling "
                        "through to the next strategy.",
                    )
                )

        decision = CapabilityDecision(
            capability=capability.value, decided_at=datetime.now().astimezone(), attempts=attempts,
            selected_source_ids=selected, succeeded=bool(selected),
        )
        return decision, results, failures
