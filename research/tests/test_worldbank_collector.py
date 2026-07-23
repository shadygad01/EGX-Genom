"""WorldBankCollector tests: parsing exercised against a recorded-format
fixture (the real World Bank v2 JSON response shape) via an injected fake
fetcher. No live network involved.
"""

from datetime import date
from pathlib import Path

import pytest

from agx_research.collectors.worldbank import WorldBankCollector
from agx_research.sources.catalog import seed_sources
from agx_research.sources.spec import SourceStatus

FIXTURES = Path(__file__).parent / "fixtures"


def worldbank_spec():
    return next(s for s in seed_sources() if s.id == "worldbank")


class FakeFetcher:
    def __init__(self, text: str):
        self.text = text
        self.calls: list[str] = []

    def fetch_text(self, url, spec):
        self.calls.append(url)
        return self.text


def test_fetch_builds_one_document_per_indicator_with_country_and_indicator_in_url():
    fetcher = FakeFetcher((FIXTURES / "worldbank_synthetic.json").read_text())
    collector = WorldBankCollector(
        worldbank_spec(), {"FP.CPI.TOTL.ZG": "egypt_cpi_inflation"}, fetcher=fetcher
    )
    documents = collector.fetch()
    assert len(documents) == 1
    assert "country/EGY/indicator/FP.CPI.TOTL.ZG" in documents[0].original_url


def test_parse_produces_expected_macro_observations_and_drops_null_values():
    fetcher = FakeFetcher((FIXTURES / "worldbank_synthetic.json").read_text())
    collector = WorldBankCollector(
        worldbank_spec(), {"FP.CPI.TOTL.ZG": "egypt_cpi_inflation"}, fetcher=fetcher
    )
    [document] = collector.fetch()
    batch = collector.parse(document)

    assert len(batch.macro_observations) == 2  # the null 2023 entry is dropped
    assert any("2023" in w for w in batch.parse_warnings)
    by_year = {obs.observation_date.year: obs for obs in batch.macro_observations}
    assert by_year[2025].value == 24.4
    assert by_year[2025].series_id == "egypt_cpi_inflation"
    assert by_year[2025].observation_date == date(2025, 12, 31)


def test_parse_invalid_json_recorded_as_warning():
    fetcher = FakeFetcher("not json")
    collector = WorldBankCollector(worldbank_spec(), {"FP.CPI.TOTL.ZG": "x"}, fetcher=fetcher)
    [document] = collector.fetch()
    batch = collector.parse(document)
    assert batch.macro_observations == []
    assert "Invalid JSON" in batch.parse_warnings[0]


def test_parse_unexpected_shape_recorded_as_warning():
    fetcher = FakeFetcher('{"not": "a list"}')
    collector = WorldBankCollector(worldbank_spec(), {"FP.CPI.TOTL.ZG": "x"}, fetcher=fetcher)
    [document] = collector.fetch()
    batch = collector.parse(document)
    assert batch.macro_observations == []
    assert "Unexpected response shape" in batch.parse_warnings[0]


def test_collector_rejects_non_implemented_source():
    spec = worldbank_spec().model_copy(update={"status": SourceStatus.PLANNED})
    with pytest.raises(ValueError):
        WorldBankCollector(spec, {"FP.CPI.TOTL.ZG": "x"})
