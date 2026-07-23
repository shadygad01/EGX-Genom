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
              engine.py -- AcquisitionIntelligenceEngine orchestrator
              continuity.py -- AcquisitionContinuityMonitor (re-discover on DOWN)
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
   discovery logic duplicated, the same engine System 03 already built.
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
| REST/JSON API | `WorldBankCollector`, `AlphaVantageCollector`, `FmpCollector` — one class per API shape (shapes differ enough that a single generic JSON collector would either be too rigid or reinvent per-source mapping) |
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
- **NEEDS_KEY** — free tier requires a user-registered API key
  (AlphaVantage, FMP, Polygon, Tiingo). Keys are credentials: a business/
  user action, never fabricated or bypassed. Collector *code* can exist and
  be fully tested against the API's public documented shape (see
  AlphaVantage/FMP below) without the source becoming collectable — seeded
  at `CANDIDATE`/`PAUSED`.
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

### Code-complete but not yet collectable

`AlphaVantageCollector` and `FmpCollector` are fully implemented and
unit-tested against each API's documented public JSON response shape
(`Meta Data`/`Time Series (Daily)` for AlphaVantage; `symbol`/`historical`
for FMP) — but their seed catalog entries stay `NEEDS_KEY` because no API
key exists to actually collect with. This is the platform's "small
adapter" promise made concrete: once a user supplies their own free-tier
key, activating the source is a `SourceSpec.status` flip plus passing the
key into the constructor — no new parsing code.

## What's still blocked

The 16-collector build order in the program's implementation policy
(EGX, Company IR, Mubasher, Reuters, Zawya, Enterprise, Asharq Business,
CNBC Arabia, Trading Economics, CBE, FRA, CAPMAS, Yahoo Finance, FMP,
AlphaVantage, TradingView News) breaks down as:

- **FMP, AlphaVantage** — code-complete, `NEEDS_KEY` (above).
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

## Legal compliance (enforced, not aspirational)

- `FetchPolicy.respect_robots` blocks fetches disallowed by robots.txt.
- No collector authenticates, bypasses paywalls, or touches restricted
  data; NEEDS_KEY sources idle until the user supplies their own key.
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
