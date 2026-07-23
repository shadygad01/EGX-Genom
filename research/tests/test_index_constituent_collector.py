"""IndexConstituentCollector tests: parsing exercised against synthetic CSV
content via an injected fake fetcher. No live network involved -- same
posture as every other collector's tests.
"""

from datetime import date, datetime

from agx_research.collectors.index_constituents import IndexConstituentCollector
from agx_research.sources.spec import AccessMethod, SourceCategory, SourceSpec, SourceStatus


def make_spec(**overrides) -> SourceSpec:
    defaults = dict(
        id="egx_official",
        name="Egyptian Exchange (EGX)",
        category=SourceCategory.OFFICIAL,
        access_method=AccessMethod.CSV_DOWNLOAD,
        status=SourceStatus.IMPLEMENTED,
        base_url="https://egx.test/constituents.csv",
        reliability_score=0.9,
        freshness_score=0.8,
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
    fetcher = FakeFetcher("Code,Company Name\nCOMI,Commercial International Bank\n")
    collector = IndexConstituentCollector(make_spec(), index="EGX30", fetcher=fetcher)
    [document] = collector.fetch()
    assert fetcher.calls == ["https://egx.test/constituents.csv"]
    assert document.original_url == "https://egx.test/constituents.csv"


def test_parse_finds_ticker_and_name_columns_regardless_of_order():
    text = "Company Name,Ticker Code\nCommercial International Bank,COMI\nTelecom Egypt,ETEL\n"
    fetcher = FakeFetcher(text)
    collector = IndexConstituentCollector(make_spec(), index="EGX30", fetcher=fetcher)
    [document] = collector.fetch()
    document = document.model_copy(update={"fetched_at": datetime(2026, 6, 14, 9, 0, 0)})
    batch = collector.parse(document)

    assert batch.parse_warnings == []
    assert len(batch.index_constituents) == 2
    comi = next(c for c in batch.index_constituents if c.ticker == "COMI")
    assert comi.company_name == "Commercial International Bank"
    assert comi.index == "EGX30"
    assert comi.as_of_date == date(2026, 6, 14)


def test_parse_records_warning_when_columns_cannot_be_identified():
    fetcher = FakeFetcher("Foo,Bar\n1,2\n")
    collector = IndexConstituentCollector(make_spec(), index="EGX30", fetcher=fetcher)
    [document] = collector.fetch()
    batch = collector.parse(document)
    assert batch.index_constituents == []
    assert "Could not identify" in batch.parse_warnings[0]


def test_parse_skips_malformed_and_blank_rows_without_dropping_silently():
    text = "Ticker,Name\nCOMI,Commercial International Bank\n,\nETEL\n"
    fetcher = FakeFetcher(text)
    collector = IndexConstituentCollector(make_spec(), index="EGX30", fetcher=fetcher)
    [document] = collector.fetch()
    batch = collector.parse(document)
    assert len(batch.index_constituents) == 1
    assert batch.index_constituents[0].ticker == "COMI"
    assert len(batch.parse_warnings) == 2


def test_empty_document_records_warning():
    fetcher = FakeFetcher("")
    collector = IndexConstituentCollector(make_spec(), index="EGX30", fetcher=fetcher)
    [document] = collector.fetch()
    batch = collector.parse(document)
    assert batch.index_constituents == []
    assert batch.parse_warnings == ["Empty document; nothing parsed."]
