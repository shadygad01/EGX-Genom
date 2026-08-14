from agx_research.collectors.raw import build_raw_document
from agx_research.collectors.stockanalysis_financials import StockAnalysisFinancialsCollector
from agx_research.sources.catalog import seed_registry

HTML = '''<table>
<tr><th>Fiscal Year</th><th>TTM</th><th>FY 2025</th><th>FY 2024</th></tr>
<tr><th>Period Ending</th><th>Jun '26 Jun 30, 2026</th><th>Dec '25 Dec 31, 2025</th><th>Dec '24 Dec 31, 2024</th></tr>
<tr><td>Revenue Revenue Growth</td><td>99</td><td>1,250</td><td>1,100</td></tr>
<tr><td>Revenue Growth</td><td>10%</td><td>5%</td><td>4%</td></tr>
<tr><td>Net Income Net Income Growth</td><td>20</td><td>220</td><td>180</td></tr>
</table>
<table>
<tr><th>Fiscal Year</th><th>Current</th><th>FY 2025</th></tr>
<tr><th>Period Ending</th><th>Dec '25 Dec 31, 2025</th><th>Dec '25 Dec 31, 2025</th></tr>
<tr><td>Total Debt Total Debt Growth</td><td>5</td><td>100</td></tr>
</table>'''


def test_stockanalysis_parser_extracts_annual_rows_only():
    spec = seed_registry().latest('company_ir')
    collector = StockAnalysisFinancialsCollector(spec, tickers=['ABUK'], fetcher=None)
    document = build_raw_document(source_id='stockanalysis_financials', collector='test', collector_version='1', original_url=collector.url('ABUK'), content_text=HTML, schema_version=spec.schema_version, license=spec.license)
    batch = collector.parse(document)
    values = {(x.line_item, x.period_end_date.isoformat(), x.value) for x in batch.financial_statement_line_items}
    assert ('revenue', '2025-12-31', 1250.0) in values
    assert ('net_income', '2024-12-31', 180.0) in values
    assert ('total_debt', '2025-12-31', 100.0) in values
    assert all(x.period_type == 'ANNUAL' for x in batch.financial_statement_line_items)
