"""Collector Selection + Execution wiring for the production pipeline.

`ExecutionMode.LIVE` builds the *real* `Collector` subclasses this platform
already ships (`StooqPriceCollector`, `WorldBankCollector`) against a real
`HttpFetcher` -- an actual network fetch, real robots.txt enforcement, real
rate limiting/retry/backoff. This is the production default: the mission is
"AGX must stop behaving as a demonstration system." `FredCsvCollector` is
real, tested code, but is no longer depended upon by any live capability
ranking (`acquisition_intelligence.capability.CAPABILITY_STRATEGIES` --
3 consecutive live runs timed out fetching it; see `docs/TECHNICAL_DEBT.md`
TD-50) -- `build_live_collector` still knows how to build one, but nothing
in the live path calls it with `source_id="fred"` anymore.
`rss_generic` is deliberately left unwired in LIVE mode: it is `IMPLEMENTED`
as a generic collector *class*, but no concrete news outlet in the catalog
has a verified real feed URL yet (every named outlet stays `PLANNED`) --
wiring one live would mean guessing a URL, which this codebase's own rule
forbids. `unavailable_sources()` reports exactly why, per source, for
Mission Control's graceful-degradation reporting.

`ExecutionMode.MOCK` and `ExecutionMode.REPLAY` remain for testing only
(never used by a production deployment):

- `MOCK` builds the same real `Collector` subclasses against a
  `MockFetcher` that returns clearly-synthetic, wire-format-correct
  content instead of making a network call -- the same numbers
  `research/data/mock/` already uses, reformatted into each source's real
  CSV/JSON/RSS shape, so parsing exercises real format-handling logic, not
  hand-built domain objects.
- `REPLAY` wraps the same real collectors in `ArchiveReplayCollector`,
  sourcing previously-archived `RawDocument`s from a persisted
  `RawDocumentRepository` instead of fetching anything.

Every mode calls `CollectionService.run()` identically -- the pipeline
genuinely cannot tell whether its data is live, mocked, or replayed,
because nothing about the call site changes.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from agx_research.collectors.archive_replay import ArchiveReplayCollector
from agx_research.collectors.base import Collector
from agx_research.collectors.capmas import CapmasIndicatorCollector
from agx_research.collectors.egx_disclosures import EgxDisclosureCollector
from agx_research.collectors.egx_prices import EgxCompositePriceCollector
from agx_research.collectors.fetcher import HttpFetcher
from agx_research.collectors.fred import FredCsvCollector
from agx_research.collectors.gdelt import GdeltDocCollector
from agx_research.collectors.orascom_financials import OrascomFinancialHighlightsCollector
from agx_research.collectors.raw import RawDocumentRepository
from agx_research.collectors.rss import RssNewsCollector
from agx_research.collectors.stooq import StooqPriceCollector
from agx_research.collectors.telecom_egypt_financials import (
    TelecomEgyptFinancialHighlightsCollector,
)
from agx_research.collectors.un_sdg import UnSdgCollector
from agx_research.collectors.worldbank import WorldBankCollector
from agx_research.sources.registry import SourceRegistry
from agx_research.sources.spec import SourceSpec, SourceStatus


class ExecutionMode(str, Enum):
    LIVE = "live"
    MOCK = "mock"
    REPLAY = "replay"


# ---- LIVE mode: real identifiers for the sources this pipeline already
# knows how to wire, never a guessed URL. Each is a well-established, long-
# stable public identifier already declared as this source's convention
# elsewhere in this codebase (never invented for this pipeline alone):
# Stooq's `.eg` suffix for EGX tickers is documented in `sources/catalog.py`'s
# own `historical_coverage` field for the `stooq` entry; the World Bank
# indicator code below is the same one the mock fixture already uses (a
# real, decades-stable indicator code, not a mock invention); the FRED
# series below are long-established, textbook-stable US government series
# (oil, dollar index, treasury yield) -- the same confidence tier this
# codebase already grants FRED's/World Bank's endpoint *shape*.
LIVE_STOOQ_TICKER_SUFFIX = ".eg"
# Declared for `build_live_collector`'s (currently unreachable in the live
# path -- see module docstring/TD-50) FRED wiring; deliberately excluded
# from `LIVE_MACRO_SERIES_IDS`/`LIVE_MACRO_SERIES_SOURCES` below so this
# platform doesn't query for series ids no live collector actually produces.
LIVE_FRED_SERIES_IDS = [
    "DCOILBRENTEU",  # Brent: exporters, fertilizers, transport and inflation
    "DCOILWTICO",  # second oil benchmark for dislocation checks
    "DTWEXBGS",  # broad USD pressure
    "VIXCLS",  # global risk aversion
    "DGS2",  # front of the US yield curve
    "DGS10",  # global discount-rate anchor
    "BAMLH0A0HYM2",  # high-yield credit stress
]
LIVE_WORLDBANK_INDICATORS = {
    "FP.CPI.TOTL.ZG": "egypt_cpi_inflation",
    "NY.GDP.MKTP.KD.ZG": "egypt_real_gdp_growth",
    "BN.CAB.XOKA.GD.ZS": "egypt_current_account_pct_gdp",
    "FI.RES.TOTL.CD": "egypt_total_reserves_usd",
    "PA.NUS.FCRF": "egypt_official_fx_egp_per_usd",
    "FR.INR.LEND": "egypt_lending_rate",
    "SL.UEM.TOTL.ZS": "egypt_unemployment_rate",
    "NE.EXP.GNFS.ZS": "egypt_exports_pct_gdp",
    "NE.IMP.GNFS.ZS": "egypt_imports_pct_gdp",
    "BX.KLT.DINV.WD.GD.ZS": "egypt_fdi_net_inflows_pct_gdp",
    "DT.DOD.DECT.CD": "egypt_external_debt_usd",
}
LIVE_UN_SDG_SERIES = {
    "8.1.1": {"NY_GDP_PCAP": "un_real_gdp_per_capita_growth"},
    "8.2.1": {"SL_EMP_PCAP": "un_labour_productivity_growth"},
    "9.2.1": {"NV_IND_MANF": "un_manufacturing_value_added_pct_gdp"},
    "10.4.1": {"SL_EMP_GTOTL": "un_labour_income_share_pct_gdp"},
    "7.3.1": {"EG_EGY_PRIM": "un_energy_intensity"},
}
LIVE_CAPMAS_INDICATORS = {
    2156: {"Urban Egypt": "egypt_urban_cpi_index"},
    2264: {
        "Urban Egypt": "egypt_urban_cpi_yoy",
        "Total Egypt": "egypt_total_cpi_yoy",
    },
    2268: {"Urban Egypt": "egypt_urban_cpi_mom"},
}
# FRED excluded (see LIVE_FRED_SERIES_IDS' comment / TD-50): no live
# collector in the actual capability-driven path produces these ids, so
# querying for them would only ever find nothing.
LIVE_MACRO_SERIES_IDS = list(LIVE_WORLDBANK_INDICATORS.values())
LIVE_MACRO_SERIES_IDS += [
    local_id for mappings in LIVE_UN_SDG_SERIES.values() for local_id in mappings.values()
]
LIVE_MACRO_SERIES_IDS += [
    local_id for mappings in LIVE_CAPMAS_INDICATORS.values() for local_id in mappings.values()
]

# series_id -> source, for `data.point_in_time`'s per-source publication-lag
# assumption (`data.snapshot.build_snapshot`'s `macro_series_sources` param)
# -- built from the exact same groupings above, never a second declaration.
LIVE_MACRO_SERIES_SOURCES: dict[str, str] = {
    **{sid: "worldbank" for sid in LIVE_WORLDBANK_INDICATORS.values()},
    **{
        local_id: "undata"
        for mappings in LIVE_UN_SDG_SERIES.values()
        for local_id in mappings.values()
    },
    **{
        local_id: "capmas"
        for mappings in LIVE_CAPMAS_INDICATORS.values()
        for local_id in mappings.values()
    },
}

# World Bank/UN SDG report annually (often with a 1-2 year publication lag)
# and CAPMAS monthly -- the 30-day window used for prices/news/events would
# starve all of them of any observation almost always (a live-confirmed gap:
# every one of `LIVE_MACRO_SERIES_IDS` showed zero observations in a real
# run). ~2.5 years comfortably covers typical reporting lag for the annual
# sources while still being a bounded, explainable window rather than "all
# history".
LIVE_MACRO_LOOKBACK_DAYS = 900

# historical_patterns_agent needs years of daily bars to search for real
# analog episodes (see agents/historical_patterns.py); egx_price_composite's
# Yahoo leg already returns full history (range=max) on every live run, so
# this window is bounded by what's a defensible, explainable search depth
# for the agent, not by what the source can supply. ~4 years balances having
# enough non-overlapping historical windows to find real analogs against an
# unbounded "all history" search.
LIVE_PATTERN_LOOKBACK_DAYS = 1460

# Conservative floors, not true full-history sizes (unknown until a real
# fetch happens) -- `assess_quality`'s coverage score is capped at 1.0, so
# lowballing here never unfairly penalizes a real result, it only avoids
# guessing at a number this pipeline cannot know in advance.
EXPECTED_RECORDS_LIVE = {
    "egx_price_composite": 100,
    "stooq": 100,
    "worldbank": 10,
    "undata": 10,
    "capmas": 10,
    "gdelt": 10,
    "telecom_egypt_ir": 8,
    "orascom_ir": 3,
    "enterprise_press": 5,
    "fra_egypt": 5,
    "alborsa": 5,
    "masrawy_economy": 5,
    "skynews_arabia_economy": 5,
}

_UNAVAILABLE_REASON_BY_STATUS = {
    SourceStatus.PLANNED: (
        "Endpoint not yet verified against a real fetch; this codebase's own "
        "rule forbids wiring a collector against a guessed URL (see "
        "docs/DATA_ACQUISITION.md)."
    ),
    SourceStatus.NEEDS_KEY: (
        "Collector is code-complete but requires a user-supplied API key that "
        "has not been provided."
    ),
    SourceStatus.TOS_REVIEW: (
        "Automated collection/redistribution terms are ambiguous; collection "
        "stays blocked until a human legal/ToS review clears them."
    ),
    SourceStatus.DISABLED: "Source explicitly disabled in the registry.",
}


def unavailable_sources(registry: SourceRegistry, wired_ids: set[str]) -> dict[str, str]:
    """Every registered source *not* collected this execution, with the
    concrete reason -- so Mission Control can show `UNAVAILABLE` and why,
    instead of silently omitting a source (the mission's graceful-
    degradation requirement: unavailable sources must be visible, not
    invisible, and every remaining collector must keep running regardless).
    """
    reasons: dict[str, str] = {}
    for spec in registry.all_latest():
        if spec.id in wired_ids:
            continue
        if spec.integrated_via and spec.integrated_via in wired_ids:
            continue
        reasons[spec.id] = _UNAVAILABLE_REASON_BY_STATUS.get(
            spec.status,
            "IMPLEMENTED collector exists, but this pipeline has no verified "
            "live configuration (e.g. a real per-outlet feed URL) for it yet.",
        )
    return reasons


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
        for ticker, content in _STOOQ_PRICES.items():
            content_by_url[f"{base}?s={ticker.lower()}.eg&i=d"] = content
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


def build_live_collector(
    source_id: str,
    spec: SourceSpec,
    *,
    fetcher: HttpFetcher,
    tickers: list[str],
    companies: dict[str, str] | None = None,
) -> Collector | None:
    """The one place that knows how to construct a real, network-backed
    `Collector` for a given source id in LIVE mode -- reused by both the
    flat collector plan below and the capability-driven decision engine
    (`acquisition_intelligence.capability_engine.CapabilityDecisionEngine`,
    injected as its `collector_factory`), so there is exactly one live-
    wiring definition per source, not two. Returns `None` for any source id
    this deployment has no live wiring for yet -- never a guess.

    `companies` (ticker -> display name), when given, is threaded into any
    news collector's `ticker_hints` so its ticker attribution uses real
    entity resolution (`universe.entity_resolution.resolve_ticker_mentions`)
    instead of a bare ticker list; `tickers` alone still works (ticker-only
    matching, no company-name match) for any caller that hasn't looked one
    up.
    """
    if source_id == "egx_price_composite":
        return EgxCompositePriceCollector(spec, symbols=tickers, fetcher=fetcher)
    if source_id == "eac_egx_disclosures":
        return EgxDisclosureCollector(spec, tickers=tickers, fetcher=fetcher)
    if source_id == "stooq":
        symbols = {t: f"{t.lower()}{LIVE_STOOQ_TICKER_SUFFIX}" for t in tickers}
        return StooqPriceCollector(spec, symbols=symbols, fetcher=fetcher)
    if source_id == "fred":
        return FredCsvCollector(spec, series_ids=list(LIVE_FRED_SERIES_IDS), fetcher=fetcher)
    if source_id == "worldbank":
        return WorldBankCollector(spec, indicators=dict(LIVE_WORLDBANK_INDICATORS), fetcher=fetcher)
    if source_id == "undata":
        return UnSdgCollector(spec, series=dict(LIVE_UN_SDG_SERIES), fetcher=fetcher)
    if source_id == "capmas":
        return CapmasIndicatorCollector(
            spec, indicators=dict(LIVE_CAPMAS_INDICATORS), fetcher=fetcher
        )
    if source_id == "gdelt":
        # AND-of-ORs, not a single broad OR: a real historical run of the
        # old query (Egypt OR Egyptian OR "Egyptian Exchange" OR EGX) pulled
        # 13,464 articles of which only ~3.8% even mentioned "Egypt" in the
        # headline (see sources.catalog's gdelt evidence_tier note) --
        # requiring an Egypt term AND a finance term cuts the same false
        # positives (Nigeria telecom, Gaza ceasefire, Spanish tourism, ...)
        # without needing to guess at a stricter single-clause query. Still
        # discovery-tier regardless -- this narrows the candidate pool, it
        # doesn't replace `reconcile_discovery_news()`'s primary-source gate.
        return GdeltDocCollector(
            spec,
            query=(
                '(Egypt OR Egyptian OR "Egyptian Exchange" OR "EGX30" OR "Cairo Stock Exchange") '
                "(stock OR shares OR exchange OR economy OR pound OR inflation OR "
                '"interest rate" OR IPO OR earnings OR investors OR market OR trading)'
            ),
            ticker_hints=companies if companies is not None else tickers,
            max_records=50,
            fetcher=fetcher,
        )
    if source_id == "telecom_egypt_ir":
        return TelecomEgyptFinancialHighlightsCollector(spec, fetcher=fetcher)
    if source_id == "orascom_ir":
        return OrascomFinancialHighlightsCollector(spec, fetcher=fetcher)
    if (
        spec.access_method.value == "rss_feed"
        and spec.collector == "RssNewsCollector"
        and spec.base_url
    ):
        # Every configured RSS source has an endpoint recorded only after a
        # direct fetch and robots check.  Keeping this adapter generic means a
        # newly-qualified outlet needs catalog evidence, not another hardcoded
        # branch. Headline-classified corporate events remain informational
        # only (details={}); they can affect event risk but never price or
        # dividend adjustments.
        return RssNewsCollector(
            spec,
            feed_url=spec.base_url,
            ticker_hints=companies if companies is not None else tickers,
            classify_corporate_events=True,
            fetcher=fetcher,
        )
    # rss_generic and every other source deliberately excluded: no real,
    # verified feed URL/config exists yet (see `unavailable_sources`).
    return None


def live_wired_source_ids(registry: SourceRegistry) -> set[str]:
    """Sources this deployment can construct in LIVE mode right now.

    This is wiring topology, not execution state: a fallback such as Stooq
    remains wired even when a higher-ranked price strategy satisfies the
    capability before Stooq needs to run.
    """
    explicitly_wired = {
        "egx_price_composite",
        "eac_egx_disclosures",
        "stooq",
        # "fred" deliberately excluded -- see TD-50; it is no longer ranked
        # by any live capability, so it would never actually be attempted
        # and shouldn't be reported as a ready standby fallback.
        "worldbank",
        "undata",
        "capmas",
        "gdelt",
        "telecom_egypt_ir",
        "orascom_ir",
    }
    return {
        spec.id
        for spec in registry.collectable()
        if spec.id in explicitly_wired
        or (
            spec.access_method.value == "rss_feed"
            and spec.collector == "RssNewsCollector"
            and bool(spec.base_url)
        )
    }


def build_collector_plan(
    registry: SourceRegistry,
    *,
    mode: ExecutionMode,
    raw_documents: RawDocumentRepository,
    tickers: list[str] | None = None,
    companies: dict[str, str] | None = None,
) -> list[PlannedCollector]:
    """Collector Selection: pick the collectable sources this pipeline knows
    how to wire (a small, explicit set -- adding a source here is the "small
    adapter" the Data Acquisition Platform promises, not new framework work),
    and build each as a real `Collector`, backed by the execution mode's data
    source. Sources this pipeline has no wiring for (e.g. `global_benchmarks`,
    whose `collector` field names two classes jointly) are left to a future,
    explicit collector plan entry rather than guessed at.

    LIVE mode only builds the fixed set (stooq/fred/worldbank/enterprise_press)
    this function has always built; the production pipeline's own LIVE-mode
    collector *execution* stage no longer calls this function at all --
    it uses the capability-driven `CapabilityDecisionEngine` instead (see
    `production/pipeline.py`), which ranks every catalogued strategy per
    capability rather than a fixed website list. This function stays,
    unchanged in behavior, for MOCK/REPLAY (testing-only, deterministic
    fixtures) and as `build_live_collector`'s original callers may still
    reference it directly.
    """
    wireable = {"stooq", "fred", "rss_generic", "worldbank", "enterprise_press"}
    collectable = {s.id: s for s in registry.collectable() if s.id in wireable}
    tickers = tickers or list(_STOOQ_PRICES)

    plans: list[PlannedCollector] = []
    if mode == ExecutionMode.LIVE:
        fetcher = HttpFetcher()
        for source_id in ("stooq", "fred", "worldbank", "enterprise_press"):
            if source_id not in collectable:
                continue
            collector = build_live_collector(
                source_id, collectable[source_id], fetcher=fetcher, tickers=tickers, companies=companies
            )
            if collector is not None:
                plans.append(PlannedCollector(source_id, collector))
        return plans

    if mode == ExecutionMode.MOCK:
        content_by_url = _mock_url_map(collectable)
        fetcher = MockFetcher(content_by_url)
        if "stooq" in collectable:
            symbols = {t: f"{t.lower()}.eg" for t in tickers if t in _STOOQ_PRICES}
            plans.append(
                PlannedCollector(
                    "stooq",
                    StooqPriceCollector(collectable["stooq"], symbols=symbols, fetcher=fetcher),
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
                        collectable["rss_generic"],
                        feed_url=_MOCK_FEED_URL,
                        ticker_hints=companies if companies is not None else tickers,
                        classify_corporate_events=True,
                        fetcher=fetcher,
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
                spec,
                feed_url=_MOCK_FEED_URL,
                ticker_hints=companies if companies is not None else tickers,
                classify_corporate_events=True,
            )
        elif source_id == "worldbank":
            real = WorldBankCollector(spec, indicators={_WORLDBANK_INDICATOR: _WORLDBANK_SERIES_ID})
        else:
            continue
        plans.append(PlannedCollector(source_id, ArchiveReplayCollector(real, raw_documents)))
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
