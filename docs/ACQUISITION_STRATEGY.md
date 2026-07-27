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

**Update (capability-driven runtime engine, this phase):** the analysis
below was turned into executable runtime logic, not left as narrative —
see "Runtime Implementation" near the end of this document for what now
actually runs `agx run --mode live`'s Collector Selection/Execution stages,
and "Collector Classification" for how every existing collector maps onto
this model. Nothing in Steps 1-6 below changed; this phase closed the gap
between the analysis and the code.

**Update (no-API-key sources decision, later phase):** the project owner
decided the platform relies exclusively on genuinely free, no-registration
sources — waiting indefinitely on a `NEEDS_KEY` credential serves no goal.
Every reference below to AlphaVantage/FMP/Polygon/Tiingo as `NEEDS_KEY,
code-complete` describes the historical state at the time this document
was written; all four were subsequently removed from the seed catalog,
along with `AlphaVantageCollector`/`FmpCollector` and their tests (see
`docs/DATA_ACQUISITION.md`'s "No API-key sources" section and
`CURRENT_MISSION.md`). The rest of this document's analysis (which legal
strategies exist per capability, the live-evidence findings) is otherwise
unaffected and preserved below for its historical accuracy.

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
| Stooq CSV download (`.eg` suffix) | Free personal use, verify redistribution | Documented URL shape | Full | End-of-day | Broad EGX + global | Medium (aggregator) | Low | CSV download | **Blocked, now confirmed blanket** — robots.txt disallows the CSV-download mechanism entirely (a US-ticker path and the bare `/q/d/l/` path are disallowed identically to the EGX path; even robots.txt itself is disallowed by its own rule) — see "Price Data Feasibility Mission" below |
| EGX official bulk download | Official regulator/exchange terms | Would be highest if reachable | Full (once verified) | Real-time/EOD | Complete, authoritative | Highest | Low once verified | CSV/PDF download | **Blocked** — TCP connection dropped (network-level), reconfirmed every session including this one |
| Yahoo Finance (unofficial API) | Ambiguous, assumed | High | Full | Real-time | EGX tickers (`.CA` suffix) | Medium-high | Low | JSON API | **Blocked, now confirmed by real ToS text** — explicitly prohibits "automated means... robots, spiders, scrapers, data mining tools... without express, prior permission" |
| Investing.com | Ambiguous, assumed | — | — | — | — | — | — | — | **Blocked** — 403 Forbidden even on the ToS page itself |
| TradingView | Ambiguous, assumed | — | — | — | — | — | — | — | **Blocked, now confirmed by real ToS text** — explicit data-ownership/redistribution restriction language |
| Mubasher / Zawya (Egyptian financial portals) | N/A | N/A | N/A | N/A | N/A | N/A | N/A | — | **Not suitable** — both reachable, but a full anchor scan of their own homepages (508 and 154 links respectively) found zero download/historical/export/csv/xlsx/market-data links; these are news portals, not price-data providers |
| Financial aggregator APIs (AlphaVantage, FMP, Twelve Data, EODHD) | Documented ToS, key-gated free tiers | High (versioned REST) | Full | Real-time to EOD depending on tier | EGX coverage varies by vendor, unverified per-vendor | Medium-high | Low | JSON API (keyed) | AlphaVantage/FMP: **NEEDS_KEY, code-complete**; Twelve Data/EODHD: not yet catalogued, same class — the one category that is a business decision, not a legal/technical wall |
| Company IR direct download (per-listed-company) | Company's own published data | Low (per-site format) | Partial (PDF/HTML) | Irregular | Only that company | Low-medium per company | High (N sites) | PDF/HTML | PLANNED (`company_ir`) |

**Chosen strategy, updated by the Price Data Feasibility Mission (see
below)**: no autonomously-implementable free strategy currently exists for
EGX equity OHLCV. Every option engineering can act on alone is now
evidenced-blocked; the only remaining path (a NEEDS_KEY aggregator) is
explicitly a business decision reserved for the project owner, per this
program's existing rule that a credential is "a business/user action,
never fabricated or bypassed." EGX official stays the long-term target
once its network-level block is independently resolved (business/legal
outreach, not an engineering fix).

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
| Outlet RSS/Atom feed (Reuters, Enterprise, Mubasher, Zawya, Asharq, CNBC Arabia, Al Arabiya, MarketScreener, Investing.com News, Al Mal, Al Borsa, Masrawy, Youm7, Sky News Arabia, Asharq Economy) | Per-outlet, feed publication implies syndication intent | High (RSS is a stable protocol) | Full via `RssNewsCollector` | Minutes-hours | Broad in aggregate | Medium | Low (one generic collector) | RSS | Enterprise, Al Borsa and Masrawy Economy: **IMPLEMENTED and live-yield verified**; Mubasher's EGX feed is reachable but its feed subdomain has no robots policy, so remains PLANNED; Zawya has no verified feed; other outlets remain evidence-blocked or unverified rather than silently promoted. |
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
| IMF DataMapper API | Free, documented, no key | High | Full (blocked in practice) | Varies by series | Broad, incl. Egypt | High | Low | JSON API | **Verified and blocked, Final Data Acquisition sprint**: `imf.org/external/datamapper/api/v1/{indicator}/EGY`, the real current public endpoint (the older `dataservices.imf.org/REST/SDMX_JSON.svc` this document previously flagged as "mismodeled" doesn't resolve at all — DNS failure), returns `403 Forbidden` on every real indicator probed — a WAF/bot-detection block, the same class as CBE's, not an engineering gap this program will defeat |
| OECD SDMX API | Free, documented, no key | High | Full | Varies | Partial Egypt coverage | Medium-high | Low | JSON API | Unverified this pass — the specific dataflow-listing path probed earlier returned 404 (wrong path, not proof of blockage); deprioritized given IMF's WAF result and this sprint's freeze |
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
| User-supplied, official-page-reviewed list | Official URLs + human transcription | High (static until the next review) | Manual ingestion | As often as the snapshot is reviewed | 31 EGX30 rows + 70 EGX70 rows | High with ISIN/weight/count tests | Low | Versioned CSV bootstrap → collected runtime directory | **Connected** on 2026-07-26; source manifest and regression tests included |

**Chosen strategy**: the reviewed bootstrap is the production input while EGX
continues blocking automated retrieval. It is ingested into the same runtime
directory used by live constituent collection, so `CollectedUniverseProvider`
remains the sole reader and a future verified automated snapshot needs no
pipeline or frontend change. The bootstrap must be refreshed at each index
review; it is not presented as a live scraper.

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

## Runtime Implementation (Capability-Driven Acquisition Engine)

This phase turned this document's analysis into executable runtime logic —
"stop thinking in terms of websites, think only in terms of required
data" — reusing every existing component (`CollectionService`, the real
`Collector` subclasses, `SourceRegistry`, `sources.reputation`, Mission
Control's existing artifact-export pattern) with no new architecture:

- **`acquisition_intelligence.capability.Capability`**: the 12 named data
  requirements above, plus Research Papers (named by this phase's mission
  alongside them), as a runtime enum. `CAPABILITY_STRATEGIES` maps each one
  to its declared candidate pool of *catalogued* `SourceSpec` ids (verified
  to exist in `sources/catalog.py`, never invented) — a capability is the
  primary object; a source id is one interchangeable implementation of it.
  Market Breadth has no independent entry: it is computed from Price Data
  already collected (Step 8), not fetched from a second feed, so listing
  price-data ids again here would double-attempt the same collectors for
  no new information.
- **`acquisition_intelligence.capability_engine.rank_capability_strategies`**:
  ranks every candidate for a capability using the registry's own declared
  priors (`reliability_score`/`freshness_score`), folded evenly against
  measured reputation (`sources.reputation.compute_reputation`) once real
  run history exists, with `conflict_priority` breaking close ties — never
  a fresh network probe (that remains the Acquisition Intelligence Engine's
  job for *undiscovered* sources reached via homepage/sitemap scanning;
  this ranks strategies for capabilities whose candidates are already
  catalogued). A source not catalogued, or catalogued but not
  `IMPLEMENTED`, still appears with `ready=False` and the concrete reason —
  never silently dropped.
- **`acquisition_intelligence.capability_engine.CapabilityDecisionEngine`**:
  the runtime Acquisition Decision Engine. Given one capability, it ranks,
  then executes the top-ranked collectable strategy via the same
  `CollectionService` every mode already uses; if that strategy's fetch
  raises, or connects but yields zero usable records (`collection_yield`,
  the single shared "usable output" definition — see
  `collectors.service.collection_yield`, extracted this phase to remove
  the duplicate yield-sum formula previously inlined twice in
  `production/artifacts.py`), it automatically falls through to the next
  ranked candidate. Macroeconomic is the one capability marked
  `EXHAUSTIVE`: World Bank's Egypt CPI and FRED's global oil/dollar/
  treasury series are complementary, not interchangeable alternatives for
  the same fact, so every ready strategy runs rather than stopping at the
  first success — every other capability stops at the first strategy that
  produces usable output, per the mission's fallback-chain model. Every
  strategy considered (selected, skipped-not-ready, skipped-already-
  satisfied, failed, or zero-yield) is recorded on the returned
  `CapabilityDecision`, never just the outcome.
- **Wired into `production/pipeline.py`, LIVE mode only** (MOCK/REPLAY are
  deterministic test fixtures and keep the unchanged fixed collector plan
  — matching how Discovery is already LIVE-only): Collector Selection now
  ranks every capability's candidates (a pure registry read, no fetch);
  Collector Execution runs `CapabilityDecisionEngine.decide_and_execute()`
  per capability, using `production.collector_plan.build_live_collector`
  (extracted from the old fixed per-source branches so there is exactly
  one live-wiring definition per source, reused by both the flat plan and
  this engine — closing the Phase 6 "remove duplicated logic" requirement)
  as the injected collector factory. `self.collection_results`/
  `self.collector_failures`/`self._unavailable` — the exact same fields
  every downstream stage (raw archive, canonical transformation,
  validation, `collector_status.json`) already reads — are populated
  identically to before for the sources already solved (stooq, fred,
  worldbank), verified by a live-fixture run reproducing every existing
  `test_production_pipeline.py` assertion unchanged. Every decision is
  additionally persisted as `acquisition_decisions.json` (a new "bonus"
  dashboard artifact, following the exact `model_dump(mode="json")`
  pattern every other artifact already uses — no new schema convention)
  and rendered in Mission Control's "Acquisition Decisions" section,
  replacing what was previously an honest "not yet available" placeholder.
- **Verified end to end**: a live-fixture run (real `HttpFetcher`, real
  collector classes, canned wire-format content, the same technique
  `test_production_pipeline.py` already uses) shows Price Data correctly
  skip `egx_official`/`polygon`/`tiingo`/`fmp`/`company_ir` (each with its
  real not-ready reason) before selecting `stooq`, and Macroeconomic
  correctly run both `fred` and `worldbank` after skipping `cbe` (not yet
  verified). All 510 backend tests pass; `ruff check` is clean; `web`/`api`
  typecheck and build clean.

## Collector Classification (Phase 6)

Every existing collector, reviewed against the capability-driven model.
None are deprecated or removed — each still serves a real, named
capability or a real generic access-method base; nothing is fully
replaced by this phase's work, so nothing is removed (per the mission's
own "do not remove working code unless fully replaced" rule).

| Collector | Classification | Why |
|---|---|---|
| `StooqPriceCollector` | Capability Strategy | Serves Price Data (and Market Breadth, derived); one of several ranked candidates, not a hardcoded default. |
| `FredCsvCollector` | Capability Strategy | Serves Macroeconomic (global benchmark series); complementary to World Bank, not redundant with it. |
| `WorldBankCollector` | Capability Strategy | Serves Macroeconomic (Egypt-specific indicators); the precedent this whole model generalizes from. |
| `RssNewsCollector` | Reusable Strategy | One generic, layout-tolerant class configured per outlet `SourceSpec` — serves News directly and Corporate Actions via its `classify_corporate_events` flag; reusable across many capability candidates, not tied to one. |
| `AlphaVantageCollector`, `FmpCollector` | Capability Strategy | Code-complete alternates for Price Data (`FmpCollector` also for Financial Statements); `NEEDS_KEY` until a user supplies credentials — a business action, not an engineering gap. |
| `IndexConstituentCollector` | Capability Strategy | Serves Index Constituents and Sector Membership; code-complete, unwired pending `egx_official` verification. |
| `FinancialStatementCollector` | Capability Strategy | Serves Financial Statements; code-complete, unwired pending `company_ir` verification. |
| `ExcelSeriesCollector`, `PdfDocumentCollector` | Reusable Strategy | Generic bases keyed to an access method (XLSX/PDF), not to one capability — any capability whose best strategy is a spreadsheet or PDF repository reuses these. |
| `FilesystemCollector` | Reusable Strategy | Generic ingestion path for a human-supplied file; the legitimate no-network unblock for Index Constituents/Sector Membership named in `docs/ROADMAP.md`. |
| `ArchiveReplayCollector` | Reusable Strategy | Wraps any collector to replay archived history; capability-agnostic by construction. |
| `corporate_event_classifier` (in `RssNewsCollector`) | Reusable Strategy | The only real (headline-only) Corporate Actions signal flowing today; a classifier applied within the generic RSS collector, not a capability-specific one. |
| `BrowserAutomationCollector` | Legacy stub (unchanged) | An honest `NotImplementedError` — no scripted-browser method has a verified, ToS-cleared target yet. Not deprecated: it is the correct placeholder until one does. |

## First Live Egyptian Source (Enterprise, this phase)

A follow-on sprint's explicit mandate was to stop improving the platform
and obtain real Egyptian data through at least one verified, legal,
maintainable strategy. Re-running live verification (the same GitHub
Actions live-run technique used throughout this document) surfaced a real
discovery: **Enterprise's homepage (`enterprise.press`) is now reachable**
(it previously failed via robots.txt disallow on the bare domain / a
broken `www.` certificate — see the Step 6 table above), and its real HTML
carries a standard RSS autodiscovery tag pointing to
`https://enterpriseam.com/egypt/feed/` — a different domain from
`enterprise.press` itself (likely Enterprise's underlying publishing
platform). The Acquisition Intelligence Engine found this the same way it
finds every candidate: `discovery.discover_rss_feeds()`'s existing
`<link rel="alternate" type="application/rss+xml">` heuristic, no new
code, no guess.

**Verified, not assumed**, per this sprint's explicit rules:
- **Legal**: robots.txt allows it; access method is `RSS_FEED`, not
  `HTML_SCRAPE`, so `assess_legality()` could clear it to `ALLOWED`
  (unlike Zawya's sitemap-derived HTML article candidates, which can
  never auto-clear).
- **Reachable and stable**: a real reachability probe succeeded; the
  engine registered it at `lifecycle_state=QUARANTINE`, composite
  reputation 0.75 on its first run.
- **Produces structured, parseable data**: confirmed by an actual live
  collection run, not just reachability — `RssNewsCollector` (the same
  generic, already-tested class every other RSS source uses) parsed
  **6 real news items**, all materialized (`data_quality_score=0.97`),
  and 6 real events registered in the Event Platform. The registry then
  promoted it to `lifecycle_state=TRUSTED` on that evidence.
- **Reproducible**: wired as a static catalog entry
  (`sources/catalog.py`'s `enterprise_press`, `status=IMPLEMENTED`) plus a
  three-line addition to `production.collector_plan.build_live_collector()`
  — every future live pipeline run collects from it the same way, no
  manual step required.

### Bugs found and fixed getting here

Verifying this candidate experimentally (not trusting documentation
alone, per this sprint's Step 2) surfaced four real, previously-latent
bugs — each blocking verification itself, not general platform polish:

1. **`HttpFetcher` crashed on non-ASCII URLs.** Zawya's real sitemap-index
   (confirmed genuinely reachable and parseable) lists per-section
   sitemaps whose entries include Arabic-slugged article URLs with literal
   (non-percent-encoded) non-ASCII characters. `http.client`'s
   `_encode_request()` calls `.encode('ascii')` on the request line, which
   raised `UnicodeEncodeError` — an unhandled crash, not a normal
   `FetchError`, that took down the whole `discover-sources` CLI
   invocation and the pipeline's own discovery stage. Fixed by
   percent-encoding a URL's path/query/fragment before constructing the
   request (`collectors.fetcher._encode_request_url`).
2. **`HttpFetcher`'s robots.txt fetch had no timeout.** Stdlib
   `urllib.robotparser.RobotFileParser.read()` calls `urlopen()` with no
   timeout at all; a host that accepts the TCP connection but never
   responds (a real anti-bot behavior, distinct from a fast
   connection-refused) hung that call — and the whole sequential
   discovery run behind it — indefinitely. One live run had to be
   cancelled after 90+ minutes stuck here. Fixed by fetching robots.txt
   through the same timeout-bounded path every other request already
   uses, then feeding the raw lines to `parser.parse()`.
3. **Unbounded sitemap-candidate count.** Even after fixing (1), a second
   live run hung for ~70 minutes: Zawya's sitemap-index's per-section
   sitemaps (a "pages" or "authors" sitemap) can list thousands of URLs,
   and the sitemap fallback (added last phase) probed and historically-
   assessed every single one before ranking — not a true infinite loop,
   but effectively unbounded at real-world sitemap sizes. Fixed by capping
   nested-sitemap-index following to 5 sitemaps and total candidates
   returned to 25.
4. **Discovery silently regressed an `IMPLEMENTED` source back to
   `PLANNED`.** The pipeline's own discovery stage re-attempts every named
   Egyptian priority target on *every* run (including `enterprise_press`),
   and `run_for_target()` unconditionally registered a fresh spec each
   time — `generate_source_spec()` always mints one at `status=PLANNED`,
   per this platform's own AD-16 rule that auto-generation never marks
   something `IMPLEMENTED`. This meant the very next pipeline run after
   marking Enterprise `IMPLEMENTED` immediately reset it back to
   `PLANNED`, before collector execution even ran — Enterprise showed
   `UNAVAILABLE` in that run's `collector_status.json` despite being
   correctly catalogued moments earlier. Fixed by skipping re-registration
   when a target's `existing_source_id` is already `IMPLEMENTED` and not
   `DOWN` — a healthy, engineered source needs no fresh discovery, while a
   `DOWN` one still gets rediscovered (preserving
   `AcquisitionContinuityMonitor`'s recovery path, which depends on
   exactly this re-discovery happening for a degraded source).

None of these four fixes touched architecture, the pipeline's stage
sequence, the capability engine's design, or Mission Control — each is a
narrowly-scoped correctness fix directly blocking verification of a real
acquisition candidate, consistent with this sprint's "optimize data
acquisition, not internal systems" framing.

### What's still not flowing

EGX official, CBE, and Mubasher remain blocked by the same genuine,
evidenced defensive measures documented earlier in this file (network-
level reset, WAF rejection, robots.txt disallow) — this program's own
rules correctly refuse to defeat any of them. Zawya's sitemap is now
confirmed real and fully parseable (no crash, no hang), but every entry
discovered so far is an ordinary HTML article page (`HTML_SCRAPE`), which
`assess_legality()` can never auto-clear regardless of robots.txt — Zawya
has not produced a legally-clearable candidate. The other ~14 named news
outlets in the `NEWS`/`CORPORATE_DISCLOSURES`/`CORPORATE_ACTIONS`
capability pools remain unattempted; the same RSS-autodiscovery mechanism
that found Enterprise's feed applies unchanged to each of them the next
time discovery runs against them.

## Coverage-Expansion Mission (post-First-Live-Egyptian-Source)

The explicit job this phase: audit every registered source's real
operational state, then expand production coverage using only verified,
legal, maintainable acquisition strategies — reusing the existing
architecture, never redesigning it.

**Two new live production sources, same rigor as Enterprise's
verification**: `fra_egypt` (Egypt's own Financial Regulatory Authority,
`https://fra.gov.eg/feed/`) and `skynews_arabia_economy`
(`https://skynewsarabia.com/rss.xml`), both found by the same
RSS-autodiscovery heuristic, both legally cleared (robots.txt allows,
`RSS_FEED` access method), both confirmed producing real records in a live
run before being flipped from `PLANNED` to `IMPLEMENTED`. `fra_egypt` is
the first source from an actual Egyptian government regulator: 10 real
disclosure items parsed, 10 events registered, `data_quality_score=0.95`,
`health_status=healthy` — and, at `conflict_priority=98`, the first source
this platform can treat as primary/authoritative rather than aggregated
secondary reporting for corporate disclosures.

**Root cause of the coverage gap, found and closed**: nine outlets already
catalogued in `sources/catalog.py` as `PLANNED`
(`alarabiya_business`/`marketscreener`/`investing_news`/`almal`/`alborsa`/
`masrawy_economy`/`youm7_economy`/`skynews_arabia_economy`/
`asharq_economy`) had never actually been attempted by the Acquisition
Intelligence Engine — `target.py`'s `seed_target_organizations()` never
had an entry for them, so `agx discover-sources` had nothing to run
against those ids. Closed by adding a `TargetOrganization` for each, with
each outlet's own publicly-known brand domain as a hint (same category of
public knowledge as the pre-existing Reuters/Asharq Business/CNBC Arabia
entries, independently re-verified for reachability before anything is
trusted, never asserted). A second, deeper instance of the same class of
gap: `production/pipeline.py`'s own `_stage_discovery_engine` had a
*separate* hardcoded 5-id allowlist (`egx_official`/`cbe`/
`enterprise_press`/`mubasher`/`zawya`) left over from the original
Egyptian Live Data Sprint, so even a target with a `TargetOrganization`
entry was never automatically attempted by a real production run — only
reachable via a manual `discover-sources --target <id>` CLI call. Fresh
discovery now runs every non-per-constituent seeded target every live run;
a newly catalogued target needs no second registration step to actually be
attempted.

**A real crash, found and fixed by running this expanded discovery
live**: `cnbc_arabia`'s real sitemap.xml contains a `<loc>` entry that
isn't a compliant absolute URL (sitemaps.org requires one). Unlike every
other discovery function, `discover_sitemap_urls()` had never resolved a
`<loc>` entry against the sitemap's own URL — the malformed string flowed
straight through to `robots_status()`, which built
`f"{scheme}://{netloc}/robots.txt"` from a URL with neither, producing
`":///robots.txt"` and crashing `urllib.request.Request()` with a
`ValueError` the discovery stage's own exception handling didn't catch,
taking down the whole stage. Fixed with `urljoin()` (matching every other
discovery function) plus a `HttpFetcher._get_robots_parser()` widening to
also catch `ValueError`, since a malformed URL degrading to "robots.txt
unreachable" is exactly the existing convention for a genuinely
unreachable host, not a reason to crash the caller.

**Full audit of all 51 registered sources, classified into the mission's
six categories** (Production Ready / Temporarily Blocked / Technically
Blocked / Policy Blocked / Not Suitable / Needs Business Decision), with
per-source evidence, is the `collector_status.json`/`execution_report.json`
trail from this phase's live runs plus the discovery-reason diagnostics
added to `deploy-pages.yml` — see `CURRENT_MISSION.md` for the consolidated
summary. Live result this phase: 3 sources `COLLECTED` (`enterprise_press`,
`fra_egypt`, `worldbank`), 2 `FAILED` with an evidenced reason each
(`stooq` — robots.txt, `fred` — intermittent timeout), 47 `UNAVAILABLE`
each with a concrete, non-fabricated reason (`NEEDS_KEY`, `TOS_REVIEW`, or
"endpoint not yet verified"). `skynews_arabia_economy` is wired identically
but not yet exercised by a live collection cycle in production — the
capability engine's fallback chain stops at `enterprise_press`, which
ranks higher for the same capabilities (`corporate_disclosures`/
`corporate_actions`/`news`), so `skynews_arabia_economy` would only be
selected if `enterprise_press` degrades or fails; its feed URL and legal
clearance are independently verified (a raw fetch confirmed the endpoint
resolves), but its own collector's yield is unconfirmed until it actually
gets a turn.

## Price Data Feasibility Mission (post-Coverage-Expansion)

The explicit question this phase: can AGX build statistically valid
investment research using *only* legally obtainable free Egyptian market
price data? If not, prove it with live evidence after evaluating every
realistic free source; if so, implement the minimum viable price-data
capability.

**Verdict: no autonomously-implementable free strategy currently exists.**
Every option this program's own rules allow it to act on unilaterally is
now evidenced-blocked by a live fetch this phase, not by inherited
assumption:

| Source | What was actually checked | Result |
|---|---|---|
| Stooq | Full `robots.txt` fetched; `robots_status()` checked for the exact failing EGX ticker path, an equivalent US-ticker path, and the bare `/q/d/l/` path | **All three disallowed identically** — a blanket block on the CSV-download mechanism, not scoped to EGX at all. Even fetching `robots.txt` itself is disallowed by its own rule. Settles the prior "evidence gap" (Cloudflare-challenge-on-homepage-only) framing: the real cause is a total robots.txt block on the whole mechanism. |
| Yahoo Finance | Homepage reachable; its real Terms of Service fetched (`https://guce.yahoo.com/terms`) | **Explicit prohibition**, quoted directly: *"access or collect data... using any automated means, devices, programs, algorithms or methodologies, including but not limited to robots, spiders, scrapers, data mining tools, or data gathering or extraction tools, for any purpose without our express, prior permission."* Not "ambiguous" — this program's own `TOS_REVIEW` status is superseded by a definitive Policy Blocked. |
| Investing.com | Homepage/ToS page fetch attempted | **403 Forbidden** outright — couldn't even reach the terms page. |
| TradingView | Homepage reachable; its real policies page fetched (`https://www.tradingview.com/policies/`) | Explicit **data-ownership/redistribution restriction** language found ("Ownership of information; license to use TradingView; redistribution of data; non-display usage..."). Confirms the existing `TOS_REVIEW` classification with real evidence instead of assumption. |
| Mubasher / Zawya | Every anchor on both homepages (508 and 154 links respectively) scanned for `download`/`historical`/`export`/`.csv`/`.xlsx`/`market data` | **Zero matches on either.** These are news portals; no structured price-data page exists to discover. Not a legality question — there is nothing there. |
| EGX official | Reconfirmed | **`Connection reset by peer`** on both `egx.com.eg` and `www.egx.com.eg` — the same network-level block this program has now confirmed independently across six-plus sessions. |
| FMP / AlphaVantage / Polygon / Tiingo | Not re-probed this phase (already `NEEDS_KEY`, code-complete) | The one candidate that is **not** a legal/technical wall — it's explicitly a business decision (the project owner registering for a free-tier key), which this program's own rules already forbid engineering from doing unilaterally ("a business/user action, never fabricated or bypassed"). EGX-specific ticker coverage on any of these free tiers remains unverified either way. |
| FRED, World Bank, IMF, OECD | N/A | Structurally out of scope — global macro/commodity/FX series, not EGX-listed equity OHLCV, regardless of legality. |

**What this means for "statistically valid investment research"**: nothing
changes about the platform's honesty posture — `Price Data`/`Market
Breadth` stay correctly `UNAVAILABLE` in `collector_status.json`, no
collector was written against a source that can't legally supply it, and
no number was fabricated to fill the gap. The corporate-disclosure/news
side of the pipeline gained real EGX-relevant evidence this mission
(`fra_egypt`, `enterprise_press`) — but per `CLAUDE.md`'s own "returns
always go through `adjusted_returns_for_ticker()`, never a raw close-price
diff" rule and the charter's statistical-validation gate, correlating a
real event with subsequent market behavior requires real market behavior
to correlate it against, which no free, legally-obtainable, autonomously-
implementable source currently supplies. This is not a new blocker
`docs/ROADMAP.md`/`MISSION_CONTROL.md` didn't already name (a licensed EGX
market data vendor decision) — this phase replaces the inherited framing
with today's direct, quoted, live evidence for every realistic
alternative, so the conclusion is demonstrated rather than assumed.

**Not implemented, and why that is the correct outcome**: writing a
collector against Stooq/Yahoo/Investing.com/TradingView would violate this
program's own hard rules (never bypass robots.txt, never bypass ToS) that
exist specifically to prevent exactly this kind of pressure-driven
shortcut. Writing one against Mubasher/Zawya is impossible — there is no
structured endpoint to write it against. The only remaining path (a
NEEDS_KEY vendor) requires the project owner's own action; it isn't
engineering's decision to make on their behalf.

## Final Data Acquisition Sprint — closing verification, then freeze

Two closing questions before declaring this program's acquisition
architecture frozen: is there a real, working source left to add, and is
everything currently claimed as "connected" actually verified, not just
plausible?

**A real self-correction**: `skynews_arabia_economy` was promoted to
`IMPLEMENTED` in the Coverage-Expansion Mission on the strength of
reachability and legal clearance alone — the same qualification bar
`AcquisitionIntelligenceEngine` uses to reach `lifecycle_state=QUARANTINE`
— without first confirming an actual successful collection run, unlike
`enterprise_press`/`fra_egypt`, both of which were only promoted after a
live run proved real yield. Directly exercising its collector this sprint
(bypassing the capability engine's fallback ranking, which always
prefers `enterprise_press` for the same capabilities and so had never
given `skynews_arabia_economy` a real turn) returned `HTTP 404 Not Found`
on its only known feed URL — a clear, non-transient failure. **Reverted
to `PLANNED`** with the finding recorded in its catalog notes. This is
exactly the class of mistake `sources.qualification`'s stricter
`QUARANTINE → EVALUATION → TRUSTED` gates exist to catch given enough run
history; this correction closes it immediately rather than leaving a
false "connected" claim standing.

**IMF, verified rather than left as a documented-but-unmodeled gap**: the
`dataservices.imf.org` SDMX endpoint this document previously flagged as
"mismodeled" doesn't resolve at all (DNS failure, confirmed in the Price
Data Feasibility Mission above) — IMF has moved off it. The real current
public endpoint, IMF's DataMapper API
(`imf.org/external/datamapper/api/v1/{indicator}/EGY`), is genuinely
documented and keyless — but returns `403 Forbidden` on every real
indicator probed this sprint, a WAF/bot-detection block in the same class
as CBE's, not an engineering gap. IMF is now definitively evidenced-
blocked, not merely unattempted.

**Verdict: no further real, working, legally-obtainable source remains to
connect right now.** Every named candidate across all twelve capabilities
has now been either connected and verified (World Bank, Enterprise, FRA),
attempted and evidence-blocked (EGX official, CBE, IMF, Stooq, Yahoo
Finance, Investing.com, TradingView, Mubasher, Zawya, and the sixteen
other named news outlets), or is explicitly gated on a business decision
this program's own rules correctly refuse to make unilaterally (a
NEEDS_KEY vendor's key, a verified EGX30/EGX70 constituent list, a
licensed EGX vendor). Continuing to probe would mean either re-testing
already-stable negative findings or reaching for a workaround this
program's charter forbids.

**Acquisition architecture is now frozen.** No further `TargetOrganization`
entries, collectors, or source-discovery engineering should be added
without a new, named business input clearing one of the standing
blockers above (see `MISSION_CONTROL.md`'s "Known blockers" and
`docs/ROADMAP.md`). Every subsequent sprint's engineering effort goes
toward turning the evidence already flowing (`enterprise_press`,
`fra_egypt`, `worldbank`) into validated, ranked, explainable investment
intelligence — the hypothesis/validation/genome/explainability/Meta
Decision Engine side of the pipeline — not toward collecting more data.
See `CURRENT_MISSION.md` and `NEXT_MISSIONS.md` for what that means
concretely.
