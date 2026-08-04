from datetime import date

from agx_research.collectors.orascom_financials import OrascomFinancialHighlightsCollector
from agx_research.collectors.provenance_index import ProvenanceIndexRepository
from agx_research.collectors.raw import build_raw_document
from agx_research.collectors.service import CollectionService
from agx_research.production.collector_plan import MockFetcher
from agx_research.sources.spec import (
    AccessMethod,
    LegalUseStatus,
    SourceCategory,
    SourceSpec,
    SourceStatus,
)


def _spec() -> SourceSpec:
    return SourceSpec(
        id="orascom_ir",
        name="Orascom Construction Investor Relations",
        category=SourceCategory.COMPANY,
        access_method=AccessMethod.HTML_SCRAPE,
        status=SourceStatus.IMPLEMENTED,
        legal_use_status=LegalUseStatus.RESEARCH_ONLY,
        base_url="https://orascom.com/updates/",
        reliability_score=0.95,
        freshness_score=0.9,
    )


def test_fetch_discovers_latest_result_article():
    article_url = (
        "https://orascom.com/updates/orascom-construction-reports-backlog-"
        "and-results-in-q1-2026/"
    )
    fetcher = MockFetcher(
        {
            _spec().base_url: f'<a href="{article_url}">Q1 2026 results</a>',
            article_url: "<h1>Q1 2026 Results</h1>",
        }
    )
    documents = OrascomFinancialHighlightsCollector(_spec(), fetcher=fetcher).fetch()
    assert documents[0].original_url == article_url


def test_parse_extracts_only_explicit_issuer_highlights():
    html = """
    <script>Revenue of USD 999,999 million</script>
    <h1>Results Q1 2026</h1>
    <p>Revenue of USD 1,468.4 million, EBITDA of USD 108.3 million, and
       net profit attributable to shareholders of USD 53.4 million in Q1 2026</p>
    """
    document = build_raw_document(
        source_id="orascom_ir",
        collector="OrascomFinancialHighlightsCollector",
        collector_version="1.0.0",
        original_url="https://orascom.com/updates/results-q1-2026/",
        content_text=html,
        schema_version="1.0.0",
        license="public issuer release",
    )
    batch = OrascomFinancialHighlightsCollector(_spec(), fetcher=MockFetcher({})).parse(document)
    assert [(row.line_item, row.value) for row in batch.financial_statement_line_items] == [
        ("revenue", 1_468_400_000.0),
        ("ebitda", 108_300_000.0),
        ("net_income_attributable", 53_400_000.0),
    ]
    assert all(row.period_end_date == date(2026, 3, 31) for row in batch.financial_statement_line_items)
    assert all(row.currency == "USD" for row in batch.financial_statement_line_items)


def test_parse_fails_closed_when_highlight_shape_changes():
    document = build_raw_document(
        source_id="orascom_ir",
        collector="OrascomFinancialHighlightsCollector",
        collector_version="1.0.0",
        original_url="https://orascom.com/updates/results/",
        content_text="<p>Q1 2026 revenue was strong.</p>",
        schema_version="1.0.0",
        license="public issuer release",
    )
    batch = OrascomFinancialHighlightsCollector(_spec(), fetcher=MockFetcher({})).parse(document)
    assert batch.financial_statement_line_items == []
    assert batch.parse_warnings


def test_collection_materializes_and_traces_every_financial_value(tmp_path):
    article_url = "https://orascom.com/updates/orascom-construction-reports-q1-2026/"
    fetcher = MockFetcher(
        {
            _spec().base_url: f'<a href="{article_url}">Q1 2026 results</a>',
            article_url: (
                "<h1>Q1 2026</h1><p>Revenue of USD 1,468.4 million, "
                "EBITDA of USD 108.3 million, and net profit attributable to "
                "shareholders of USD 53.4 million in Q1 2026</p>"
            ),
        }
    )
    provenance = ProvenanceIndexRepository()
    result = CollectionService(
        tmp_path, provenance_index=provenance, min_confidence=0.5
    ).run(OrascomFinancialHighlightsCollector(_spec(), fetcher=fetcher), expected_records=3)

    assert result.financial_statement_line_items_written == 3
    for line_item in ("revenue", "ebitda", "net_income_attributable"):
        record = provenance.trace(
            "financial_statement", f"ORAS|INCOME_STATEMENT|{line_item}", date(2026, 3, 31)
        )
        assert record is not None
        assert record.source_id == "orascom_ir"
        assert record.collector == "OrascomFinancialHighlightsCollector"
        assert record.content_hash
        assert record.raw_document_id
