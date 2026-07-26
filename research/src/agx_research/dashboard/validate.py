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

from agx_research.acquisition_intelligence.capability_engine import CapabilityDecision
from agx_research.dashboard.schemas import DashboardSystemStatus
from agx_research.events.event import Event
from agx_research.financials.schema import FinancialStatementLineItem
from agx_research.genome.gene import Gene
from agx_research.graph.edges import GraphEdge
from agx_research.graph.nodes import GraphNode
from agx_research.hypotheses.hypothesis import Hypothesis
from agx_research.knowledge.schema import KnowledgeObject
from agx_research.market_memory.state import MarketState
from agx_research.meta.decision_engine import Recommendation
from agx_research.meta.readiness import DecisionReadiness
from agx_research.papers.paper import ResearchPaper
from agx_research.portfolio.constructor import PortfolioRecommendation
from agx_research.production.mission_control import MissionControlStatus
from agx_research.production.report import ExecutionReport
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

    # The following are only produced by the full production pipeline
    # (`agx run`), not by `export-dashboard` alone -- validated if present,
    # skipped (not an error) if absent, so `export-dashboard`'s narrower
    # eight-artifact contract stays unchanged.
    _validate_optional_execution_report(directory, counts)
    _validate_optional_mission_status(directory, counts)
    _validate_optional_investment_cases(directory, counts)
    _validate_optional_collector_status(directory, counts)
    _validate_optional_runtime_status(directory, counts)
    _validate_optional_dashboard_metrics(directory, counts)
    _validate_optional_model_list(directory, "genes.json", Gene, counts)
    _validate_optional_model_list(directory, "papers.json", ResearchPaper, counts)
    _validate_optional_model_list(directory, "hypotheses.json", Hypothesis, counts)
    _validate_optional_model_list(
        directory, "financial_statements.json", FinancialStatementLineItem, counts
    )
    _validate_optional_knowledge_graph(directory, counts)
    _validate_optional_source_metrics(directory, counts)
    _validate_optional_model_list(
        directory, "acquisition_decisions.json", CapabilityDecision, counts
    )
    _validate_optional_model_list(
        directory, "decision_readiness.json", DecisionReadiness, counts
    )

    return counts


def _load_optional_json(directory: Path, filename: str):
    path = directory / filename
    if not path.exists():
        return None, False
    try:
        return json.loads(path.read_text()), True
    except json.JSONDecodeError as exc:
        raise DashboardArtifactError(f"{filename}: invalid JSON ({exc})") from exc


def _validate_optional_execution_report(directory: Path, counts: dict[str, int]) -> None:
    payload, present = _load_optional_json(directory, "execution_report.json")
    if not present:
        return
    try:
        ExecutionReport.model_validate(payload)
    except Exception as exc:
        raise DashboardArtifactError(f"execution_report.json: {exc}") from exc
    counts["execution_report.json"] = 1


def _validate_optional_mission_status(directory: Path, counts: dict[str, int]) -> None:
    payload, present = _load_optional_json(directory, "mission_status.json")
    if not present:
        return
    try:
        MissionControlStatus.model_validate(payload)
    except Exception as exc:
        raise DashboardArtifactError(f"mission_status.json: {exc}") from exc
    counts["mission_status.json"] = 1


def _validate_optional_investment_cases(directory: Path, counts: dict[str, int]) -> None:
    payload, present = _load_optional_json(directory, "investment_cases.json")
    if not present:
        return
    if not isinstance(payload, dict) or "recommendations" not in payload:
        raise DashboardArtifactError(
            "investment_cases.json: expected an object with a 'recommendations' key"
        )
    try:
        for item in payload["recommendations"]:
            Recommendation.model_validate(item)
        if payload.get("portfolio") is not None:
            PortfolioRecommendation.model_validate(payload["portfolio"])
    except Exception as exc:
        raise DashboardArtifactError(f"investment_cases.json: {exc}") from exc
    counts["investment_cases.json"] = len(payload["recommendations"])


def _validate_optional_collector_status(directory: Path, counts: dict[str, int]) -> None:
    payload, present = _load_optional_json(directory, "collector_status.json")
    if not present:
        return
    if not isinstance(payload, list):
        raise DashboardArtifactError("collector_status.json: expected a JSON array")
    counts["collector_status.json"] = len(payload)


def _validate_optional_runtime_status(directory: Path, counts: dict[str, int]) -> None:
    payload, present = _load_optional_json(directory, "runtime_status.json")
    if not present:
        return
    if payload is not None:
        try:
            RunRecord.model_validate(payload)
        except Exception as exc:
            raise DashboardArtifactError(f"runtime_status.json: {exc}") from exc
    counts["runtime_status.json"] = 0 if payload is None else 1


def _validate_optional_dashboard_metrics(directory: Path, counts: dict[str, int]) -> None:
    payload, present = _load_optional_json(directory, "dashboard_metrics.json")
    if not present:
        return
    if not isinstance(payload, dict) or "artifacts" not in payload:
        raise DashboardArtifactError("dashboard_metrics.json: expected an object with an 'artifacts' key")
    counts["dashboard_metrics.json"] = 1


def _validate_optional_model_list(
    directory: Path, filename: str, model_cls: type, counts: dict[str, int]
) -> None:
    payload, present = _load_optional_json(directory, filename)
    if not present:
        return
    if not isinstance(payload, list):
        raise DashboardArtifactError(f"{filename}: expected a JSON array, got {type(payload)}")
    try:
        for item in payload:
            model_cls.model_validate(item)
    except Exception as exc:
        raise DashboardArtifactError(f"{filename}: {exc}") from exc
    counts[filename] = len(payload)


def _validate_optional_knowledge_graph(directory: Path, counts: dict[str, int]) -> None:
    payload, present = _load_optional_json(directory, "knowledge_graph.json")
    if not present:
        return
    if not isinstance(payload, dict) or "nodes" not in payload or "edges" not in payload:
        raise DashboardArtifactError(
            "knowledge_graph.json: expected an object with 'nodes' and 'edges' keys"
        )
    try:
        for node in payload["nodes"]:
            GraphNode.model_validate(node)
        for edge in payload["edges"]:
            GraphEdge.model_validate(edge)
    except Exception as exc:
        raise DashboardArtifactError(f"knowledge_graph.json: {exc}") from exc
    counts["knowledge_graph.json"] = len(payload["nodes"])


def _validate_optional_source_metrics(directory: Path, counts: dict[str, int]) -> None:
    payload, present = _load_optional_json(directory, "source_metrics.json")
    if not present:
        return
    if not isinstance(payload, list):
        raise DashboardArtifactError("source_metrics.json: expected a JSON array")
    for row in payload:
        if not isinstance(row, dict) or "source_id" not in row:
            raise DashboardArtifactError("source_metrics.json: expected each row to have 'source_id'")
    counts["source_metrics.json"] = len(payload)
