from agx_research.collectors.raw import build_raw_document
from agx_research.collectors.telecom_egypt_financials import (
    TelecomEgyptFinancialHighlightsCollector,
)
from agx_research.production.collector_plan import MockFetcher
from agx_research.sources.spec import (
    AccessMethod,
    SourceCategory,
    SourceSpec,
    SourceStatus,
)

HOME = "https://ir.te.eg/"
RELEASE = (
    "https://ir.te.eg/en/CorporateNews/PressRelease/236/"
    "Q1-2026-Results-Telecom-Egypt-Reports-Strong-Underlying-Business-Performance"
)


def make_spec() -> SourceSpec:
    return SourceSpec(
        id="telecom_egypt_ir",
        name="Telecom Egypt Investor Relations",
        category=SourceCategory.COMPANY,
        access_method=AccessMethod.HTML_SCRAPE,
        status=SourceStatus.IMPLEMENTED,
        base_url=HOME,
        reliability_score=0.95,
        freshness_score=0.9,
        license="Public issuer IR release; research use with attribution.",
    )


RELEASE_HTML = """
<html><head><script>const noise = 'Net profit reached EGP 999bn';</script></head>
<body><h1>Q1 2026 Results: Telecom Egypt Reports Strong Underlying Business Performance</h1>
<p>Total revenue grew 14% YoY to EGP 28.2bn.</p>
<p>EBITDA rose 17% YoY to EGP 12.6bn.</p>
<p>Net profit reached EGP 3.6bn, with a 13% net margin.</p>
<p>FCFF rose to EGP 6.4bn from EGP 3.5bn YoY.</p>
<p>Net debt/EBITDA stood at 1.3x at period-end.</p></body></html>
"""


def test_fetch_discovers_latest_release_from_official_ir_homepage():
    fetcher = MockFetcher(
        {
            HOME: f'<a href="{RELEASE.removeprefix(HOME)}">Q1 2026 Results</a>',
            RELEASE: RELEASE_HTML,
        }
    )
    documents = TelecomEgyptFinancialHighlightsCollector(make_spec(), fetcher).fetch()

    assert fetcher.calls == [HOME, RELEASE]
    assert len(documents) == 1
    assert documents[0].original_url == RELEASE
    assert documents[0].content_text == RELEASE_HTML


def test_parse_materializes_only_explicit_labelled_primary_metrics():
    document = build_raw_document(
        source_id="telecom_egypt_ir",
        collector="TelecomEgyptFinancialHighlightsCollector",
        collector_version="1.0.0",
        original_url=RELEASE,
        content_text=RELEASE_HTML,
        schema_version="1.0.0",
        license="Public issuer IR release; research use with attribution.",
    )
    batch = TelecomEgyptFinancialHighlightsCollector(make_spec()).parse(document)

    by_item = {item.line_item: item for item in batch.financial_statement_line_items}
    assert set(by_item) == {
        "revenue",
        "ebitda",
        "net_income",
        "free_cash_flow",
        "revenue_growth_yoy",
        "ebitda_growth_yoy",
        "net_margin",
        "net_debt_to_ebitda",
    }
    assert by_item["revenue"].value == 28_200_000_000
    assert by_item["net_income"].value == 3_600_000_000
    assert by_item["free_cash_flow"].statement_type == "CASH_FLOW"
    assert by_item["revenue_growth_yoy"].value == 14
    assert by_item["ebitda_growth_yoy"].value == 17
    assert by_item["net_margin"].value == 13
    assert by_item["net_debt_to_ebitda"].value == 1.3
    assert by_item["net_debt_to_ebitda"].currency == "x"
    assert all(item.period_end_date.isoformat() == "2026-03-31" for item in by_item.values())
    assert batch.parse_warnings == []


def test_parse_fails_closed_without_a_reporting_period():
    document = build_raw_document(
        source_id="telecom_egypt_ir",
        collector="TelecomEgyptFinancialHighlightsCollector",
        collector_version="1.0.0",
        original_url=RELEASE,
        content_text="<p>Total revenue grew to EGP 28.2bn.</p>",
        schema_version="1.0.0",
        license="Public issuer IR release; research use with attribution.",
    )
    batch = TelecomEgyptFinancialHighlightsCollector(make_spec()).parse(document)
    assert batch.financial_statement_line_items == []
    assert batch.parse_warnings == [
        "Could not identify the financial reporting period; nothing parsed."
    ]
