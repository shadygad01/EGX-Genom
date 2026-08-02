from datetime import date

from agx_research.collectors.egypt_nsdp import EgyptNsdpCollector
from agx_research.production.collector_plan import build_live_collector
from agx_research.sources.catalog import seed_registry


HTML = """
<table>
 <tr><td>- Net International Reserves (US$)</td><td>US Mill. $</td><td>Jun/26</td><td>55,072.3</td></tr>
 <tr><td>5. External debt</td><td>US Mill. $</td><td>Q1/26</td><td>164776</td></tr>
</table>
"""


class FakeFetcher:
    def __init__(self, text=HTML):
        self.text = text
        self.calls = []

    def fetch_text(self, url, spec):
        self.calls.append(url)
        return self.text


def test_live_plan_wires_official_nsdp_page():
    spec = seed_registry().latest("egypt_nsdp")
    collector = build_live_collector(
        "egypt_nsdp", spec, fetcher=FakeFetcher(), tickers=["COMI"]
    )
    assert isinstance(collector, EgyptNsdpCollector)


def test_parse_current_monthly_and_quarterly_official_values():
    collector = EgyptNsdpCollector(seed_registry().latest("egypt_nsdp"), fetcher=FakeFetcher())
    [document] = collector.fetch()
    batch = collector.parse(document)

    assert [(x.series_id, x.observation_date, x.value) for x in batch.macro_observations] == [
        ("egypt_net_international_reserves_usd", date(2026, 6, 30), 55_072_300_000.0),
        ("egypt_external_debt_usd", date(2026, 3, 31), 164_776_000_000.0),
    ]
    assert batch.parse_warnings == []


def test_missing_or_changed_rows_are_visible_warnings_not_silent_stale_data():
    collector = EgyptNsdpCollector(
        seed_registry().latest("egypt_nsdp"), fetcher=FakeFetcher("<html></html>")
    )
    [document] = collector.fetch()
    batch = collector.parse(document)
    assert batch.macro_observations == []
    assert len(batch.parse_warnings) == 2
