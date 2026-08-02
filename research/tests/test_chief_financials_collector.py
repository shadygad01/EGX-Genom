from agx_research.collectors.chief_financials import ChiefFinancialsCollector
from agx_research.production.collector_plan import build_live_collector
from agx_research.sources.catalog import seed_registry

INDEX = '<a href="https://chiefcapitalco.com/companies/telecom-egypt/">ETEL</a>'
PAGE = """
Ticker: <span class="cc-meta-value">ETEL</span>
<script>var ccData={csvURL: "https://chiefcapitalco.com/uploads/telecom-egypt.csv"};</script>
"""
CSV = """Year,Assets,BookValue,Revenue,NetProfit,EPS,OCF,FCF,SharesOutstanding,P/E,P/BV,ClosingPrice,TotalDebt
2024,1000,400,800,100,2,120,90,50,8,2,16,200
2025,1200,500,950,130,2.6,150,110,50,9,2.3,23.4,180
"""


class Fetcher:
    def __init__(self):
        self.request_latencies = []

    def fetch_text(self, url, spec):
        if url.endswith("telecom-egypt/"):
            return PAGE
        if url.endswith("telecom-egypt.csv"):
            return CSV
        return INDEX


def test_live_plan_wires_chief_structured_financials():
    spec = seed_registry().latest("chief_egx_financials")
    collector = build_live_collector(
        "chief_egx_financials", spec, fetcher=Fetcher(), tickers=["ETEL"]
    )
    assert isinstance(collector, ChiefFinancialsCollector)


def test_discovers_public_csv_and_maps_only_explicit_financial_headers():
    collector = ChiefFinancialsCollector(
        seed_registry().latest("chief_egx_financials"), tickers=["ETEL"], fetcher=Fetcher()
    )
    [document] = collector.fetch()
    batch = collector.parse(document)

    assert batch.parse_warnings == []
    assert {item.period_end_date.year for item in batch.financial_statement_line_items} == {2024, 2025}
    latest = {
        item.line_item: item.value
        for item in batch.financial_statement_line_items
        if item.period_end_date.year == 2025
    }
    assert latest["free_cash_flow"] == 110
    assert latest["shares_outstanding"] == 50
    assert latest["historical_pe"] == 9
    assert latest["historical_pb"] == 2.3
