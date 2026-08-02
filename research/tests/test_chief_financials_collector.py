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


def test_walks_index_pagination_until_a_page_adds_no_new_company():
    page1 = '<a href="https://chiefcapitalco.com/companies/telecom-egypt/">ETEL</a>'
    page2 = '<a href="https://chiefcapitalco.com/companies/orascom-construction/">ORAS</a>'
    company_page = {
        "https://chiefcapitalco.com/companies/telecom-egypt/": (
            'Ticker: <span class="cc-meta-value">ETEL</span>'
            '<script>var ccData={csvURL: "https://chiefcapitalco.com/uploads/telecom-egypt.csv"};</script>'
        ),
        "https://chiefcapitalco.com/companies/orascom-construction/": (
            'Ticker: <span class="cc-meta-value">ORAS</span>'
            '<script>var ccData={csvURL: "https://chiefcapitalco.com/uploads/orascom.csv"};</script>'
        ),
    }
    csv_by_url = {
        "https://chiefcapitalco.com/uploads/telecom-egypt.csv": CSV,
        "https://chiefcapitalco.com/uploads/orascom.csv": CSV.replace("2024", "2024"),
    }

    class PaginatingFetcher:
        def __init__(self):
            self.request_latencies = []
            self.requested_pages: list[str] = []

        def fetch_text(self, url, spec):
            if url == "https://chiefcapitalco.com/companies/":
                self.requested_pages.append(url)
                return page1
            if url == "https://chiefcapitalco.com/companies/page/2/":
                self.requested_pages.append(url)
                return page2
            if url == "https://chiefcapitalco.com/companies/page/3/":
                self.requested_pages.append(url)
                # Same content as page 2 -- no new company link -- pagination stops.
                return page2
            if url in company_page:
                return company_page[url]
            if url in csv_by_url:
                return csv_by_url[url]
            raise AssertionError(f"unexpected fetch: {url}")

    fetcher = PaginatingFetcher()
    collector = ChiefFinancialsCollector(
        seed_registry().latest("chief_egx_financials"), tickers=["ETEL", "ORAS"], fetcher=fetcher
    )
    documents = collector.fetch()

    assert fetcher.requested_pages == [
        "https://chiefcapitalco.com/companies/",
        "https://chiefcapitalco.com/companies/page/2/",
        "https://chiefcapitalco.com/companies/page/3/",
    ]
    assert {doc.original_url for doc in documents} == set(csv_by_url)


def test_derives_real_sector_from_chiefs_own_csv_url_category():
    # Real, live-observed URL shape (2026-08-02 production run):
    # ".../egx-egyptian-stock-exchange/building-materials/metrics.csv/
    # arabian-cement-company.csv" -- Chief's own category, not a guess.
    real_shaped_page = """
    Ticker: <span class="cc-meta-value">ETEL</span>
    <script>var ccData={csvURL: "https://chiefcapitalco.com/wp-content/uploads/companydata/egx-egyptian-stock-exchange/building-materials/metrics.csv/arabian-cement-company.csv"};</script>
    """

    class Fetcher:
        request_latencies: list[float] = []

        def fetch_text(self, url, spec):
            if url.endswith("telecom-egypt/"):
                return real_shaped_page
            if url.endswith("arabian-cement-company.csv"):
                return CSV
            return INDEX

    collector = ChiefFinancialsCollector(
        seed_registry().latest("chief_egx_financials"), tickers=["ETEL"], fetcher=Fetcher()
    )
    [document] = collector.fetch()
    batch = collector.parse(document)

    assert batch.parse_warnings == []
    [classification] = batch.sector_classifications
    assert classification.ticker == "ETEL"
    assert classification.sector == "Building Materials"
    assert classification.source_id == "chief_egx_financials"


def test_no_sector_classification_when_url_has_no_category_segment():
    # The existing fixture's CSV URL (no .../egx-egyptian-stock-exchange/
    # {category}/ segment) -- must not fabricate a sector from nothing.
    collector = ChiefFinancialsCollector(
        seed_registry().latest("chief_egx_financials"), tickers=["ETEL"], fetcher=Fetcher()
    )
    [document] = collector.fetch()
    batch = collector.parse(document)

    assert batch.sector_classifications == []


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
