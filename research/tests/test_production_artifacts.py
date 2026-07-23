"""export_collector_status: one row per source run, reporting every record
type CollectionService can materialize. Regression test for a real gap
found while auditing: the dashboard artifact silently omitted the newer
record types (corporate events, index constituents, financial statement
line items) CollectionService already materializes.
"""

from agx_research.collectors.service import CollectionRunResult
from agx_research.production.artifacts import export_collector_status
from agx_research.sources.registry import SourceRegistry


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
