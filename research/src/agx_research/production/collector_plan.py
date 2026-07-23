"""Collector Selection + Execution wiring for the production pipeline.

Per the mission brief: "Do NOT implement live production collectors yet.
Instead implement production-ready execution using mock/replay/archive
providers... the execution path must be identical to the future live
path; only the data source changes." This module is exactly that seam:

- `ExecutionMode.MOCK` builds the *real* `Collector` subclasses this
  platform already ships (`StooqPriceCollector`, `FredCsvCollector`,
  `RssNewsCollector`, `WorldBankCollector`) against a `MockFetcher` that
  returns clearly-synthetic, wire-format-correct content instead of making
  a network call -- the same numbers `research/data/mock/` already uses,
  reformatted into each source's real CSV/JSON/RSS shape, so parsing
  exercises real format-handling logic, not hand-built domain objects.
- `ExecutionMode.REPLAY` wraps the same real collectors in
  `ArchiveReplayCollector`, sourcing previously-archived `RawDocument`s
  from a persisted `RawDocumentRepository` instead of fetching anything.

Either way, `CollectionService.run()` is called identically -- the
pipeline genuinely cannot tell whether its data is live, mocked, or
replayed, because nothing about the call site changes.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from agx_research.collectors.archive_replay import ArchiveReplayCollector
from agx_research.collectors.base import Collector
from agx_research.collectors.fred import FredCsvCollector
from agx_research.collectors.raw import RawDocumentRepository
from agx_research.collectors.rss import RssNewsCollector
from agx_research.collectors.stooq import StooqPriceCollector
from agx_research.collectors.worldbank import WorldBankCollector
from agx_research.sources.registry import SourceRegistry
from agx_research.sources.spec import SourceSpec


class ExecutionMode(str, Enum):
    MOCK = "mock"
    REPLAY = "replay"


class MockFetcher:
    """Drop-in for `HttpFetcher.fetch_text` (same `fetch_text(url, spec)`
    signature) that returns pre-recorded, clearly-synthetic wire-format
    content keyed by the exact URL a real collector constructs -- never a
    guess, never a partial match. A URL with no canned content raises
    immediately rather than silently returning something wrong.
    """

    def __init__(self, content_by_url: dict[str, str]):
        self.content_by_url = content_by_url
        self.calls: list[str] = []

    def fetch_text(self, url: str, spec: SourceSpec) -> str:
        self.calls.append(url)
        if url not in self.content_by_url:
            raise KeyError(f"MockFetcher has no canned content configured for {url!r}")
        return self.content_by_url[url]


# ---- canned content: the same synthetic numbers research/data/mock/ uses,
# reformatted into each source's real wire format --------------------------

_STOOQ_PRICES = {
    "COMI": """Date,Open,High,Low,Close,Volume
2026-06-01,68.10,68.90,67.80,68.50,1250000
2026-06-02,68.50,69.20,68.30,69.00,1180000
2026-06-03,69.00,69.10,67.90,68.20,1420000
2026-06-04,68.20,68.60,67.50,67.70,1310000
2026-06-07,67.70,68.30,67.40,68.10,1050000
2026-06-08,68.10,69.50,68.00,69.30,1600000
2026-06-09,69.30,70.10,69.00,69.90,1720000
2026-06-10,69.90,70.20,69.20,69.40,1390000
2026-06-11,69.40,69.80,68.70,68.90,1220000
2026-06-14,68.90,69.30,68.20,68.40,1180000
""",
    "MFPC": """Date,Open,High,Low,Close,Volume
2026-06-01,215.00,218.50,214.00,217.80,320000
2026-06-02,217.80,220.00,216.50,219.40,290000
2026-06-03,219.40,221.10,218.00,220.60,340000
2026-06-04,220.60,222.00,219.30,221.50,310000
2026-06-07,221.50,223.80,220.90,223.20,360000
2026-06-08,223.20,224.50,221.70,222.10,300000
2026-06-09,222.10,222.90,220.10,220.80,280000
2026-06-10,220.80,221.60,219.00,219.50,250000
2026-06-11,219.50,221.00,218.60,220.30,270000
2026-06-14,220.30,222.40,219.80,221.90,310000
""",
}

_FRED_SERIES = {
    "BRENT_USD": """DATE,BRENT_USD
2026-06-01,82.10
2026-06-02,82.90
2026-06-03,83.40
2026-06-04,84.20
2026-06-07,85.00
2026-06-08,84.60
2026-06-09,83.80
2026-06-10,83.20
2026-06-11,84.10
2026-06-14,85.30
""",
    "EGP_USD": """DATE,EGP_USD
2026-06-01,49.20
2026-06-02,49.25
2026-06-03,49.22
2026-06-04,49.30
2026-06-07,49.35
2026-06-08,49.33
2026-06-09,49.40
2026-06-10,49.38
2026-06-11,49.42
2026-06-14,49.45
""",
}

_MOCK_FEED_URL = "https://mock-news.internal/agx/feed.xml"
_MOCK_NEWS_FEED = """<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
<channel>
<title>AGX Mock News Feed (synthetic, production pipeline fixture)</title>
<item>
<title>COMI reports strong Q2 net income growth</title>
<link>https://mock-news.internal/agx/comi-q2</link>
<pubDate>Tue, 09 Jun 2026 00:00:00 GMT</pubDate>
</item>
<item>
<title>MFPC board declares dividend</title>
<link>https://mock-news.internal/agx/mfpc-dividend</link>
<pubDate>Thu, 04 Jun 2026 00:00:00 GMT</pubDate>
</item>
<item>
<title>Brent crude climbs on supply concerns</title>
<link>https://mock-news.internal/agx/brent-supply</link>
<pubDate>Mon, 08 Jun 2026 00:00:00 GMT</pubDate>
</item>
</channel>
</rss>
"""

_WORLDBANK_INDICATOR = "FP.CPI.TOTL.ZG"
_WORLDBANK_SERIES_ID = "egypt_cpi_inflation"
_WORLDBANK_PAYLOAD = """[
  {"page": 1, "pages": 1, "per_page": 1000, "total": 2},
  [
    {"indicator": {"id": "FP.CPI.TOTL.ZG", "value": "Inflation, consumer prices"},
     "country": {"id": "EG", "value": "Egypt, Arab Rep."}, "countryiso3code": "EGY",
     "date": "2025", "value": 24.4, "unit": "", "obs_status": "", "decimal": 1},
    {"indicator": {"id": "FP.CPI.TOTL.ZG", "value": "Inflation, consumer prices"},
     "country": {"id": "EG", "value": "Egypt, Arab Rep."}, "countryiso3code": "EGY",
     "date": "2024", "value": 33.3, "unit": "", "obs_status": "", "decimal": 1}
  ]
]
"""


@dataclass
class PlannedCollector:
    source_id: str
    collector: Collector


def _mock_url_map(spec_by_id: dict[str, SourceSpec]) -> dict[str, str]:
    content_by_url: dict[str, str] = {}
    if "stooq" in spec_by_id:
        base = spec_by_id["stooq"].base_url
        for ticker in _STOOQ_PRICES:
            content_by_url[f"{base}?s={ticker.lower()}.eg&i=d"] = _STOOQ_PRICES[ticker]
    if "fred" in spec_by_id:
        base = spec_by_id["fred"].base_url
        for series_id, content in _FRED_SERIES.items():
            content_by_url[f"{base}?id={series_id}"] = content
    if "rss_generic" in spec_by_id:
        content_by_url[_MOCK_FEED_URL] = _MOCK_NEWS_FEED
    if "worldbank" in spec_by_id:
        base = spec_by_id["worldbank"].base_url
        content_by_url[
            f"{base}/country/EGY/indicator/{_WORLDBANK_INDICATOR}?format=json&per_page=1000"
        ] = _WORLDBANK_PAYLOAD
    return content_by_url


def build_collector_plan(
    registry: SourceRegistry,
    *,
    mode: ExecutionMode,
    raw_documents: RawDocumentRepository,
    tickers: list[str] | None = None,
) -> list[PlannedCollector]:
    """Collector Selection: pick the collectable sources this pipeline knows
    how to wire (a small, explicit set -- adding a source here is the "small
    adapter" the Data Acquisition Platform promises, not new framework work),
    and build each as a real `Collector`, backed by the execution mode's data
    source. Sources this pipeline has no wiring for (e.g. `global_benchmarks`,
    whose `collector` field names two classes jointly) are left to a future,
    explicit collector plan entry rather than guessed at.
    """
    wireable = {"stooq", "fred", "rss_generic", "worldbank"}
    collectable = {s.id: s for s in registry.collectable() if s.id in wireable}
    tickers = tickers or list(_STOOQ_PRICES)

    plans: list[PlannedCollector] = []
    if mode == ExecutionMode.MOCK:
        content_by_url = _mock_url_map(collectable)
        fetcher = MockFetcher(content_by_url)
        if "stooq" in collectable:
            symbols = {t: f"{t.lower()}.eg" for t in tickers if t in _STOOQ_PRICES}
            plans.append(
                PlannedCollector(
                    "stooq", StooqPriceCollector(collectable["stooq"], symbols=symbols, fetcher=fetcher)
                )
            )
        if "fred" in collectable:
            plans.append(
                PlannedCollector(
                    "fred",
                    FredCsvCollector(
                        collectable["fred"], series_ids=list(_FRED_SERIES), fetcher=fetcher
                    ),
                )
            )
        if "rss_generic" in collectable:
            plans.append(
                PlannedCollector(
                    "rss_generic",
                    RssNewsCollector(
                        collectable["rss_generic"], feed_url=_MOCK_FEED_URL,
                        ticker_hints=tickers, classify_corporate_events=True, fetcher=fetcher,
                    ),
                )
            )
        if "worldbank" in collectable:
            plans.append(
                PlannedCollector(
                    "worldbank",
                    WorldBankCollector(
                        collectable["worldbank"],
                        indicators={_WORLDBANK_INDICATOR: _WORLDBANK_SERIES_ID},
                        fetcher=fetcher,
                    ),
                )
            )
        return plans

    # REPLAY: same real collectors, wrapped to read from the archive instead
    # of fetching -- built with a spec temporarily marked IMPLEMENTED isn't
    # needed here since `collectable` already only contains IMPLEMENTED specs.
    for source_id, spec in collectable.items():
        if source_id == "stooq":
            symbols = {t: f"{t.lower()}.eg" for t in tickers if t in _STOOQ_PRICES}
            real = StooqPriceCollector(spec, symbols=symbols)
        elif source_id == "fred":
            real = FredCsvCollector(spec, series_ids=list(_FRED_SERIES))
        elif source_id == "rss_generic":
            real = RssNewsCollector(
                spec, feed_url=_MOCK_FEED_URL, ticker_hints=tickers, classify_corporate_events=True,
            )
        elif source_id == "worldbank":
            real = WorldBankCollector(spec, indicators={_WORLDBANK_INDICATOR: _WORLDBANK_SERIES_ID})
        else:
            continue
        plans.append(
            PlannedCollector(source_id, ArchiveReplayCollector(real, raw_documents))
        )
    return plans


# Rough expected-record counts per source, used only for this pipeline's own
# quality-assessment call (`assess_quality`'s `expected_records`) -- declared
# here because the pipeline knows what its own mock/replay fixtures contain,
# not because any collector needs to know this about a live source.
EXPECTED_RECORDS = {
    "stooq": len(_STOOQ_PRICES) * 10,
    "fred": len(_FRED_SERIES) * 10,
    "rss_generic": 3,
    "worldbank": 2,
}
