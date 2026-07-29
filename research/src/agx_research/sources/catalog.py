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

Per the project owner's explicit decision, this catalog seeds no
NEEDS_KEY sources: the platform is scoped to sources collectable with no
registration/credential of any kind, so a capability whose only real
strategy would require one is left honestly uncovered rather than
catalogued and left waiting indefinitely (see `docs/DATA_ACQUISITION.md`'s
"No API-key sources" note; FMP/AlphaVantage/Polygon/Tiingo were removed
for exactly this reason, not because their collector code was wrong).
"""

from __future__ import annotations

from agx_research.sources.registry import SourceRegistry
from agx_research.sources.spec import (
    AccessMethod,
    LegalUseStatus,
    RateLimit,
    RetryPolicy,
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
            id="egx_price_composite",
            name="EGX price provider (Yahoo + StockAnalysis + Mubasher fallback)",
            category=SourceCategory.MARKET_DATA,
            access_method=AccessMethod.JSON_API,
            status=SourceStatus.IMPLEMENTED,
            legal_use_status=LegalUseStatus.RESEARCH_ONLY,
            base_url="https://query1.finance.yahoo.com/v8/finance/chart/",
            reliability_score=0.75,
            freshness_score=0.9,
            historical_coverage=(
                "Yahoo maximum daily history plus StockAnalysis recent daily overlap; "
                "Mubasher post-close snapshot fallback"
            ),
            expected_latency="end-of-day",
            update_frequency="daily",
            collector="EgxCompositePriceCollector",
            collector_version="1.0.0",
            retry_policy=RetryPolicy(max_attempts=2, backoff_seconds=0.5, backoff_multiplier=2.0),
            rate_limit=RateLimit(requests_per_minute=60, min_seconds_between_requests=0.25),
            license=(
                "Operational collection authorized by the repository owner; upstream terms "
                "and endpoint stability remain provider-specific and must be monitored."
            ),
            validation_rules=["data.quality.validate_price_bars"],
            normalization_rules=[
                "UniverseProvider ticker + .CA vendor mapping",
                "dates ISO-8601",
                "OHLCV floats/ints",
                "StockAnalysis overwrites overlapping Yahoo dates",
                "Mubasher snapshots materialize only after Cairo market close",
            ],
            conflict_priority=70,
            priority=100,
            supported_entities=["UniverseProvider EGX tickers"],
            supported_event_types=["market", "corporate"],
            notes=(
                "Live feasibility probes dated 2026-07-26 measured Yahoo at 91/101 and "
                "StockAnalysis at 99/101, with union coverage 101/101. The single composite "
                "adapter is deliberate: fallback is evaluated per ticker, so partial success "
                "cannot cause the capability engine to abandon uncovered constituents. Raw "
                "document URLs retain provider=ticker provenance. No constituent list is "
                "embedded; production injects the current UniverseProvider symbols."
            ),
        ),
        _spec(
            id="stooq",
            name="Stooq",
            category=SourceCategory.MARKET_DATA,
            access_method=AccessMethod.CSV_DOWNLOAD,
            status=SourceStatus.IMPLEMENTED,
            legal_use_status=LegalUseStatus.BLOCKED,
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
            legal_use_status=LegalUseStatus.CLEARED,
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
            legal_use_status=LegalUseStatus.CLEARED,
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
            status=SourceStatus.DISABLED,
            reliability_score=0.9,
            freshness_score=0.8,
            historical_coverage="official listings/indices/disclosures",
            update_frequency="daily",
            conflict_priority=95,
            supported_event_types=["corporate", "market"],
            supported_languages=["ar", "en"],
            notes=(
                "Not a paid-service block -- egx.com.eg/www.egx.com.eg actively reset the TCP "
                "connection, reconfirmed across 6+ live sessions including automated weekly "
                "discovery. This program's rules forbid defeating a network-level anti-bot "
                "measure, so it cannot become IMPLEMENTED by further engineering attempts; "
                "disabled rather than left as an open 'planned' item with no real path forward. "
                "Reopen only on a business/legal action (EGX outreach for allowlisting, or a "
                "licensed EGX data vendor) -- see docs/ACQUISITION_STRATEGY.md capability 1/2/8/9/10."
            ),
        ),
        _spec(
            id="egid_financial_filings",
            name="EGID official issuer financial-filings service",
            category=SourceCategory.OFFICIAL,
            access_method=AccessMethod.JSON_API,
            status=SourceStatus.TOS_REVIEW,
            legal_use_status=LegalUseStatus.BLOCKED,
            base_url="https://ir.egidegypt.com:8080/api/Feed/getnewsbysearch",
            reliability_score=0.95,
            freshness_score=0.9,
            historical_coverage="up to six years of issuer financial-statement attachments",
            expected_latency="same day as EGX disclosure",
            update_frequency="event driven",
            conflict_priority=98,
            supported_entities=["EGX issuers by ISIN"],
            supported_event_types=["corporate"],
            supported_languages=["ar", "en"],
            integrated_capabilities=["financial_statements", "investor_relations"],
            license=(
                "Official public issuer-IR display service. Cross-issuer automated API use is "
                "not authorized by published documentation and therefore remains blocked."
            ),
            notes=(
                "Live audit 2026-07-28 verified that public company pages obtain a Feed:Get "
                "JWT scoped to one company and POST an ISIN to getnewsbysearch. The backend "
                "accepted other ISINs with that company-scoped token, but relying on that "
                "behavior could bypass intended tenant authorization. Do not automate until "
                "EGID confirms a market-wide credential or public bulk-feed terms."
            ),
        ),
        _spec(
            id="egx_universe_seed",
            name="Official EGX30/EGX70 Universe snapshot",
            category=SourceCategory.OFFICIAL,
            access_method=AccessMethod.CSV_DOWNLOAD,
            status=SourceStatus.IMPLEMENTED,
            legal_use_status=LegalUseStatus.CLEARED,
            reliability_score=0.95,
            freshness_score=0.8,
            historical_coverage="reviewed EGX30 and EGX70 constituent snapshots",
            update_frequency="on official index rebalance",
            collector="UniverseProvider",
            collector_version="1.0.0",
            conflict_priority=99,
            priority=100,
            supported_entities=["EGX30", "EGX70", "EGX tickers"],
            supported_event_types=["market"],
            integrated_capabilities=["index_constituents"],
            notes="Materialized official index membership is the production UniverseProvider source of truth.",
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
            status=SourceStatus.DISABLED,
            reliability_score=0.95,
            freshness_score=0.8,
            conflict_priority=98,
            supported_entities=["EGP rates", "policy rates", "inflation"],
            supported_event_types=["macroeconomic"],
            supported_languages=["ar", "en"],
            notes=(
                "Not a paid-service block -- cbe.org.eg's WAF returns an explicit 'Request "
                "Rejected... consult with your administrator' page, confirmed repeatedly "
                "including today's automated discovery run. Disabled rather than left "
                "'planned' with no real path forward; a separate, non-WAF-protected CBE data "
                "API/subdomain remains an unverified possibility, not assumed -- reopen if one "
                "is found. See docs/ACQUISITION_STRATEGY.md capability 7/12."
            ),
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
            access_method=AccessMethod.JSON_API,
            status=SourceStatus.IMPLEMENTED,
            legal_use_status=LegalUseStatus.RESEARCH_ONLY,
            base_url="https://www.capmas.gov.eg:8080/api",
            collector="CapmasIndicatorCollector",
            collector_version="1.0.0",
            license=(
                "Research/general use with CAPMAS attribution; no resale or direct commercial "
                "exploitation of extracted data."
            ),
            terms_of_use_url="https://www.capmas.gov.eg:8080/api/UsageRightAndTerm",
            reliability_score=0.9,
            freshness_score=0.8,
            conflict_priority=90,
            supported_event_types=["macroeconomic"],
            supported_languages=["ar"],
            notes=(
                "Official unauthenticated JSON API used by the CAPMAS public web application; "
                "CPI aggregate filters verified live. Raw extracted data must not be sold."
            ),
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
        # ---- COMPANY ----
        _spec(
            id="telecom_egypt_ir",
            name="Telecom Egypt Investor Relations",
            category=SourceCategory.COMPANY,
            access_method=AccessMethod.HTML_SCRAPE,
            status=SourceStatus.IMPLEMENTED,
            legal_use_status=LegalUseStatus.RESEARCH_ONLY,
            base_url="https://ir.te.eg/",
            reliability_score=0.95,
            freshness_score=0.9,
            historical_coverage="Latest issuer-published quarterly financial highlights",
            expected_latency="issuer publication",
            update_frequency="quarterly",
            collector="TelecomEgyptFinancialHighlightsCollector",
            collector_version="1.0.0",
            license=(
                "Public primary issuer investor-relations release; research use with "
                "source attribution. Raw release content is not redistributed."
            ),
            validation_rules=["FinancialStatementLineItem schema", "explicit EGP-labelled values"],
            normalization_rules=["EGP bn to EGP units", "quarter label to ISO period end"],
            conflict_priority=95,
            priority=95,
            supported_entities=["ETEL"],
            supported_event_types=["corporate"],
            supported_languages=["en"],
            notes=(
                "Live-verified official IR homepage and Q1 2026 release. The collector "
                "fails closed unless a reporting period and explicitly labelled revenue, "
                "EBITDA, net profit or FCFF amount are present. Scanned statement PDFs are "
                "archival evidence but are not heuristically OCR-parsed."
            ),
        ),
        _spec(
            id="orascom_ir",
            name="Orascom Construction Investor Relations",
            category=SourceCategory.COMPANY,
            access_method=AccessMethod.HTML_SCRAPE,
            status=SourceStatus.IMPLEMENTED,
            legal_use_status=LegalUseStatus.RESEARCH_ONLY,
            base_url="https://orascom.com/updates/",
            reliability_score=0.95,
            freshness_score=0.9,
            historical_coverage="Latest issuer-published quarterly or annual result highlights",
            expected_latency="issuer publication",
            update_frequency="quarterly",
            collector="OrascomFinancialHighlightsCollector",
            collector_version="1.0.0",
            license=(
                "Public primary issuer investor-relations release; research use with "
                "source attribution. Raw article content is not redistributed."
            ),
            validation_rules=["FinancialStatementLineItem schema", "explicit USD-labelled values"],
            normalization_rules=["USD million to USD units", "quarter/FY label to ISO period end"],
            conflict_priority=95,
            priority=94,
            supported_entities=["ORAS"],
            supported_event_types=["corporate"],
            supported_languages=["en"],
            notes=(
                "Live-verified official updates archive and Q1 2026 result article. "
                "The collector fails closed unless a period plus one issuer-labelled "
                "revenue/EBITDA/net-profit highlight sentence is present."
            ),
        ),
        # Generic per-company IR expansion remains planned.
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
            status=SourceStatus.DISABLED,
            reliability_score=0.7,
            freshness_score=0.9,
            conflict_priority=55,
            supported_entities=["EGX tickers (.CA suffix)", "global"],
            integrated_via="egx_price_composite",
            integrated_capabilities=["price_data"],
            notes=(
                "Not a paid-service block -- Yahoo's own Terms of Service, fetched and quoted "
                "live (guce.yahoo.com/terms), explicitly prohibits 'automated means... robots, "
                "spiders, scrapers, data mining tools... without our express, prior permission.' "
                "This id exists only to record that leg's role inside egx_price_composite "
                "(already IMPLEMENTED, operated under the repository owner's own authorization "
                "-- see that spec's license note); no separate standalone collector will be "
                "built against this id, so it is disabled rather than left as a fake 'planned' "
                "work item. See docs/ACQUISITION_STRATEGY.md's Price Data Feasibility Mission."
            ),
        ),
        _spec(
            id="stockanalysis",
            name="StockAnalysis EGX history",
            category=SourceCategory.MARKET_DATA,
            access_method=AccessMethod.HTML_SCRAPE,
            status=SourceStatus.DISABLED,
            reliability_score=0.7,
            freshness_score=0.9,
            conflict_priority=60,
            supported_entities=["UniverseProvider EGX tickers"],
            integrated_via="egx_price_composite",
            integrated_capabilities=["price_data"],
            notes=(
                "Not blocked and not a paid service -- this id exists only to record that "
                "StockAnalysis's role is already served as a live provider leg inside "
                "egx_price_composite (IMPLEMENTED). No standalone collector is planned against "
                "this id by design, so it is disabled rather than left as an open 'planned' "
                "item nothing is actually working toward."
            ),
        ),
        _spec(
            id="investing_com",
            name="Investing.com",
            category=SourceCategory.MARKET_DATA,
            access_method=AccessMethod.HTML_SCRAPE,
            status=SourceStatus.DISABLED,
            reliability_score=0.6,
            freshness_score=0.8,
            conflict_priority=40,
            notes=(
                "Not a paid-service block -- investing.com returns 403 Forbidden site-wide, "
                "confirmed on a direct fetch and reconfirmed by today's automated discovery run "
                "('no reachable domain'). No structured/legal acquisition method exists to build "
                "a collector against; disabled rather than left as an open 'planned' item."
            ),
        ),
        _spec(
            id="tradingview",
            name="TradingView (incl. news)",
            category=SourceCategory.MARKET_DATA,
            access_method=AccessMethod.JSON_API,
            status=SourceStatus.DISABLED,
            reliability_score=0.6,
            freshness_score=0.9,
            conflict_priority=40,
            notes=(
                "Not a paid-service block per se, though TradingView's paid data plans are the "
                "only sanctioned way to use this data at all -- its real policies page "
                "(tradingview.com/policies/), fetched and quoted live, carries explicit "
                "data-ownership/redistribution restriction language forbidding non-display "
                "automated use. Disabled rather than left as an open 'planned' item with no "
                "free, legal path forward."
            ),
        ),
        # Coverage-expansion mission: a free, independent third-party EGX
        # listed-companies directory (found via public web search, not
        # training-data recall), targeted primarily as a company-directory
        # hint supplier for the `company_ir` chain -- see
        # `acquisition_intelligence.target`'s `PRIORITY_COMPANY_DIRECTORY`
        # and AD-33. Not asserted reachable or legal to scrape; that's the
        # Acquisition Intelligence Engine's job on its next real run.
        _spec(
            id="african_markets_egx",
            name="African Markets -- EGX Listed Companies",
            category=SourceCategory.MARKET_DATA,
            access_method=AccessMethod.HTML_SCRAPE,
            status=SourceStatus.PLANNED,
            reliability_score=0.5,
            freshness_score=0.6,
            conflict_priority=35,
            notes="Third-party pan-African exchange directory listing EGX-listed companies; "
            "candidate company-directory hint source for company_ir, independent of egx_official. "
            "Standalone price/news collector not planned.",
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
            legal_use_status=LegalUseStatus.CLEARED,
            base_url="https://api.gdeltproject.org/api/v2/doc/doc",
            reliability_score=0.55,
            freshness_score=0.95,
            collector="GdeltDocCollector",
            collector_version="1.0.0",
            conflict_priority=35,
            historical_coverage="rolling global multilingual news window",
            expected_latency="minutes",
            update_frequency="continuous",
            # Widened from 5 req/min (12s) after a live historical-backfill run
            # (2026-07-29) evidenced GDELT returning HTTP 429 as early as the
            # second request at that pace, on two separate attempts -- a real,
            # observed server-side throttle, not a guess (see TD-41).
            rate_limit=RateLimit(requests_per_minute=2, min_seconds_between_requests=30.0),
            license="GDELT metadata; AGX stores headline/link metadata only, not article text.",
            terms_of_use_url="https://www.gdeltproject.org/about.html",
            supported_event_types=["news"],
            supported_languages=["en", "ar"],
            notes="Official free no-key DOC 2.0 JSON API, queried for Egypt/EGX coverage. "
            "Lower conflict priority than first-party and established direct publishers.",
        ),
        # ---- NEWS (English) -- each a config of rss_generic once feed URL verified ----
        _spec(
            id="alborsa",
            name="Al Borsa News",
            category=SourceCategory.ARABIC_NEWS,
            access_method=AccessMethod.RSS_FEED,
            status=SourceStatus.IMPLEMENTED,
            base_url="https://www.alborsaanews.com/feed",
            reliability_score=0.5,
            freshness_score=0.9,
            collector="RssNewsCollector",
            collector_version="1.0.0",
            conflict_priority=40,
            supported_event_types=["news"],
            supported_languages=["ar"],
            notes="Verified live on 2026-07-26: the publisher homepage advertises this "
            "RSS endpoint, a direct fetch returned application/rss+xml with real items, "
            "and robots.txt explicitly leaves collection allowed.",
        ),
        _spec(
            id="masrawy_economy",
            name="Masrawy Economy",
            category=SourceCategory.ARABIC_NEWS,
            access_method=AccessMethod.RSS_FEED,
            status=SourceStatus.IMPLEMENTED,
            base_url=("https://www.masrawy.com/rss/feed/206/%D8%A5%D9%82%D8%AA%D8%B5%D8%A7%D8%AF"),
            reliability_score=0.5,
            freshness_score=0.9,
            collector="RssNewsCollector",
            collector_version="1.0.0",
            conflict_priority=40,
            supported_event_types=["news"],
            supported_languages=["ar"],
            notes="Verified live on 2026-07-26: Masrawy's own RSS directory links this "
            "economy feed, a direct fetch returned parseable XML with dated real items, "
            "and its robots.txt does not disallow the endpoint.",
        ),
        *[
            _spec(
                id=source_id,
                name=name,
                category=SourceCategory.NEWS,
                access_method=AccessMethod.RSS_FEED,
                status=(
                    SourceStatus.DISABLED
                    if source_id == "investing_news"
                    else SourceStatus.PLANNED
                ),
                reliability_score=rel,
                freshness_score=0.9,
                collector="RssNewsCollector",
                conflict_priority=priority,
                supported_event_types=["news"],
                notes=(
                    "Not a paid-service block -- investing.com (the same domain this feed would "
                    "live on) returns 403 Forbidden site-wide, confirmed on a direct fetch and "
                    "reconfirmed by today's automated discovery run. Disabled alongside the "
                    "investing_com market-data entry rather than left as a separately-open "
                    "'planned' item on a domain already known to be unreachable."
                    if source_id == "investing_news"
                    else "Feed URL to be verified, then this becomes RssNewsCollector configuration."
                ),
            )
            for source_id, name, rel, priority in [
                ("reuters", "Reuters", 0.8, 70),
                ("zawya", "Zawya", 0.6, 50),
                ("asharq_business", "Asharq Business", 0.6, 50),
                ("cnbc_arabia", "CNBC Arabia", 0.6, 50),
                ("alarabiya_business", "Al Arabiya Business", 0.55, 45),
                ("marketscreener", "MarketScreener", 0.55, 40),
                ("investing_news", "Investing.com News", 0.5, 35),
            ]
        ],
        _spec(
            id="mubasher",
            name="Mubasher",
            category=SourceCategory.NEWS,
            access_method=AccessMethod.HTML_SCRAPE,
            status=SourceStatus.DISABLED,
            reliability_score=0.6,
            freshness_score=0.9,
            conflict_priority=55,
            supported_event_types=["news", "market"],
            integrated_via="egx_price_composite",
            integrated_capabilities=["price_data"],
            notes=(
                "Not a paid-service block -- robots.txt disallows both mubasher.info and "
                "www.mubasher.info outright, and a full anchor scan of the homepage found no "
                "download/historical/export link anyway (it is a news portal, not a "
                "price-data provider). Standalone news scraping is disabled rather than left "
                "'planned' with no legal path forward; the separate post-close price snapshot "
                "leg inside egx_price_composite (IMPLEMENTED) is unaffected."
            ),
        ),
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
                status=(
                    SourceStatus.IMPLEMENTED
                    if source_id == "undata"
                    else SourceStatus.DISABLED
                    if source_id in ("imf", "trading_economics")
                    else SourceStatus.PLANNED
                ),
                base_url=("https://unstats.un.org/SDGAPI/v1/sdg" if source_id == "undata" else ""),
                collector="UnSdgCollector" if source_id == "undata" else "",
                collector_version="1.0.0" if source_id == "undata" else "",
                license="UN public statistical data" if source_id == "undata" else "",
                terms_of_use_url=(
                    "https://unstats.un.org/SDGAPI/swagger/" if source_id == "undata" else ""
                ),
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
                    "Not a paid-service block -- IMF's real current public endpoint "
                    "(imf.org/external/datamapper/api/v1/{indicator}/EGY, free and keyless) "
                    "returned 403 Forbidden on every real indicator probed live, a WAF/bot-"
                    "detection block in the same class as CBE's. Disabled rather than left "
                    "'planned' with no real path forward.",
                ),
                ("oecd", "OECD", AccessMethod.JSON_API, "SDMX API free; Egypt coverage partial."),
                (
                    "undata",
                    "UN Statistics SDG API",
                    AccessMethod.JSON_API,
                    (
                        "Official no-key SDG API verified live for Egypt; aggregate series are "
                        "mapped explicitly by indicator and UN series code."
                    ),
                ),
                (
                    "trading_economics",
                    "Trading Economics",
                    AccessMethod.JSON_API,
                    "Real production use requires a paid subscription -- the free tier is too "
                    "limited to serve as a genuine data source, and this platform is scoped to "
                    "sources collectable with no paid service or key of any kind (same policy "
                    "that already removed FMP/AlphaVantage/Polygon/Tiingo). Live discovery also "
                    "confirms no candidate on the free tier clears legal review. Disabled, not "
                    "left as an open 'planned' item a free collector will eventually satisfy.",
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
                    SourceStatus.PLANNED,
                    "No official API; standalone collector not implemented.",
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
                    SourceStatus.PLANNED,
                    "Platform APIs require keys and restrict automation; per-platform review needed.",
                ),
                (
                    "public_telegram",
                    "Public Telegram channels",
                    AccessMethod.JSON_API,
                    SourceStatus.PLANNED,
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
                    SourceStatus.PLANNED,
                    "Standalone collector not implemented; prefer an available public feed/API.",
                ),
                (
                    "researchgate",
                    "ResearchGate",
                    AccessMethod.HTML_SCRAPE,
                    SourceStatus.PLANNED,
                    "Standalone collector not implemented; prefer an available public feed/API.",
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
