"""Offline contract tests for the live multi-provider EGX price adapter."""

import json
from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

from agx_research.collectors.egx_prices import EgxCompositePriceCollector
from agx_research.collectors.fetcher import HttpFetcher
from agx_research.collectors.raw import RawDocumentRepository
from agx_research.collectors.service import CollectionService
from agx_research.config import Horizon
from agx_research.data.mock_provider import LocalCsvDataProvider
from agx_research.financials.collected import CollectedFinancialStatementProvider
from agx_research.market_memory.memory import MarketMemory
from agx_research.meta.readiness import assess_decision_readiness
from agx_research.production.collector_plan import build_live_collector
from agx_research.sources.catalog import seed_sources
from agx_research.universe.provider import MappingUniverseProvider
from agx_research.universe.sector import StaticSectorProvider

CAIRO = ZoneInfo("Africa/Cairo")


def price_spec():
    return next(source for source in seed_sources() if source.id == "egx_price_composite")


def yahoo_payload(ticker="COMI", latest="2026-07-26"):
    timestamp = int(datetime.fromisoformat(f"{latest}T12:00:00+00:00").timestamp())
    return json.dumps(
        {
            "chart": {
                "result": [
                    {
                        "meta": {"symbol": f"{ticker}.CA"},
                        "timestamp": [timestamp],
                        "indicators": {
                            "quote": [
                                {
                                    "open": [70.0],
                                    "high": [72.0],
                                    "low": [69.0],
                                    "close": [71.5],
                                    "volume": [123456],
                                }
                            ]
                        },
                        "events": {
                            "dividends": {str(timestamp): {"date": timestamp, "amount": 1.25}},
                            "splits": {
                                str(timestamp - 1): {
                                    "date": timestamp,
                                    "numerator": 2,
                                    "denominator": 1,
                                    "splitRatio": "2:1",
                                }
                            },
                        },
                    }
                ],
                "error": None,
            },
        }
    )


STOCK_PAYLOAD = """<script>data:[
{a:71.4,c:71.5,h:72,l:69,o:70,t:"2026-07-26",v:123456,ch:1.2},
{a:68,c:68,h:69,l:67,o:67.5,t:"2026-07-25",v:111000,ch:.5}
],created_at:"now"</script>"""

MUBASHER_PAYLOAD = """
<div class="market-summary__last-price">15.47</div>
<div>Open</div><div class="market-summary__block-number">15.46</div>
<div>High</div><div class="market-summary__block-number">15.65</div>
<div>Low</div><div class="market-summary__block-number">15.40</div>
<div>Volume</div><div class="market-summary__block-number">517,127</div>
"""


class MappingFetcher:
    def __init__(self, content):
        self.content = content
        self.calls = []

    def fetch_text(self, url, spec):
        self.calls.append(url)
        value = self.content[url]
        if isinstance(value, Exception):
            raise value
        return value


def test_parse_yahoo_price_and_corporate_actions():
    ticker = "COMI"
    url = EgxCompositePriceCollector.yahoo_url(ticker)
    fetcher = MappingFetcher(
        {
            url: yahoo_payload(),
            EgxCompositePriceCollector.stockanalysis_urls(ticker)[0]: STOCK_PAYLOAD,
        }
    )
    collector = EgxCompositePriceCollector(
        price_spec(),
        [ticker],
        fetcher=fetcher,
        now=lambda: datetime(2026, 7, 26, 15, tzinfo=CAIRO),
    )
    yahoo = next(d for d in collector.fetch() if "provider=yahoo" in d.original_url)
    batch = collector.parse(yahoo)
    assert [(bar.ticker, bar.trade_date, bar.close) for bar in batch.price_bars] == [
        ("COMI", date(2026, 7, 26), 71.5)
    ]
    assert {event.event_type for event in batch.corporate_events} == {"dividend", "stock_split"}


def test_stockanalysis_overwrites_yahoo_overlap_when_materialized(tmp_path: Path):
    ticker = "COMI"
    yahoo_url = EgxCompositePriceCollector.yahoo_url(ticker)
    stock_url = EgxCompositePriceCollector.stockanalysis_urls(ticker)[0]
    fetcher = MappingFetcher({yahoo_url: yahoo_payload(), stock_url: STOCK_PAYLOAD})
    collector = EgxCompositePriceCollector(
        price_spec(),
        [ticker],
        fetcher=fetcher,
        now=lambda: datetime(2026, 7, 26, 15, tzinfo=CAIRO),
    )
    result = CollectionService(
        tmp_path, raw_documents=RawDocumentRepository(tmp_path / "raw.json")
    ).run(collector, expected_records=1)
    csv_text = (tmp_path / "prices" / "COMI.csv").read_text(encoding="utf-8")
    assert result.documents_fetched == 2
    assert "2026-07-26,70.0,72.0,69.0,71.5,123456" in csv_text
    assert "2026-07-25,67.5,69.0,67.0,68.0,111000" in csv_text


def test_per_ticker_fallback_reaches_mubasher_after_close():
    ticker = "ICFC"
    yahoo_url = EgxCompositePriceCollector.yahoo_url(ticker)
    stock_urls = EgxCompositePriceCollector.stockanalysis_urls(ticker)
    mubasher_url = EgxCompositePriceCollector.mubasher_url(ticker)
    fetcher = MappingFetcher(
        {
            yahoo_url: yahoo_payload(ticker, latest="2026-07-19"),
            stock_urls[0]: KeyError("not found"),
            stock_urls[1]: KeyError("not found"),
            mubasher_url: MUBASHER_PAYLOAD,
        }
    )
    collector = EgxCompositePriceCollector(
        price_spec(),
        [ticker],
        fetcher=fetcher,
        now=lambda: datetime(2026, 7, 26, 15, tzinfo=CAIRO),
    )
    documents = collector.fetch()
    mubasher = next(d for d in documents if "provider=mubasher" in d.original_url)
    [bar] = collector.parse(mubasher).price_bars
    assert (bar.ticker, bar.trade_date, bar.close, bar.volume) == (
        "ICFC",
        date(2026, 7, 26),
        15.47,
        517127,
    )


def test_fallback_uses_latest_complete_yahoo_bar_not_metadata_timestamp():
    ticker = "IEEC"
    old_timestamp = int(datetime(2026, 7, 16, 12, tzinfo=UTC).timestamp())
    new_timestamp = int(datetime(2026, 7, 26, 12, tzinfo=UTC).timestamp())
    payload = json.dumps(
        {
            "chart": {
                "result": [
                    {
                        "timestamp": [old_timestamp, new_timestamp],
                        "indicators": {
                            "quote": [
                                {
                                    "open": [1.0, None],
                                    "high": [1.1, None],
                                    "low": [0.9, None],
                                    "close": [1.0, None],
                                    "volume": [1000, None],
                                }
                            ]
                        },
                    }
                ]
            },
        }
    )
    yahoo_url = EgxCompositePriceCollector.yahoo_url(ticker)
    stock_urls = EgxCompositePriceCollector.stockanalysis_urls(ticker)
    mubasher_url = EgxCompositePriceCollector.mubasher_url(ticker)
    collector = EgxCompositePriceCollector(
        price_spec(),
        [ticker],
        fetcher=MappingFetcher(
            {
                yahoo_url: payload,
                stock_urls[0]: KeyError("not found"),
                stock_urls[1]: KeyError("not found"),
                mubasher_url: MUBASHER_PAYLOAD,
            }
        ),
        now=lambda: datetime(2026, 7, 26, 15, tzinfo=CAIRO),
    )

    documents = collector.fetch()

    assert [collector._metadata(document.original_url)["provider"] for document in documents] == [
        "yahoo",
        "mubasher",
    ]


def test_universe_symbols_are_injected_without_a_fixed_ticker_list():
    fetcher = MappingFetcher({})
    collector = build_live_collector(
        "egx_price_composite",
        price_spec(),
        fetcher=fetcher,
        tickers=["AAA", "BBB"],
    )
    assert isinstance(collector, EgxCompositePriceCollector)
    assert collector.symbols == ["AAA", "BBB"]


def test_live_wiring_scopes_owner_authorized_robots_override_to_price_collector():
    shared = HttpFetcher(respect_robots=True, timeout_seconds=7)
    collector = build_live_collector(
        "egx_price_composite",
        price_spec(),
        fetcher=shared,
        tickers=["COMI"],
    )
    assert collector.fetcher is not shared
    assert collector.fetcher.respect_robots is False
    assert collector.fetcher.timeout_seconds == 7
    assert shared.respect_robots is True
    assert collector.spec.retry_policy.max_attempts == 2


def test_collected_prices_reach_market_memory_and_decision_readiness(tmp_path: Path):
    as_of = date(2026, 7, 26)
    rows = []
    for offset in range(20):
        day = as_of - timedelta(days=offset)
        rows.append(f'{{a:10,c:10,h:11,l:9,o:10,t:"{day.isoformat()}",v:100000,ch:0}}')
    stock_payload = f"<script>data:[{','.join(rows)}],created_at:'now'</script>"
    ticker = "NEWC"
    yahoo_url = EgxCompositePriceCollector.yahoo_url(ticker)
    stock_url = EgxCompositePriceCollector.stockanalysis_urls(ticker)[0]
    collector = EgxCompositePriceCollector(
        price_spec(),
        [ticker],
        fetcher=MappingFetcher(
            {
                yahoo_url: KeyError("not listed"),
                stock_url: stock_payload,
            }
        ),
        now=lambda: datetime(2026, 7, 26, 15, tzinfo=CAIRO),
    )
    CollectionService(tmp_path).run(collector, expected_records=20)

    universe = MappingUniverseProvider({ticker: "New constituent"})
    state = MarketMemory(
        LocalCsvDataProvider(tmp_path),
        universe,
        StaticSectorProvider({}),
        lookback_days=30,
    ).reconstruct(as_of)
    [readiness] = assess_decision_readiness(
        state,
        CollectedFinancialStatementProvider(tmp_path),
        [],
    )
    assert state.dataset_snapshot.tickers == [ticker]
    assert readiness.price_observations == 20
    assert readiness.latest_price_date == as_of
    assert Horizon.MICRO in readiness.ready_horizons
    assert all("price" not in blocker.lower() for blocker in readiness.blockers)
