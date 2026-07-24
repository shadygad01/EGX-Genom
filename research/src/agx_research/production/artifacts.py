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

from agx_research.collectors.service import CollectionRunResult
from agx_research.events.service import EventPlatform
from agx_research.financials.collected import CollectedFinancialStatementProvider
from agx_research.genome.service import AlphaGenome
from agx_research.graph.knowledge_graph import KnowledgeGraph
from agx_research.hypotheses.repository import HypothesisRepository
from agx_research.knowledge.store import KnowledgeStore
from agx_research.meta.recommendation_service import RecommendationService
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
    ).recommend(tickers, as_of)
    portfolio = PortfolioConstructor().construct(recommendations, as_of)
    return {
        "as_of": as_of.isoformat(),
        "recommendations": [r.model_dump(mode="json") for r in recommendations],
        "portfolio": portfolio.model_dump(mode="json"),
    }


def export_collector_status(
    registry: SourceRegistry, results: dict[str, CollectionRunResult]
) -> list[dict[str, Any]]:
    """One row per source actually run this execution: what it fetched,
    materialized, and withheld, plus the registry's current health/lifecycle/
    reputation state for that source after this run.
    """
    rows = []
    for source_id, result in results.items():
        spec = registry.latest(source_id)
        rows.append(
            {
                "source_id": source_id,
                "documents_fetched": result.documents_fetched,
                "batches_materialized": result.batches_materialized,
                "batches_withheld": result.batches_withheld,
                "price_bars_written": result.price_bars_written,
                "macro_observations_written": result.macro_observations_written,
                "news_items_written": result.news_items_written,
                "corporate_events_written": result.corporate_events_written,
                "index_constituents_written": result.index_constituents_written,
                "financial_statement_line_items_written": (
                    result.financial_statement_line_items_written
                ),
                "events_registered": result.events_registered,
                "lifecycle_state": spec.lifecycle_state.value if spec else None,
                "health_status": spec.health_status.value if spec else None,
                "reputation_score": spec.reputation_score if spec else None,
                "data_quality_score": spec.data_quality_score if spec else None,
            }
        )
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
