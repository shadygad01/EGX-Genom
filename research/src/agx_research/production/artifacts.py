"""Production artifact exports beyond the existing eight dashboard files
(`dashboard.export.write_dashboard_artifacts`, unchanged): the Investment
Case Generator's output, a per-collector run summary, this execution's
research-pipeline run record, and a small dashboard-metrics rollup. Every
function here is the same pattern `dashboard/export.py` already
established -- a thin `model_dump(mode="json")` over an existing domain
model, no new schema invented for something that already has one.
"""

from __future__ import annotations

from datetime import date, datetime
from pathlib import Path
from typing import Any

from agx_research.acquisition_intelligence.capability_engine import CapabilityDecision
from agx_research.collectors.service import CollectionRunResult, collection_yield
from agx_research.dashboard.schemas import SourceTruthRow
from agx_research.events.service import EventPlatform
from agx_research.financials.collected import CollectedFinancialStatementProvider
from agx_research.genome.service import AlphaGenome
from agx_research.graph.knowledge_graph import KnowledgeGraph
from agx_research.hypotheses.repository import HypothesisRepository
from agx_research.knowledge.store import KnowledgeStore
from agx_research.meta.readiness import DecisionReadiness, build_ticker_data_gap_report
from agx_research.meta.recommendation_service import RecommendationService
from agx_research.config import Horizon
from agx_research.papers.repository import PaperRepository
from agx_research.portfolio.constructor import PortfolioConstructor
from agx_research.runtime.engine import RunRecord
from agx_research.sources.registry import SourceRegistry
from agx_research.sources.reputation import SourceMetricsRepository, compute_reputation

# Financial statements have no natural "start" date to filter by (a company's
# full collected history should surface, not an arbitrary recent window) --
# this predates any real EGX filing by construction, so it never excludes one.
_EARLIEST_POSSIBLE_FILING_DATE = date(2000, 1, 1)


def export_investment_cases(
    knowledge_store: KnowledgeStore,
    event_platform: EventPlatform,
    *,
    tickers: list[str],
    as_of: date | None,
    ready_horizons_by_ticker: dict[str, set[Horizon]] | None = None,
    latest_prices: dict[str, float] | None = None,
) -> dict[str, Any]:
    """The Investment Case Generator: per-ticker recommendations (already
    `meta.RecommendationService`) plus the cross-ticker portfolio built from
    them (already `portfolio.PortfolioConstructor`) -- composed, not
    reimplemented. Absence of evidence produces an empty case, never a
    fabricated one.
    """
    if as_of is None:
        return {"as_of": None, "recommendations": [], "portfolio": None}
    recommendations = RecommendationService(
        knowledge_store, event_platform=event_platform
    ).recommend(
        tickers,
        as_of,
        ready_horizons_by_ticker=ready_horizons_by_ticker,
        latest_prices=latest_prices,
    )
    portfolio = PortfolioConstructor().construct(recommendations, as_of)
    return {
        "as_of": as_of.isoformat(),
        "recommendations": [r.model_dump(mode="json") for r in recommendations],
        "portfolio": portfolio.model_dump(mode="json"),
    }


def _collector_status_row(
    source_id: str,
    registry: SourceRegistry,
    *,
    status: str,
    reason: str | None,
    result: CollectionRunResult | None = None,
) -> dict[str, Any]:
    spec = registry.latest(source_id)
    yield_count = collection_yield(result) if result else 0
    return {
        "source_id": source_id,
        "status": status,
        "reason": reason,
        # Explicit, mission-required metrics -- health is computed from
        # usable output (yield/events), never from HTTP success alone.
        "connection_success": bool(result and result.documents_fetched > 0),
        "parse_success": yield_count > 0,
        "yield": yield_count,
        "events_produced": result.events_registered if result else 0,
        "documents_fetched": result.documents_fetched if result else 0,
        "batches_materialized": result.batches_materialized if result else 0,
        "batches_withheld": result.batches_withheld if result else 0,
        "price_bars_written": result.price_bars_written if result else 0,
        "macro_observations_written": result.macro_observations_written if result else 0,
        "news_items_written": result.news_items_written if result else 0,
        "corporate_events_written": result.corporate_events_written if result else 0,
        "index_constituents_written": (
            result.index_constituents_written if result else 0
        ),
        "financial_statement_line_items_written": (
            result.financial_statement_line_items_written if result else 0
        ),
        "events_registered": result.events_registered if result else 0,
        "lifecycle_state": spec.lifecycle_state.value if spec else None,
        "health_status": spec.health_status.value if spec else None,
        "reputation_score": spec.reputation_score if spec else None,
        "data_quality_score": spec.data_quality_score if spec else None,
        "integration_via": spec.integrated_via if spec else None,
        "integrated_capabilities": spec.integrated_capabilities if spec else [],
    }


def export_collector_status(
    registry: SourceRegistry,
    results: dict[str, CollectionRunResult],
    *,
    unavailable: dict[str, str] | None = None,
    failures: dict[str, str] | None = None,
    standby: dict[str, str] | None = None,
) -> list[dict[str, Any]]:
    """One row per source this execution knew about, with an explicit,
    output-based status -- never HTTP success alone:

    - `COLLECTED`: ran, connected, and produced at least one usable
      canonical record (yield > 0).
    - `DEGRADED`: ran and connected (HTTP-level success, documents
      fetched), but parsing produced zero usable records -- e.g. an
      anti-bot challenge page, a wrong endpoint, or an unexpected format.
      Never reported as healthy on zero yield, per the mission's explicit
      rule (a real gap this closes: a source's first-ever zero-yield run
      previously showed as COLLECTED/healthy with no reason at all).
    - `FAILED`: the collector was attempted this run but `fetch()` itself
      raised (timeout, DNS, connection refused, ...) -- `reason` carries
      the exact exception.
    - `UNAVAILABLE`: never attempted this run at all (PLANNED/NEEDS_KEY/
      TOS_REVIEW/no verified config) -- `reason` explains why, per the
      mission's graceful-degradation requirement: an unreachable/blocked
      source must be visible with a reason, never silently omitted.

    `health_status`/`reputation_score`/`data_quality_score` are read from
    the registry *after* this run's `CollectionService` call, which now
    records metrics/health for a `FAILED` fetch too (previously a fetch
    exception bypassed the health/reputation system entirely).
    """
    rows = []
    for source_id, result in results.items():
        yield_count = collection_yield(result)
        if yield_count > 0:
            if result.fetch_warnings:
                status = "DEGRADED"
                reason = "Partial fetch: " + "; ".join(result.fetch_warnings)
            else:
                status, reason = "COLLECTED", None
        else:
            status = "DEGRADED"
            reason = (
                f"Connected and fetched {result.documents_fetched} document(s), but "
                "parsing produced zero usable records this run (see the raw archived "
                "document/parse warnings for the exact cause)."
            )
        rows.append(_collector_status_row(source_id, registry, status=status, reason=reason, result=result))

        # Provider legs inside a composite are first-class operational sources.
        # They get their own rows without pretending that a standalone collector ran.
        for provider_id, documents in sorted(result.provider_documents.items()):
            provider_spec = registry.latest(provider_id)
            if provider_spec is None or provider_spec.integrated_via != source_id:
                continue
            provider_yield = result.provider_yields.get(provider_id, 0)
            row = _collector_status_row(
                provider_id,
                registry,
                status="COLLECTED" if provider_yield > 0 else "DEGRADED",
                reason=f"Integrated via {source_id} for {', '.join(provider_spec.integrated_capabilities)}.",
            )
            row.update({
                "connection_success": documents > 0,
                "parse_success": provider_yield > 0,
                "yield": provider_yield,
                "documents_fetched": documents,
                "health_status": (
                    registry.latest(source_id).health_status.value
                    if registry.latest(source_id) else None
                ),
            })
            rows.append(row)
    emitted_ids = {row["source_id"] for row in rows}
    for spec in registry.all_latest():
        if (
            spec.integrated_via
            and spec.integrated_via in results
            and spec.id not in emitted_ids
        ):
            rows.append(_collector_status_row(
                spec.id,
                registry,
                status="STANDBY",
                reason=(
                    f"Wired as a fallback via {spec.integrated_via}; the primary provider "
                    "covered this run, so no request was needed."
                ),
            ))
    for source_id, reason in (failures or {}).items():
        rows.append(_collector_status_row(source_id, registry, status="FAILED", reason=reason))
    for source_id, reason in (standby or {}).items():
        rows.append(_collector_status_row(source_id, registry, status="STANDBY", reason=reason))
    for source_id, reason in (unavailable or {}).items():
        rows.append(_collector_status_row(source_id, registry, status="UNAVAILABLE", reason=reason))
    return rows


def export_runtime_status(run_record: RunRecord | None) -> dict[str, Any] | None:
    """This execution's own research-pipeline run record (singular) --
    distinct from `runtime_metrics.json`'s full accumulated ledger.
    """
    return run_record.model_dump(mode="json") if run_record else None


def export_dashboard_metrics(
    dashboard_dir: Path, artifact_counts: dict[str, int]
) -> dict[str, Any]:
    return {
        "generated_at": datetime.now().isoformat(),
        "dashboard_dir": str(dashboard_dir),
        "artifacts": artifact_counts,
        "total_artifacts": len(artifact_counts),
    }


def export_genes(genome: AlphaGenome) -> list[dict[str, Any]]:
    """`Gene` lineage -- every generation, including `REPLACED` parents, so
    the Company Research Workspace can render a full mutation history, not
    just the currently-active gene.
    """
    return [g.model_dump(mode="json") for g in genome.repository.all_latest()]


def export_papers(papers: PaperRepository) -> list[dict[str, Any]]:
    return [p.model_dump(mode="json") for p in papers.all_latest()]


def export_hypotheses(hypotheses: HypothesisRepository) -> list[dict[str, Any]]:
    """Every hypothesis at its current pipeline stage, `stage_history`
    included -- this is the Research Center's validation queue (in-flight
    gates), discovery history (every stage ever evaluated), and retired-
    knowledge view (a hypothesis that failed a gate) all from the same
    already-persisted record, not three separate exports.
    """
    return [h.model_dump(mode="json") for h in hypotheses.all_latest()]


def export_knowledge_graph(graph: KnowledgeGraph) -> dict[str, Any]:
    """The Knowledge Graph is a *view* over `Provenance` (see
    `graph.builder.edges_from_provenance`'s docstring) -- exporting its
    already-populated nodes/edges repositories, not recomputing anything.
    """
    return {
        "nodes": [n.model_dump(mode="json") for n in graph.nodes.all_latest()],
        "edges": [e.model_dump(mode="json") for e in graph.edges.all_latest()],
    }


def export_financial_statements(
    data_dir: Path, tickers: list[str], as_of: date | None
) -> list[dict[str, Any]]:
    """Every collected financial-statement line item across `tickers`, up
    to `as_of` -- empty per ticker (never fabricated) until a real
    financial-statement collector has run (see `docs/TECHNICAL_DEBT.md`
    TD-31/TD-32 for what's still collector-side blocked).
    """
    if as_of is None:
        return []
    provider = CollectedFinancialStatementProvider(data_dir)
    items: list[dict[str, Any]] = []
    for ticker in tickers:
        items.extend(
            item.model_dump(mode="json")
            for item in provider.get_line_items(ticker, _EARLIEST_POSSIBLE_FILING_DATE, as_of)
        )
    return items


def export_ticker_data_gap_report(
    readiness_rows: list[DecisionReadiness],
) -> list[dict[str, Any]]:
    """Per-ticker breakdown of `decision_readiness.json` into five named
    data layers (Financials/Disclosures/News/Macro/Knowledge), each with a
    completeness percentage -- so it's visible at a glance exactly which
    layer blocks a given ticker's Swing/Investment readiness. Derived
    entirely from `assess_decision_readiness`'s own counts and gates
    (`meta.readiness.build_ticker_data_gap_report`); never a second set of
    thresholds that could disagree with `decision_readiness.json`.
    """
    return [r.model_dump(mode="json") for r in build_ticker_data_gap_report(readiness_rows)]


def export_acquisition_decisions(decisions: list[CapabilityDecision]) -> list[dict[str, Any]]:
    """Every capability's full acquisition decision this run -- which
    strategies were ranked, which were attempted, and why the winner (if
    any) was selected. This is what makes the capability-driven Acquisition
    Decision Engine's choices explainable in Mission Control, not just its
    bottom-line collection results (`collector_status.json`).
    """
    return [d.model_dump(mode="json") for d in decisions]


def export_source_metrics(
    registry: SourceRegistry, metrics: SourceMetricsRepository
) -> list[dict[str, Any]]:
    """The full nine-dimension `ReputationScore` breakdown per source,
    joined with the registry's identity fields -- `source_registry.json`
    only carries the final composite `reputation_score`; this is what the
    Source Intelligence page needs to explain *why* a source scores what
    it does (availability vs. freshness vs. latency, not just one number).
    """
    rows: list[dict[str, Any]] = []
    for spec in registry.collectable():
        source_metrics = metrics.latest(spec.id)
        score = compute_reputation(source_metrics) if source_metrics else None
        rows.append(
            {
                "source_id": spec.id,
                "name": spec.name,
                "category": spec.category.value,
                "runs_total": source_metrics.runs_total if source_metrics else 0,
                "first_run_at": (
                    source_metrics.first_run_at.isoformat()
                    if source_metrics and source_metrics.first_run_at
                    else None
                ),
                "last_run_at": (
                    source_metrics.last_run_at.isoformat()
                    if source_metrics and source_metrics.last_run_at
                    else None
                ),
                "reputation": score.model_dump(mode="json") if score else None,
            }
        )
    return rows


def export_source_truth(
    registry: SourceRegistry,
    collector_status: list[dict[str, Any]],
    source_metrics: list[dict[str, Any]],
    decision_routes: list[dict[str, Any]],
    *,
    generated_at: datetime | None = None,
    freshness_hours: int = 48,
) -> list[dict[str, Any]]:
    """Join catalogue, legality, latest run, freshness and decision routing.

    A declared route alone is insufficient: `reached_decision_path` is true
    only when this run produced usable records and the source has a consumer
    ending at the Meta Decision Engine.
    """
    now = generated_at or datetime.now()
    collector_by_id = {row["source_id"]: row for row in collector_status}
    metrics_by_id = {row["source_id"]: row for row in source_metrics}
    routes_by_id = {row["source_id"]: row for row in decision_routes}
    rows: list[SourceTruthRow] = []
    for spec in registry.all_latest():
        collector = collector_by_id.get(spec.id, {})
        metrics = metrics_by_id.get(spec.id, {})
        route = routes_by_id.get(spec.id, {})
        last_run_raw = metrics.get("last_run_at")
        last_run_at = datetime.fromisoformat(last_run_raw) if last_run_raw else None
        comparison_now = now
        if last_run_at and last_run_at.tzinfo and not comparison_now.tzinfo:
            comparison_now = comparison_now.replace(tzinfo=last_run_at.tzinfo)
        fresh = bool(
            last_run_at
            and (comparison_now - last_run_at).total_seconds() <= freshness_hours * 3600
        )
        produced_records = int(collector.get("yield", 0) or 0)
        consumers = list(route.get("consumers", []))
        legal = (
            spec.legal_use_status.value == "cleared"
            and spec.status.value == "implemented"
            and spec.activation_status.value == "active"
        )
        status = str(collector.get("status", "NOT_RUN"))
        rows.append(
            SourceTruthRow(
                source_id=spec.id,
                name=spec.name,
                category=spec.category.value,
                legally_usable=legal,
                attempted_this_run=status in {"COLLECTED", "DEGRADED", "FAILED"},
                fetched_this_run=bool(collector.get("connection_success", False)),
                fresh=fresh,
                produced_records=produced_records,
                reached_decision_path=(
                    produced_records > 0 and "meta_decision_engine" in consumers
                ),
                corroborated=(
                    produced_records > 0
                    and len(route.get("providers", [])) >= 2
                ),
                collector_status=status,
                blocker=collector.get("reason") if not produced_records else None,
                last_run_at=last_run_at,
                consumers=consumers,
            )
        )
    return [row.model_dump(mode="json") for row in rows]
