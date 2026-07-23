"""Source Qualification Pipeline: Candidate -> Quarantine -> Evaluation ->
Trusted -> Core.

Every discovered source starts as a `SourceCandidate` (see `discovery/`) and
is registered at `LifecycleState.CANDIDATE`. This module is the only place
that decides whether a source may move forward, and the decision is always
mechanical evidence over `reputation.SourceMetrics`/`ReputationScore` —
never a one-off judgment call. `evaluate_promotion` never returns more than
one stage of movement at a time, and never fabricates a recommendation for a
dimension with no data (it recommends staying put instead). Registry
mutation is a separate, explicit step (`apply_promotion`) so evaluation stays
a pure, testable function of evidence.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from agx_research.discovery.candidate import SourceCandidate
from agx_research.sources.reputation import ReputationScore, SourceMetrics, compute_reputation
from agx_research.sources.registry import SourceRegistry
from agx_research.sources.spec import (
    HealthStatus,
    LifecycleState,
    SourceCategory,
    SourceSpec,
    SourceStatus,
)

_STAGE_ORDER = [
    LifecycleState.CANDIDATE,
    LifecycleState.QUARANTINE,
    LifecycleState.EVALUATION,
    LifecycleState.TRUSTED,
    LifecycleState.CORE,
]

# Minimum successful runs required before a stage's evidence bar is even
# checked, and the composite reputation score required to clear it. Declared
# thresholds, not measured -- exactly like the seed catalog's reliability
# priors, subject to revision once real collection history accumulates.
_MIN_RUNS = {
    LifecycleState.QUARANTINE: 1,
    LifecycleState.EVALUATION: 5,
    LifecycleState.TRUSTED: 20,
    LifecycleState.CORE: 100,
}
_MIN_COMPOSITE = {
    LifecycleState.EVALUATION: None,  # reachability alone is enough to start scoring
    LifecycleState.TRUSTED: 0.70,
    LifecycleState.CORE: 0.85,
}


@dataclass
class PromotionDecision:
    source_id: str
    current_stage: LifecycleState
    recommended_stage: LifecycleState
    reason: str
    evidence: ReputationScore | None = field(default=None)

    @property
    def changed(self) -> bool:
        return self.recommended_stage != self.current_stage


def evaluate_promotion(spec: SourceSpec, metrics: SourceMetrics | None) -> PromotionDecision:
    current = spec.lifecycle_state
    if metrics is None or metrics.runs_total == 0:
        if current != LifecycleState.CANDIDATE:
            return PromotionDecision(
                spec.id, current, LifecycleState.CANDIDATE,
                "No run history recorded -- cannot justify any stage past Candidate.",
            )
        return PromotionDecision(spec.id, current, current, "No run history yet.")

    reputation = compute_reputation(metrics)

    # A source in DOWN health is demoted one stage regardless of history --
    # trust is earned slowly and lost immediately on the current signal.
    if spec.health_status == HealthStatus.DOWN and current != LifecycleState.CANDIDATE:
        demoted = _STAGE_ORDER[_STAGE_ORDER.index(current) - 1]
        return PromotionDecision(
            spec.id, current, demoted, "Health status DOWN: demoted one stage.", reputation
        )

    current_index = _STAGE_ORDER.index(current)
    if current_index == len(_STAGE_ORDER) - 1:
        return PromotionDecision(spec.id, current, current, "Already at Core.", reputation)

    next_stage = _STAGE_ORDER[current_index + 1]

    if spec.status != SourceStatus.IMPLEMENTED and next_stage != LifecycleState.QUARANTINE:
        return PromotionDecision(
            spec.id, current, current,
            f"Source status is {spec.status.value}, not IMPLEMENTED: cannot advance.",
            reputation,
        )

    min_runs = _MIN_RUNS.get(next_stage, 0)
    if metrics.runs_total < min_runs:
        return PromotionDecision(
            spec.id, current, current,
            f"{metrics.runs_total}/{min_runs} runs recorded for {next_stage.value}.",
            reputation,
        )

    min_composite = _MIN_COMPOSITE.get(next_stage)
    if min_composite is not None:
        if reputation.composite is None:
            return PromotionDecision(
                spec.id, current, current,
                f"No composite reputation score yet; required >= {min_composite} for "
                f"{next_stage.value}.",
                reputation,
            )
        if reputation.composite < min_composite:
            return PromotionDecision(
                spec.id, current, current,
                f"Composite reputation {reputation.composite:.3f} < {min_composite} required "
                f"for {next_stage.value}.",
                reputation,
            )

    return PromotionDecision(
        spec.id, current, next_stage,
        f"{metrics.runs_total} runs, composite reputation "
        f"{reputation.composite if reputation.composite is not None else 'n/a'} clears "
        f"{next_stage.value}.",
        reputation,
    )


def apply_promotion(registry: SourceRegistry, decision: PromotionDecision) -> SourceSpec | None:
    """Persist a decision's recommended stage if it actually changed anything."""
    if not decision.changed:
        return None
    return registry.transition_lifecycle(decision.source_id, decision.recommended_stage)


# Conservative priors for a source nobody has reviewed yet -- deliberately
# lower than every seeded-and-verified source's declared prior, since a
# discovery heuristic's guess earns no trust by itself.
_UNREVIEWED_RELIABILITY_PRIOR = 0.3
_UNREVIEWED_FRESHNESS_PRIOR = 0.3


def register_candidate(
    registry: SourceRegistry,
    candidate: SourceCandidate,
    *,
    source_id: str,
    name: str,
    category: SourceCategory,
    license: str = "unknown",
    terms_of_use_url: str | None = None,
) -> SourceSpec:
    """Turn a discovery-produced `SourceCandidate` into a real `SourceSpec`,
    always at `LifecycleState.CANDIDATE` / `SourceStatus.PLANNED` regardless of
    what the caller passes, and always with the conservative unreviewed
    priors -- a discovery run (or whoever calls this next) cannot mint a
    pre-trusted or pre-collectable source no matter what fields it supplies.
    Advancing past Candidate is exclusively `evaluate_promotion`'s job, gated
    on run history that does not exist yet for a source just discovered.
    """
    existing = registry.latest(source_id)
    if existing is not None:
        raise ValueError(f"Source id {source_id} already registered.")

    spec = SourceSpec(
        id=source_id,
        name=name,
        category=category,
        access_method=candidate.access_method_guess,
        status=SourceStatus.PLANNED,
        lifecycle_state=LifecycleState.CANDIDATE,
        base_url=candidate.discovered_url,
        reliability_score=_UNREVIEWED_RELIABILITY_PRIOR,
        freshness_score=_UNREVIEWED_FRESHNESS_PRIOR,
        license=license,
        terms_of_use_url=terms_of_use_url,
        notes=(
            f"Discovered via {candidate.discovery_method.value} from "
            f"{candidate.origin_page_url} on {candidate.discovered_at.isoformat()}. "
            f"Evidence: {candidate.evidence}"
        ),
    )
    return registry.add(spec)
