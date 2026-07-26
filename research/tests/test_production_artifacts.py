"""export_collector_status: one row per source run, reporting every record
type CollectionService can materialize. Regression test for a real gap
found while auditing: the dashboard artifact silently omitted the newer
record types (corporate events, index constituents, financial statement
line items) CollectionService already materializes.

Also covers the frontend-audit-driven artifact additions (genes, papers,
hypotheses, knowledge graph, financial statements, source metrics) --
each a thin `model_dump(mode="json")` over an already-existing repository,
per `CLAUDE.md`'s sanctioned dashboard-artifact extension point.
"""

from datetime import date, datetime
from pathlib import Path

from agx_research.collectors.service import CollectionRunResult
from agx_research.domain.provenance import Provenance
from agx_research.genome.gene import Gene, GeneStatus
from agx_research.genome.service import AlphaGenome
from agx_research.graph.edges import GraphEdge
from agx_research.graph.knowledge_graph import KnowledgeGraph
from agx_research.graph.nodes import GraphNode, NodeType
from agx_research.hypotheses.hypothesis import Hypothesis
from agx_research.hypotheses.repository import HypothesisRepository
from agx_research.papers.paper import ResearchPaper
from agx_research.papers.repository import PaperRepository
from agx_research.production.artifacts import (
    export_collector_status,
    export_financial_statements,
    export_genes,
    export_hypotheses,
    export_knowledge_graph,
    export_papers,
    export_source_metrics,
)
from agx_research.sources.catalog import seed_registry
from agx_research.sources.registry import SourceRegistry
from agx_research.sources.reputation import SourceMetricsRepository
from agx_research.sources.spec import AccessMethod, SourceCategory, SourceSpec, SourceStatus


def make_result(**overrides) -> CollectionRunResult:
    defaults = dict(
        source_id="rss_generic",
        documents_fetched=1,
        batches_materialized=1,
        batches_withheld=0,
        price_bars_written=0,
        macro_observations_written=0,
        news_items_written=3,
        corporate_events_written=2,
        index_constituents_written=1,
        financial_statement_line_items_written=4,
        events_registered=3,
        assessments=[],
    )
    defaults.update(overrides)
    return CollectionRunResult(**defaults)


def test_reports_every_record_type_the_collection_service_can_materialize():
    registry = SourceRegistry()
    rows = export_collector_status(registry, {"rss_generic": make_result()})

    assert len(rows) == 1
    row = rows[0]
    assert row["news_items_written"] == 3
    assert row["corporate_events_written"] == 2
    assert row["index_constituents_written"] == 1
    assert row["financial_statement_line_items_written"] == 4


def test_reports_zero_for_a_source_that_produced_nothing_of_those_types():
    registry = SourceRegistry()
    rows = export_collector_status(
        registry,
        {"stooq": make_result(source_id="stooq", price_bars_written=10, news_items_written=0,
                               corporate_events_written=0, index_constituents_written=0,
                               financial_statement_line_items_written=0, events_registered=0)},
    )
    row = rows[0]
    assert row["corporate_events_written"] == 0
    assert row["index_constituents_written"] == 0
    assert row["financial_statement_line_items_written"] == 0


def test_zero_yield_is_reported_degraded_not_collected():
    """A source that connected (documents_fetched > 0) but produced zero
    usable records must never be reported COLLECTED/healthy -- e.g. Stooq
    returning an anti-bot challenge page instead of CSV."""
    registry = SourceRegistry()
    rows = export_collector_status(
        registry,
        {
            "stooq": make_result(
                source_id="stooq", documents_fetched=10, price_bars_written=0,
                news_items_written=0, corporate_events_written=0,
                index_constituents_written=0, financial_statement_line_items_written=0,
                events_registered=0,
            )
        },
    )
    row = rows[0]
    assert row["status"] == "DEGRADED"
    assert row["connection_success"] is True
    assert row["parse_success"] is False
    assert row["yield"] == 0
    assert row["reason"] is not None


def test_nonzero_yield_is_reported_collected():
    registry = SourceRegistry()
    rows = export_collector_status(
        registry,
        {
            "worldbank": make_result(
                source_id="worldbank", macro_observations_written=66, news_items_written=0,
                corporate_events_written=0, index_constituents_written=0,
                financial_statement_line_items_written=0,
            )
        },
    )
    row = rows[0]
    assert row["status"] == "COLLECTED"
    assert row["connection_success"] is True
    assert row["parse_success"] is True
    assert row["yield"] == 66
    assert row["reason"] is None


def test_composite_provider_legs_are_reported_as_collected_sources():
    registry = seed_registry(SourceRegistry())
    result = make_result(
        source_id="egx_price_composite",
        price_bars_written=30,
        news_items_written=0,
        corporate_events_written=0,
        index_constituents_written=0,
        financial_statement_line_items_written=0,
        provider_documents={"yahoo_finance": 2, "stockanalysis": 3},
        provider_yields={"yahoo_finance": 20, "stockanalysis": 10},
    )

    rows = export_collector_status(registry, {"egx_price_composite": result})
    by_id = {row["source_id"]: row for row in rows}

    assert by_id["yahoo_finance"]["status"] == "COLLECTED"
    assert by_id["yahoo_finance"]["yield"] == 20
    assert by_id["stockanalysis"]["documents_fetched"] == 3
    assert by_id["stockanalysis"]["integration_via"] == "egx_price_composite"
    assert by_id["mubasher"]["status"] == "STANDBY"
    assert "fallback" in by_id["mubasher"]["reason"]


def test_partial_fetch_with_usable_output_is_degraded_not_failed():
    registry = SourceRegistry()
    result = make_result(
        source_id="fred",
        macro_observations_written=2,
        news_items_written=0,
        corporate_events_written=0,
        index_constituents_written=0,
        financial_statement_line_items_written=0,
        fetch_warnings=["SERIES_X: TimeoutError: timeout"],
    )

    [row] = export_collector_status(registry, {"fred": result})

    assert row["status"] == "DEGRADED"
    assert row["yield"] == 2
    assert "SERIES_X" in row["reason"]


def test_fetch_failure_reported_as_failed_row_with_exact_reason():
    """A source whose fetch() raised entirely (never reaching results) must
    still get a visible row -- previously only surfaced in the execution
    report's warnings, not in collector_status.json at all."""
    registry = SourceRegistry()
    rows = export_collector_status(
        registry, {}, failures={"fred": "FetchError: 3 attempt(s) failed: timed out"}
    )
    row = rows[0]
    assert row["source_id"] == "fred"
    assert row["status"] == "FAILED"
    assert row["connection_success"] is False
    assert row["parse_success"] is False
    assert "timed out" in row["reason"]


def test_wired_unselected_source_is_reported_standby_not_unavailable():
    registry = seed_registry(SourceRegistry())
    rows = export_collector_status(
        registry,
        {},
        standby={"stooq": "Live collector is wired but a higher-ranked strategy won."},
    )

    [row] = rows
    assert row["source_id"] == "stooq"
    assert row["status"] == "STANDBY"
    assert row["connection_success"] is False
    assert "wired" in row["reason"]


def _provenance(**overrides):
    defaults = dict(produced_by="test", produced_at=datetime(2026, 6, 14), inputs=[])
    defaults.update(overrides)
    return Provenance(**defaults)


def test_export_genes_returns_every_gene_including_replaced_lineage():
    genome = AlphaGenome()
    gene = Gene(
        id="gene_1", knowledge_id="know_1", generation=0, status=GeneStatus.PROMOTED,
        provenance=_provenance(),
    )
    genome.repository.add(gene)
    result = export_genes(genome)
    assert len(result) == 1
    assert result[0]["id"] == "gene_1"
    assert result[0]["status"] == "promoted"


def test_export_genes_empty_when_none_promoted_yet():
    assert export_genes(AlphaGenome()) == []


def test_export_papers_returns_every_paper():
    papers = PaperRepository()
    papers.add(
        ResearchPaper(
            id="paper_1", title="COMI momentum persists", gene_id="gene_1",
            knowledge_id="know_1", hypothesis_id="hyp_1", problem="p", observation="o",
            methodology="m", dataset="d", experiments="e", evidence="ev", results="r",
            limitations="l", conclusion="c", future_work="f",
            published_at=datetime(2026, 6, 14), provenance=_provenance(),
        )
    )
    result = export_papers(papers)
    assert len(result) == 1
    assert result[0]["title"] == "COMI momentum persists"


def test_export_hypotheses_returns_stage_history():
    hypotheses = HypothesisRepository()
    hypotheses.add(
        Hypothesis(
            id="hyp_1", statement="COMI leads MFPC", created_by="macro_agent",
            created_at=date(2026, 6, 14), horizon="swing", affected_assets=["COMI", "MFPC"],
            provenance=_provenance(),
        )
    )
    result = export_hypotheses(hypotheses)
    assert len(result) == 1
    assert result[0]["created_by"] == "macro_agent"
    assert result[0]["stage_history"] == []


def test_export_knowledge_graph_returns_nodes_and_edges():
    graph = KnowledgeGraph()
    graph.add_node(GraphNode(id="COMI", node_type=NodeType.COMPANY, label="COMI"))
    graph.add_edge(
        GraphEdge(
            id="edge_1", source_id="event_1", source_type=NodeType.EVENT,
            target_id="COMI", target_type=NodeType.COMPANY, relationship="involves",
        )
    )
    result = export_knowledge_graph(graph)
    assert len(result["nodes"]) == 1
    assert len(result["edges"]) == 1
    assert result["edges"][0]["relationship"] == "involves"


def test_export_knowledge_graph_empty_when_nothing_populated():
    result = export_knowledge_graph(KnowledgeGraph())
    assert result == {"nodes": [], "edges": []}


def test_export_financial_statements_returns_none_when_as_of_is_none():
    assert export_financial_statements(Path("/nonexistent"), ["COMI"], None) == []


def test_export_financial_statements_flattens_across_tickers(tmp_path):
    path = tmp_path / "financial_statements" / "COMI.csv"
    path.parent.mkdir(parents=True)
    path.write_text(
        "period_end_date,period_type,statement_type,line_item,value,currency\n"
        "2026-06-30,QUARTERLY,INCOME_STATEMENT,revenue,1000000,EGP\n"
    )
    result = export_financial_statements(tmp_path, ["COMI", "MFPC"], date(2026, 12, 31))
    assert len(result) == 1
    assert result[0]["ticker"] == "COMI"
    assert result[0]["line_item"] == "revenue"


def _implemented_spec(source_id: str) -> SourceSpec:
    return SourceSpec(
        id=source_id, name=source_id.title(), category=SourceCategory.MARKET_DATA,
        access_method=AccessMethod.CSV_DOWNLOAD, status=SourceStatus.IMPLEMENTED,
        reliability_score=0.9, freshness_score=0.8,
    )


def test_export_source_metrics_joins_registry_identity_with_reputation_breakdown():
    registry = SourceRegistry()
    registry.add(_implemented_spec("stooq"))
    metrics = SourceMetricsRepository()
    metrics.record_run(
        "stooq", succeeded=True, records_expected=10, records_produced=10,
        confidence_score=0.9, freshness_score=0.8, coverage_score=0.7, materialized=True,
    )

    result = export_source_metrics(registry, metrics)

    assert len(result) == 1
    row = result[0]
    assert row["source_id"] == "stooq"
    assert row["runs_total"] == 1
    assert row["reputation"]["accuracy"] == 0.9


def test_export_source_metrics_reports_none_reputation_when_never_run():
    registry = SourceRegistry()
    registry.add(_implemented_spec("stooq"))
    result = export_source_metrics(registry, SourceMetricsRepository())
    assert result[0]["runs_total"] == 0
    assert result[0]["reputation"] is None
