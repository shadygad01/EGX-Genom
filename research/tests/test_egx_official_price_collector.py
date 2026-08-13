from datetime import UTC, datetime

from agx_research.collectors.egx_official_prices import EgxOfficialPriceCollector
from agx_research.production.collector_plan import build_live_collector
from agx_research.sources.catalog import seed_sources

OFFICIAL_HTML = """
<html><body>
<h1>Today's Market Watch - Stocks - Trading Data</h1>
<table>
<tr><th>Code</th><th>Company</th><th>Open</th><th>High</th><th>Low</th><th>Last Price</th><th>Volume</th></tr>
<tr><td>COMI.CA</td><td>Commercial International Bank</td><td>139.990</td><td>140.500</td><td>138.900</td><td>139.400</td><td>327,400</td></tr>
<tr><td>ETEL</td><td>Telecom Egypt</td><td>112.000</td><td>113.000</td><td>111.500</td><td>112.520</td><td>1,200,000</td></tr>
<tr><td>BADROW</td><td>Incomplete</td><td>1.0</td><td></td><td>0.9</td><td>1.0</td><td>100</td></tr>
</table>
</body></html>
"""


class MappingFetcher:
    def __init__(self, payload):
        self.payload = payload
        self.calls = []

    def fetch_text(self, url, spec):
        self.calls.append(url)
        return self.payload


def official_spec():
    return next(source for source in seed_sources() if source.id == "egx_official_prices")


def test_official_page_parses_complete_ohlcv_rows_and_withholds_incomplete_rows():
    collector = EgxOfficialPriceCollector(
        official_spec(),
        ["COMI", "ETEL", "BADROW"],
        fetcher=MappingFetcher(OFFICIAL_HTML),
        now=lambda: datetime(2026, 8, 13, tzinfo=UTC),
    )
    [document] = collector.fetch()
    batch = collector.parse(document)

    assert [(bar.ticker, bar.close, bar.volume) for bar in batch.price_bars] == [
        ("COMI", 139.4, 327400),
        ("ETEL", 112.52, 1200000),
    ]
    assert any("BADROW" in warning for warning in batch.parse_warnings)


def test_official_source_is_live_wired_with_injected_universe():
    collector = build_live_collector(
        "egx_official_prices",
        official_spec(),
        fetcher=MappingFetcher(OFFICIAL_HTML),
        tickers=["COMI", "ETEL"],
    )
    assert isinstance(collector, EgxOfficialPriceCollector)
    assert collector.symbols == {"COMI", "ETEL"}
