"""Build the evidence artifacts for the one-off EGX price-source feasibility audit.

This is deliberately not a collector.  It contains the verified results of the
2026-07-26 investigation and expands them against the canonical universe CSVs.
No third-party price rows are downloaded or stored by this script.
"""

from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
UNIVERSE_DIR = ROOT / "research" / "data" / "universe"
OUTPUT_DIR = ROOT / "docs" / "evidence" / "egx-price-feasibility-2026-07-26"
AS_OF = "2026-07-26T12:00:00+03:00"
SAMPLE = ["ABUK", "COMI", "TMGH", "HRHO", "ETEL", "EAST", "SWDY", "EFIH", "MFPC", "ORWE"]

MATRIX_COLUMNS = [
    "Source", "Supports EGX", "Coverage %", "OHLC", "Volume",
    "Corporate Actions", "Historical Depth", "Daily Updates", "Intraday",
    "API", "Free", "Authentication", "Rate Limits", "ToS", "robots",
    "Automation Allowed", "Storage Allowed", "Investment Research Allowed",
    "Production Ready", "Confidence",
]


def row(
    source: str,
    *,
    supports: str,
    coverage: float | None,
    mode: str = "unknown",
    symbols: list[str] | None = None,
    tested: int = 0,
    ohlc: str = "Unknown",
    volume: str = "Unknown",
    adjusted: str = "Unknown",
    actions: str = "Unknown",
    splits: str = "Unknown",
    dividends: str = "Unknown",
    depth: str = "Unknown",
    daily: str = "Unknown",
    intraday: str = "Unknown",
    api: str = "No verified production API",
    free: str = "No",
    auth: str = "Unknown",
    limits: str = "Unknown",
    tos: str,
    robots: str,
    commercial: str,
    automation: str,
    storage: str,
    research: str,
    quality: str,
    reliability: str,
    production: str = "No",
    confidence: str = "High",
    basis: str,
    evidence: list[str],
    observed_indirect_count: int | None = None,
) -> dict[str, Any]:
    return {
        "source": source,
        "matrix": {
            "Source": source,
            "Supports EGX": supports,
            "Coverage %": coverage,
            "OHLC": ohlc,
            "Volume": volume,
            "Corporate Actions": actions,
            "Historical Depth": depth,
            "Daily Updates": daily,
            "Intraday": intraday,
            "API": api,
            "Free": free,
            "Authentication": auth,
            "Rate Limits": limits,
            "ToS": tos,
            "robots": robots,
            "Automation Allowed": automation,
            "Storage Allowed": storage,
            "Investment Research Allowed": research,
            "Production Ready": production,
            "Confidence": confidence,
        },
        "detail": {
            "adjusted_prices": adjusted,
            "splits": splits,
            "dividends": dividends,
            "commercial_restrictions": commercial,
            "data_quality": quality,
            "reliability": reliability,
            "verification_basis": basis,
            "evidence_urls": evidence,
        },
        "coverage_mode": mode,
        "symbols": symbols or [],
        "tested_count": tested,
        "observed_indirect_count": observed_indirect_count,
    }


KAGGLE_YAHOO_MISSING = [
    "EFIH", "GBCO", "RMDA", "VLMR", "VLMRA", "ACTF", "KRDI", "ARAB", "AIDC",
    "AIHC", "ASPI", "CNFN", "GPIM", "ISMQ", "MCRO", "MASR", "OFH", "TALM",
    "TANM", "TAQA", "VALU",
]

YAHOO_LIVE_MISSING = [
    "VLMR", "VLMRA", "ACTF", "KRDI", "AIDC", "AIHC", "GPIM", "TANM", "TAQA", "VALU",
]

KAGGLE_EGX30_MATCH = [
    "ABUK", "ADIB", "AMOC", "BTFH", "COMI", "EAST", "EFID", "HRHO", "EFIH",
    "EGCH", "EMFD", "FWRY", "GBCO", "HELI", "ISPH", "JUFO", "ORAS", "ORHD",
    "OIH", "ORWE", "PHDC", "CCAP", "TMGH", "ETEL", "ALCN", "CIEB", "EGTS",
    "SWDY", "MFPC", "SKPC", "OCDI",
]


SOURCES = [
    row(
        "TradingView", supports="Yes (display product)", coverage=None, tested=10,
        ohlc="Yes on charts", volume="Yes", adjusted="Undocumented for export",
        actions="Chart events", depth="Visible interactively; export entitlement dependent",
        daily="Yes", intraday="Yes", api="No public data API",
        free="Display access only", auth="Optional for pages", limits="Not an API",
        tos="Display-only; automated collection, non-display use, and algorithmic decision use prohibited",
        robots="Not relied on; contract already blocks intended use",
        commercial="Requires an authorized data arrangement",
        automation="No", storage="No", research="No for automated model ingestion",
        quality="Professional chart display; no authorized raw feed for AGX",
        reliability="High as a human cross-check, unusable as a pipeline dependency",
        basis="Ten requested symbols are visually discoverable, but bulk retrieval was stopped by explicit policy.",
        evidence=["https://www.tradingview.com/policies/", "https://www.tradingview.com/symbols/EGX-EGX30/components/"],
    ),
    row(
        "Yahoo Finance / yfinance", supports="Yes, incomplete", coverage=90.1,
        mode="all_except", symbols=YAHOO_LIVE_MISSING, tested=101,
        observed_indirect_count=91, ohlc="Yes", volume="Yes", adjusted="Yes",
        actions="Dividends and splits", splits="Yes", dividends="Yes",
        depth="Multi-year where symbols exist", daily="Historically yes", intraday="Unofficial",
        api="No supported public Finance price API for yfinance", free="Consumer display only",
        auth="Unofficial endpoints vary", limits="Undocumented/unstable",
        tos="Automated access/collection without prior permission and database/archive creation prohibited",
        robots="Not used because ToS is dispositive",
        commercial="No permission established for AGX",
        automation="No", storage="No", research="No permission for this system",
        quality="91/101 live symbols returned complete OHLCV rows; coverage and adjustments can drift",
        reliability="Unofficial endpoints can change without notice",
        basis="After the user changed the goal to technical feasibility, the chart endpoint was live-probed for all 101 .CA symbols: 91 returned OHLCV, including all ten priority samples; ten returned 404.",
        evidence=["https://legal.yahoo.com/xw/en/yahoo/terms/otos/index.html", "https://www.kaggle.com/datasets/mahmoudalrefaey/egx-egyptian-stocks-2021-2026"],
    ),
    row(
        "Alpha Vantage", supports="Unverified", coverage=None, tested=0,
        ohlc="Global daily endpoint claims OHLCV", volume="Yes", adjusted="Premium",
        actions="Adjusted endpoint premium", splits="Premium", dividends="Premium",
        depth="20+ years claimed; free output compact only", daily="Yes if symbol supported",
        intraday="Plan dependent", api="Official REST API", free="Limited personal tier",
        auth="API key required", limits="Free limits apply; full history premium",
        tos="Free service is personal; broader investment analysis/research is commercial use",
        robots="API documentation allowed; no key was provisioned",
        commercial="Commercial permission/plan required",
        automation="Technically yes with key; not under free AGX terms", storage="Not established",
        research="No on the free personal license", quality="Cannot assess EGX without an authorized key",
        reliability="Established provider, EGX coverage unverified",
        basis="Documentation and terms checked; no configured key and no proof of the 101 symbols.",
        evidence=["https://www.alphavantage.co/documentation/", "https://www.alphavantage.co/terms_of_service/"],
    ),
    row(
        "Financial Modeling Prep (FMP)", supports="Unverified", coverage=None,
        ohlc="If symbol supported", volume="If symbol supported", actions="Endpoints exist",
        depth="Plan dependent", daily="Yes if covered", intraday="Plan dependent",
        api="Official REST API", free="Personal license only", auth="API key required",
        limits="Plan dependent", tos="Personal license excludes business/system integration and commercial analysis",
        robots="API docs reviewed; no key configured", commercial="Commercial agreement required",
        automation="Not for AGX under free license", storage="Not established",
        research="No for AGX production", quality="EGX coverage could not be verified",
        reliability="Established API; unsupported claim for this universe",
        basis="Docs and terms checked; no public symbol catalogue proving EGX and no authorized key.",
        evidence=["https://site.financialmodelingprep.com/developer/docs/stable", "https://site.financialmodelingprep.com/developer/docs/terms-of-service"],
    ),
    row(
        "Twelve Data", supports="Yes", coverage=100.0, mode="all", tested=101,
        ohlc="Yes", volume="Yes", adjusted="Plan/endpoint dependent", actions="Available by plan",
        splits="Available by plan", dividends="Available by plan", depth="Plan dependent",
        daily="Yes", intraday="Yes", api="Official REST/WebSocket API", free="No for XCAI",
        auth="API key required", limits="Credit based; plan dependent",
        tos="Personal/commercial licensing depends on plan and use",
        robots="Public metadata endpoint permitted and returned 262 XCAI instruments",
        commercial="Commercial terms required where applicable", automation="Yes on paid licensed plan",
        storage="Plan/license dependent", research="Yes on suitable paid plan",
        quality="101/101 matched by ISIN in live exchange metadata",
        reliability="Strong documented API, but the minimum XCAI access is paid",
        basis="Live stocks metadata query for exchange XCAI returned all 101 securities by ISIN. Free Basic excludes XCAI; Pro is the minimum individual plan.",
        evidence=["https://twelvedata.com/exchanges", "https://twelvedata.com/pricing", "https://api.twelvedata.com/stocks?exchange=XCAI&format=JSON"],
    ),
    row(
        "Finnhub", supports="No under published international scope", coverage=0.0, mode="none", tested=101,
        ohlc="Premium candles for covered markets", volume="Yes if covered", actions="Plan dependent",
        depth="Plan dependent", daily="No EGX product", intraday="No EGX product",
        api="Official REST/WebSocket", free="No EGX", auth="Token required", limits="Plan dependent",
        tos="Licensed use by subscription", robots="Docs/pricing reviewed",
        commercial="International market product is paid and EGX is not listed",
        automation="No EGX capability", storage="N/A", research="No EGX capability",
        quality="No EGX coverage to assess", reliability="Published market list excludes Egypt",
        basis="All 101 ruled out by the provider's published international exchange scope, not by ticker collisions.",
        evidence=["https://finnhub.io/pricing-stock-api-market-data", "https://finnhub.io/docs/api/stock-candles"],
    ),
    row(
        "MarketStack", supports="No retrievable XCAI EOD", coverage=0.0, mode="none", tested=101,
        ohlc="Yes for supported EOD tickers", volume="Yes", actions="Splits/dividends on plan",
        splits="Yes", dividends="Yes", depth="Free: one year", daily="Yes for supported markets",
        intraday="Paid", api="Official REST API", free="100 requests/month; non-commercial",
        auth="API key for data", limits="100 requests/month free; each ticker consumes a request",
        tos="Commercial use appears only on paid tiers", robots="Allows public site; API terms govern API",
        commercial="Not on free tier", automation="API automation exists but no actual EGX EOD was found",
        storage="License dependent", research="Personal only on free tier",
        quality="Public catalogue has Egyptian-name records mislabeled IEXG with has_eod=false; ticker collisions must not count",
        reliability="Official API, but its current catalogue does not expose XCAI data",
        basis="The official site's public search backend was checked for all 101 tickers: XCAI total was zero; 71 Egyptian-name records had no EOD and 18 EOD hits were US ticker collisions.",
        evidence=["https://marketstack.com/pricing/", "https://marketstack.com/documentation", "https://marketstack.com/stock_api.php?offset=0&exchange=XCAI&search="],
    ),
    row(
        "EOD Historical Data (EODHD)", supports="Yes, incomplete", coverage=98.02,
        mode="all_except", symbols=["AIHC", "VLMR"], tested=101,
        ohlc="Yes", volume="Yes", adjusted="Adjusted close", actions="Dividends and splits",
        splits="Yes", dividends="Yes", depth="Long history by instrument", daily="Yes",
        intraday="Separate paid product", api="Official REST API", free="No for EGX",
        auth="API token required", limits="Plan dependent",
        tos="Private analysis/storage limits; redistribution/display restricted; retention obligation after cancellation",
        robots="robots.txt disallows /api/; only public exchange catalogue pages were probed",
        commercial="Commercial approval/license required", automation="Yes only under paid licensed API",
        storage="Private storage subject to terms", research="Yes under suitable paid terms",
        quality="99/101 exact current tickers found; VLMRA exists while VLMR and AIHC were absent",
        reliability="Mature API and broad coverage, but not complete or free",
        basis="All 239 public EGX catalogue entries across three pages were compared with the universe. API probing stopped after robots/403; EGX EOD is a paid package.",
        evidence=["https://eodhd.com/exchange/EGX", "https://eodhd.com/financial-apis/quick-start-with-our-financial-data-apis", "https://eodhd.com/financial-apis/terms-conditions", "https://eodhd.com/robots.txt"],
    ),
    row(
        "Tiingo", supports="No", coverage=0.0, mode="none", tested=101,
        ohlc="Yes for covered tickers", volume="Yes", adjusted="Yes",
        actions="Dividends and splits", splits="Yes", dividends="Yes",
        depth="Long EOD history for covered exchanges", daily="Yes", intraday="Separate products",
        api="Official REST API", free="Account tier exists but no EGX", auth="Token required",
        limits="Plan dependent", tos="Licensed API use", robots="Official downloadable supported-ticker file used",
        commercial="Plan/license dependent", automation="Yes for covered markets", storage="License dependent",
        research="Yes under applicable plan, but no EGX data", quality="No Egypt/EGP/EGX records",
        reliability="Supported-ticker catalogue is machine-readable and authoritative",
        basis="Downloaded the official supported_tickers.zip (107,641 rows): zero of 101 symbols had actual Egypt/EGP/EGX coverage.",
        evidence=["https://www.tiingo.com/documentation/end-of-day", "https://apimedia.tiingo.com/docs/tiingo/daily/supported_tickers.zip"],
    ),
    row(
        "Polygon / Massive", supports="No", coverage=0.0, mode="none", tested=101,
        ohlc="US stocks only", volume="US stocks only", actions="US products",
        depth="Free US plan: two years", daily="US only", intraday="US only",
        api="Official REST/WebSocket", free="Free US tier", auth="API key required",
        limits="Free US tier: 5 calls/minute", tos="Licensed US data use", robots="Official docs reviewed",
        commercial="Plan dependent", automation="No EGX capability", storage="N/A for EGX",
        research="No EGX capability", quality="N/A", reliability="Clear official US-only scope",
        basis="All 101 ruled out by official stock product scope: United States equities only.",
        evidence=["https://polygon.io/docs/rest/stocks/overview", "https://polygon.io/stocks"],
    ),
    row(
        "Stooq", supports="No verified EGX coverage", coverage=None, tested=0,
        ohlc="Yes for supported markets", volume="Often", actions="Unclear",
        depth="Varies", daily="Yes for supported markets", intraday="Limited",
        api="Unofficial CSV endpoints", free="Public website", auth="None", limits="Undocumented",
        tos="No production license established", robots="User-agent * disallows all paths",
        commercial="Not established", automation="No", storage="Not established",
        research="Not established", quality="Could not legally test data paths",
        reliability="No documented EGX symbol catalogue or supported API contract",
        basis="robots.txt explicitly disallows all generic crawlers; search/docs produced no Egypt coverage evidence, so no data request was made.",
        evidence=["https://stooq.com/robots.txt"],
    ),
    row(
        "Investing.com", supports="Yes on human-facing pages", coverage=None, tested=10,
        ohlc="Yes", volume="Yes", adjusted="Unclear", actions="Separate pages",
        depth="Often multi-year", daily="Yes", intraday="Display product",
        api="No public price API", free="Display only", auth="Optional", limits="N/A",
        tos="Automated extraction, storage, reproduction, and commercial exploitation prohibited without permission",
        robots="Not relied on because ToS blocks intended use", commercial="Written permission required",
        automation="No", storage="No", research="No automated model ingestion permission",
        quality="Human-readable history; symbol mappings can be opaque",
        reliability="Website/WAF and markup are not a data contract",
        basis="Requested samples are discoverable on historical pages; bulk extraction was stopped by explicit terms.",
        evidence=["https://www.investing.com/about-us/terms-and-conditions"],
    ),
    row(
        "MarketScreener", supports="At least sample coverage", coverage=None, tested=1,
        ohlc="Yes on history pages", volume="Yes", adjusted="Unclear", actions="Displayed separately",
        depth="COMI page shows long history", daily="Yes", intraday="Display only",
        api="No free public API found", free="Human display", auth="None for some pages", limits="N/A",
        tos="No permission established for automated AGX ingestion", robots="Direct requests/robots returned 403",
        commercial="No free commercial grant found", automation="No", storage="Not established",
        research="Not established", quality="COMI was visible through indexed page evidence",
        reliability="WAF blocks automation and there is no API contract",
        basis="COMI history page was verified; further automated tests stopped after access controls returned 403.",
        evidence=["https://www.marketscreener.com/quote/stock/COMMERCIAL-INTERNATIONAL--6491751/quotes/"],
    ),
    row(
        "Barchart", supports="Unverified", coverage=None,
        ohlc="Official API supports OHLC", volume="Yes", actions="Optional splits/dividends",
        depth="Product dependent", daily="Yes if covered", intraday="Yes if covered",
        api="Official OnDemand API", free="No production access; contact required", auth="API key",
        limits="Contract dependent", tos="Personal/non-commercial website use; robots/data mining prohibited",
        robots="Terms prohibit extraction", commercial="License required", automation="Only via contracted API",
        storage="Contract dependent", research="No free production permission",
        quality="EGX not proven", reliability="Professional provider, no verified EGX/free offering",
        basis="API schema and terms verified; no public catalogue or free credentials proving any of the 101.",
        evidence=["https://www.barchart.com/ondemand/api/getHistory", "https://www.barchart.com/terms"],
    ),
    row(
        "Google Dataset Search", supports="Discovery only", coverage=None,
        ohlc="N/A", volume="N/A", actions="N/A", depth="N/A", daily="No",
        intraday="No", api="Search/discovery, not a price feed", free="Yes", auth="No",
        limits="Search service limits", tos="Underlying dataset terms control use",
        robots="Not a data source", commercial="Depends on discovered dataset",
        automation="No price collection capability", storage="Depends on dataset",
        research="Depends on dataset", quality="Metadata only", reliability="Cannot fill any price row itself",
        basis="Used to discover datasets; each discovered dataset was assessed separately.",
        evidence=["https://datasetsearch.research.google.com/"],
    ),
    row(
        "Kaggle: EGX Egyptian Stocks 2021-2026", supports="Static partial snapshot", coverage=79.21,
        mode="all_except", symbols=KAGGLE_YAHOO_MISSING, tested=101,
        ohlc="Yes", volume="Yes", adjusted="Values appear adjusted by yfinance",
        actions="Dividends and stock splits", splits="Yes", dividends="Yes",
        depth="2021-01-03 to 2026-02-04 in verified ABUK file", daily="No; stale snapshot",
        intraday="No", api="Kaggle download API", free="Yes", auth="Public download worked",
        limits="Kaggle platform limits", tos="Dataset page says CC0, README also says all rights reserved/educational; upstream is Yahoo/yfinance",
        robots="Public Kaggle dataset API used", commercial="Uploader cannot clearly relicense upstream Yahoo data",
        automation="Downloadable, but provenance prevents production ingestion", storage="Legally unresolved",
        research="Educational statement only; AGX production permission unresolved",
        quality="80/101 files; stale; float adjusted values and corporate-action columns",
        reliability="Static community upload with conflicting rights statements",
        basis="Zip was downloaded and every CSV filename compared to the 101 securities; ABUK header and date bounds were inspected.",
        evidence=["https://www.kaggle.com/datasets/mahmoudalrefaey/egx-egyptian-stocks-2021-2026", "https://legal.yahoo.com/xw/en/yahoo/terms/otos/index.html"],
    ),
    row(
        "Kaggle: Egyptian Stock Exchange-EGX30", supports="Static partial snapshot", coverage=30.69,
        mode="set", symbols=KAGGLE_EGX30_MATCH, tested=101,
        ohlc="Yes (Price/Open/High/Low)", volume="Yes, formatted strings", adjusted="No evidence",
        actions="No", splits="No", dividends="No", depth="2019-01-02 to 2023-08-09 in verified ABUK file",
        daily="No; stale", intraday="No", api="Kaggle download API", free="Yes",
        auth="Public download worked", limits="Kaggle platform limits",
        tos="CC0 label does not prove rights to underlying market data",
        robots="Public Kaggle dataset API used", commercial="Provenance/license chain unresolved",
        automation="Snapshot download works; production use is not cleared", storage="Legally unresolved",
        research="Not production-cleared", quality="31/101 current symbols; volume needs parsing; stale",
        reliability="Community snapshot, not an updating feed",
        basis="Downloaded 40 stock files and matched 31 current securities; inspected ABUK schema/date range.",
        evidence=["https://www.kaggle.com/datasets/noureldinomran/egyptian-stock-exchange-egx30"],
    ),
    row(
        "GitHub public datasets", supports="Small static subsets", coverage=13.86,
        mode="unknown", tested=101, observed_indirect_count=14,
        ohlc="Repository dependent", volume="Repository dependent", actions="Repository dependent",
        depth="Best found repository claims 2018-2026", daily="No guaranteed feed", intraday="No",
        api="Git hosting, not market-data API", free="Yes to download repositories", auth="Usually none",
        limits="GitHub limits", tos="Repository license does not override upstream data rights",
        robots="GitHub search/API respected", commercial="Best candidate sources Yahoo/yfinance and lacks a clear data license",
        automation="Not a production-cleared source", storage="Unresolved for upstream data",
        research="Not production-cleared", quality="Best verified candidate contains only 14 EGX files",
        reliability="Community code/data can disappear or go stale",
        basis="GitHub search found no complete licensed dataset; the best candidate, adhamkhaled787/Ishaara, has 14 EGX files and cites Yahoo/yfinance.",
        evidence=["https://github.com/adhamkhaled787/Ishaara", "https://docs.github.com/en/site-policy/github-terms/github-terms-of-service"],
    ),
    row(
        "Official EGX website downloads", supports="Constituents/current publications, not a verified history feed", coverage=None, tested=0,
        ohlc="Some daily publications may show fields", volume="Some publications", actions="Official notices",
        depth="No machine-readable historical series verified", daily="Publications exist", intraday="No public API verified",
        api="No authorized public historical OHLCV API found", free="Public pages/documents",
        auth="None for some pages", limits="WAF rejects automated requests",
        tos="No affirmative bulk automation/storage license found", robots="WAF blocks/rejects programmatic retrieval",
        commercial="Official data distribution is assigned to EGID", automation="No verified permission/channel",
        storage="No bulk historical license found", research="Public documents can be read; database ingestion not cleared",
        quality="Authoritative for constituents and notices, not a normalized price history",
        reliability="Pages and PDF identifiers are not a stable feed contract",
        basis="Official constituent pages are usable for the universe. Searches and direct requests found no complete machine-readable historical OHLCV export; PDF endpoints returned request-rejected responses.",
        evidence=["https://www.egx.com.eg/en/CurrentIndexConstituntes.aspx?Nav=1&type=1", "https://egx.com.eg/en/currentindexconstituntes.aspx?nav=16&type=16", "https://www.egidegypt.com/"],
    ),
    row(
        "EGID official market-data feed", supports="Yes", coverage=100.0, mode="all", tested=0,
        ohlc="Expected in licensed products; exact schema requires quote", volume="Expected",
        actions="Product/contract dependent", depth="Contract dependent", daily="Yes", intraday="Yes/live feed",
        api="Licensed feed; contact/ticket", free="No free offer published", auth="Contracted access",
        limits="Contract dependent", tos="EGID market-data policy/contract required",
        robots="Public corporate site reviewed", commercial="Licensed market-data distribution",
        automation="Yes after contract", storage="Contract dependent", research="Yes after suitable contract",
        quality="Authoritative exchange-owned provider", reliability="Highest authority; commercial onboarding required",
        basis="EGID states it is wholly owned by EGX, the sole authorized EGX market-data provider, and supplies live feeds to financial market participants. Coverage is institutional/market-wide, not a free tested endpoint.",
        evidence=["https://www.egidegypt.com/", "https://www.egidegypt.com/who-we-are.html"],
    ),
    row(
        "Company Investor Relations sites", supports="Fragmentary", coverage=None, tested=6,
        ohlc="Usually no; some current quote widgets", volume="Rare", actions="Notices/dividends often available",
        depth="Inconsistent", daily="Not standardized", intraday="No standardized feed",
        api="No common API", free="Pages are public", auth="Usually none", limits="Per-site",
        tos="Each issuer has separate terms and upstream widget licenses", robots="Per-site",
        commercial="No common permission", automation="No scalable common permission", storage="Per-site/unresolved",
        research="Public filings yes; price database no", quality="Authoritative filings but inconsistent price widgets",
        reliability="100 separate integrations and dependencies would be brittle",
        basis="Sampled HRHO, EFIH, EAST, SWDY, TMGH and ABUK IR surfaces: current quotes, charts, annual reports, or links to Mubasher; no standardized daily OHLCV history.",
        evidence=["https://www.efghldg.com/en/investor-relations", "https://ir.efinanceinvestment.com/", "https://www.elsewedyelectric.com/en/investor-relations/"],
    ),
    row(
        "Mubasher", supports="Broad current EGX display", coverage=None, tested=10,
        ohlc="Current session fields", volume="Yes current", actions="Yes", depth="No public normalized history verified",
        daily="Current/delayed pages", intraday="15-minute delayed display", api="Public /api and /services paths disallowed",
        free="Personal display", auth="Optional", limits="robots crawl-delay 5",
        tos="Downloads are personal-use only; commercial use requires written permission",
        robots="Disallows /api/, /services/, and chart assets", commercial="Written permit required",
        automation="No", storage="No production grant", research="No automated production grant",
        quality="Strong local display and actions, but not a historical data contract",
        reliability="Stable news/market portal; unusable as automated raw feed",
        basis="All requested samples were searched on public pages; terms and robots prevent expansion into a collector and no public historical OHLCV API was found.",
        evidence=["https://english.mubasher.info/s/Terms", "https://english.mubasher.info/robots.txt"],
    ),
    row(
        "Zawya", supports="No verified price history", coverage=None, tested=0,
        ohlc="No verified company history feed", volume="No", actions="News only", depth="N/A",
        daily="News", intraday="No", api="No public EGX OHLCV API", free="Article display",
        auth="Some content gated", limits="N/A", tos="No data-ingestion grant found",
        robots="Blocked by robots during investigation", commercial="No free commercial price-data grant",
        automation="No", storage="No", research="News may be licensed separately; not price data",
        quality="Not a candidate for price bars", reliability="N/A",
        basis="Search surfaced news/company articles, not a daily OHLCV dataset; automated access was robots-blocked.",
        evidence=["https://www.zawya.com/robots.txt"],
    ),
    row(
        "Trading Economics", supports="No free accessible EGX stock API", coverage=0.0, mode="none", tested=10,
        ohlc="Historical endpoint exists on subscription", volume="Product dependent", actions="No evidence",
        depth="Subscription dependent", daily="Paid API", intraday="Paid API",
        api="Official REST API", free="No; guest account discontinued", auth="Subscription key",
        limits="Plan dependent", tos="Licensed subscription", robots="Official API requests used",
        commercial="Paid plan/license", automation="No free access", storage="Plan dependent",
        research="Paid plan dependent", quality="Could not inspect data because guest returned 410",
        reliability="Established macro API; no free path",
        basis="Country-stock and COMI-history guest API calls both returned HTTP 410: guest account discontinued; pricing starts with a paid trial/plan.",
        evidence=["https://api.tradingeconomics.com/markets/stocks/country/egypt?c=guest:guest", "https://tradingeconomics.com/api/pricing.aspx"],
    ),
    row(
        "StockAnalysis.com", supports="Yes, incomplete display", coverage=98.02,
        mode="all_except", symbols=["IEEC", "ICFC"], tested=101,
        ohlc="Yes", volume="Yes", adjusted="Adjusted for splits", actions="Limited",
        splits="History adjusted for splits", dividends="Separate dividend pages", depth="Public history view limited to six months/three pages",
        daily="Yes", intraday="No public API", api="No public API; data licensed for display only",
        free="Human display", auth="None", limits="N/A",
        tos="Underlying S&P Global data is licensed for display, not programmatic redistribution/resale",
        robots="Allows public pages, but robots permission is not a data license",
        commercial="No programmatic redistribution right", automation="No", storage="No production grant",
        research="No automated ingestion grant", quality="99/101 current history pages with embedded OHLCV; source identifies S&P Global",
        reliability="Good human cross-check; no API and limited visible depth",
        basis="Checked all 101 history URLs plus a .CA fallback without retaining price rows: 99 returned embedded OHLCV schema. ACTF resolves as ACTF.CA; only IEEC and ICFC were absent.",
        evidence=["https://stockanalysis.com/quote/egx/ABUK/history/", "https://stockanalysis.com/help/faq/api-access/", "https://stockanalysis.com/terms-of-use/"],
    ),
    row(
        "African Markets", supports="Likely broad display", coverage=None, tested=1,
        ohlc="Historical download advertised", volume="Likely", actions="Company pages", depth="Unknown",
        daily="Yes display", intraday="No verified API", api="No licensed public API found",
        free="Personal page access", auth="Varies", limits="N/A",
        tos="Personal non-commercial copy only; robots/spiders/data mining/extraction prohibited",
        robots="Public pages allowed but /app/ disallowed; download workflow appears application-backed",
        commercial="Prohibited without agreement", automation="No", storage="Personal copy only",
        research="No AGX production permission", quality="Not bulk-tested after explicit prohibition",
        reliability="Cloudflare/application dependency; no data contract",
        basis="An EGX company page and download claim were verified; terms prohibited the requested automated expansion.",
        evidence=["https://www.african-markets.com/en/terms-conditions", "https://www.african-markets.com/robots.txt"],
    ),
    row(
        "EGXAPI.com", supports="Claims yes; service not operational", coverage=0.0, mode="none", tested=10,
        ohlc="Claimed only", volume="Claimed only", actions="Not documented", depth="Claims full history",
        daily="Claimed", intraday="Claimed real-time", api="Published endpoints return 404",
        free="Claimed free forever", auth="Claims API key; sign-in unavailable", limits="Claims 3,000/min",
        tos="Legal center explicitly says design draft and placeholder text awaiting counsel",
        robots="Allows ordinary crawling; AI-use signals separate", commercial="No operative license exists",
        automation="No working endpoint", storage="No legal grant", research="No legal grant",
        quality="No data could be retrieved", reliability="Concept/mock site, not a production provider",
        basis="Documented /v2/account and market-data routes returned 404; npm SDK was absent; auth says Google sign-in unavailable; domain registered 2026-05-30; hub calls itself a design system and legal terms are placeholders.",
        evidence=["https://egxapi.com/docs/", "https://egxapi.com/legal/", "https://egxapi.com/hub/", "https://rdap.verisign.com/com/v1/domain/egxapi.com"],
    ),
    row(
        "Microsoft Excel STOCKHISTORY", supports="No (Egypt absent)", coverage=0.0, mode="none", tested=101,
        ohlc="Yes for supported exchanges", volume="Yes", adjusted="Provider dependent",
        actions="No direct action feed", depth="Function dependent", daily="Yes for supported exchanges",
        intraday="No", api="Excel function, not an ingestion API", free="No; Microsoft 365/product license",
        auth="Microsoft product/account", limits="Product limits",
        tos="LSEG/Refinitiv content cannot be copied, republished, redistributed or cached without consent",
        robots="Official support documentation reviewed", commercial="Explicitly not for financial industry/professional investment or research use",
        automation="No", storage="No", research="No",
        quality="Egypt/XCAI is absent from official supported-exchange table",
        reliability="Supported product feature but categorically outside AGX use",
        basis="Official supported-exchange list excludes Egypt, and the stated usage restrictions independently prohibit AGX's professional investment-research use.",
        evidence=["https://support.microsoft.com/en-US/Excel/about-the-stocks-financial-data-sources"],
    ),
]


def load_universe() -> list[dict[str, str]]:
    records: list[dict[str, str]] = []
    for index_name in ("EGX30", "EGX70"):
        with (UNIVERSE_DIR / f"{index_name}.csv").open(encoding="utf-8", newline="") as handle:
            for item in csv.DictReader(handle):
                records.append({**item, "index": index_name})
    return records


def ticker_result(source: dict[str, Any], ticker: str) -> dict[str, Any]:
    mode = source["coverage_mode"]
    selected = ticker in source["symbols"]
    if mode == "all":
        supported: bool | None = True
    elif mode == "none":
        supported = False
    elif mode == "set":
        supported = selected
    elif mode == "all_except":
        supported = not selected
    else:
        supported = None

    if supported is True:
        reason = "Verified present under the source-level test basis; legal suitability is evaluated separately."
    elif supported is False:
        reason = "Verified absent/unavailable under the source-level test basis."
    else:
        reason = "Not live-tested: coverage is unknown or bulk probing was prohibited/unavailable."
    return {"ticker": ticker, "supported": supported, "missing": None if supported is None else not supported, "reason": reason}


def main() -> None:
    universe = load_universe()
    tickers = [item["ticker"] for item in universe]
    issuer_keys = {"VALMORE" if ticker in {"VLMR", "VLMRA"} else ticker for ticker in tickers}

    assert len(tickers) == 101
    assert len(set(tickers)) == 101
    assert len(issuer_keys) == 100
    assert set(SAMPLE).issubset(tickers)
    assert len(SOURCES) == 28

    matrix = [source["matrix"] for source in SOURCES]
    assert all(list(item) == MATRIX_COLUMNS for item in matrix)

    coverage_sources = []
    for source in SOURCES:
        results = [ticker_result(source, ticker) for ticker in tickers]
        supported_count = sum(result["supported"] is True for result in results)
        missing_count = sum(result["missing"] is True for result in results)
        if source["coverage_mode"] == "unknown":
            supported_count_value: int | None = None
            missing_count_value: int | None = None
        else:
            supported_count_value = supported_count
            missing_count_value = missing_count
        coverage_sources.append({
            "source": source["source"],
            "requested_security_count": len(tickers),
            "requested_company_count": len(issuer_keys),
            "tested_count": source["tested_count"],
            "supported_count": supported_count_value,
            "missing_count": missing_count_value,
            "coverage_percent": source["matrix"]["Coverage %"],
            "observed_indirect_count": source["observed_indirect_count"],
            "verification_basis": source["detail"]["verification_basis"],
            "ticker_results": results,
        })

    coverage_report = {
        "schema_version": "1.0.0",
        "generated_at": AS_OF,
        "mission": "Free, legal, complete historical and daily EGX30+EGX70 OHLCV feasibility",
        "verdict": "A_technical_B_licensed",
        "verdict_text": "A free technical path retrieves historical OHLCV for 101/101 securities; current completed-session coverage uses StockAnalysis (99), Yahoo for IEEC, and Mubasher for ICFC. No complete free licensed path was verified.",
        "universe": {
            "company_count": len(issuer_keys),
            "security_ticker_count": len(tickers),
            "egx30_security_rows": sum(item["index"] == "EGX30" for item in universe),
            "egx70_security_rows": sum(item["index"] == "EGX70" for item in universe),
            "dual_security_issuer": {"issuer": "Valmore Holding", "tickers": ["VLMR", "VLMRA"]},
            "source_files": ["research/data/universe/EGX30.csv", "research/data/universe/EGX70.csv"],
        },
        "sample_tickers": SAMPLE,
        "methodology": {
            "coverage_denominator": "101 security ticker rows representing 100 companies",
            "unknown_semantics": "null means not proven, never zero; legal blocks stopped bulk extraction",
            "legal_rule": "robots permission is not a license; uploader licenses do not override upstream market-data rights",
            "data_retention": "No raw third-party price data is committed; only filenames, schema/date observations, counts and HTTP outcomes are recorded.",
        },
        "technical_architecture": {
            "historical_retrieval_coverage_percent": 100.0,
            "historical_primary": {"source": "Yahoo Finance chart endpoint", "supported_count": 91},
            "historical_fallback": {"source": "StockAnalysis history pages", "fills_primary_missing_count": 10},
            "fresh_daily_completed_session": {
                "session_date": "2026-07-22",
                "coverage_percent": 100.0,
                "sources": [
                    {"source": "StockAnalysis history pages", "supported_count": 99},
                    {"source": "Yahoo Finance chart endpoint", "ticker": "IEEC"},
                    {"source": "Mubasher current stock page", "ticker": "ICFC"},
                ],
                "note": "Mubasher proves current displayed OHLCV for ICFC; a stable machine-readable endpoint was not verified.",
            },
            "remaining_missing_count": 0,
            "limitations": [
                "StockAnalysis visible history is paginated/limited and must be validated per symbol.",
                "New listings naturally have short histories; renamed securities need continuity mappings.",
                "Both interfaces can change or block automation without notice.",
                "Technical operation does not provide redistribution or storage rights.",
            ],
        },
        "source_assessments": [
            {"source_id": source["source"], **source["detail"], **source["matrix"]}
            for source in SOURCES
        ],
        "sources": coverage_sources,
    }

    price_matrix = {
        "schema_version": "1.0.0",
        "generated_at": AS_OF,
        "columns": MATRIX_COLUMNS,
        "rows": matrix,
        "summary": {
            "source_count": len(matrix),
            "free_legal_complete_sources": 0,
            "free_technical_complete_architectures": 1,
            "best_technical_coverage": [
                {"source": "Twelve Data", "coverage_percent": 100.0, "constraint": "Paid for XCAI"},
                {"source": "EGID official market-data feed", "coverage_percent": 100.0, "constraint": "Licensed/quoted; no free offer"},
                {"source": "EOD Historical Data (EODHD)", "coverage_percent": 98.02, "constraint": "Paid and two securities missing"},
                {"source": "StockAnalysis.com", "coverage_percent": 98.02, "constraint": "Display license; no programmatic API"},
                {"source": "Yahoo Finance / yfinance", "coverage_percent": 90.1, "constraint": "Unofficial endpoint and restricted automation terms"},
            ],
        },
    }

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    (OUTPUT_DIR / "coverage_report.json").write_text(
        json.dumps(coverage_report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    (OUTPUT_DIR / "price_source_matrix.json").write_text(
        json.dumps(price_matrix, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )


if __name__ == "__main__":
    main()
