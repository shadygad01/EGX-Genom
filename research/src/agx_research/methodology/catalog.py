"""Methodology & Research source catalog + registry.

Deliberately separate from `sources.catalog`/`sources.registry` -- those
back the *operational* source registry `production.pipeline
.ProductionPipeline`, `acquisition_intelligence.capability_engine`, and
every `DatasetSnapshot` actually read from. This module is a second,
independent instance of the exact same generic, versioned `SourceRegistry`/
`SourceSpec` machinery (reused as-is, never duplicated as a new type),
holding sources whose only purpose is improving AGX's own investment
*methodology*: new quant-finance literature that can feed hypothesis
generation, model improvement, and rule discovery -- never a same-day
investment decision.

Project owner direction (2026-08-02): a real user-reported audit of
Mission Control's source table found `arxiv`/`ssrn`/`nber` (previously
catalogued under `sources.catalog` as `Capability.RESEARCH_PAPERS`) had
zero downstream consumer -- no agent, hypothesis, or decision ever read
their output -- while `docs/FREE_DECISION_DATA_BLUEPRINT.md` Part 3
already documented all three as "methodology only, None directly" for
decision impact. The explicit correction: academic papers must never be
classified as decision-time data and must not remain inside the
operational registry, but shouldn't be deleted either -- they belong to a
future Research & Methodology Pipeline (literature review -> hypothesis
generation -> this codebase's existing `hypotheses.pipeline`'s 8-gate
validation -> Shadow Fund backtest -> Investment Proof, exactly the same
survival bar every other hypothesis must clear, never a shortcut straight
to a production rule), kept structurally apart from the Operational
Decision Pipeline (`production.pipeline.ProductionPipeline`, run daily) so
the two are never mixed.

Nothing in this codebase reads `seed_methodology_registry()`'s output yet
-- no CLI command, dashboard artifact, or agent. That is honestly a real
gap, not fabricated closed: turning a collected paper into a
`ResearchFinding` an agent can propose is the Research & Methodology
Pipeline mission itself, named as future work in `docs/PHASE_STATUS.md`,
not built here. This module only gives these sources a correctly-scoped,
non-operational home instead of either deleting them or leaving them
inside the registry that drives real decisions.
"""

from __future__ import annotations

from agx_research.sources.registry import SourceRegistry
from agx_research.sources.spec import (
    AccessMethod,
    SourceCategory,
    SourceSpec,
    SourceStatus,
    default_lifecycle_for_status,
)


def _spec(**kwargs) -> SourceSpec:
    spec = SourceSpec(**kwargs)
    lifecycle_state, activation_status = default_lifecycle_for_status(spec.status)
    return spec.model_copy(
        update={"lifecycle_state": lifecycle_state, "activation_status": activation_status}
    )


def seed_research_sources() -> list[SourceSpec]:
    """Academic quant-finance literature sources -- methodology inputs
    only. None of these carry a `Capability` mapping or a `collector`
    class: they are not, and must never become, part of the operational
    collector plan.
    """
    return [
        _spec(
            id=source_id,
            name=name,
            category=SourceCategory.RESEARCH,
            access_method=AccessMethod.RSS_FEED,
            status=SourceStatus.PLANNED,
            reliability_score=0.7,
            freshness_score=0.3,
            conflict_priority=30,
            notes=note,
        )
        for source_id, name, note in [
            ("arxiv", "arXiv (q-fin)", "Official free API/RSS."),
            ("ssrn", "SSRN", "Public RSS for new papers."),
            ("nber", "NBER", "Public new-papers feed."),
        ]
    ]


def seed_methodology_registry(registry: SourceRegistry | None = None) -> SourceRegistry:
    """Same add/sync/retire lifecycle `sources.catalog.seed_registry()`
    uses for the operational registry, applied to this independent
    instance -- so a future promotion (e.g. a verified real arXiv feed
    URL) or removal self-heals here exactly the same way, without
    duplicating that logic or its edge cases.
    """
    registry = registry or SourceRegistry()
    current_ids: set[str] = set()
    specs = seed_research_sources()
    for spec in specs:
        current_ids.add(spec.id)
        if registry.latest(spec.id) is None:
            registry.add(spec)
    registry.sync_declared_fields(specs)
    registry.retire_removed(current_ids)
    return registry
