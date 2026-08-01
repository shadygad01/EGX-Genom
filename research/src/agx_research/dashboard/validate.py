"""Validates a directory of exported dashboard artifacts by re-parsing
each file back into its owning pydantic model.

This is the CI gate between "the export step ran" and "the artifacts are
safe to publish": a schema drift, a truncated write, or a malformed value
fails loudly here rather than surfacing as a broken dashboard render on
the live site.
"""

from __future__ import annotations

import json
from datetime import date
from pathlib import Path

from agx_research.acquisition_intelligence.capability_engine import CapabilityDecision
from agx_research.dashboard.committee_summary import CommitteeSummaryReport
from agx_research.dashboard.monitoring import MonitoringWarningsReport
from agx_research.dashboard.portfolio_summary import PortfolioSummaryReport
from agx_research.dashboard.schemas import DashboardSystemStatus
from agx_research.events.event import Event
from agx_research.financials.coverage import (
    FinancialCoverageReport,
    build_financial_coverage_report,
)
from agx_research.financials.schema import FinancialStatementLineItem
from agx_research.genome.gene import Gene
from agx_research.graph.edges import GraphEdge
from agx_research.graph.nodes import GraphNode
from agx_research.hypotheses.hypothesis import Hypothesis
from agx_research.knowledge.schema import KnowledgeObject
from agx_research.market_memory.breadth import MarketBreadthReport
from agx_research.market_memory.regime import MarketRegimeReport
from agx_research.market_memory.state import MarketState
from agx_research.meta.decision_engine import (
    DecisionAction,
    PublicationStatus,
    Recommendation,
)
from agx_research.meta.publication_gate import PublicationGateReport
from agx_research.meta.readiness import DecisionReadiness, TickerDataGapReport
from agx_research.papers.paper import ResearchPaper
from agx_research.portfolio.constructor import PortfolioRecommendation
from agx_research.production.mission_control import MissionControlStatus
from agx_research.production.report import ExecutionReport
from agx_research.runtime.engine import RunRecord
from agx_research.shadow_fund.models import ShadowFundHistory, ShadowFundPublicState
from agx_research.sources.spec import SourceSpec
from agx_research.universe.provider import UniverseArtifact

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
# happened); patterns.json is always an empty list until a dedicated
# Pattern pydantic model/contract exists for its dashboard-specific shape
# (TD-15) -- HistoricalPatternsAgent itself is implemented and its findings
# already flow through the normal finding/hypothesis/knowledge pipeline
# like any other agent's, this is only about the separate raw-pattern
# display artifact. Both are validated structurally below rather than via
# the generic maps.


class DashboardArtifactError(Exception):
    pass


def validate_dashboard_artifacts(
    directory: Path, *, require_complete_financials: bool = False
) -> dict[str, int]:
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
    market_state_payload = payload
    if market_state_payload is not None:
        try:
            MarketState.model_validate(market_state_payload)
        except Exception as exc:
            raise DashboardArtifactError(f"market_state.json: {exc}") from exc
    counts["market_state.json"] = 0 if market_state_payload is None else 1

    universe_path = directory / "universe.json"
    if not universe_path.exists():
        raise DashboardArtifactError("universe.json: missing")
    try:
        universe_payload = json.loads(universe_path.read_text())
    except json.JSONDecodeError as exc:
        raise DashboardArtifactError(f"universe.json: invalid JSON ({exc})") from exc
    if universe_payload is not None:
        try:
            universe = UniverseArtifact.model_validate(universe_payload)
        except Exception as exc:
            raise DashboardArtifactError(f"universe.json: {exc}") from exc
        counts["universe.json"] = universe.count
        if market_state_payload is not None:
            market_constituents = sorted(market_state_payload["constituents"])
            snapshot_tickers = market_state_payload["dataset_snapshot"]["tickers"]
            if market_constituents != universe.tickers or snapshot_tickers != universe.tickers:
                raise DashboardArtifactError(
                    "universe.json: membership differs from market_state.json"
                )
    else:
        counts["universe.json"] = 0

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
            "patterns.json: expected empty (no dashboard Pattern schema exists yet, TD-15) "
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
    _validate_optional_publication_safety(directory, counts)
    _validate_optional_collector_status(directory, counts)
    _validate_optional_runtime_status(directory, counts)
    _validate_optional_dashboard_metrics(directory, counts)
    _validate_optional_model_list(directory, "genes.json", Gene, counts)
    _validate_optional_model_list(directory, "papers.json", ResearchPaper, counts)
    _validate_optional_model_list(directory, "hypotheses.json", Hypothesis, counts)
    _validate_optional_model_list(
        directory, "financial_statements.json", FinancialStatementLineItem, counts
    )
    _validate_optional_financial_coverage(directory, counts, universe_payload)
    if require_complete_financials:
        _validate_complete_financial_coverage(directory, universe_payload)
    _validate_optional_knowledge_graph(directory, counts)
    _validate_optional_source_metrics(directory, counts)
    _validate_optional_model_list(
        directory, "acquisition_decisions.json", CapabilityDecision, counts
    )
    _validate_optional_model_list(directory, "decision_readiness.json", DecisionReadiness, counts)
    readiness_path = directory / "decision_readiness.json"
    if readiness_path.exists() and universe_payload is not None:
        readiness_tickers = sorted(row["ticker"] for row in json.loads(readiness_path.read_text()))
        if readiness_tickers != universe.tickers:
            raise DashboardArtifactError(
                "decision_readiness.json: membership differs from universe.json"
            )

    _validate_optional_model_list(
        directory, "ticker_data_gap_report.json", TickerDataGapReport, counts
    )
    gap_report_path = directory / "ticker_data_gap_report.json"
    if gap_report_path.exists() and universe_payload is not None:
        gap_report_tickers = sorted(
            row["ticker"] for row in json.loads(gap_report_path.read_text())
        )
        if gap_report_tickers != universe.tickers:
            raise DashboardArtifactError(
                "ticker_data_gap_report.json: membership differs from universe.json"
            )

    _validate_optional_market_breadth(directory, counts)
    _validate_optional_market_regime(directory, counts)
    _validate_optional_portfolio_summary(directory, counts)
    _validate_optional_warnings(directory, counts)
    _validate_optional_committee_summary(directory, counts)
    _validate_optional_shadow_fund(directory, counts)
    _validate_optional_shadow_fund_history(directory, counts)

    return counts


def _validate_optional_market_breadth(directory: Path, counts: dict[str, int]) -> None:
    payload, present = _load_optional_json(directory, "market_breadth.json")
    if not present:
        return
    if payload is not None:
        try:
            MarketBreadthReport.model_validate(payload)
        except Exception as exc:
            raise DashboardArtifactError(f"market_breadth.json: {exc}") from exc
    counts["market_breadth.json"] = 0 if payload is None else 1


def _validate_optional_market_regime(directory: Path, counts: dict[str, int]) -> None:
    payload, present = _load_optional_json(directory, "market_regime.json")
    if not present:
        return
    if payload is not None:
        try:
            MarketRegimeReport.model_validate(payload)
        except Exception as exc:
            raise DashboardArtifactError(f"market_regime.json: {exc}") from exc
    counts["market_regime.json"] = 0 if payload is None else 1


def _validate_optional_portfolio_summary(directory: Path, counts: dict[str, int]) -> None:
    payload, present = _load_optional_json(directory, "portfolio_summary.json")
    if not present:
        return
    if payload is not None:
        try:
            PortfolioSummaryReport.model_validate(payload)
        except Exception as exc:
            raise DashboardArtifactError(f"portfolio_summary.json: {exc}") from exc
    counts["portfolio_summary.json"] = 0 if payload is None else 1


def _validate_optional_warnings(directory: Path, counts: dict[str, int]) -> None:
    payload, present = _load_optional_json(directory, "warnings.json")
    if not present:
        return
    if payload is not None:
        try:
            MonitoringWarningsReport.model_validate(payload)
        except Exception as exc:
            raise DashboardArtifactError(f"warnings.json: {exc}") from exc
    counts["warnings.json"] = 0 if payload is None else len(payload.get("warnings", []))


def _validate_optional_committee_summary(directory: Path, counts: dict[str, int]) -> None:
    payload, present = _load_optional_json(directory, "committee_summary.json")
    if not present:
        return
    if payload is not None:
        try:
            CommitteeSummaryReport.model_validate(payload)
        except Exception as exc:
            raise DashboardArtifactError(f"committee_summary.json: {exc}") from exc
    counts["committee_summary.json"] = 0 if payload is None else 1


def _validate_optional_shadow_fund(directory: Path, counts: dict[str, int]) -> None:
    payload, present = _load_optional_json(directory, "shadow_fund.json")
    if not present:
        return
    if payload is not None:
        try:
            ShadowFundPublicState.model_validate(payload)
        except Exception as exc:
            raise DashboardArtifactError(f"shadow_fund.json: {exc}") from exc
    counts["shadow_fund.json"] = 0 if payload is None else 1


def _validate_optional_shadow_fund_history(directory: Path, counts: dict[str, int]) -> None:
    payload, present = _load_optional_json(directory, "shadow_fund_history.json")
    if not present:
        return
    try:
        history = ShadowFundHistory.model_validate(payload)
    except Exception as exc:
        raise DashboardArtifactError(f"shadow_fund_history.json: {exc}") from exc
    counts["shadow_fund_history.json"] = len(history.nav_series)


def _validate_complete_financial_coverage(directory: Path, universe_payload) -> None:
    """Require at least one reported financial item for every constituent.

    Prices and technical indicators do not qualify. A canonical financial item
    must have a reporting period and retain its raw-document lineage.
    """
    if universe_payload is None:
        raise DashboardArtifactError(
            "financial_statements.json: complete coverage requires a non-null universe.json"
        )
    payload, present = _load_optional_json(directory, "financial_statements.json")
    if not present:
        raise DashboardArtifactError(
            "financial_statements.json: missing (100% financial coverage is required)"
        )
    if not isinstance(payload, list):
        raise DashboardArtifactError("financial_statements.json: expected a JSON array")

    items = [FinancialStatementLineItem.model_validate(item) for item in payload]
    report = build_financial_coverage_report(
        tickers=universe_payload["tickers"],
        items=items,
        as_of=date.fromisoformat(universe_payload["as_of"]),
    )
    failures = [
        (
            f"{row.ticker}: no financial statements"
            if row.latest_period_end_date is None
            else f"{row.ticker}@{row.latest_period_end_date}: missing {','.join(row.missing_items)}"
        )
        for row in report.tickers
        if not row.covered
    ]

    if failures:
        preview = "; ".join(failures[:10])
        suffix = f"; and {len(failures) - 10} more" if len(failures) > 10 else ""
        raise DashboardArtifactError(
            "financial_statements.json: reported financial-data coverage is "
            f"{report.covered_count}/{report.universe_count}; {preview}{suffix}"
        )


def _validate_optional_financial_coverage(
    directory: Path, counts: dict[str, int], universe_payload
) -> None:
    payload, present = _load_optional_json(directory, "financial_coverage.json")
    if not present:
        return
    try:
        report = FinancialCoverageReport.model_validate(payload)
    except Exception as exc:
        raise DashboardArtifactError(f"financial_coverage.json: {exc}") from exc
    if universe_payload is not None and sorted(row.ticker for row in report.tickers) != sorted(
        universe_payload["tickers"]
    ):
        raise DashboardArtifactError(
            "financial_coverage.json: membership differs from universe.json"
        )
    statements_payload, statements_present = _load_optional_json(
        directory, "financial_statements.json"
    )
    if universe_payload is not None and statements_present:
        if not isinstance(statements_payload, list):
            raise DashboardArtifactError(
                "financial_statements.json: expected a JSON array"
            )
        try:
            items = [
                FinancialStatementLineItem.model_validate(item)
                for item in statements_payload
            ]
        except Exception as exc:
            raise DashboardArtifactError(f"financial_statements.json: {exc}") from exc
        expected = build_financial_coverage_report(
            tickers=universe_payload["tickers"],
            items=items,
            as_of=date.fromisoformat(universe_payload["as_of"]),
        )
        if report != expected:
            raise DashboardArtifactError(
                "financial_coverage.json: values differ from financial_statements.json"
            )
    counts["financial_coverage.json"] = report.universe_count


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


def _validate_optional_publication_safety(directory: Path, counts: dict[str, int]) -> None:
    gate_payload, gate_present = _load_optional_json(directory, "publication_gate.json")
    cases_payload, cases_present = _load_optional_json(directory, "investment_cases.json")
    if not gate_present and not cases_present:
        return

    gate = None
    if gate_present:
        try:
            gate = PublicationGateReport.model_validate(gate_payload)
        except Exception as exc:
            raise DashboardArtifactError(f"publication_gate.json: {exc}") from exc
        counts["publication_gate.json"] = 1

    if not cases_present:
        return
    recommendations = [
        Recommendation.model_validate(item) for item in cases_payload.get("recommendations", [])
    ]
    ready_decisions = {
        (recommendation.ticker, decision.horizon)
        for recommendation in recommendations
        for decision in recommendation.horizon_decisions.values()
        if decision.publication_status == PublicationStatus.PUBLICATION_READY
    }
    if ready_decisions and (gate is None or not gate.publication_ready):
        raise DashboardArtifactError(
            "investment_cases.json: publication_ready decision exists without a passing "
            "publication_gate.json"
        )

    portfolio_payload = cases_payload.get("portfolio")
    if portfolio_payload is None:
        return
    portfolio = PortfolioRecommendation.model_validate(portfolio_payload)
    if gate is None or not gate.publication_ready:
        if portfolio.positions or abs(portfolio.cash_weight - 1.0) > 1e-9:
            raise DashboardArtifactError(
                "investment_cases.json: blocked or missing publication gate requires "
                "an all-cash portfolio"
            )
        return

    eligible_tickers = {
        recommendation.ticker
        for recommendation in recommendations
        if any(
            decision.publication_status == PublicationStatus.PUBLICATION_READY
            and decision.action == DecisionAction.BUY_CANDIDATE
            and decision.entry_value is not None
            and decision.invalidation_value is not None
            for decision in recommendation.horizon_decisions.values()
        )
    }
    ineligible = sorted(
        position.ticker
        for position in portfolio.positions
        if position.ticker not in eligible_tickers
    )
    if ineligible:
        raise DashboardArtifactError(
            "investment_cases.json: portfolio contains tickers without a publication-ready "
            f"numeric buy decision: {', '.join(ineligible)}"
        )


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
        raise DashboardArtifactError(
            "dashboard_metrics.json: expected an object with an 'artifacts' key"
        )
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
            raise DashboardArtifactError(
                "source_metrics.json: expected each row to have 'source_id'"
            )
    counts["source_metrics.json"] = len(payload)
