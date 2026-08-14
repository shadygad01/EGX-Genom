from agx_research.collectors.mubasher_financials import MubasherFinancialsCollector
from agx_research.collectors.raw import build_raw_document
from agx_research.sources.catalog import seed_registry

HTML = """<script>
midata.financialStatement = {'currency':'Egyptian Pound(EGP)','periods':[{'label':'Fourth Quarter','sections':[{'label':'Balance Sheet','records':[{'label':'Total Assets','values':{'2025':1000.0,'2024':900.0}},{'label':'Total Liabilities','values':{'2025':400.0,'2024':350.0}},{'label':\"Total Owners' Equity & Minority Interest Equity\",'values':{'2025':600.0,'2024':550.0}}]},{'label':'Income Statement','records':[{'label':'Net Income or Loss','values':{'2025':120.0,'2024':100.0}}]},{'label':'Cash Flow','records':[{'label':'Net Cash Flow from (Used In) Operating Activities','values':{'2025':200.0,'2024':180.0}}]}]}]};
</script>"""


def test_mubasher_parser_extracts_structured_financials():
    spec = seed_registry().latest('mubasher_financials')
    collector = MubasherFinancialsCollector(spec, tickers=['TANM'], fetcher=None)
    document = build_raw_document(source_id=spec.id, collector=collector.name, collector_version=collector.version, original_url=collector.url('TANM'), content_text=HTML, schema_version=spec.schema_version, license=spec.license)
    batch = collector.parse(document)
    values = {(item.line_item, item.period_end_date.isoformat(), item.value, item.currency) for item in batch.financial_statement_line_items}
    assert ('total_assets', '2025-12-31', 1000.0, 'Egyptian Pound(EGP)') in values
    assert ('net_income', '2024-12-31', 100.0, 'Egyptian Pound(EGP)') in values
    assert ('operating_cash_flow', '2025-12-31', 200.0, 'Egyptian Pound(EGP)') in values
