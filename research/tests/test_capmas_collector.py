from datetime import date

import pytest

from agx_research.collectors.capmas import CapmasIndicatorCollector
from agx_research.production.collector_plan import LIVE_CAPMAS_INDICATORS, build_live_collector
from agx_research.sources.catalog import seed_registry
from agx_research.sources.spec import SourceStatus

PAYLOAD = """{
  "state": true,
  "data": [
    {"name": "urban", "filterTranslations": [{"name": "Urban Egypt", "locale": "en"}],
     "data": [
       {"value": 14.3, "year": 2026, "month": 6, "quarter": null},
       {"value": "missing", "year": 2026, "month": 7, "quarter": null}
     ]},
    {"name": "total", "filterTranslations": [{"name": "Total Egypt", "locale": "en"}],
     "data": [{"value": 13.9, "year": 2026, "month": 6, "quarter": null}]},
    {"name": "rural", "filterTranslations": [{"name": "Rural Egypt", "locale": "en"}],
     "data": [{"value": 12.0, "year": 2026, "month": 6, "quarter": null}]}
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
    return seed_registry().latest("capmas")


def test_catalog_and_live_plan_wire_official_capmas_api():
    spec = _spec()
    assert spec.status == SourceStatus.IMPLEMENTED
    assert spec.base_url == "https://www.capmas.gov.eg:8080/api"
    collector = build_live_collector(
        "capmas", spec, fetcher=FakeFetcher(), tickers=["COMI"]
    )
    assert isinstance(collector, CapmasIndicatorCollector)
    assert collector.indicators == LIVE_CAPMAS_INDICATORS


def test_fetch_uses_explicit_indicator_and_subsubject_ids():
    fetcher = FakeFetcher()
    collector = CapmasIndicatorCollector(
        _spec(), {2264: {"Urban Egypt": "urban_cpi_yoy"}}, fetcher=fetcher
    )
    [document] = collector.fetch()
    assert "IndicatorId=2264" in document.original_url
    assert "SubSubjectId=13" in document.original_url


def test_parse_keeps_only_named_filters_and_normalizes_to_month_end():
    collector = CapmasIndicatorCollector(
        _spec(),
        {2264: {"Urban Egypt": "urban_cpi_yoy", "Total Egypt": "total_cpi_yoy"}},
        fetcher=FakeFetcher(),
    )
    [document] = collector.fetch()
    batch = collector.parse(document)

    assert [(x.series_id, x.observation_date, x.value) for x in batch.macro_observations] == [
        ("urban_cpi_yoy", date(2026, 6, 30), 14.3),
        ("total_cpi_yoy", date(2026, 6, 30), 13.9),
    ]
    assert any("missing" in warning for warning in batch.parse_warnings)


def test_unimplemented_spec_is_rejected():
    planned = _spec().model_copy(update={"status": SourceStatus.PLANNED})
    with pytest.raises(ValueError):
        CapmasIndicatorCollector(planned, {2264: {"Urban Egypt": "x"}})
