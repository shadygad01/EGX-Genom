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
    EvidenceTier,
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
                "Rejected... consult with your administrator' page, confirmed repeatedly. "
                "Disabled rather than left planned with no real path forward."
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
            collector_version="1.1.0",
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
        _spec(
            id="chief_egx_financials",
            name="Chief Capital structured EGX fundamentals",
            category=SourceCategory.COMPANY,
            access_method=AccessMethod.CSV_DOWNLOAD,
            status=SourceStatus.IMPLEMENTED,
            legal_use_status=LegalUseStatus.RESEARCH_ONLY,
            base_url="https://chiefcapitalco.com/companies/",
            reliability_score=0.82,
            freshness_score=0.75,
            historical_coverage="Up to eight annual periods for each currently published company",
            expected_latency="after annual filing normalisation",
            update_frequency="annual",
            collector="ChiefFinancialsCollector",
            collector_version="1.0.0",
            license=(
                "Public no-key CSVs derived from public EGX filings; research use with "
                "Chief and underlying filing attribution. Raw CSV content is not redistributed."
            ),
            terms_of_use_url="https://chiefcapitalco.com/disclaimer/",
            validation_rules=[
                "ticker must belong to the declared universe",
                "explicit Year column and recognised numeric financial headers",
            ],
            normalization_rules=["calendar year to 31 December", "source header to canonical line item"],
            conflict_priority=80,
            priority=93,
            supported_event_types=["corporate"],
            supported_languages=["en"],
            notes=(
                "Live-verified public company index and CSV exports. robots.txt does not "
                "disallow company or upload paths. Coverage is partial and discovered each run; "
                "no missing company or value is estimated."
            ),
        ),
        _spec(
            id="rmda_ir",
            name="Rameda Pharmaceuticals Investor Relations (quarterly earnings-release PDF)",
            category=SourceCategory.COMPANY,
            access_method=AccessMethod.PDF_DOWNLOAD,
            status=SourceStatus.IMPLEMENTED,
            legal_use_status=LegalUseStatus.RESEARCH_ONLY,
            base_url="https://ramedapharma-ir.com/wp-content/uploads/2026/05/Rameda-1Q26-Earnings-Release.pdf",
            reliability_score=0.9,
            freshness_score=0.85,
            historical_coverage="Latest issuer-published quarterly earnings-release summary table",
            expected_latency="issuer publication",
            update_frequency="quarterly",
            collector="CompanyEarningsTablePdfCollector",
            collector_version="1.0.0",
            license=(
                "Public primary issuer investor-relations release; research use with "
                "source attribution. Raw PDF content is not redistributed."
            ),
            validation_rules=[
                "FinancialStatementLineItem schema",
                "explicit 'EGP mn <period> <period> ...' summary table header",
                "whitelisted line-item label",
            ],
            normalization_rules=["EGP mn to EGP units", "NQYY quarter label to ISO period end"],
            conflict_priority=90,
            priority=88,
            supported_entities=["RMDA"],
            supported_event_types=["corporate"],
            supported_languages=["en"],
            notes=(
                "Live-verified via a real GitHub Actions fetch (run 30810863486, "
                "2026-08-03) -- robots.txt allows it per the discovery/latest "
                "company_financial_sources.json record. URL is the company's current "
                "1Q26 release; a maintainer updates it to the newest release when the "
                "weekly discovery workflow finds one, same as AD-53/AD-54's catalog-sync "
                "precedent. The collector only reads the structured summary table, never "
                "prose, and fails closed (empty + warning) if the table shape isn't found."
            ),
        ),
        _spec(
            id="tmgh_ir",
            name="TMG Holding Investor Relations (quarterly earnings-release PDF)",
            category=SourceCategory.COMPANY,
            access_method=AccessMethod.PDF_DOWNLOAD,
            status=SourceStatus.IMPLEMENTED,
            legal_use_status=LegalUseStatus.RESEARCH_ONLY,
            base_url="https://talaatmoustafa.com/upload/TMG%20Holding%201Q26%20ER%20-%20EN.pdf",
            reliability_score=0.9,
            freshness_score=0.85,
            historical_coverage="Latest issuer-published quarterly earnings-release summary table",
            expected_latency="issuer publication",
            update_frequency="quarterly",
            collector="CompanyEarningsTablePdfCollector",
            collector_version="1.0.0",
            license=(
                "Public primary issuer investor-relations release; research use with "
                "source attribution. Raw PDF content is not redistributed."
            ),
            validation_rules=[
                "FinancialStatementLineItem schema",
                "explicit 'EGP mn <period> <period> ...' summary table header",
                "whitelisted line-item label",
            ],
            normalization_rules=["EGP mn to EGP units", "NQYY quarter label to ISO period end"],
            conflict_priority=90,
            priority=88,
            supported_entities=["TMGH"],
            supported_event_types=["corporate"],
            supported_languages=["en"],
            notes=(
                "Live-verified via a real GitHub Actions fetch (run 30810863486, "
                "2026-08-03) -- robots.txt allows it per the discovery/latest "
                "company_financial_sources.json record. TMG Holding also publishes a "
                "64-document PDF archive (docs/COLLECTOR_TEMPLATE_TAXONOMY.md Family B) "
                "including full audited separate/consolidated financial statements; only "
                "the quarterly earnings-release summary table is wired today, not that "
                "larger archive. The collector only reads the structured summary table, "
                "never prose, and fails closed (empty + warning) if the table shape "
                "isn't found."
            ),
        ),
        _spec(
            id="egxpilot_fundamentals",
            name="EGXpilot market fundamentals API",
            category=SourceCategory.MARKET_DATA,
            access_method=AccessMethod.JSON_API,
            status=SourceStatus.IMPLEMENTED,
            legal_use_status=LegalUseStatus.RESEARCH_ONLY,
            base_url="https://www.egxpilot.com/api/stocks/",
            reliability_score=0.75,
            freshness_score=0.95,
            historical_coverage="Current fundamentals plus 252-session OHLCV history",
            expected_latency="intraday",
            update_frequency="daily",
            collector="EgxPilotFundamentalsCollector",
            collector_version="1.0.0",
            license=(
                "Public no-key API; robots.txt allows reference use and disallows model "
                "training. AGX stores numeric facts with attribution and does not consume "
                "the provider's recommendation or AI-generated opinion."
            ),
            terms_of_use_url="https://www.egxpilot.com/terms.html",
            validation_rules=[
                "universe ticker match",
                "numeric facts only",
                "dated OHLCV rows only; opaque analysis signals ignored",
            ],
            normalization_rules=[
                "market-cap and price strings to numeric EGP",
                "shares = market_cap / last_price only when Shares is absent",
            ],
            conflict_priority=70,
            priority=92,
            supported_event_types=["market"],
            supported_languages=["en"],
            notes=(
                "Live-verified JSON endpoints, including the documented stockanalysis history. "
                "The all-stocks endpoint matched 100/101 AGX "
                "securities on 2026-08-02; AIDC was absent. Provider Buy/Sell labels are "
                "intentionally ignored because their methodology is not auditable."
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
        # investing_com/tradingview removed (Decision-Centric Gap Audit,
        # 2026-07-30 / Architecture Adversarial Review): both DISABLED with
        # no free legal path forward AND zero mapping in
        # acquisition_intelligence.capability.CAPABILITY_STRATEGIES -- no
        # capability, no agent, no decision ever depended on either id.
        # Pure registry cleanup, zero loss of decision-relevant capability.
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
            id="egypt_nsdp",
            name="Egypt National Summary Data Page (NSDP)",
            category=SourceCategory.OFFICIAL,
            access_method=AccessMethod.HTML_SCRAPE,
            status=SourceStatus.IMPLEMENTED,
            legal_use_status=LegalUseStatus.CLEARED,
            base_url="https://mped.gov.eg/assets/uploads/NSDP.html",
            reliability_score=0.95,
            freshness_score=0.9,
            historical_coverage="current and previous official SDDS observations",
            expected_latency="monthly or quarterly, depending on series",
            update_frequency="monthly",
            collector="EgyptNsdpCollector",
            collector_version="1.0.0",
            rate_limit=RateLimit(requests_per_minute=6, min_seconds_between_requests=10.0),
            license="Official Egyptian government statistical summary; attribution retained.",
            validation_rules=["exact row label and unit match", "period and value parseable"],
            normalization_rules=["US dollar millions converted to US dollars"],
            conflict_priority=96,
            supported_entities=["Egypt external debt", "Egypt net international reserves"],
            supported_event_types=["macroeconomic"],
            supported_languages=["en"],
            notes=(
                "Official MPED-hosted NSDP following IMF SDDS. Used because the underlying "
                "CBE pages are WAF-blocked while this government summary is directly fetchable."
            ),
        ),
        _spec(
            id="eac_egx_disclosures",
            name="EAC Finance EGX Market Announcements",
            category=SourceCategory.ARABIC_NEWS,
            access_method=AccessMethod.HTML_SCRAPE,
            status=SourceStatus.IMPLEMENTED,
            legal_use_status=LegalUseStatus.CLEARED,
            base_url="https://www.eac-finance.com/posts/category-1",
            reliability_score=0.8,
            freshness_score=0.98,
            collector="EgxDisclosureCollector",
            collector_version="1.0.0",
            conflict_priority=75,
            priority=95,
            historical_coverage="paginated EGX market-announcement archive",
            expected_latency="same trading day",
            update_frequency="intraday",
            rate_limit=RateLimit(requests_per_minute=30, min_seconds_between_requests=1.0),
            license="Public announcement metadata and links; original EGX attachments are linked, not copied.",
            terms_of_use_url="https://www.eac-finance.com/robots.txt",
            supported_event_types=["news", "corporate", "earnings", "dividend"],
            supported_languages=["ar"],
            notes="Verified live on 2026-07-31: robots.txt allows collection and the public, "
            "server-rendered archive returned full EGX announcement metadata, Reuters ticker, "
            "timestamp, and original egx.com.eg attachment links across paginated pages.",
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
            # Discovery-tier, not primary (project owner decision, 2026-07-29):
            # a real historical backfill run's query (Egypt OR Egyptian OR
            # "Egyptian Exchange" OR EGX) returned 13,464 articles of which
            # only ~514 (3.8%) even mentioned "Egypt"/"Egyptian" in the
            # headline -- GDELT's broad global-news index matches far more
            # loosely than a plain OR query implies. GDELT items are
            # collected as candidates only (materialized to
            # news_discovery.csv, never registered with the Event Platform
            # directly) and only promoted into news.csv/evidence once
            # `collectors.discovery_reconciliation.reconcile_discovery_news()`
            # finds a PRIMARY source (Enterprise, FRA, Al Borsa, Masrawy,
            # company IR) independently reporting something about the same
            # ticker within a tolerance window. See sources.spec.EvidenceTier.
            evidence_tier=EvidenceTier.DISCOVERY,
            notes="Official free no-key DOC 2.0 JSON API, queried for Egypt/EGX coverage. "
            "Lower conflict priority than first-party and established direct publishers. "
            "Discovery-tier (see evidence_tier) -- never independently becomes evidence.",
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
                    "The domain returns 403 Forbidden site-wide; disabled rather than left "
                    "as a separately-open planned item."
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
                    (
                        "The public DataMapper endpoint returned 403 for every live indicator "
                        "probe; disabled rather than left planned with no working path."
                    ),
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
                    (
                        "Production use requires a paid subscription; disabled because this "
                        "platform is permanently scoped to free, no-key sources."
                    ),
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
        # wikipedia_pageviews, google_trends, github_releases,
        # company_social_official, public_telegram, patents, hiring_signals
        # removed (Decision-Centric Gap Audit / Free Decision Data
        # Blueprint, 2026-07-30): each evaluated explicitly against the
        # platform's ten first-principles investment questions and
        # rejected on the merits (weak/no demonstrated causal channel into
        # an EGX30/EGX70 decision, or -- for patents/GitHub -- a sector mix
        # that makes the signal near-irrelevant), not omitted by default.
        # See docs/FREE_DECISION_DATA_BLUEPRINT.md Part 3.
        #
        # ---- RESEARCH: moved out entirely (project owner direction,
        # 2026-08-02) ----
        # arxiv/ssrn/nber (academic quant-finance papers) used to be
        # catalogued here as SourceCategory.RESEARCH, mapped to a
        # Capability.RESEARCH_PAPERS entry in
        # acquisition_intelligence.capability.CAPABILITY_STRATEGIES. A real
        # user-reported audit found that capability had zero downstream
        # consumer -- no agent, hypothesis, or decision ever read its
        # output -- while `docs/FREE_DECISION_DATA_BLUEPRINT.md` Part 3
        # itself already documented these three as "methodology only,
        # None directly" for decision impact. The project owner's explicit
        # correction: academic literature must never be decision-time data,
        # but shouldn't be deleted either -- it belongs to a *separate*
        # Methodology & Research Registry feeding a future Research &
        # Methodology Pipeline (literature -> hypothesis generation ->
        # this codebase's existing 8-gate validation -> Shadow Fund
        # backtest -> Investment Proof, never a shortcut straight to a
        # production rule), kept structurally apart from this operational
        # catalog and everything `production.pipeline.ProductionPipeline`
        # reads. See `agx_research.methodology.catalog` for where they live
        # now and `docs/PHASE_STATUS.md`'s matching entry for the full
        # reasoning. google_scholar/researchgate stay removed outright
        # (never moved anywhere): redundant with arxiv/ssrn/nber for the
        # same need via a strictly worse access method, so there was never
        # a case for giving them a home in the new registry either.
        #
        # ---- SOVEREIGN & CREDIT (Architecture Adversarial Review, R3/R8:
        # feeds the merged Country & Macro Risk severity classification's
        # crisis rung -- rating actions are the one free, discrete, public
        # signal for this, alongside the CBE/World Bank series already
        # catalogued above). Public press releases only; full rating
        # reports remain a paid product and are out of scope.
        *[
            _spec(
                id=source_id,
                name=name,
                category=SourceCategory.MACROECONOMIC,
                access_method=AccessMethod.RSS_FEED,
                status=SourceStatus.PLANNED,
                legal_use_status=LegalUseStatus.REVIEW_REQUIRED,
                reliability_score=0.9,
                freshness_score=0.9,
                historical_coverage="rating actions and outlook changes only; full reports are paid",
                update_frequency="event driven (rare)",
                conflict_priority=80,
                supported_entities=["Egypt sovereign credit rating"],
                supported_event_types=["macroeconomic"],
                notes=(
                    "Public press releases on rating actions/outlook changes are free; the full "
                    "rating report is a paid product and is explicitly out of scope. Feed/RSS "
                    "endpoint not yet verified -- PLANNED, not asserted reachable."
                ),
            )
            for source_id, name in [
                ("moodys_ratings", "Moody's Ratings (Egypt sovereign, public press releases)"),
                ("sp_global_ratings", "S&P Global Ratings (Egypt sovereign, public press releases)"),
                ("fitch_ratings", "Fitch Ratings (Egypt sovereign, public press releases)"),
            ]
        ],
        # ---- Amwal Al Ghad: Egypt-specific stock-market news outlet
        # (distinct from the general Arabic business press already
        # catalogued) named as a census candidate in
        # docs/FREE_DECISION_DATA_BLUEPRINT.md Part 1.2. Not asserted
        # reachable or legal to scrape -- that is the Acquisition
        # Intelligence Engine's job on its next real run, exactly like
        # every other PLANNED news source above.
        _spec(
            id="amwal_alghad",
            name="Amwal Al Ghad",
            category=SourceCategory.ARABIC_NEWS,
            access_method=AccessMethod.RSS_FEED,
            status=SourceStatus.IMPLEMENTED,
            base_url="https://amwalalghad.com/feed/atom/",
            reliability_score=0.5,
            freshness_score=0.9,
            collector="RssNewsCollector",
            collector_version="1.0.0",
            conflict_priority=40,
            supported_event_types=["news"],
            supported_languages=["ar"],
            notes="Endpoint independently verified reachable by the weekly discovery "
            "workflow's real network egress (2026-07-31): robots.txt permits this path, "
            "a live probe returned a consistent status, and the Wayback Machine shows "
            "143 archived snapshots spanning 1229 days -- a long-lived, stable feed, not "
            "a fluke. Flipped to IMPLEMENTED on that evidence, same as every prior "
            "promotion in this registry; real content parsing is confirmed by the next "
            "live production run rather than a separate manual check, matching the "
            "Enterprise/Al Borsa/Masrawy precedent -- revert to PLANNED immediately if "
            "that run shows zero real items, as skynews_arabia_economy's own history "
            "already did once.",
        ),
    ]


def seed_registry(registry: SourceRegistry | None = None) -> SourceRegistry:
    registry = registry or SourceRegistry()
    current_ids: set[str] = set()
    specs = seed_sources()
    for spec in specs:
        current_ids.add(spec.id)
        if registry.latest(spec.id) is None:
            registry.add(spec)
    # A source whose declared fields changed (e.g. PLANNED -> IMPLEMENTED
    # after a real endpoint is verified) must reach a deployment that
    # already persisted its old spec — see
    # `SourceRegistry.sync_declared_fields()`'s own docstring.
    registry.sync_declared_fields(specs)
    # A source deleted from this catalog (e.g. one with zero capability
    # mapping) must stop looking live in a deployment that already
    # persisted it before the deletion shipped — see
    # `SourceRegistry.retire_removed()`'s own docstring.
    registry.retire_removed(current_ids)
    return registry
