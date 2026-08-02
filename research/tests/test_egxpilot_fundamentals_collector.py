import json

import pytest

from agx_research.collectors.egxpilot_fundamentals import EgxPilotFundamentalsCollector
from agx_research.collectors.fetcher import FetchError
from agx_research.production.collector_plan import build_live_collector
from agx_research.sources.catalog import seed_registry


class Fetcher:
    def __init__(self):
        self.request_latencies = []

    def fetch_text(self, url, spec):
        ticker = url.rsplit("/", 1)[-1]
        if ticker == "MISSING":
            raise FetchError("404")
        if "/api/stockanalysis/" in url:
            return json.dumps(
                {
                    "status": "OK",
                    "symbol": ticker,
                    "history": [
                        {
                            "time": "2026-07-30",
                            "open": 19,
                            "high": 21,
                            "low": 18,
                            "close": 20,
                            "volume": 1000,
                        }
                    ],
                    "Recommendation": "Strong Buy",
                }
            )
        return json.dumps(
            {
                "updatedAt": "2026-08-02T08:19:36.681Z",
                "stock": {
                    "Symbol": ticker,
                    "LastPrice": 20,
                    "PE": 8,
                    "EPS": 2.5,
                    "MarketCap": "1,000",
                    "Shares": None,
                    "Dividend": 1,
                    "Yield": 5,
                    "Beta": 0.8,
                    "Revenue": "5,000",
                    "Recommendation": "Strong Buy",
                },
            }
        )


def test_live_plan_wires_no_key_market_fundamentals():
    spec = seed_registry().latest("egxpilot_fundamentals")
    collector = build_live_collector(
        "egxpilot_fundamentals", spec, fetcher=Fetcher(), tickers=["COMI"]
    )
    assert isinstance(collector, EgxPilotFundamentalsCollector)


def test_numeric_facts_are_mapped_but_opaque_provider_recommendation_is_ignored():
    collector = EgxPilotFundamentalsCollector(
        seed_registry().latest("egxpilot_fundamentals"),
        tickers=["COMI"],
        fetcher=Fetcher(),
    )
    document = next(d for d in collector.fetch() if "updatedAt" in d.content_text)
    batch = collector.parse(document)
    facts = {item.line_item: item.value for item in batch.financial_statement_line_items}
    assert facts["market_cap"] == 1000
    assert facts["market_pe"] == 8
    assert facts["shares_outstanding"] == 50
    assert "recommendation" not in facts


def test_one_missing_symbol_does_not_discard_covered_universe():
    collector = EgxPilotFundamentalsCollector(
        seed_registry().latest("egxpilot_fundamentals"),
        tickers=["COMI", "MISSING"],
        fetcher=Fetcher(),
    )
    documents = collector.fetch()
    assert len(documents) == 2
    assert collector.fetch_warnings == [
        "MISSING/fundamentals: FetchError: 404",
        "MISSING/history: FetchError: 404",
    ]


def test_all_missing_symbols_fail_the_collector_loudly():
    collector = EgxPilotFundamentalsCollector(
        seed_registry().latest("egxpilot_fundamentals"),
        tickers=["MISSING"],
        fetcher=Fetcher(),
    )

    with pytest.raises(FetchError, match="no usable ticker documents"):
        collector.fetch()


def test_ticker_outside_declared_universe_is_withheld():
    collector = EgxPilotFundamentalsCollector(
        seed_registry().latest("egxpilot_fundamentals"), tickers=["COMI"], fetcher=Fetcher()
    )
    document = next(d for d in collector.fetch() if "updatedAt" in d.content_text)
    payload = json.loads(document.content_text)
    payload["stock"]["Symbol"] = "OTHER"
    altered = document.model_copy(update={"content_text": json.dumps(payload)})
    batch = collector.parse(altered)
    assert batch.financial_statement_line_items == []
    assert batch.parse_warnings


def test_documented_history_is_materialized_but_opaque_signal_is_ignored():
    collector = EgxPilotFundamentalsCollector(
        seed_registry().latest("egxpilot_fundamentals"),
        tickers=["COMI"],
        fetcher=Fetcher(),
    )
    document = next(d for d in collector.fetch() if '"history"' in d.content_text)

    batch = collector.parse(document)

    assert len(batch.price_bars) == 1
    assert batch.price_bars[0].ticker == "COMI"
    assert batch.price_bars[0].close == 20
    assert batch.financial_statement_line_items == []
