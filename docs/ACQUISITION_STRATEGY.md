# Acquisition Strategy Matrix

This document answers one question, first-principles: **is the acquisition
*strategy* wrong, separately from whether the *platform* (registry,
discovery, qualification, collectors, Mission Control) is wrong?** The
platform is not in question here — `docs/DATA_ACQUISITION.md` describes it
and it stays as built. This document is the missing layer above it: for
each independent data requirement, what legal acquisition strategies exist,
which one is actually best, and does the current catalog/collector set
already reflect that.

It was written after a live production run (`.github/workflows/deploy-pages.yml`,
`--mode live`, real GitHub Actions egress) produced first-party evidence of
exactly how each attempted Egyptian source fails or succeeds — not
speculation. That evidence is Step 6's input.

## The corrected assumption

The acquisition program's original mental model, implicit in treating every
named organization as a `TargetOrganization` whose **homepage** is scanned
for a feed, was: *reach the organization's website, and a usable acquisition
method will be discoverable there.* Live evidence this session falsifies
that as a general rule:

| Target | What actually happened | Failure class |
|---|---|---|
| `egx_official` (egx.com.eg) | TCP connection actively closed, no response | Network-level anti-bot |
| `cbe` (cbe.org.eg) | WAF returns an explicit "Request Rejected... consult with your administrator" page | WAF rejection |
| `enterprise_press` | robots.txt disallows the bare domain; `www.` variant has a broken/mismatched TLS certificate | robots.txt + broken infra |
| `mubasher` | robots.txt disallows both `mubasher.info` and `www.mubasher.info` | robots.txt disallow |
| `zawya` | Reachable, 242KB of real HTML returned — but no RSS/PDF-repo/dataset/API-doc link on the page | **Homepage has content but no discoverable feed** |
| `stooq` (control) | Cloudflare-style JS proof-of-work challenge, not the documented CSV endpoint | Anti-bot at the CDN layer |
| `worldbank` (control) | Real data collected: 66 Egypt CPI inflation observations | **Documented API, no homepage involved at all** |

The pattern: four of five Egyptian targets are blocked by a defensive
measure this program correctly refuses to defeat (WAF, anti-bot, robots.txt,
broken TLS — all governed by the rules below), and the fifth (Zawya) shows
the homepage-scan heuristic itself has a real, closeable gap. Meanwhile the
one source that worked outright (World Bank) was never approached via
homepage discovery at all — it was catalogued directly against a *known,
documented, stable API contract*, exactly like `FredCsvCollector`/
`StooqPriceCollector`. **"Homepage = data source" is the wrong default
strategy for organizations with a hardened public web presence (exchanges,
central banks, WAF-protected news portals); "find the documented API/feed/
bulk-download contract first, fall back to homepage discovery only when no
such contract is publicly known" is the correct one.** The sections below
apply that correction capability by capability rather than target by
target, since two capabilities from the same organization can have
different legal strategies (e.g. CBE's rate data may have a bulk CSV
download even though its homepage is WAF-protected — unverified, catalogued
as a gap, not assumed).

## Rules this document and every recommendation in it obey

Never bypass robots.txt. Never bypass Terms of Service. Never defeat WAF or
anti-bot protections. Never fabricate URLs. Never guess hidden endpoints.
Never hardcode undocumented feeds. Every endpoint must be verified before a
`SourceSpec` becomes `IMPLEMENTED` (`docs/DATA_ACQUISITION.md`'s status
policy already enforces this; nothing here proposes weakening it).

## Step 1-4: Capability × Strategy Matrix

Each row is one independent data requirement. "Chosen strategy" is Step 5's
answer, folded into the same row for readability. "Current state" cites the
actual catalog entry (`sources/catalog.py`) or live-run evidence.

### 1. Price Data (EGX-listed tickers, OHLCV)

| Strategy | Legality | Stability | Automation | Freshness | Coverage | Reliability | Maintenance | Collector type | Status |
|---|---|---|---|---|---|---|---|---|---|
| Stooq CSV download (`.eg` suffix) | Free personal use, verify redistribution | Documented URL shape | Full | End-of-day | Broad EGX + global | Medium (aggregator) | Low | CSV download | **Blocked live** — Cloudflare JS challenge observed this session on the homepage; the documented `/q/d/l/` CSV endpoint itself was not confirmed challenged (evidence gap, not a fabricated pass) |
| EGX official bulk download | Official regulator/exchange terms | Would be highest if reachable | Full (once verified) | Real-time/EOD | Complete, authoritative | Highest | Low once verified | CSV/PDF download | **Blocked** — TCP connection dropped (network-level) |
| Financial aggregator APIs (AlphaVantage, FMP, Twelve Data, EODHD) | Documented ToS, key-gated free tiers | High (versioned REST) | Full | Real-time to EOD depending on tier | EGX coverage varies by vendor, unverified per-vendor | Medium-high | Low | JSON API (keyed) | AlphaVantage/FMP: **NEEDS_KEY, code-complete**; Twelve Data/EODHD: not yet catalogued, same class |
| Company IR direct download (per-listed-company) | Company's own published data | Low (per-site format) | Partial (PDF/HTML) | Irregular | Only that company | Low-medium per company | High (N sites) | PDF/HTML | PLANNED (`company_ir`) |

**Chosen strategy**: keep Stooq as the primary (already `IMPLEMENTED`;
today's Cloudflare challenge is evidenced against the *homepage*, not
necessarily the CSV endpoint documented in `docs/DATA_ACQUISITION.md` —
this is a health/monitoring finding, not a strategy change) and treat a
keyed aggregator (AlphaVantage or FMP) as the qualified fallback the moment
a user supplies a key — this is a **diversification** move (two independent
vendors covering the same capability), not a replacement. EGX official
stays the long-term target once its network-level block is independently
resolved (business/legal outreach, not an engineering fix).

### 2. Corporate Disclosures (regulatory filings, material announcements)

| Strategy | Legality | Stability | Automation | Freshness | Coverage | Reliability | Maintenance | Collector type | Status |
|---|---|---|---|---|---|---|---|---|---|
| EGX official disclosure archive | Official | High once verified | Full | Same-day | Complete | Highest | Low | CSV/PDF download or structured page | **Blocked** — network-level (see above) |
| FRA (Financial Regulatory Authority) disclosure feed | Official regulator | Unverified | Unverified | Unverified | Complete for regulated matters | Highest | Low once verified | HTML/PDF/possible feed | PLANNED, unattempted this session — no live evidence yet either way |
| Company IR press-release RSS/PDF | Company's own | Medium (per-company) | Full for RSS, partial for PDF | Same-day to weekly | Only that company | Medium | High (N companies) | RSS/PDF | PLANNED (`company_ir`); this is what `generate_company_ir_targets()` already targets per constituent |
| News-outlet corporate coverage (Enterprise/Mubasher/Zawya/Reuters) | Aggregated secondary reporting, not primary disclosure | Medium | Full via RSS where available | Hours | Broad but secondary, not authoritative | Medium | Low-medium | RSS | Enterprise/Mubasher: **blocked** (robots.txt); Zawya: **homepage has no feed** (this session's sitemap-fallback fix directly targets this) |

**Chosen strategy**: primary disclosures should come from FRA/EGX once
verified (regulator-of-record, highest authority); until then, per-company
IR (RSS/PDF) is the only legally-clear path for individual disclosures, and
news-outlet coverage is corroborating-only (`conflict_priority` already
ranks it below official/company sources in the seed catalog) — never
treated as authoritative on its own, matching the Event Platform's
corroboration model this program already relies on.

### 3. Corporate Actions (dividends, splits, rights issues)

| Strategy | Legality | Stability | Automation | Freshness | Coverage | Reliability | Maintenance | Collector type | Status |
|---|---|---|---|---|---|---|---|---|---|
| EGX official corporate-actions feed | Official | High once verified | Full | Same-day | Complete | Highest | Low | CSV/structured page | **Blocked** (network-level) |
| Company IR announcement (RSS/PDF) | Company's own | Medium | Full/partial | Same-day to weekly | Only that company | Medium | High | RSS/PDF | PLANNED |
| Headline-keyword classification of general news RSS | Same as underlying feed's ToS | Medium | Full | Hours | Broad but low-precision | Low-medium (headline-only, no numeric detail — TD-29) | Low | RSS + classifier | **IMPLEMENTED** today (`RssNewsCollector.classify_corporate_events`) — the only corporate-action signal actually flowing today |

**Chosen strategy**: the currently-`IMPLEMENTED` headline classifier is the
right *stopgap* (already correctly scoped as informational-only,
`details={}`, per TD-29) but is not a substitute for EGX's or a company's
own structured corporate-action feed, which is the only source that can
ever carry a numeric split ratio or dividend amount
(`data.adjustments.adjusted_returns_for_ticker()` needs exactly that).
Nothing to change here beyond what TD-29/TD-32 already track.

### 4. Financial Statements

| Strategy | Legality | Stability | Automation | Freshness | Coverage | Reliability | Maintenance | Collector type | Status |
|---|---|---|---|---|---|---|---|---|---|
| Company IR structured export (CSV/XLSX) | Company's own | Low (per-company format) | Full once format known | Quarterly | Per-company | Medium | High | Excel/CSV | `FinancialStatementCollector` **code-complete**, unverified column layout (TD-31) |
| Company IR PDF filing | Company's own | Low | Partial (extraction risk) | Quarterly | Per-company | Low until layout verified | High | PDF | Deliberately unimplemented (TD-32) — extracting the wrong line item silently is worse than not extracting at all |
| Financial aggregator API (FMP has a financials endpoint; AlphaVantage does not for most EGX tickers) | Keyed, documented | High | Full | Quarterly, lagged | Coverage unverified for EGX specifically | Medium | Low | JSON API | Not yet explored for financial-statement coverage specifically — flagged as a gap below |

**Chosen strategy**: no change to the honest-gap posture (TD-31/TD-32)
until a real export or filing is fetched and its layout inspected. New
finding to flag: FMP's `/v3/income-statement/{symbol}` family of endpoints
(same product FMP's already-cataloged NEEDS_KEY price collector uses) is
worth checking for EGX-ticker coverage once a key exists — same collector
class, no new engineering, but unverified without a key.

### 5. Investor Relations (company profile, presentations, calendar)

| Strategy | Legality | Stability | Automation | Freshness | Coverage | Reliability | Maintenance | Collector type | Status |
|---|---|---|---|---|---|---|---|---|---|
| Per-company IR page (PDF repository / RSS) | Company's own | Low-medium | Partial-full | Irregular | Per-company | Medium | High (N companies) | PDF/RSS | PLANNED, driven by `generate_company_ir_targets()` + EGX-directory hint chain (`discover_company_directory_links`) |

**Chosen strategy**: unchanged — this is the one capability where
per-company homepage discovery genuinely is the correct strategy (there is
no single aggregator that legally republishes every constituent's IR
material), so the existing `AcquisitionIntelligenceEngine` design is
already right for this capability specifically. The only thing this session
adds is the sitemap-fallback fix (Step 7), which now also applies to each
of the ~30-70 individual company-IR homepages, not just the five
organization-level targets — a company IR site with no RSS autodiscovery
tag but a `/sitemap.xml` listing PDF press releases will now be found.

### 6. News

| Strategy | Legality | Stability | Automation | Freshness | Coverage | Reliability | Maintenance | Collector type | Status |
|---|---|---|---|---|---|---|---|---|---|
| Outlet RSS/Atom feed (Reuters, Enterprise, Mubasher, Zawya, Asharq, CNBC Arabia, Al Arabiya, MarketScreener, Investing.com News, Al Mal, Al Borsa, Masrawy, Youm7, Sky News Arabia, Asharq Economy) | Per-outlet, feed publication implies syndication intent | High (RSS is a stable protocol) | Full via `RssNewsCollector` | Minutes-hours | Broad in aggregate | Medium | Low (one generic collector) | RSS | Enterprise/Mubasher: **blocked** (robots.txt); Zawya: **no feed link on homepage** (sitemap-fallback fix targets exactly this); the other ~11 outlets: **PLANNED, unattempted this session** — no live evidence for or against yet |
| Direct HTML scrape of an outlet with no feed | Ambiguous by default | Low | Full but fragile | Minutes | Single outlet | Low | High | HTML scrape | `assess_legality()` can never auto-clear this (charter rule); correctly never chosen automatically |

**Chosen strategy**: no change to the RSS-first design — it is already
correct. The concrete, evidenced gap is Zawya-class ("reachable, no
autodiscovery tag"), which the sitemap/robots.txt fallback now closes
*mechanically* wherever a real feed is discoverable that way. For the ~11
untried outlets, the next step is simply running discovery against them
(now with the fallback active) — not a strategy change.

### 7. Macro (Egypt-specific: inflation, GDP, reserves, trade, policy rate)

| Strategy | Legality | Stability | Automation | Freshness | Coverage | Reliability | Maintenance | Collector type | Status |
|---|---|---|---|---|---|---|---|---|---|
| World Bank Open Data API | CC-BY 4.0, documented | Very high (versioned public API) | Full | Annual | Broad Egypt macro indicators | High | Low | JSON API | **IMPLEMENTED, live-verified this session** (66 real Egypt CPI observations collected) |
| CBE bulletins/time series | Official central bank | Unverified (homepage is WAF-blocked) | Unverified | Unverified | Highest for EGP-specific rates | Highest | Low once verified | CSV/PDF, or possibly a documented API distinct from the WAF-protected homepage | **Blocked at the homepage**; **the WAF blocking cbe.org.eg does not necessarily block a separate documented data-API subdomain/endpoint if one exists — unverified, not assumed either way** |
| IMF SDMX/JSON API | Free, documented, no key | Very high (standardized SDMX, same tier as World Bank) | Full | Varies by series | Broad, incl. Egypt | High | Low | JSON API | **PLANNED in catalog, but currently modeled as a homepage-discovery `TargetOrganization` — this is the wrong model for it** (see Step 6) |
| OECD SDMX API | Free, documented, no key | High | Full | Varies | Partial Egypt coverage | Medium-high | Low | JSON API | Same mismodeling as IMF |
| Trading Economics API | Free tier limited, ToS/key unreviewed | Medium | Partial | Daily | Broad | Medium | Low-medium | JSON API | PLANNED, ToS review pending |

**Chosen strategy**: World Bank remains primary and is already proven live.
IMF and OECD should stop being modeled as `TargetOrganization`s whose
*homepage* needs discovering — their SDMX/JSON APIs are exactly as
well-documented and stable as World Bank's, which was hand-catalogued
directly as `IMPLEMENTED` against `api.worldbank.org/v2` without ever going
through homepage discovery. This is Step 6's clearest "incorrect
assumption" finding, detailed below.

### 8. Market Breadth (advancers/decliners, volume, index-level aggregates)

| Strategy | Legality | Stability | Automation | Freshness | Coverage | Reliability | Maintenance | Collector type | Status |
|---|---|---|---|---|---|---|---|---|---|
| Derived from Price Data capability (Stooq/aggregator OHLCV across the universe) | Same as capability 1 | Same as capability 1 | Full | Same as capability 1 | As wide as the universe's Price Data coverage | Same as capability 1 | Low (no new collector) | — | Follows capability 1; no independent source needed |
| EGX official market-summary page/download | Official | Unverified | Unverified | Real-time/EOD | Complete | Highest | Low once verified | CSV/structured page | Blocked (network-level, same as capability 1/2) |

**Chosen strategy**: this is not an independently-sourced capability —
market breadth is computed from Price Data already collected, not fetched
from a separate feed. No new strategy needed; it inherits capability 1's
gaps and its eventual EGX-official upgrade.

### 9. Trading Calendar (holidays, half-days, settlement calendar)

| Strategy | Legality | Stability | Automation | Freshness | Coverage | Reliability | Maintenance | Collector type | Status |
|---|---|---|---|---|---|---|---|---|---|
| EGX official calendar publication | Official | Unverified | Unverified | Annual/ad hoc | Complete | Highest | Low once verified | PDF/structured page | Blocked (network-level) |
| Static/placeholder calendar (current state) | N/A — internal | N/A | N/A | Never updates | Partial, may drift | Low (explicitly a placeholder per CLAUDE.md) | None | — | Current state, documented as non-authoritative |

**Chosen strategy**: no legal alternative exists that is more authoritative
than EGX's own calendar; this capability stays blocked on the same
network-level issue as capabilities 1/2/3/8/9/10 until EGX's official
channel clears. No independent workaround is legally equivalent — a
third-party calendar site would itself need the same verification rigor and
offers no reliability advantage.

### 10. Index Constituents (EGX30/EGX70 membership)

| Strategy | Legality | Stability | Automation | Freshness | Coverage | Reliability | Maintenance | Collector type | Status |
|---|---|---|---|---|---|---|---|---|---|
| EGX official constituent list | Official | Unverified | Unverified | Rebalance events | Complete | Highest | Low once verified | CSV/structured page | Blocked (network-level); `IndexConstituentCollector` **code-complete**, column layout unverified (TD-30) |
| User-supplied verified list | N/A — human-provided | High (static until user updates) | Manual | As often as user updates it | Complete if kept current | High if sourced carefully by the user | Low | `FilesystemCollector` | Available today, real and tested, but requires the user to supply and refresh it — a legitimate immediate unblock named in `docs/ROADMAP.md` |

**Chosen strategy**: unchanged from `docs/ROADMAP.md`'s existing framing —
either EGX's official feed clears, or the user supplies a verified list via
the already-real `FilesystemCollector` path. Both are legitimate; the first
needs no user action once EGX is reachable, the second needs no network at
all.

### 11. Sector Membership

| Strategy | Legality | Stability | Automation | Freshness | Coverage | Reliability | Maintenance | Collector type | Status |
|---|---|---|---|---|---|---|---|---|---|
| EGX official sector classification | Official | Unverified | Unverified | Rebalance events | Complete | Highest | Low once verified | CSV/structured page | Blocked (network-level) |
| `StaticSectorProvider` (current state) | N/A — internal | N/A | N/A | Never updates | Partial, placeholder | Low (documented placeholder) | None | — | Current state |

**Chosen strategy**: same posture as capability 10 — blocked on the same
official-source issue, same `FilesystemCollector` workaround available.

### 12. Economic Releases (calendar of macro data release dates/events)

| Strategy | Legality | Stability | Automation | Freshness | Coverage | Reliability | Maintenance | Collector type | Status |
|---|---|---|---|---|---|---|---|---|---|
| CBE/CAPMAS/MoF release calendars | Official | Unverified | Unverified | Per-release | Egypt-specific | Highest | Low once verified | HTML/PDF | Blocked (CBE: WAF; CAPMAS/MoF: unattempted this session) |
| Trading Economics economic calendar | Free tier limited | Medium | Partial | Real-time | Broad, incl. Egypt | Medium | Low-medium | JSON API | PLANNED, ToS/key review pending |
| Derived from World Bank/IMF/OECD release cadence (indicators arrive on known schedules) | Same as capability 7 | High | Full | Coarse (annual/quarterly, not release-day precision) | Partial (only what those APIs cover) | Medium | Low | — | Follows capability 7, not a standalone feed |

**Chosen strategy**: no dedicated collector exists or is proposed yet; this
capability's best low-effort proxy is deriving release timing from the
same World Bank/IMF/OECD indicators already prioritized under capability 7,
accepting coarser precision until a release-calendar-specific source (CBE
or Trading Economics) clears its own blocker.

## Step 6: Comparison against the current implementation

**What the current implementation gets right and should not change:**
- The RSS-first, structured-download-second, PDF-repository-third,
  scraping-never-auto-cleared ranking (`legality.py`/`ranking.py`) is sound
  and matches every capability's actual best strategy above.
- Per-company Investor Relations genuinely needs homepage-level discovery
  (capability 5) — there is no legal aggregator substitute — so
  `AcquisitionIntelligenceEngine`'s `TargetOrganization` model is *correct*
  for that capability specifically.
- The `NEEDS_KEY`/`TOS_REVIEW`/`PLANNED` honesty states, and refusing to
  fabricate a consistency score or a column layout ahead of real data
  (TD-11, TD-30, TD-31), are exactly right and unaffected by this analysis.
- World Bank's direct-API cataloguing (bypassing homepage discovery
  entirely) was the right call and the right precedent — this document's
  main correction is applying that same precedent more broadly.

**Incorrect assumption identified:** treating every named organization,
including ones with a well-known documented API contract (IMF, OECD), as a
homepage-discovery `TargetOrganization` rather than a direct-API catalog
entry like World Bank. IMF's and OECD's SDMX/JSON APIs are public,
versioned, and free — the same confidence tier `docs/DATA_ACQUISITION.md`
already assigns FRED and World Bank. Nothing about their homepages needs
scanning; what needs verifying is the documented API contract itself
(series identifiers, endpoint shape), exactly as `WorldBankCollector` was
built and tested against `api.worldbank.org/v2/country/EGY/indicator/{code}`
without a discovery run ever touching imf.org or oecd.org. **This is a
catalog-modeling correction, not a code change** — no collector is written
in this pass (see "what is not done" below), because writing one against
an endpoint shape I have not verified this session would itself violate
"never guess a hidden endpoint." It is recorded here as the concrete next
step, not implemented blind.

**Missing discovery heuristic, now closed:** `discovery.DiscoveryEngine`
already had `discover_sitemap_urls()`/`scan_sitemap()` implemented and
tested in isolation, but `AcquisitionIntelligenceEngine.run_for_target()`
never called it — a homepage with real content but no RSS/PDF/dataset/API
link (exactly Zawya's evidenced failure mode) produced "no candidates" and
stopped, even though the sitemaps.org protocol (robots.txt's `Sitemap:`
directive, or the conventional `/sitemap.xml` path) is a standardized,
non-guessing way to find more of a site's structure. This is TD-18's exact
description ("`discover_sitemap_urls` doesn't recurse into a sitemap-index
pointing at other sitemaps" — and, this analysis adds, isn't wired in as a
fallback at all). Closed this pass (Step 7 below).

**Unnecessary collectors:** none identified — every `IMPLEMENTED`/
`NEEDS_KEY`/`PLANNED`/`TOS_REVIEW` entry in the seed catalog maps to a real
capability above; nothing is redundant with another entry for the same
capability from the same organization category in a way that wastes
maintenance (the two keyed aggregators, AlphaVantage and FMP, are
deliberate diversification for capability 1, not redundancy).

**Architecture strengths reaffirmed:** the three-axis state model
(`status`/`lifecycle_state`/`health_status`), the fail-loud LIVE mode added
this session, and the corroboration-over-single-source-of-truth design
(Event Platform) all directly support "no single website is a point of
failure" — this document's recommendations lean on that existing machinery
rather than proposing new machinery.

**Architecture weaknesses this analysis surfaces (already tracked, not
new):** TD-20 (ToS keyword lists uncalibrated against real pages), TD-21
(domain resolver's bounded TLD fallback list would not resolve an org with
an uncommon TLD and no `domain_hints` — not a problem for any of the 12
current named targets, all of which have hints, but would matter for a
13th discovered organically), TD-23 (continuity monitor is reactive-only).

## Step 7: Minimum engineering changes made this pass

1. **Sitemap discovery wired into the fallback path**
   (`acquisition_intelligence/engine.py`): when `scan_page()` finds nothing
   on the homepage, `run_for_target()` now tries robots.txt's own declared
   `Sitemap:` directive, then the conventional `/sitemap.xml` root path —
   both real, verifying fetches through the same injected `fetch_text`
   already used everywhere else in the engine (which enforces robots.txt
   via the caller's `HttpFetcher`), never a fabricated or hardcoded feed
   URL. A sitemap-index (`<sitemapindex>` root) is followed one level.
2. **`discover_sitemap_urls()` no longer blanket-guesses `HTML_SCRAPE`**
   (`discovery/engine.py`): a `<loc>` entry ending in a known structured
   extension (`.csv`/`.xlsx`/`.xls`/`.json`/`.xml`) is classified the same
   way `discover_structured_datasets()` already classifies ordinary anchor
   links — mechanical, extension-based, no new guessing logic invented.
3. **`is_sitemap_index()` added** (`discovery/engine.py`) so the
   orchestration layer can tell a sitemap-index apart from a flat sitemap
   without duplicating XML-sniffing logic at the call site.
4. Both changes are fully unit-tested with fakes (no network) —
   `test_discovery.py` (extension classification, index detection) and
   `test_acquisition_engine.py` (three new end-to-end scenarios: sitemap
   fallback discovers a dataset, a sitemap-index is followed one level, and
   the "nothing anywhere" case still reports its original honest reason).
5. `docs/TECHNICAL_DEBT.md` TD-18 updated to reflect partial closure (the
   sitemap-index/fallback-wiring half is done; the JS-rendered-content half
   remains open, unchanged).

**What is deliberately not done in this pass** (flagged, not silently
skipped): no new collector was written for IMF/OECD (Step 6's
catalog-modeling correction needs their exact documented endpoint/series
shape verified against real API documentation before any code is written,
per "every endpoint must be verified" — this is recorded as the concrete
next engineering step, not implemented blind). No ToS/legal review was
performed for `TOS_REVIEW` sources (Yahoo Finance, Investing.com,
TradingView, Google Trends) — that review is explicitly a human/legal
action this program has never automated, and remains so. No new API key
was obtained for AlphaVantage/FMP/Twelve Data/EODHD — acquiring one is a
user/business action (`docs/ROADMAP.md` already frames this the same way).
