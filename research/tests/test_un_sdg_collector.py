from datetime import date

import pytest

from agx_research.collectors.un_sdg import UnSdgCollector
from agx_research.production.collector_plan import LIVE_UN_SDG_SERIES, build_live_collector
from agx_research.sources.catalog import seed_registry
from agx_research.sources.spec import SourceStatus

PAYLOAD = """{
  "size": 1000,
  "totalElements": 3,
  "totalPages": 1,
  "data": [
    {"indicator": ["9.2.1"], "series": "NV_IND_MANF", "geoAreaCode": "818",
     "timePeriodStart": 2023.0, "value": "15.6"},
    {"indicator": ["9.2.1"], "series": "NV_IND_MANFPC", "geoAreaCode": "818",
     "timePeriodStart": 2023.0, "value": "412.0"},
    {"indicator": ["9.2.1"], "series": "NV_IND_MANF", "geoAreaCode": "818",
     "timePeriodStart": 2024.0, "value": "not-available"}
  ]
}"""


class FakeFetcher:
    def __init__(self, text=PAYLOAD):
        self.text = text
        self.calls = []

    def fetch_text(self, url, spec):
        self.calls.append(url)
        return self.text


def _spec():
    return seed_registry().latest("undata")


def test_catalog_promotes_verified_un_api_and_live_plan_wires_it():
    spec = _spec()
    assert spec.status == SourceStatus.IMPLEMENTED
    assert spec.base_url == "https://unstats.un.org/SDGAPI/v1/sdg"
    collector = build_live_collector(
        "undata", spec, fetcher=FakeFetcher(), tickers=["COMI"]
    )
    assert isinstance(collector, UnSdgCollector)
    assert collector.series == LIVE_UN_SDG_SERIES


def test_fetch_uses_egypt_area_and_requests_complete_page():
    fetcher = FakeFetcher()
    collector = UnSdgCollector(
        _spec(), {"9.2.1": {"NV_IND_MANF": "manufacturing_pct_gdp"}}, fetcher=fetcher
    )
    [document] = collector.fetch()
    assert "indicator=9.2.1" in document.original_url
    assert "areaCode=818" in document.original_url
    assert "pageSize=1000" in document.original_url


def test_parse_keeps_only_configured_aggregate_series_and_warns_on_bad_value():
    collector = UnSdgCollector(
        _spec(), {"9.2.1": {"NV_IND_MANF": "manufacturing_pct_gdp"}}, fetcher=FakeFetcher()
    )
    [document] = collector.fetch()
    batch = collector.parse(document)

    assert len(batch.macro_observations) == 1
    assert batch.macro_observations[0].series_id == "manufacturing_pct_gdp"
    assert batch.macro_observations[0].observation_date == date(2023, 12, 31)
    assert batch.macro_observations[0].value == 15.6
    assert any("not-available" in warning for warning in batch.parse_warnings)


def test_unimplemented_spec_is_rejected():
    planned = _spec().model_copy(update={"status": SourceStatus.PLANNED})
    with pytest.raises(ValueError):
        UnSdgCollector(planned, {"8.1.1": {"NY_GDP_PCAP": "gdp"}})
