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
from agx_research.knowledge.store import KnowledgeStore
from agx_research.meta.recommendation_service import RecommendationService
from agx_research.portfolio.constructor import PortfolioConstructor
from agx_research.runtime.engine import RunRecord
from agx_research.sources.registry import SourceRegistry


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
