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

The registry now also owns the Claim Registry used by the Research &
Methodology Pipeline. Literature sources still have no operational collector
or decision capability; papers must first be decomposed into claims and those
claims must survive their evidence lifecycle before production eligibility.
"""

from __future__ import annotations

from pathlib import Path

from agx_research.claims.registry import ClaimRegistry
from agx_research.sources.registry import SourceRegistry
from agx_research.sources.spec import (
    AccessMethod,
    SourceCategory,
    SourceSpec,
    SourceStatus,
    default_lifecycle_for_status,
)


class MethodologyRegistry(SourceRegistry):
    """The existing methodology source registry, extended with claims.

    Source lifecycle stays on ``SourceRegistry`` and claim lifecycle stays on
    the shared versioned repository.  One registry owns both; production never
    reads the literature-source side directly.
    """

    def __init__(
        self,
        source_persist_path: Path | str | None = None,
        claim_persist_path: Path | str | None = None,
    ):
        super().__init__(source_persist_path)
        self.claims = ClaimRegistry(claim_persist_path)


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


def seed_methodology_registry(
    registry: MethodologyRegistry | SourceRegistry | None = None,
    *,
    claim_persist_path: Path | str | None = None,
) -> MethodologyRegistry | SourceRegistry:
    """Same add/sync/retire lifecycle `sources.catalog.seed_registry()`
    uses for the operational registry, applied to this independent
    instance -- so a future promotion (e.g. a verified real arXiv feed
    URL) or removal self-heals here exactly the same way, without
    duplicating that logic or its edge cases.
    """
    registry = registry or MethodologyRegistry(claim_persist_path=claim_persist_path)
    current_ids: set[str] = set()
    specs = seed_research_sources()
    for spec in specs:
        current_ids.add(spec.id)
        if registry.latest(spec.id) is None:
            registry.add(spec)
    registry.sync_declared_fields(specs)
    registry.retire_removed(current_ids)
    return registry
