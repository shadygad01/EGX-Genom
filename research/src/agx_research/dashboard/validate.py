"""Validates a directory of exported dashboard artifacts by re-parsing
each file back into its owning pydantic model.

This is the CI gate between "the export step ran" and "the artifacts are
safe to publish": a schema drift, a truncated write, or a malformed value
fails loudly here rather than surfacing as a broken dashboard render on
the live site.
"""

from __future__ import annotations

import json
from pathlib import Path

from agx_research.events.event import Event
from agx_research.knowledge.schema import KnowledgeObject
from agx_research.market_memory.state import MarketState
from agx_research.meta.decision_engine import Recommendation
from agx_research.dashboard.schemas import DashboardSystemStatus
from agx_research.runtime.engine import RunRecord
from agx_research.sources.spec import SourceSpec

_LIST_MODELS = {
    "knowledge.json": KnowledgeObject,
    "events.json": Event,
    "recommendations.json": Recommendation,
    "runtime_metrics.json": RunRecord,
    "source_registry.json": SourceSpec,
}

_OBJECT_MODELS = {
    "system_status.json": DashboardSystemStatus,
}

# market_state.json is a nullable single object (None until a run has
# happened); patterns.json is always an empty list until
# HistoricalPatternsAgent is implemented -- both are validated structurally
# below rather than via the generic maps.


class DashboardArtifactError(Exception):
    pass


def validate_dashboard_artifacts(directory: Path) -> dict[str, int]:
    """Returns a filename -> item-count map on success; raises
    DashboardArtifactError (naming the file and reason) on any failure."""
    counts: dict[str, int] = {}

    for filename, model_cls in _LIST_MODELS.items():
        path = directory / filename
        if not path.exists():
            raise DashboardArtifactError(f"{filename}: missing")
        try:
            items = json.loads(path.read_text())
        except json.JSONDecodeError as exc:
            raise DashboardArtifactError(f"{filename}: invalid JSON ({exc})") from exc
        if not isinstance(items, list):
            raise DashboardArtifactError(f"{filename}: expected a JSON array, got {type(items)}")
        try:
            for item in items:
                model_cls.model_validate(item)
        except Exception as exc:  # pydantic ValidationError, re-raised with file context
            raise DashboardArtifactError(f"{filename}: {exc}") from exc
        counts[filename] = len(items)

    for filename, model_cls in _OBJECT_MODELS.items():
        path = directory / filename
        if not path.exists():
            raise DashboardArtifactError(f"{filename}: missing")
        try:
            payload = json.loads(path.read_text())
        except json.JSONDecodeError as exc:
            raise DashboardArtifactError(f"{filename}: invalid JSON ({exc})") from exc
        try:
            model_cls.model_validate(payload)
        except Exception as exc:
            raise DashboardArtifactError(f"{filename}: {exc}") from exc
        counts[filename] = 1

    market_state_path = directory / "market_state.json"
    if not market_state_path.exists():
        raise DashboardArtifactError("market_state.json: missing")
    try:
        payload = json.loads(market_state_path.read_text())
    except json.JSONDecodeError as exc:
        raise DashboardArtifactError(f"market_state.json: invalid JSON ({exc})") from exc
    if payload is not None:
        try:
            MarketState.model_validate(payload)
        except Exception as exc:
            raise DashboardArtifactError(f"market_state.json: {exc}") from exc
    counts["market_state.json"] = 0 if payload is None else 1

    patterns_path = directory / "patterns.json"
    if not patterns_path.exists():
        raise DashboardArtifactError("patterns.json: missing")
    try:
        payload = json.loads(patterns_path.read_text())
    except json.JSONDecodeError as exc:
        raise DashboardArtifactError(f"patterns.json: invalid JSON ({exc})") from exc
    if not isinstance(payload, list):
        raise DashboardArtifactError(f"patterns.json: expected a JSON array, got {type(payload)}")
    if payload:
        raise DashboardArtifactError(
            "patterns.json: expected empty (HistoricalPatternsAgent is not yet implemented) "
            f"but found {len(payload)} item(s)"
        )
    counts["patterns.json"] = 0

    return counts
