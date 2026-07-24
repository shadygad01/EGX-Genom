"""Dashboard artifact export: the one place that turns already-versioned
platform state into the flat JSON files the web dashboard reads.

Every function here is a thin `model_dump(mode="json")` over an existing
domain model -- there is deliberately no dashboard-specific schema for
knowledge/events/recommendations/market state/run records/sources. That's
what "the static and API providers use exactly the same contract" means
in practice: a `GET /knowledge` response and `knowledge.json`'s contents
are produced by calling `.model_dump(mode="json")` on the exact same
`KnowledgeObject` list, nothing upstream of that differs.

`patterns.json` is the one deliberate exception: `HistoricalPatternsAgent`
raises `NotImplementedError` (see `agents/historical_patterns.py`), so
there is no real pattern-matching output to export yet. Rather than invent
a schema for a concept that doesn't exist, `export_patterns()` always
returns an empty list -- honestly empty, not fabricated, until that agent
is implemented (tracked in docs/TECHNICAL_DEBT.md).
"""

from __future__ import annotations

import json
from datetime import date, datetime
from pathlib import Path
from typing import Any

from agx_research.dashboard.schemas import DashboardSystemStatus
from agx_research.events.repository import EventRepository
from agx_research.events.service import EventPlatform
from agx_research.knowledge.store import KnowledgeStore
from agx_research.market_memory.memory import MarketMemory
from agx_research.market_memory.state import MarketState
from agx_research.meta.recommendation_service import RecommendationService
from agx_research.runtime.engine import RunRecordRepository, RunStatus
from agx_research.sources.catalog import seed_sources
from agx_research.sources.registry import SourceRegistry

ARTIFACT_FILENAMES = (
    "knowledge.json",
    "events.json",
    "patterns.json",
    "recommendations.json",
    "market_state.json",
    "runtime_metrics.json",
    "system_status.json",
    "source_registry.json",
)


def export_knowledge(store: KnowledgeStore) -> list[dict[str, Any]]:
    return [k.model_dump(mode="json") for k in store.all_latest()]


def export_events(events: EventRepository) -> list[dict[str, Any]]:
    return [e.model_dump(mode="json") for e in events.all_latest()]


def export_patterns() -> list[dict[str, Any]]:
    return []


def export_recommendations(
    knowledge_store: KnowledgeStore,
    event_platform: EventPlatform,
    *,
    tickers: list[str],
    as_of: date | None,
) -> list[dict[str, Any]]:
    if as_of is None:
        return []
    service = RecommendationService(knowledge_store, event_platform=event_platform)
    return [r.model_dump(mode="json") for r in service.recommend(tickers, as_of)]


def export_market_state(memory: MarketMemory, as_of: date | None) -> dict[str, Any] | None:
    if as_of is None:
        return None
    state: MarketState = memory.reconstruct(as_of)
    return state.model_dump(mode="json")


def export_runtime_metrics(runs: RunRecordRepository) -> list[dict[str, Any]]:
    return [r.model_dump(mode="json") for r in runs.all_latest()]


def export_system_status(
    runs: RunRecordRepository,
    knowledge_store: KnowledgeStore,
    *,
    pipeline_run_date: date | None,
) -> dict[str, Any]:
    records = runs.all_latest()
    knowledge = knowledge_store.all_latest()
    by_status: dict[str, int] = {}
    for k in knowledge:
        by_status[k.status.value] = by_status.get(k.status.value, 0) + 1
    status = DashboardSystemStatus(
        generated_at=datetime.now(),
        pipeline_run_date=pipeline_run_date,
        runs=len(records),
        succeeded=sum(1 for r in records if r.status == RunStatus.SUCCEEDED),
        failed=sum(1 for r in records if r.status == RunStatus.FAILED),
        knowledge_objects=len(knowledge),
        by_status=by_status,
    )
    return status.model_dump(mode="json")


def export_source_registry(registry: SourceRegistry | None = None) -> list[dict[str, Any]]:
    """The registry's *current* state -- health/lifecycle/reputation as
    actually measured by real collection/discovery runs -- when a real,
    persisted `SourceRegistry` is supplied. Falls back to the static seed
    catalog only when no registry exists (a real gap this closes: this
    previously always called `seed_sources()` unconditionally, so
    `source_registry.json` never reflected a single real collection or
    discovery run no matter how many had actually happened).
    """
    if registry is not None:
        return [s.model_dump(mode="json") for s in registry.all_latest()]
    return [s.model_dump(mode="json") for s in seed_sources()]


def write_dashboard_artifacts(
    *,
    knowledge_store: KnowledgeStore,
    event_repository: EventRepository,
    runs: RunRecordRepository,
    memory: MarketMemory,
    tickers: list[str],
    as_of: date | None,
    out_dir: Path,
    registry: SourceRegistry | None = None,
) -> dict[str, int]:
    """Writes every artifact in `ARTIFACT_FILENAMES` to `out_dir` and
    returns a filename -> item-count map (1 for the two single-object
    artifacts, 0 if a single-object artifact is null)."""
    out_dir.mkdir(parents=True, exist_ok=True)
    event_platform = EventPlatform(repository=event_repository)

    artifacts: dict[str, Any] = {
        "knowledge.json": export_knowledge(knowledge_store),
        "events.json": export_events(event_repository),
        "patterns.json": export_patterns(),
        "recommendations.json": export_recommendations(
            knowledge_store, event_platform, tickers=tickers, as_of=as_of
        ),
        "market_state.json": export_market_state(memory, as_of),
        "runtime_metrics.json": export_runtime_metrics(runs),
        "system_status.json": export_system_status(
            runs, knowledge_store, pipeline_run_date=as_of
        ),
        "source_registry.json": export_source_registry(registry),
    }

    counts: dict[str, int] = {}
    for filename, payload in artifacts.items():
        (out_dir / filename).write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
        counts[filename] = len(payload) if isinstance(payload, list) else (1 if payload else 0)
    return counts
