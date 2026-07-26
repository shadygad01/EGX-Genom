"""FredCsvCollector tests against a recorded-format fixture. No live network."""

from datetime import date
from pathlib import Path

from agx_research.collectors.fred import FredCsvCollector
from agx_research.sources.catalog import seed_sources

FIXTURES = Path(__file__).parent / "fixtures"


def fred_spec():
    return next(s for s in seed_sources() if s.id == "fred")


class FakeFetcher:
    def __init__(self, text: str):
        self.text = text
        self.calls: list[str] = []

    def fetch_text(self, url, spec):
        self.calls.append(url)
        return self.text


def test_fetch_one_document_per_series():
    fetcher = FakeFetcher((FIXTURES / "fred_synthetic.csv").read_text())
    collector = FredCsvCollector(fred_spec(), series_ids=["AGXTEST", "OTHER"], fetcher=fetcher)
    documents = collector.fetch()
    assert len(documents) == 2
    assert all("id=" in url for url in fetcher.calls)


def test_parse_drops_missing_observations_with_warning_never_imputed():
    fetcher = FakeFetcher((FIXTURES / "fred_synthetic.csv").read_text())
    collector = FredCsvCollector(fred_spec(), series_ids=["AGXTEST"], fetcher=fetcher)
    [document] = collector.fetch()
    batch = collector.parse(document)
    assert len(batch.macro_observations) == 2
    dates = {o.observation_date for o in batch.macro_observations}
    assert date(2026, 6, 2) not in dates  # the "." row
    assert len(batch.parse_warnings) == 1
    assert "missing observation" in batch.parse_warnings[0]


def test_parse_values_and_series_id_correct():
    fetcher = FakeFetcher((FIXTURES / "fred_synthetic.csv").read_text())
    collector = FredCsvCollector(fred_spec(), series_ids=["AGXTEST"], fetcher=fetcher)
    [document] = collector.fetch()
    batch = collector.parse(document)
    first = batch.macro_observations[0]
    assert first.series_id == "AGXTEST"
    assert first.observation_date == date(2026, 6, 1)
    assert first.value == 4.25


def test_parse_current_observation_date_header():
    fetcher = FakeFetcher("observation_date,DGS10\n2026-07-25,4.42\n")
    collector = FredCsvCollector(fred_spec(), series_ids=["DGS10"], fetcher=fetcher)

    [document] = collector.fetch()
    batch = collector.parse(document)

    assert batch.parse_warnings == []
    assert batch.macro_observations[0].observation_date == date(2026, 7, 25)
    assert batch.macro_observations[0].value == 4.42


def test_parse_unexpected_header_recorded_as_warning():
    fetcher = FakeFetcher("NOT,A,HEADER\n1,2,3\n")
    collector = FredCsvCollector(fred_spec(), series_ids=["X"], fetcher=fetcher)
    [document] = collector.fetch()
    batch = collector.parse(document)
    assert batch.macro_observations == []
    assert "Unexpected header" in batch.parse_warnings[0]


def test_parse_malformed_row_recorded_as_warning():
    fetcher = FakeFetcher("DATE,X\n2026-06-01\n")  # missing value column
    collector = FredCsvCollector(fred_spec(), series_ids=["X"], fetcher=fetcher)
    [document] = collector.fetch()
    batch = collector.parse(document)
    assert batch.macro_observations == []
    assert "malformed row" in batch.parse_warnings[0]
