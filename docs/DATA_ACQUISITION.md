# AGX Data Acquisition Platform

Data collection is a core product of AGX: the goal is the largest
continuously growing structured research database for the Egyptian Stock
Exchange, built exclusively from legally accessible free sources, where no
source is authoritative by itself — truth emerges through corroboration
(the Event Platform's existing fingerprint/corroboration/conflict
machinery is the arbiter; this program feeds it).

This is a *platform*, not a set of one-off scripts: the goal is that adding
a new source in the future requires implementing only a small adapter
(a `Collector` subclass and a `SourceSpec` entry, or often just a
configuration of an existing generic collector) — every other concern
(registry, discovery, qualification, reputation, health monitoring, raw
archive, provenance, replay, and now *finding the acquisition method itself*
via the Acquisition Intelligence Engine) is shared infrastructure built once.

## Architecture

```
acquisition_intelligence/
              TargetOrganization (identity, never a URL) + seed catalog
              domain_resolution.py -- verified-reachable-domain resolution
              legality.py / stability.py / historical.py -- per-method verification
              ranking.py / config_generation.py -- rank, select, auto-generate a SourceSpec
              engine.py -- AcquisitionIntelligenceEngine orchestrator (discovers
                           NEW candidates via homepage/sitemap scanning)
              capability.py -- Capability enum + per-capability strategy pools
                           (docs/ACQUISITION_STRATEGY.md's runtime form)
              capability_engine.py -- ranks + executes strategies for capabilities
                           whose candidates are already catalogued, with automatic
                           fallback (CapabilityDecisionEngine)
              continuity.py -- AcquisitionContinuityMonitor (re-discover on DOWN)
              discovery_report.py -- weekly scheduled verification report +
                           incremental cache (see "Discovery workflow" below)
              live.py -- real HttpFetcher/Wayback-backed adapters (deployment only)
sources/      SourceSpec (full charter field set) + SourceRegistry + seed catalog
              qualification.py  -- Candidate/Quarantine/Evaluation/Trusted/Core
              reputation.py     -- SourceMetrics + nine-dimension reputation score
              health.py         -- HealthMonitor + HealthAlert
discovery/    SourceCandidate + DiscoveryEngine (RSS/PDF-repo/dataset/sitemap scan)
collectors/   RawDocument (provenance envelope) + RawArchive (binary blob store)
              + Collector ABC + FetchPolicy + concrete/generic collectors
              + ProvenanceIndexRepository + HistoricalReplayEngine
              + quality scoring + CollectionService
              + materialization into the local CSV data layout
```

### Acquisition Intelligence Engine (`acquisition_intelligence/`)

The system must never require a manually specified endpoint. This is the
subsystem that makes that true: for a `TargetOrganization` (an identity —
name, category, country, and optionally a few publicly-known brand-domain
hints — never a hand-picked acquisition URL), it autonomously:

1. **Resolves a reachable domain.** `domain_resolution.HeuristicDomainResolver`
   tries the organization's public brand hints (if any) and, when none
   exist, name-derived guesses across a bounded set of TLDs — every
   candidate is independently probed for reachability before being trusted;
   nothing is asserted as a real domain without a successful probe.
2. **Discovers acquisition-method candidates** on the verified homepage via
   the existing `discovery.DiscoveryEngine` (RSS autodiscovery, PDF
   repositories, structured datasets, sitemaps, API docs) — no new
   discovery logic duplicated, the same engine System 03 already built. If
   the homepage's own markup carries nothing discoverable, `run_for_target`
   falls back to the sitemaps.org protocol (robots.txt's `Sitemap:`
   directive, then the conventional `/sitemap.xml` path, following a
   sitemap-index one level) before giving up — closing the exact
   "homepage reachable with real content but nothing discoverable" gap a
   live run evidenced (Zawya); see `docs/ACQUISITION_STRATEGY.md`.
3. **Verifies legality** (`legality.py`): robots.txt (three-state — allowed/
   disallowed/unknown, via `HttpFetcher.robots_status`) plus a terms-of-use
   red-flag/green-flag keyword scan. `HTML_SCRAPE` can never auto-clear to
   `ALLOWED` (charter rule: scraping is last-resort, always needs a human
   ToS read); any ambiguity blocks, exactly like the seed catalog's
   `TOS_REVIEW` convention.
4. **Verifies stability** (`stability.py`): URL-shape heuristics (a
   canonical `.csv`/`.json`/`.rss`/`.pdf` path scores higher; a session
   token or opaque generated-looking identifier scores lower) plus
   repeated-probe status-code consistency when more than one probe exists.
5. **Verifies historical availability** (`historical.py`): the Internet
   Archive's free, no-key, decades-stable Wayback Machine APIs (`wayback/
   available` + the CDX API) — same confidence tier as FRED's/World Bank's
   endpoints already used for real collectors — scored by how long a span
   of archived snapshots exists, not just whether one exists.
6. **Ranks and selects** (`ranking.py`): legality is a hard gate — a
   `BLOCKED`/`AMBIGUOUS` method is excluded from ranking entirely, never
   scored down and reconsidered; among methods that clear it, the composite
   is the mean of the stability and historical-availability scores.
7. **Auto-generates a `SourceSpec`** (`config_generation.py`) for the
   winning method: category/country from the target, access method and
   base URL from the discovered candidate, a conflict priority below every
   hand-verified source (40), a reliability prior scaled by the composite
   score but capped well below any `IMPLEMENTED` source's declared prior,
   and a suggested collector class name where one is unambiguous (RSS →
   `RssNewsCollector`; `.xlsx`/`.xls` → `ExcelSeriesCollector`; `.pdf` →
   `PdfDocumentCollector`, subclass still required; plain CSV/JSON API
   left `None` — schema inspection still needed before a generic collector
   applies). **The generated spec's `status` always stays `PLANNED`, never
   `IMPLEMENTED`, however high the score** — becoming collectable still
   requires an engineer to write and test the concrete collector, exactly
   as `AD-16`'s `IMPLEMENTED` gate already requires for every source. What
   auto-generation removes is the manual "which URL, which method, is it
   even legal" research — not the final engineering step.
8. **Registers and begins qualification**: the spec is added to the
   `SourceRegistry` (or a new version of an existing catalog entry, if
   the target links to one via `existing_source_id`), and an initial
   "reachability confirmed" run is recorded through `sources.reputation`,
   immediately handed to `sources.qualification.evaluate_promotion` —
   which, on real evidence, promotes it from `CANDIDATE` to `QUARANTINE`.
   No later stage is ever reached this way; `TRUSTED`/`CORE` still require
   real collection-run history, per the qualification pipeline's own rules.
9. **Continuity** (`continuity.py`): `AcquisitionContinuityMonitor` watches
   the registry for any source whose `health_status` has gone `DOWN` (as
   maintained by `sources.health.HealthMonitor` during real collection)
   and, if it maps to a known `TargetOrganization`, re-runs the engine
   excluding the failed method's URL — letting ranking surface the next-best
   alternative automatically. A target with nothing left simply reports why,
   same as any other result; nothing is fabricated.

Every network-touching step (`prober`, `fetch_text`, `robots_checker`, the
Wayback client) is an injected callable, so `engine.py`/`continuity.py` have
no import of `urllib` at all and are fully tested with fakes (20 tests
covering the happy path, every failure branch, re-run idempotency,
exclusion-driven alternative selection, and continuity recovery — see
`research/tests/test_acquisition_engine.py`). `acquisition_intelligence/
live.py` is the one file that wires the real internet (`HttpFetcher` +
a live Wayback client) for a deployment with egress; `cli.py`'s
`discover-sources` subcommand runs it end-to-end.

**This development sandbox has no outbound network egress to arbitrary
hosts** (confirmed directly: `curl`/`WebFetch` both 403 on every target
site attempted, egress is allowlisted to PyPI/npm/anthropic.com only — see
the proxy status output referenced in `CURRENT_MISSION.md`). Running
`agx discover-sources` against the seed target catalog in this environment
correctly reports "no reachable domain" for every target — the honest,
expected result of the domain resolver refusing to trust an unprobed
domain, not a bug. The engine is complete, tested, and ready; it has not
yet produced a live-verified acquisition method for any of the twelve named
organizations because this sandbox cannot reach them, not because the
engine doesn't work.

### Source Registry (`sources/`)

Every `SourceSpec` carries the full charter field set: id, name, category,
country, language(s), supported entities/event types, access method,
authentication, license, terms-of-use URL, rate limits, retry policy,
collector + version, schema version, normalization/validation rule
references, conflict priority (who wins cross-source disputes) and
scheduling priority, plus three *independent* state axes:

- **`status`** (`SourceStatus`) — whether a collector may run at all:
  `IMPLEMENTED` / `PLANNED` / `NEEDS_KEY` / `TOS_REVIEW` / `DISABLED`.
- **`lifecycle_state`** (`LifecycleState`) — how much the rest of the
  platform trusts it: `CANDIDATE` -> `QUARANTINE` -> `EVALUATION` ->
  `TRUSTED` -> `CORE`. Distinct from `status`: a source can be
  `IMPLEMENTED` and still only `CANDIDATE` until it has run history.
- **`health_status`** (`HealthStatus`) — current operational health:
  `UNKNOWN` / `HEALTHY` / `DEGRADED` / `DOWN`, maintained by `health.py`.
- **`activation_status`** (`ActivationStatus`) — `ACTIVE` / `PAUSED`
  (held pending a credential/legal review or a health alert) / `RETIRED`.

Every source is independently replaceable: `collector`/`collector_version`
name which class serves the spec, so swapping an implementation is a
registry field change, not a code change at every call site.

### Collector Framework (`collectors/`)

The framework, not the collectors. Every collector inherits one interface
(`Collector.fetch() -> list[RawDocument]`, `Collector.parse(RawDocument) ->
CollectionBatch`) and automatically gets, from the framework rather than
from its own code: retry + backoff (`HttpFetcher`/`SourceSpec.retry_policy`),
rate limiting (`SourceSpec.rate_limit`), robots.txt enforcement, logging via
`RawDocument.validation_history`/`normalization_history`, quality metrics
(`quality.py`), provenance (`RawDocument` + `ProvenanceIndexRepository`),
versioning (`collector_version` + `RawDocument.schema_version`), and
parallel execution (each `Collector.run()` call is independent and
stateless beyond its own repositories, so running many concurrently needs
no framework change).

Collector *types* covered, per the charter's list:

| Type | How it's served |
|---|---|
| RSS/Atom | `RssNewsCollector` — one generic collector serving every feed-publishing outlet via `SourceSpec` configuration |
| REST/JSON API | `WorldBankCollector` — one class per API shape (shapes differ enough that a single generic JSON collector would either be too rigid or reinvent per-source mapping) |
| CSV download | `StooqPriceCollector`, `FredCsvCollector` |
| Excel (XLSX) | `ExcelSeriesCollector` — generic, column-mapped (openpyxl-backed) |
| PDF | `PdfDocumentCollector` — generic fetch/archive/text-extraction base (pypdf-backed); `parse()` stays source-specific by necessity |
| XML | served today by `RssNewsCollector` (Atom/RSS are XML dialects); a non-feed XML source is a `PdfDocumentCollector`-style generic base away if/when one is verified |
| JSON | see REST/JSON API row |
| Browser Automation | `BrowserAutomationCollector` — an honest `NotImplementedError` stub (see "What's still blocked" below) |
| Filesystem | `FilesystemCollector` — real and fully implemented: ingests files a human (or a future legitimate process) has placed on disk, same provenance standard as a network fetch |
| Archive Replay | `ArchiveReplayCollector` — `fetch()` returns previously-archived `RawDocument`s instead of hitting the network; `parse()` delegates to whatever collector currently owns the source, so replaying history through a fixed parser needs no new fetch |

### Source Discovery Engine (`discovery/`)

`DiscoveryEngine` finds candidate sources — RSS feeds (`<link rel=alternate>`
autodiscovery), PDF repositories (a page linking several PDFs, modeled as
one source, matching how Company IR / regulatory disclosure pages actually
work), structured dataset links (CSV/XLS/JSON/XML), and sitemap URLs. It
takes only already-fetched HTML/XML (the caller owns fetching, through the
same `HttpFetcher` that enforces robots.txt) and has **no import of
`SourceRegistry` or `SourceSpec` at all** — structurally, a discovery run
cannot register or trust anything. Turning a `SourceCandidate` into a real,
catalogued `SourceSpec` is the separate, explicit
`qualification.register_candidate` step, which always mints the new source
at `LifecycleState.CANDIDATE` / `SourceStatus.PLANNED` with conservative
priors, regardless of what the discovery heuristic found.

### Source Qualification Pipeline (`sources/qualification.py`)

Candidate -> Quarantine -> Evaluation -> Trusted -> Core. Promotion is
always mechanical, evidence-gated, and moves at most one stage per
evaluation:

- **Candidate -> Quarantine**: first successful collection run (proves
  reachability).
- **Quarantine -> Evaluation**: 5+ runs recorded (enough to start scoring).
- **Evaluation -> Trusted**: 20+ runs *and* composite reputation >= 0.70.
- **Trusted -> Core**: 100+ runs *and* composite reputation >= 0.85.
- Any stage is demoted one level immediately if `health_status` is `DOWN`
  — trust accrues slowly, and is lost immediately on the current signal.

Run-count/composite thresholds are declared policy (documented in
`qualification.py`), not a calibration result — there is no run history
yet to calibrate against (same honesty convention as the seed catalog's
declared reliability priors).

### Source Reputation Engine (`sources/reputation.py`)

`SourceMetrics` is a plain, versioned counter accumulator per source
(`SourceMetricsRepository`, `record_run()` called once per collection
attempt). `compute_reputation()` turns those counters into the charter's
nine dimensions — availability, accuracy, freshness, coverage, latency,
correction rate, duplicate rate, schema stability, historical usefulness —
plus a composite mean. A dimension with no observations yet is `None` and
excluded from the mean, never defaulted to an assumed value (the same rule
`quality.assess_quality`'s `consistency_score` already follows). This
closes the previously-open gap where `SourceRegistry.record_measured_quality()`
existed with nothing calling it: `CollectionService` now records a
`SourceMetrics` update and writes the resulting composite back to
`SourceSpec.data_quality_score`/`reputation_score` on every run.

### Source Health Monitoring (`sources/health.py`)

`HealthMonitor.evaluate_run()` is called once per collection attempt
(wired from `CollectionService`) with the concrete signals that run
produced, and detects: fetch failures, auth failures, robots.txt blocks,
parser exceptions, layout changes (a *previously-producing* source
suddenly parsing zero records — the measurable symptom, never a guessed
cause), schema drift (a new `schema_version` value observed), staleness
(freshness score below a floor), and consecutive-failure runs (3+ ->
`HealthStatus.DOWN`). Alerts (`HealthAlert`) are append-only and
resolvable, forming their own audit trail.

### Raw Archive (`collectors/raw.py` + `collectors/archive.py`)

Every collected artifact is stored forever, never overwritten. Text
formats (CSV/JSON/XML/RSS) live inline in `RawDocument.content_text`;
binary formats (PDF/Excel/images) go through `RawArchive`, a content-
addressed store keyed by sha256 under `<archive_dir>/<hash[:2]>/<hash>.bin`
— storing identical bytes twice is a no-op (the file already exists at
that path), which *is* the "never overwrite" rule enforced by
construction, not convention. Every `RawDocument` carries source id,
collector name+version, fetch timestamp, original URL, content hash,
schema version, and license, whether the payload is text or binary.

### Canonical Transformation

`Collector.parse()` is the transformation step: a pure function of one
`RawDocument` into canonical `PriceBar`/`MacroObservation`/`NewsItem`
candidates (`CollectionBatch`), replayable forever from the same archived
bytes. It never modifies the raw archive. Transformation is versioned via
`collector_version`, which is exactly what makes replay meaningful — a new
version's `parse()` reprocessing an old `RawDocument` is a deliberate,
tracked change, not a silent one.

### Provenance Layer (`collectors/provenance_index.py`)

Every materialized value traces back to source, collector, artifact,
transformation, timestamp, hash, and schema version. `RawDocument` already
carries that at the document level; `ProvenanceIndexRepository` extends it
to the *value* level — one `ProvenanceRecord` per materialized price bar /
macro observation / news item, keyed by `(artifact_type, key, record_date)`.
Re-materializing a value (a corrected re-fetch, a replay with a newer
parser) appends a new version rather than losing the old lineage.
`CollectionService` writes these automatically for every materialized
price bar and macro observation, closing a real prior gap: before this,
only news items carried their `raw_document_id` forward (via event
metadata); price/macro data reached the CSV layer with no per-value trace.

### Historical Replay (`collectors/replay.py` + `collectors/archive_replay.py`)

`ArchiveReplayCollector` wraps a real collector so its `fetch()` returns
already-archived `RawDocument`s instead of hitting the network, and its
`parse()` delegates to the real collector — meaning `CollectionService.run()`
needs no special case to replay history at all. `HistoricalReplayEngine`
is the convenience layer: `replay_source()` re-processes one source's full
archived history through today's parser (`CollectionService` is itself
idempotent about re-adding already-stored documents, so replay is safe to
run repeatedly), and `replay_all()` rebuilds every source with a live
collector wired in, reporting sources with no archived documents as
skipped rather than silently dropping them. This is what makes "changing
parsers must never require recollecting data" true: fix a bug in
`StooqPriceCollector.parse`, bump `collector_version`, replay every
historical Stooq `RawDocument` through the fixed parser — no new fetch.

### Quality is mechanical (`collectors/quality.py`)

`quality.py` computes the seven per-batch charter scores (coverage,
freshness, reliability, consistency, completeness, validation, confidence)
from measurable inputs; `consistency` is honestly `None` until a second
source covers the same values — never invented. `CollectionService`
refuses to materialize a batch whose composite confidence falls below a
configurable floor — "no downstream system may ignore data quality" is
enforced by withholding, not by passing degraded data through.

### Materialization

Validated price/macro/news batches are written into the local CSV layout
`MockDataProvider` already reads (aliased `LocalCsvDataProvider`). Collected
real data therefore flows into snapshots, the pipeline, and everything
downstream with zero further integration.

## Source catalog policy (honesty rules)

Every source named by the program is catalogued in the seed registry with
an explicit status:

- **IMPLEMENTED** — a real collector exists, tested against recorded-format
  fixtures; runs live wherever network egress exists. Seeded at
  `LifecycleState.TRUSTED` (engineering-verified, not yet CORE — CORE needs
  measured run history the qualification pipeline hasn't accumulated yet).
- **PLANNED** — catalogued with known access details; collector not yet
  written (most are one configuration of an existing generic collector,
  e.g. an RSS feed URL). Seeded at `LifecycleState.CANDIDATE`, `ACTIVE`.
- **NEEDS_KEY** — reserved for a source whose only access route requires a
  user-registered credential. **No seed source currently uses this
  status.** The project owner's explicit decision: this platform is
  scoped to sources collectable with no registration/credential of any
  kind, so a capability whose only real strategy needs a key is left
  honestly uncovered rather than catalogued and left waiting indefinitely.
  `AlphaVantageCollector`/`FmpCollector` and the `alphavantage`/`fmp`/
  `polygon`/`tiingo` catalog entries existed under this status and were
  removed for exactly this reason (see "No API-key sources" below) — not
  because their collector code was wrong. The status value itself stays
  in `SourceStatus` as a structural classification (a source that turns
  out to be genuinely free but happens to require a no-cost registration
  step is a decision to revisit explicitly, not a status this codebase
  auto-assigns).
- **TOS_REVIEW** — access exists but redistribution/automation terms are
  ambiguous (Yahoo Finance unofficial API, Investing.com, TradingView,
  Google Trends automation, LinkedIn). Not collected until the review
  clears — "respect Terms of Service" is a hard rule, so ambiguity blocks.
  Seeded at `CANDIDATE`/`PAUSED`.
- **Declared priors, not measurements.** `reliability_score` etc. in seed
  entries are documented starting priors (official regulator > exchange >
  aggregator > social), replaced by measured values as collection history
  accumulates via `reputation.py`. `data_quality_score` starts `None` — it
  is only ever measured.

## Implemented collectors (v1)

| Collector | Source(s) | Why first |
|---|---|---|
| `StooqPriceCollector` | Stooq daily CSV (`stooq.com/q/d/l/?s=...&i=d`) | Free, no auth, explicit CSV download endpoint, permissive personal-use terms; covers EGX symbols (`.eg` suffix convention) and global benchmarks (indices, commodities, FX). |
| `FredCsvCollector` | FRED `fredgraph.csv?id=SERIES` | Free, no auth for CSV export, US-government open data; covers oil, dollar index, treasury yields, and other global-macro series the vision requires. |
| `WorldBankCollector` | World Bank v2 API (`api.worldbank.org/v2/country/EGY/indicator/{code}`) | Free, no auth, canonical/stable documented public API (same confidence tier as FRED); Egypt-specific annual macro indicators (inflation, GDP growth, reserves, trade, etc.) not otherwise covered. |
| `RssNewsCollector` | Any RSS/Atom feed | One generic, layout-tolerant collector covers every news source that publishes a feed (most named Arabic/English outlets); per-source configuration lives in the registry entry, not in code. |

All parse recorded-format fixtures in tests (clearly labeled synthetic
fixtures in the real wire format — never presented as collected market
data). Live fetching uses stdlib urllib with proxy support, per-source
rate limiting, bounded retries with backoff, timeout, and a robots.txt
check for HTML-ish fetches; it is exercised in deployment, not in unit
tests (this sandbox has no outbound egress for live collection, only for
package installs).

### No API-key sources

Earlier phases carried `AlphaVantageCollector`/`FmpCollector` — fully
implemented and unit-tested against each API's documented public JSON
response shape — with their seed catalog entries (`alphavantage`, `fmp`)
staying `NEEDS_KEY` pending a user-supplied key, plus two further
placeholder entries (`polygon`, `tiingo`) with no collector code at all.
The project owner's explicit decision: the platform relies exclusively on
genuinely free, no-registration sources, so waiting on a key indefinitely
serves no goal, and a capability whose only real strategy requires one
should be dropped rather than left permanently blocked. All four catalog
entries and the two collector classes (plus their tests) were removed.
`Capability.PRICE_DATA`/`Capability.FINANCIAL_STATEMENTS`'s declared
candidate pools (`acquisition_intelligence/capability.py`) no longer name
them either. Any future capability gap must be closed with a genuinely
free source (no registration step of any kind), or left honestly
uncovered — never with a `NEEDS_KEY` catalog entry.

## What's still blocked

The 16-collector build order in the program's implementation policy
(EGX, Company IR, Mubasher, Reuters, Zawya, Enterprise, Asharq Business,
CNBC Arabia, Trading Economics, CBE, FRA, CAPMAS, Yahoo Finance, FMP,
AlphaVantage, TradingView News) breaks down as:

- **FMP, AlphaVantage** — removed from the catalog per the no-API-key
  policy above; no longer part of this program at all.
- **Yahoo Finance, TradingView News** — `TOS_REVIEW`; automation terms are
  ambiguous, so collection stays blocked until a human legal/ToS review
  clears them. Not a coding gap.
- **EGX, CBE, FRA, CAPMAS, Company IR, Mubasher, Reuters, Zawya,
  Enterprise, Asharq Business, CNBC Arabia, Trading Economics** — `PLANNED`.
  Every one of these needs a *verified* real endpoint (an exact RSS feed
  URL, an exact CSV/API download path) before a `SourceSpec` can honestly
  claim `IMPLEMENTED`. This is now the Acquisition Intelligence Engine's
  job, not a human's: `agx discover-sources` runs exactly this verification
  for every one of these targets end to end (domain resolution → discovery
  → legality/stability/historical checks → ranking → auto-generated,
  still-`PLANNED` `SourceSpec`). It is fully built and tested (20 tests in
  `test_acquisition_engine.py` covering the complete happy path with fakes)
  but **this development environment has no outbound network egress to
  arbitrary hosts** — confirmed directly (`curl`/`WebFetch` 403 on every
  target site attempted; only PyPI/npm/anthropic.com are allowlisted) — so
  a live run in this sandbox correctly reports "no reachable domain" for
  all twelve. This codebase's own explicit rule (see CLAUDE.md, "never
  guess a URL") also forbids fabricating an endpoint from memory the way a
  textbook-stable API like FRED's or the World Bank's can be trusted, which
  is exactly why the engine *verifies* rather than assumes. **This is the
  genuine, named external dependency the build order's stop condition
  anticipates**: the moment this platform runs somewhere with egress,
  `agx discover-sources` (or a scheduled `AcquisitionContinuityMonitor` run)
  does this verification autonomously, and the generic collectors that
  would serve most of these (`RssNewsCollector` for the news outlets,
  `ExcelSeriesCollector`/`PdfDocumentCollector` for the regulator bulletins)
  already exist and are tested — turning a discovered method into a
  collectable source is then the "small adapter" the platform promises,
  not new engineering.

## Discovery workflow (continuous, scheduled, evidenced)

The moment this platform runs somewhere with real network egress
(GitHub Actions), the paragraph above's "not a human's job" claim needed
to actually run somewhere on a schedule, not stay a manually-invoked CLI
command. `.github/workflows/discovery.yml` is that schedule — a
completely separate workflow from `deploy-pages.yml`'s production
pipeline (own trigger, own branch, never blocks or slows the production
deploy) that runs weekly (and on manual `workflow_dispatch`):

1. **Scope**: only catalogued `PLANNED`/`CANDIDATE` sources that have a
   matching `TargetOrganization` and are not a per-constituent marker or a
   provider leg already wired inside a composite collector (`integrated_via`
   — its real endpoint already exists in code; discovery would be
   redundant). `acquisition_intelligence.discovery_report.plan_discovery_targets`
   makes this split explicit and honest: a `PLANNED` source with no
   `TargetOrganization` yet is reported (`not_targeted`), never given a
   fabricated domain to try.
2. **Verification**: reuses the exact same `AcquisitionIntelligenceEngine.
   run_for_target` this document already describes above — real domain
   resolution, real robots.txt/legality checks, real stability/historical
   scoring, real qualification-pipeline promotion on a successful run
   (`CANDIDATE` → `QUARANTINE`). Nothing new is invented here; the workflow
   just runs the existing engine on a schedule instead of by hand.
3. **Incremental, not repetitive**: `agx discover-planned-report` (the
   `discover-planned-report` CLI subcommand,
   `acquisition_intelligence.discovery_report.run_discovery_report`) caches
   each source's last real result (`discovery_history.json`) with a 30-day
   TTL. A source is only re-probed when the cache expired, its target's own
   inputs changed (a new domain hint, for instance — fingerprinted), or a
   run explicitly forces it (`--force id1,id2`, wired to `workflow_dispatch`'s
   `force` input). A cached row still appears in the report every run
   (`from_cache: true`), so the report is always a complete picture.
4. **Evidenced, structured output**: three JSON artifacts per run —
   `discovery_report.json` (one row per in-scope source: previous/current
   status, discovered endpoints, verification result, failure reason,
   evidence, a recommendation, and a confidence score), `discovery_metrics.json`
   (aggregate counts), and `endpoint_candidates.json` (every ranked
   candidate considered, not just the winner) — all under
   `research/data/discovery/` (see its own `README.md`).
5. **Never a direct commit to `main`, never an automatic promotion**: the
   workflow commits its output only to a dedicated `discovery/latest`
   branch and opens/updates one standing pull request against `main` — a
   human always reviews before this evidence lands on `main`. Flipping a
   `SourceSpec.status` to `IMPLEMENTED` is never done by this workflow: per
   `AD-16`/`AD-24`, that still requires an engineer to write and test a
   concrete collector against the verified endpoint's real response shape
   (except for `RSS_FEED`, where `RssNewsCollector` is already a generic,
   tested collector — the PR's summary flags exactly this case as "ready
   for a maintainer to review", the same precedent already used for
   Enterprise/Al Borsa/Masrawy/FRA/Sky News Arabia, but the flip itself is
   still a reviewed, separate commit).

## Legal compliance (enforced, not aspirational)

- `FetchPolicy.respect_robots` blocks fetches disallowed by robots.txt.
- No collector authenticates, bypasses paywalls, or touches restricted
  data; per the project owner's decision, no source is catalogued at all
  if its only route requires a credential (see "No API-key sources").
- Every `SourceSpec` records `license` and `terms_of_use_url`; TOS_REVIEW
  status blocks collection outright.
- Rate limits are per-source configuration honored by the fetcher.
- `BrowserAutomationCollector` is an honest `NotImplementedError` stub —
  no scripted browser interaction has a verified, ToS-cleared target yet.

## Deployment note

This development environment has no outbound network egress for live
collection or discovery (package installs from PyPI/npm do work; direct
`curl`/`WebFetch` to arbitrary hosts return 403 by policy), so live
fetching and the Acquisition Intelligence Engine were both validated at the
parser/protocol/orchestration level against recorded-format fixtures and
fakes; first live runs (`agx collect`, `agx discover-sources`) happen
wherever the runtime is deployed with egress (a System-18 deployment
decision).
