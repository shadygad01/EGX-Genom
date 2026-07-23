"""FinancialStatementCollector tests: parsing exercised against synthetic
CSV content via an injected fake fetcher. No live network involved -- same
posture as every other collector's tests.
"""

from datetime import date

from agx_research.collectors.financial_statements import FinancialStatementCollector
from agx_research.sources.spec import AccessMethod, SourceCategory, SourceSpec, SourceStatus


def make_spec(**overrides) -> SourceSpec:
    defaults = dict(
        id="company_ir",
        name="Company Investor Relations",
        category=SourceCategory.COMPANY,
        access_method=AccessMethod.CSV_DOWNLOAD,
        status=SourceStatus.IMPLEMENTED,
        base_url="https://comi.test/financials.csv",
        reliability_score=0.85,
        freshness_score=0.5,
    )
    defaults.update(overrides)
    return SourceSpec(**defaults)


class FakeFetcher:
    def __init__(self, text: str):
        self.text = text
        self.calls: list[str] = []

    def fetch_text(self, url, spec):
        self.calls.append(url)
        return self.text


def test_fetch_calls_base_url():
    fetcher = FakeFetcher("Period End,Period Type,Statement,Line Item,Value\n")
    collector = FinancialStatementCollector(make_spec(), ticker="COMI", fetcher=fetcher)
    [document] = collector.fetch()
    assert fetcher.calls == ["https://comi.test/financials.csv"]
    assert document.original_url == "https://comi.test/financials.csv"


def test_parse_finds_columns_regardless_of_order_and_normalizes_values():
    text = (
        "Line Item,Value,Statement,Period Type,Period End\n"
        "Revenue,1000000,Income Statement,Quarterly,2026-06-30\n"
        "Net Income,150000,Income Statement,Quarterly,2026-06-30\n"
    )
    fetcher = FakeFetcher(text)
    collector = FinancialStatementCollector(make_spec(), ticker="COMI", fetcher=fetcher)
    [document] = collector.fetch()
    batch = collector.parse(document)

    assert batch.parse_warnings == []
    assert len(batch.financial_statement_line_items) == 2
    revenue = next(i for i in batch.financial_statement_line_items if i.line_item == "revenue")
    assert revenue.ticker == "COMI"
    assert revenue.period_end_date == date(2026, 6, 30)
    assert revenue.period_type == "QUARTERLY"
    assert revenue.statement_type == "INCOME STATEMENT"
    assert revenue.value == 1000000.0
    assert revenue.currency == "EGP"  # no currency column supplied


def test_parse_respects_currency_column_when_present():
    text = "Period End,Period Type,Statement,Line Item,Value,Currency\n2026-06-30,ANNUAL,BALANCE_SHEET,total_assets,5000000,USD\n"
    fetcher = FakeFetcher(text)
    collector = FinancialStatementCollector(make_spec(), ticker="COMI", fetcher=fetcher)
    [document] = collector.fetch()
    batch = collector.parse(document)
    assert batch.financial_statement_line_items[0].currency == "USD"


def test_parse_records_warning_when_required_columns_missing():
    fetcher = FakeFetcher("Foo,Bar\n1,2\n")
    collector = FinancialStatementCollector(make_spec(), ticker="COMI", fetcher=fetcher)
    [document] = collector.fetch()
    batch = collector.parse(document)
    assert batch.financial_statement_line_items == []
    assert "Could not identify column" in batch.parse_warnings[0]


def test_parse_skips_malformed_and_unparseable_rows_without_dropping_silently():
    text = (
        "Period End,Period Type,Statement,Line Item,Value\n"
        "2026-06-30,QUARTERLY,INCOME_STATEMENT,revenue,not-a-number\n"
        "2026-06-30,QUARTERLY\n"
        "2026-06-30,QUARTERLY,INCOME_STATEMENT,net_income,150000\n"
    )
    fetcher = FakeFetcher(text)
    collector = FinancialStatementCollector(make_spec(), ticker="COMI", fetcher=fetcher)
    [document] = collector.fetch()
    batch = collector.parse(document)
    assert len(batch.financial_statement_line_items) == 1
    assert batch.financial_statement_line_items[0].line_item == "net_income"
    assert len(batch.parse_warnings) == 2


def test_empty_document_records_warning():
    fetcher = FakeFetcher("")
    collector = FinancialStatementCollector(make_spec(), ticker="COMI", fetcher=fetcher)
    [document] = collector.fetch()
    batch = collector.parse(document)
    assert batch.financial_statement_line_items == []
    assert batch.parse_warnings == ["Empty document; nothing parsed."]
