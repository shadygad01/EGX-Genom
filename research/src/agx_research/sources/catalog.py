"""The seed source catalog: every source the acquisition program names,
with an honest status each.

Reliability/freshness values are DECLARED PRIORS following a documented
ordering (official regulator/central bank 0.9+ > exchange 0.9 > government
statistics 0.85 > established data aggregators 0.7 > news outlets 0.5-0.6 >
social/alternative 0.3-0.4); they are replaced by measured values as
collection history accumulates. `data_quality_score` is never seeded.

Statuses follow docs/DATA_ACQUISITION.md: IMPLEMENTED means a tested
collector exists; PLANNED means catalogued pending collector/config
(usually just a verified feed URL); NEEDS_KEY means the user must register
for the source's own free API key; TOS_REVIEW means automation or
redistribution terms are ambiguous and collection is blocked until
reviewed — ambiguity blocks, per the program's legal rules.
"""

from __future__ import annotations

from agx_research.sources.registry import SourceRegistry
from agx_research.sources.spec import (
    AccessMethod,
    RateLimit,
    SourceCategory,
    SourceSpec,
    SourceStatus,
    default_lifecycle_for_status,
)


def _spec(**kwargs) -> SourceSpec:
    spec = SourceSpec(**kwargs)
    lifecycle_state, activation_status = default_lifecycle_for_status(spec.status)
    return spec.model_copy(
        update={"lifecycle_state": lifecycle_state, "activation_status": activation_status}
    )


def seed_sources() -> list[SourceSpec]:
    return [
        # ---- IMPLEMENTED (tested collectors exist) ----
        _spec(
            id="stooq",
            name="Stooq",
            category=SourceCategory.MARKET_DATA,
            access_method=AccessMethod.CSV_DOWNLOAD,
            status=SourceStatus.IMPLEMENTED,
            base_url="https://stooq.com/q/d/l/",
            reliability_score=0.7,
            freshness_score=0.7,
            historical_coverage="multi-year daily OHLCV; EGX symbols suffixed .eg; global indices/commodities/FX",
            expected_latency="end-of-day",
            update_frequency="daily",
            collector="StooqPriceCollector",
            collector_version="1.0.0",
            rate_limit=RateLimit(requests_per_minute=6, min_seconds_between_requests=10.0),
            license="Free for personal use; verify redistribution terms before publishing raw data.",
            terms_of_use_url="https://stooq.com/pomoc/?q=8",
            validation_rules=["data.quality.validate_price_bars"],
            normalization_rules=[
                "dates ISO-8601",
                "OHLCV floats/ints",
                "symbol upper-cased, .eg stripped",
            ],
            conflict_priority=60,
            supported_entities=["EGX tickers", "global indices", "commodities", "FX"],
            supported_event_types=["market"],
            notes="Price-data feasibility mission: robots.txt now confirmed live to disallow "
            "the CSV-download mechanism entirely -- not scoped to EGX tickers (an equivalent "
            "US-ticker path and the bare /q/d/l/ path are disallowed identically; even fetching "
            "robots.txt itself is disallowed by its own rule). Collector code stays IMPLEMENTED "
            "(real, tested against recorded fixtures) since a future robots.txt change could "
            "restore this path, but no live run can legally collect from it today -- "
            "health_status correctly reflects DEGRADED/FAILED, not a code defect. Supersedes "
            "the earlier 'Cloudflare challenge on homepage, CSV endpoint unconfirmed' framing.",
        ),
        _spec(
            id="fred",
            name="FRED (St. Louis Fed)",
            category=SourceCategory.MACROECONOMIC,
            access_method=AccessMethod.CSV_DOWNLOAD,
            status=SourceStatus.IMPLEMENTED,
            base_url="https://fred.stlouisfed.org/graph/fredgraph.csv",
            reliability_score=0.9,
            freshness_score=0.8,
            historical_coverage="decades, series-dependent",
            expected_latency="days (series-dependent)",
            update_frequency="daily/weekly/monthly by series",
            collector="FredCsvCollector",
            collector_version="1.0.0",
            rate_limit=RateLimit(requests_per_minute=10, min_seconds_between_requests=6.0),
            license="FRED terms: free use with attribution.",
            terms_of_use_url="https://fred.stlouisfed.org/legal/",
            validation_rules=["numeric values; '.' means missing and is dropped"],
            normalization_rules=["dates ISO-8601", "values float"],
            conflict_priority=85,
            supported_entities=["oil", "dollar index", "US treasury yields", "global macro series"],
            supported_event_types=["macroeconomic"],
        ),
        _spec(
            id="rss_generic",
            name="Generic RSS/Atom collector (serves every feed-publishing outlet)",
            category=SourceCategory.NEWS,
            access_method=AccessMethod.RSS_FEED,
            status=SourceStatus.IMPLEMENTED,
            reliability_score=0.5,
            freshness_score=0.9,
            historical_coverage="feed window only (typically days)",
            expected_latency="minutes to hours",
            update_frequency="continuous",
            collector="RssNewsCollector",
            collector_version="1.0.0",
            license="Headlines/links per feed's own terms; full-text respect per-outlet.",
            validation_rules=["title+date required", "entry link preserved as original URL"],
            normalization_rules=["dates to ISO-8601", "whitespace collapsed"],
            conflict_priority=40,
            supported_event_types=["news"],
            supported_languages=["en", "ar"],
        ),
        _spec(
            id="worldbank",
            name="World Bank Open Data",
            category=SourceCategory.MACROECONOMIC,
            access_method=AccessMethod.JSON_API,
            status=SourceStatus.IMPLEMENTED,
            base_url="https://api.worldbank.org/v2",
            reliability_score=0.9,
            freshness_score=0.5,
            historical_coverage="annual indicators, decades of history, Egypt included",
            expected_latency="annual (some indicators lag a year or more)",
            update_frequency="annual",
            collector="WorldBankCollector",
            collector_version="1.0.0",
            rate_limit=RateLimit(requests_per_minute=20, min_seconds_between_requests=2.0),
            license="World Bank Open Data license (CC-BY 4.0): free use with attribution.",
            terms_of_use_url="https://www.worldbank.org/en/about/legal/terms-of-use-for-datasets",
            validation_rules=["value present (null years dropped, never imputed)"],
            normalization_rules=["annual observation normalized to Dec 31 of its year"],
            conflict_priority=85,
            supported_entities=["Egypt macro indicators (GDP, inflation, reserves, trade, etc.)"],
            supported_event_types=["macroeconomic"],
            supported_languages=["en"],
        ),
        # ---- OFFICIAL (PLANNED: endpoints must be verified, not guessed) ----
        _spec(
            id="egx_official",
            name="Egyptian Exchange (EGX)",
            category=SourceCategory.OFFICIAL,
            access_method=AccessMethod.CSV_DOWNLOAD,
            status=SourceStatus.PLANNED,
            reliability_score=0.9,
            freshness_score=0.8,
            historical_coverage="official listings/indices/disclosures",
            update_frequency="daily",
            conflict_priority=95,
            supported_event_types=["corporate", "market"],
            supported_languages=["ar", "en"],
            notes="Official downloads exist (indices, disclosures); exact endpoints to be verified from egx.com.eg before a collector is written -- never guessed.",
        ),
        # Coverage-expansion mission: the Acquisition Intelligence Engine's
        # standard RSS-autodiscovery heuristic found a real feed on FRA's own
        # homepage (fra.gov.eg) -- the same mechanism, same rigor, that
        # verified enterprise_press. See docs/ACQUISITION_STRATEGY.md.
        _spec(
            id="fra_egypt",
            name="Financial Regulatory Authority (FRA)",
            category=SourceCategory.OFFICIAL,
            access_method=AccessMethod.RSS_FEED,
            status=SourceStatus.IMPLEMENTED,
            base_url="https://fra.gov.eg/feed/",
            reliability_score=0.95,
            freshness_score=0.6,
            conflict_priority=98,
            collector="RssNewsCollector",
            collector_version="1.0.0",
            supported_event_types=["corporate"],
            supported_languages=["ar"],
            notes="Feed URL verified live via RSS autodiscovery on fra.gov.eg's homepage "
            "(see docs/ACQUISITION_STRATEGY.md).",
        ),
        _spec(
            id="cbe",
            name="Central Bank of Egypt",
            category=SourceCategory.OFFICIAL,
            access_method=AccessMethod.CSV_DOWNLOAD,
            status=SourceStatus.PLANNED,
            reliability_score=0.95,
            freshness_score=0.8,
            conflict_priority=98,
            supported_entities=["EGP rates", "policy rates", "inflation"],
            supported_event_types=["macroeconomic"],
            supported_languages=["ar", "en"],
            notes="Publishes exchange/policy rates and time series; endpoint verification pending.",
        ),
        _spec(
            id="mof_egypt",
            name="Ministry of Finance (Egypt)",
            category=SourceCategory.OFFICIAL,
            access_method=AccessMethod.PDF_DOWNLOAD,
            status=SourceStatus.PLANNED,
            reliability_score=0.9,
            freshness_score=0.5,
            conflict_priority=90,
            supported_event_types=["macroeconomic"],
            supported_languages=["ar", "en"],
        ),
        _spec(
            id="capmas",
            name="CAPMAS",
            category=SourceCategory.OFFICIAL,
            access_method=AccessMethod.PDF_DOWNLOAD,
            status=SourceStatus.PLANNED,
            reliability_score=0.9,
            freshness_score=0.4,
            conflict_priority=90,
            supported_event_types=["macroeconomic"],
            supported_languages=["ar"],
        ),
        _spec(
            id="egypt_open_data",
            name="Government Open Data (Egypt)",
            category=SourceCategory.OFFICIAL,
            access_method=AccessMethod.JSON_API,
            status=SourceStatus.PLANNED,
            reliability_score=0.85,
            freshness_score=0.4,
            conflict_priority=85,
            supported_event_types=["macroeconomic"],
            supported_languages=["ar", "en"],
        ),
        # ---- COMPANY (PLANNED; per-company IR config) ----
        _spec(
            id="company_ir",
            name="Company Investor Relations (per-constituent config)",
            category=SourceCategory.COMPANY,
            access_method=AccessMethod.PDF_DOWNLOAD,
            status=SourceStatus.PLANNED,
            reliability_score=0.85,
            freshness_score=0.5,
            conflict_priority=90,
            supported_event_types=["corporate"],
            supported_languages=["ar", "en"],
            notes="Annual/quarterly/interim reports, presentations, press releases, corporate actions, XBRL where published. One RSS/PDF collector config per constituent IR page; needs a PDF/XBRL extraction stage (see roadmap).",
        ),
        # ---- MARKET DATA aggregators ----
        _spec(
            id="yahoo_finance",
            name="Yahoo Finance",
            category=SourceCategory.MARKET_DATA,
            access_method=AccessMethod.JSON_API,
            status=SourceStatus.TOS_REVIEW,
            reliability_score=0.7,
            freshness_score=0.9,
            conflict_priority=55,
            supported_entities=["EGX tickers (.CA suffix)", "global"],
            notes="Unofficial API automation sits in ToS gray territory; blocked until reviewed. Ambiguity blocks.",
        ),
        _spec(
            id="fmp",
            name="Financial Modeling Prep (free tier)",
            category=SourceCategory.MARKET_DATA,
            access_method=AccessMethod.JSON_API,
            status=SourceStatus.NEEDS_KEY,
            base_url="https://financialmodelingprep.com/api/v3",
            reliability_score=0.65,
            freshness_score=0.8,
            conflict_priority=50,
            authentication="api_key(user-supplied)",
            collector="FmpCollector",
            collector_version="1.0.0",
            validation_rules=["data.quality.validate_price_bars"],
            notes="Collector code is complete and tested against FMP's documented JSON "
            "shape; status stays NEEDS_KEY until a user supplies their own API key and "
            "an operator flips this entry to IMPLEMENTED.",
        ),
        _spec(
            id="alphavantage",
            name="AlphaVantage (free tier)",
            category=SourceCategory.MARKET_DATA,
            access_method=AccessMethod.JSON_API,
            status=SourceStatus.NEEDS_KEY,
            base_url="https://www.alphavantage.co/query",
            reliability_score=0.65,
            freshness_score=0.7,
            conflict_priority=50,
            authentication="api_key(user-supplied)",
            collector="AlphaVantageCollector",
            collector_version="1.0.0",
            validation_rules=["data.quality.validate_price_bars"],
            rate_limit=RateLimit(requests_per_minute=5, min_seconds_between_requests=15.0),
            notes="Collector code is complete and tested against AlphaVantage's documented "
            "JSON shape; status stays NEEDS_KEY until a user supplies their own API key and "
            "an operator flips this entry to IMPLEMENTED.",
        ),
        _spec(
            id="polygon",
            name="Polygon.io (free tier)",
            category=SourceCategory.MARKET_DATA,
            access_method=AccessMethod.JSON_API,
            status=SourceStatus.NEEDS_KEY,
            reliability_score=0.7,
            freshness_score=0.8,
            conflict_priority=55,
            authentication="api_key(user-supplied)",
        ),
        _spec(
            id="tiingo",
            name="Tiingo (free tier)",
            category=SourceCategory.MARKET_DATA,
            access_method=AccessMethod.JSON_API,
            status=SourceStatus.NEEDS_KEY,
            reliability_score=0.7,
            freshness_score=0.8,
            conflict_priority=55,
            authentication="api_key(user-supplied)",
        ),
        _spec(
            id="investing_com",
            name="Investing.com",
            category=SourceCategory.MARKET_DATA,
            access_method=AccessMethod.HTML_SCRAPE,
            status=SourceStatus.TOS_REVIEW,
            reliability_score=0.6,
            freshness_score=0.8,
            conflict_priority=40,
            notes="ToS restricts automated collection; blocked.",
        ),
        _spec(
            id="tradingview",
            name="TradingView (incl. news)",
            category=SourceCategory.MARKET_DATA,
            access_method=AccessMethod.JSON_API,
            status=SourceStatus.TOS_REVIEW,
            reliability_score=0.6,
            freshness_score=0.9,
            conflict_priority=40,
            notes="ToS restricts automated collection; blocked.",
        ),
        # ---- Enterprise: IMPLEMENTED -- the one outlet with a verified real
        # feed URL. Discovered live by the Acquisition Intelligence Engine's
        # standard RSS-autodiscovery heuristic (a real <link rel="alternate"
        # type="application/rss+xml"> tag on enterprise.press's own homepage,
        # not a guess) and confirmed reachable, distinct from every other
        # named outlet below, which stays PLANNED until its own feed URL is
        # likewise verified. See docs/ACQUISITION_STRATEGY.md.
        _spec(
            id="enterprise_press",
            name="Enterprise",
            category=SourceCategory.NEWS,
            access_method=AccessMethod.RSS_FEED,
            status=SourceStatus.IMPLEMENTED,
            base_url="https://enterpriseam.com/egypt/feed/",
            reliability_score=0.65,
            freshness_score=0.9,
            collector="RssNewsCollector",
            collector_version="1.0.0",
            conflict_priority=55,
            supported_event_types=["news", "corporate"],
            notes="Feed URL verified live via RSS autodiscovery on enterprise.press's "
            "homepage (see docs/ACQUISITION_STRATEGY.md's Runtime Implementation section).",
        ),
        _spec(
            id="gdelt",
            name="GDELT DOC 2.0",
            category=SourceCategory.NEWS,
            access_method=AccessMethod.JSON_API,
            status=SourceStatus.IMPLEMENTED,
            base_url="https://api.gdeltproject.org/api/v2/doc/doc",
            reliability_score=0.55,
            freshness_score=0.95,
            collector="GdeltDocCollector",
            collector_version="1.0.0",
            conflict_priority=35,
            historical_coverage="rolling global multilingual news window",
            expected_latency="minutes",
            update_frequency="continuous",
            rate_limit=RateLimit(requests_per_minute=5, min_seconds_between_requests=12.0),
            license="GDELT metadata; AGX stores headline/link metadata only, not article text.",
            terms_of_use_url="https://www.gdeltproject.org/about.html",
            supported_event_types=["news"],
            supported_languages=["en", "ar"],
            notes="Official free no-key DOC 2.0 JSON API, queried for Egypt/EGX coverage. "
            "Lower conflict priority than first-party and established direct publishers.",
        ),
        # ---- NEWS (English) -- each a config of rss_generic once feed URL verified ----
        *[
            _spec(
                id=source_id,
                name=name,
                category=SourceCategory.NEWS,
                access_method=AccessMethod.RSS_FEED,
                status=SourceStatus.PLANNED,
                reliability_score=rel,
                freshness_score=0.9,
                collector="RssNewsCollector",
                conflict_priority=priority,
                supported_event_types=["news"],
                notes="Feed URL to be verified, then this becomes RssNewsCollector configuration.",
            )
            for source_id, name, rel, priority in [
                ("reuters", "Reuters", 0.8, 70),
                ("zawya", "Zawya", 0.6, 50),
                ("mubasher", "Mubasher", 0.6, 55),
                ("asharq_business", "Asharq Business", 0.6, 50),
                ("cnbc_arabia", "CNBC Arabia", 0.6, 50),
                ("alarabiya_business", "Al Arabiya Business", 0.55, 45),
                ("marketscreener", "MarketScreener", 0.55, 40),
                ("investing_news", "Investing.com News", 0.5, 35),
            ]
        ],
        # ---- ARABIC NEWS ----
        # Coverage-expansion mission: RSS autodiscovery found a real,
        # legally-cleared feed on Sky News Arabia's own homepage -- same
        # mechanism as enterprise_press/fra_egypt above.
        _spec(
            id="skynews_arabia_economy",
            name="Sky News Arabia Economy",
            category=SourceCategory.ARABIC_NEWS,
            access_method=AccessMethod.RSS_FEED,
            status=SourceStatus.PLANNED,
            base_url="https://skynewsarabia.com/rss.xml",
            reliability_score=0.5,
            freshness_score=0.9,
            collector="RssNewsCollector",
            collector_version="1.0.0",
            conflict_priority=40,
            supported_event_types=["news"],
            supported_languages=["ar"],
            notes="Corrected finding, Final Data Acquisition sprint: discovered live via "
            "RSS autodiscovery and briefly promoted to IMPLEMENTED on reachability alone, "
            "but a direct collector run against this exact URL returned HTTP 404 -- it was "
            "promoted before an actual successful collection confirmed it, unlike "
            "enterprise_press/fra_egypt. Reverted to PLANNED until the feed URL is "
            "re-verified and a real collection run confirms real yield.",
        ),
        *[
            _spec(
                id=source_id,
                name=name,
                category=SourceCategory.ARABIC_NEWS,
                access_method=AccessMethod.RSS_FEED,
                status=SourceStatus.PLANNED,
                reliability_score=0.5,
                freshness_score=0.9,
                collector="RssNewsCollector",
                conflict_priority=40,
                supported_event_types=["news"],
                supported_languages=["ar"],
                notes="Feed URL to be verified, then this becomes RssNewsCollector configuration.",
            )
            for source_id, name in [
                ("almal", "Al Mal"),
                ("alborsa", "Al Borsa News"),
                ("masrawy_economy", "Masrawy Economy"),
                ("youm7_economy", "Youm7 Economy"),
                ("asharq_economy", "Asharq Economy"),
            ]
        ],
        # ---- MACRO (international) ----
        *[
            _spec(
                id=source_id,
                name=name,
                category=SourceCategory.MACROECONOMIC,
                access_method=access,
                status=SourceStatus.PLANNED,
                reliability_score=0.9,
                freshness_score=0.5,
                conflict_priority=85,
                supported_event_types=["macroeconomic"],
                notes=note,
            )
            for source_id, name, access, note in [
                (
                    "imf",
                    "IMF",
                    AccessMethod.JSON_API,
                    "IMF SDMX/JSON APIs are free; series mapping pending.",
                ),
                ("oecd", "OECD", AccessMethod.JSON_API, "SDMX API free; Egypt coverage partial."),
                ("undata", "UN Data", AccessMethod.CSV_DOWNLOAD, "Bulk downloads free."),
                (
                    "trading_economics",
                    "Trading Economics",
                    AccessMethod.JSON_API,
                    "Free tier limited; ToS/key requirements to review.",
                ),
            ]
        ],
        # ---- GLOBAL MARKETS: served by stooq/fred series config, catalogued as coverage ----
        _spec(
            id="global_benchmarks",
            name="Global benchmarks via Stooq/FRED series",
            category=SourceCategory.GLOBAL_MARKETS,
            access_method=AccessMethod.CSV_DOWNLOAD,
            status=SourceStatus.IMPLEMENTED,
            collector="StooqPriceCollector/FredCsvCollector",
            collector_version="1.0.0",
            reliability_score=0.75,
            freshness_score=0.7,
            conflict_priority=60,
            supported_entities=[
                "S&P500",
                "NASDAQ",
                "Dow Jones",
                "FTSE",
                "US Treasury yields",
                "Dollar Index",
                "Gold",
                "Silver",
                "Oil (Brent/WTI)",
                "Natural Gas",
                "Copper",
            ],
            supported_event_types=["market", "macroeconomic"],
            notes="MSCI index data, steel, Baltic Dry, and Suez Canal statistics need dedicated sources (MSCI licensing; SCA publishes monthly stats) -- catalogued as gaps, not silently claimed.",
        ),
        _spec(
            id="suez_canal_stats",
            name="Suez Canal Authority statistics",
            category=SourceCategory.GLOBAL_MARKETS,
            access_method=AccessMethod.PDF_DOWNLOAD,
            status=SourceStatus.PLANNED,
            reliability_score=0.9,
            freshness_score=0.3,
            conflict_priority=90,
            supported_event_types=["macroeconomic"],
            supported_languages=["ar", "en"],
        ),
        # ---- ALTERNATIVE ----
        *[
            _spec(
                id=source_id,
                name=name,
                category=SourceCategory.ALTERNATIVE,
                access_method=access,
                status=status,
                reliability_score=0.35,
                freshness_score=0.8,
                conflict_priority=20,
                notes=note,
            )
            for source_id, name, access, status, note in [
                (
                    "wikipedia_pageviews",
                    "Wikipedia Page Views",
                    AccessMethod.JSON_API,
                    SourceStatus.PLANNED,
                    "Official free Wikimedia API; collector pending.",
                ),
                (
                    "google_trends",
                    "Google Trends",
                    AccessMethod.JSON_API,
                    SourceStatus.TOS_REVIEW,
                    "No official API; automation ToS-ambiguous; blocked.",
                ),
                (
                    "github_releases",
                    "GitHub Releases (listed-company tech signals)",
                    AccessMethod.JSON_API,
                    SourceStatus.PLANNED,
                    "Official free API.",
                ),
                (
                    "company_social_official",
                    "Official company social accounts (LinkedIn/FB/X/YouTube)",
                    AccessMethod.RSS_FEED,
                    SourceStatus.TOS_REVIEW,
                    "Platform APIs require keys and restrict automation; per-platform review needed.",
                ),
                (
                    "public_telegram",
                    "Public Telegram channels",
                    AccessMethod.JSON_API,
                    SourceStatus.TOS_REVIEW,
                    "Bot API needs a user bot token; channel-content licensing varies.",
                ),
                (
                    "patents",
                    "Patent databases",
                    AccessMethod.JSON_API,
                    SourceStatus.PLANNED,
                    "EPO/WIPO free APIs; Egypt-relevant mapping pending.",
                ),
                (
                    "hiring_signals",
                    "Hiring signals (official career pages/feeds)",
                    AccessMethod.RSS_FEED,
                    SourceStatus.PLANNED,
                    "Only official postings; no scraping of third-party job boards without ToS review.",
                ),
            ]
        ],
        # ---- RESEARCH ----
        *[
            _spec(
                id=source_id,
                name=name,
                category=SourceCategory.RESEARCH,
                access_method=access,
                status=status,
                reliability_score=0.7,
                freshness_score=0.3,
                conflict_priority=30,
                notes=note,
            )
            for source_id, name, access, status, note in [
                (
                    "arxiv",
                    "arXiv (q-fin)",
                    AccessMethod.RSS_FEED,
                    SourceStatus.PLANNED,
                    "Official free API/RSS.",
                ),
                (
                    "ssrn",
                    "SSRN",
                    AccessMethod.RSS_FEED,
                    SourceStatus.PLANNED,
                    "Public RSS for new papers.",
                ),
                (
                    "nber",
                    "NBER",
                    AccessMethod.RSS_FEED,
                    SourceStatus.PLANNED,
                    "Public new-papers feed.",
                ),
                (
                    "google_scholar",
                    "Google Scholar",
                    AccessMethod.HTML_SCRAPE,
                    SourceStatus.TOS_REVIEW,
                    "Explicitly prohibits automated access; blocked.",
                ),
                (
                    "researchgate",
                    "ResearchGate",
                    AccessMethod.HTML_SCRAPE,
                    SourceStatus.TOS_REVIEW,
                    "ToS restricts automated collection; blocked.",
                ),
            ]
        ],
    ]


def seed_registry(registry: SourceRegistry | None = None) -> SourceRegistry:
    registry = registry or SourceRegistry()
    for spec in seed_sources():
        if registry.latest(spec.id) is None:
            registry.add(spec)
    return registry
