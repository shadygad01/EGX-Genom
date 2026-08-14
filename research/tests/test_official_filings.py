from pathlib import Path

from agx_research.collectors.archive import RawArchive
from agx_research.collectors.official_filings import OfficialFilingsCollector
from agx_research.sources.catalog import seed_registry

HOME = "https://issuer.example/ir/"
CSV_URL = "https://issuer.example/ir/annual.csv"
HTML = '<html><a href="annual.csv">Annual Report Data</a></html>'
CSV = "period_end,period_type,statement_type,line_item,value\n2025-12-31,annual,income_statement,revenue,1250\n2025-12-31,annual,income_statement,net_profit,220\n"


class Fetcher:
    def fetch_bytes(self, url, spec):
        if url == HOME:
            return HTML.encode()
        if url == CSV_URL:
            return CSV.encode()
        raise AssertionError(url)


def test_official_filings_collector_discovers_and_parses_structured_report(tmp_path: Path):
    spec = seed_registry().latest("company_ir")
    collector = OfficialFilingsCollector(
        spec, company_urls={"TEST": HOME}, fetcher=Fetcher(),
        archive=RawArchive(tmp_path / "archive"),
    )
    documents = collector.fetch()
    assert {document.original_url for document in documents} == {HOME, CSV_URL}
    [landing, report] = documents
    assert landing.content_hash
    batch = collector.parse(report)
    assert batch.parse_warnings == []
    assert {(item.ticker, item.line_item, item.value) for item in batch.financial_statement_line_items} == {
        ("TEST", "revenue", 1250.0), ("TEST", "net_profit", 220.0)
    }


def test_binary_filings_are_archived_and_withheld_until_layout_parser(tmp_path: Path):
    class PdfFetcher:
        def fetch_bytes(self, url, spec):
            if url == "https://issuer.example/ir/":
                return b'<a href="report.pdf">Annual Report</a>'
            return b"%PDF-1.7 real filing bytes"

    spec = seed_registry().latest("company_ir")
    collector = OfficialFilingsCollector(
        spec, company_urls={"TEST": "https://issuer.example/ir/"},
        fetcher=PdfFetcher(), archive=RawArchive(tmp_path / "archive"),
    )
    documents = collector.fetch()
    assert len(documents) == 2
    report = documents[1]
    assert report.is_binary is True
    batch = collector.parse(report)
    assert batch.financial_statement_line_items == []
    assert batch.parse_warnings
