# Phase Status — MASTER_PROMPT.md's 18 Systems

The living audit the charter requires. Updated whenever a system's status
changes. Status: **DONE** (Definition of Done met, with any remaining gaps
being external/business-blocked and named) / **PARTIAL** / **NOT STARTED**.

Cross-cutting note on what DONE means here: the *architecture and
engineering* are production-shaped and fully tested; the platform still
runs on placeholder market data. Every conclusion the system produces is
only as real as its data feed, and the single largest open item for a true
Production 1.0 is the licensed EGX data vendor — a business decision
(cost/coverage/contract) explicitly reserved for the user. See
`docs/ROADMAP.md`.

Current acquisition registry after the live UN Statistics and CAPMAS API
connections: **52 sources (12 IMPLEMENTED / 28 PLANNED / 4 NEEDS_KEY /
8 TOS_REVIEW)**. This current count supersedes older counts embedded in the
long-form phase evidence below.

| # | System | Status | Evidence / remaining gaps |
|---|--------|--------|---------------------------|
| 01 | Foundation | **DONE** | `domain/`, `storage/`, `config.py`; reused unmodified by every later store; CI green. |
| 02 | Data Platform | **DONE** | Provider/fallback interfaces, snapshots(+repo), quality checks, split/dividend adjustment, plus the full Data Acquisition Platform (`sources/`+`discovery/`+`collectors/`+`acquisition_intelligence/`, see `docs/DATA_ACQUISITION.md`): a 52-source registry (11 IMPLEMENTED / 29 PLANNED / 4 NEEDS_KEY / 8 TOS_REVIEW) across 9 categories with three independent state axes (status/lifecycle_state/health_status); a discovery engine that proposes candidates from RSS-autodiscovery/PDF-repository/structured-dataset/sitemap/API-doc scans without ever trusting them; an evidence-gated Candidate→Quarantine→Evaluation→Trusted→Core qualification pipeline; a 9-dimension reputation engine and health monitor wired into every collection run; real collectors for Stooq, FRED, World Bank, UN Statistics SDG (macro), GDELT, and generic RSS/Atom (news), including live-verified Enterprise, FRA, Al Borsa and Masrawy Economy configurations, plus AlphaVantage/FMP code-complete pending a user API key; generic collector-type frameworks for PDF, Excel, Filesystem, Browser-automation (honest stub), and Archive Replay. A content-addressed Raw Archive stores binary artifacts forever; a per-value Provenance Index traces every materialized price bar/macro observation back to its source/collector/raw-document/hash/schema-version; a Historical Replay engine rebuilds materialized data from archived documents alone when a parser changes. **New this phase: the Acquisition Intelligence Engine** (`acquisition_intelligence/`) — given only an organization's identity (never a manually supplied URL), it resolves a verified-reachable domain, discovers candidate acquisition methods, verifies legality (robots.txt + ToS heuristics, scraping never auto-clears)/stability (URL-shape + probe consistency)/historical availability (Wayback Machine APIs), ranks and selects the best, auto-generates a still-`PLANNED` `SourceSpec`, registers it, and begins qualification; `AcquisitionContinuityMonitor` re-runs discovery automatically for any source whose health goes `DOWN`. Fully tested with fakes (20 tests covering the complete pipeline); wired into `cli.py`'s `discover-sources` subcommand. Blocked-external: licensed EGX vendor for guaranteed-accurate real-time/official data (business decision) remains the gap this doesn't close; the engine itself performs live, verified discovery wherever the target permits access. **New this phase: priority-ordered catalog processing** (`AcquisitionIntelligenceEngine.run_catalog`, `TargetOrganization.priority`) matching the project owner's explicit business-value order (EGX official → EGX30/EGX70 company Investor Relations → CBE/FRA/CAPMAS/Enterprise/Mubasher/Zawya/Reuters/Trading Economics → everything else discovered), plus `generate_company_ir_targets()` (one real target per EGX30 constituent, expanding the previously-inert `company_ir` marker entry) and `discover_company_directory_links()` (extracts a company's own homepage link from an already-fetched directory page by real anchor-text matching, letting a resolved exchange/regulator homepage supply real per-company hints instead of guessing ~100 corporate domains). See "Production Execution Phase" below. |
| 03 | Event Platform | **DONE** | Fingerprint identity, taxonomy/ontology, entity resolution, dedup/conflict/lifecycle, `EventPlatform` sole write path, graph projection. Blocked-external: political/technical feeds, NLP entity linking. |
| 04 | Market Memory | **DONE** | `MarketState` (snapshot+universe+sectors+events+session), `TradingCalendar` (fixed holidays as rules; movable as explicit placeholder table). Blocked-external: authoritative movable-holiday dates. |
| 05 | Knowledge Graph | **DONE** | Versioned nodes/edges, provenance-derived builder, shortest-path + n-hop subgraph queries. Deferred by choice: dedicated graph DB (swap behind `Repository[T]` when scale demands). |
| 06 | Alpha Genome | **DONE** | Immutable genes, `mutate()` (single-parent), `merge()` (multi-parent synthesis), lineage walk, status machine; never overwrites. |
| 07 | Research OS | **DONE** | TaskGraph/Artifacts/Sessions plus `DailyResearchPipeline` — the full 8-gate walk wired to real validators, board, causal gate, adversarial scientist, genome, papers, graph. End-to-end tested incl. rejection honesty and determinism. |
| 08 | Scientist Framework | **DONE** (5 of 8 agents real) | MarketStructure, Macro, CorporateEvents, Liquidity, TechnicalStructure real; News/FinancialPerformance/HistoricalPatterns are honest stubs, all data-blocked (NLP, fundamentals feed, long history). Adversarial: 6 of 9 attacks real; 3 data/harness-blocked, reported `attempted=False`. |
| 09 | Feature Discovery | **DONE** | Three autonomous generators (pairwise correlation, momentum, volatility) over three registered feature definitions; candidates versioned+evidenced. |
| 10 | Experiment Factory | **DONE** | Statistic dispatch by asset arity; CV/bootstrap/walk-forward/OOS/sensitivity real (scipy-backed); stress adapter; Monte Carlo an explicit placeholder (needs a simulator — research decision). |
| 11 | Validation Framework | **DONE** | `SignificanceThresholdValidator`, `NaiveDirectionalBacktester` (costs explicitly out of scope, stated), `HistoricalWorstWindowStressTester` (scenario located in real data, not simulated). Deferred: cost-aware portfolio-level backtesting (with 15's future optimizer). |
| 12 | Review Board | **DONE** (4 of 5 reviewers real) | Statistician, Risk, Economist (structural coherence, not economic truth — stated), PeerValidator (independent replication). Historical reviewer data-blocked. Board wired into the pipeline before `promote()`. |
| 13 | Runtime Engine | **DONE** | `RuntimeEngine.run_range`: deterministic, per-day failure isolation, non-trading days recorded not skipped silently, persistent run ledger. Now the core of `production.pipeline.ProductionPipeline`'s Research Pipeline stage — see "Production Execution Pipeline" below. OS-level scheduling = deployment config (18). |
| 14 | Prediction Intelligence | **DONE** (v1) | `KnowledgeWeightedHorizonModel`: predictions derived exclusively from promoted knowledge; no knowledge → no prediction. Trained statistical models deferred until years of real data exist (data-blocked, would otherwise be fabricated science). |
| 15 | Portfolio Intelligence | **DONE** (v1) | `PortfolioConstructor`: risk-adjusted confidence-discounted scoring, capped proportional weights, cash fallback, full explanation. Deferred: covariance-based optimization (needs real data depth). |
| 16 | Explainability Engine | **DONE** | Six-question `Explanation` with structured `evidence_refs` everywhere; `similar_historical_cases` populated from real recorded events via the Event Platform. |
| 17 | Continuous Learning | **DONE** (v1) | `ContinuousLearningMonitor`: realized performance recorded on knowledge+genes from real later-window data; mechanical sign-disagreement retirement policy with audited reasons. |
| 18 | Production Infrastructure | **PARTIAL** | Engineering-closeable parts done: integrity-checked backup/verify/restore, CLI (`run`/`status`/`backup`/`restore`/`discover-sources`/`collect`), the first production execution pipeline (`agx run` — see "Production Execution Pipeline" below), Dockerfile, CI. Business-blocked: cloud provider + payment, secrets management service, managed scheduling, API authentication context, monitoring/alerting stack. Named in `docs/ROADMAP.md`. |

## What Production 1.0 still needs (all business-blocked)

1. **Licensed EGX market data vendor** — the single gating decision.
2. Cloud/deployment target + secrets management + scheduler (18).
3. Authoritative EGX holiday calendar + universe/sector feeds (04/02).
4. Optional data feeds unlocking the remaining stubs: news NLP source,
   fundamentals feed, long-history archive (08/12 stragglers).

Everything engineering-closeable without those inputs is closed and tested
(477 Python tests + 33 TypeScript tests green).

## Dashboard dual-provider architecture (post-Data-Acquisition-Program)

The web dashboard (`api`/`web`, presentation layer) now runs on a
`DashboardDataProvider` abstraction — `StaticJsonProvider` (GitHub Pages:
JSON artifacts generated by the real research pipeline) and `ApiProvider`
(a hosted `api/`), both serving the exact same eight resources
(knowledge/events/patterns/recommendations/market_state/runtime_metrics/
system_status/source_registry) from the exact same pydantic-derived
contracts. See `docs/ARCHITECTURE.md`'s "Dashboard data providers"
section for the full design. This doesn't correspond to a new charter
system — it's a presentation-layer capability enabling the already-DONE
research engine's real output to reach a static deployment target with no
backend, which the charter's System 18 (Production Infrastructure) never
required in the first place.

## Data Acquisition Platform (post-Epoch-II, within System 02's scope)

Per the standing charter, the next objective after all 18 systems reached
DONE/PARTIAL was not more AI — it was building the largest legally
accessible free research dataset for EGX, since no research conclusion can
outrun its data. A first pass closed the *engineering* half of the source
registry + 3 collectors; this pass built the full platform around it —
the infrastructure that makes adding a source trivial, not just more
one-off collectors:

- `docs/DATA_ACQUISITION.md` — full design (source registry schema incl.
  lifecycle/health/activation state, collector architecture including
  every named collector type, discovery engine, qualification pipeline,
  reputation engine, health monitoring, raw archive, provenance layer,
  historical replay, quality scoring, legal-compliance enforcement in
  code, not just policy).
- 51 sources catalogued across all 9 named categories (Official, Company,
  Market Data, News, Arabic News, Macroeconomic, Global Markets,
  Alternative, Research); honestly split IMPLEMENTED (5) / PLANNED (34) /
  NEEDS_KEY (4) / TOS_REVIEW (8).
- 4 real collectors (Stooq, FRED, World Bank, generic RSS/Atom) fully
  tested against recorded-format fixtures; 2 more (AlphaVantage, FMP)
  code-complete and tested against each API's documented shape, blocked
  only on a user-supplied key (no live network calls in the test suite —
  this sandbox has no outbound egress for live collection; live fetching
  is a deployment-time concern only).
- Generic collector-type frameworks beyond CSV/JSON/RSS: `PdfDocumentCollector`
  (pypdf-backed text extraction), `ExcelSeriesCollector` (openpyxl-backed,
  column-mapped), `FilesystemCollector` (real, network-independent),
  `BrowserAutomationCollector` (honest `NotImplementedError` stub — no
  ToS-cleared target exists yet), `ArchiveReplayCollector`.
- `discovery/`: a Source Discovery Engine (RSS autodiscovery, PDF-repository
  scan, structured-dataset scan, sitemap scan) that structurally cannot
  register or trust a source itself — no import of `SourceRegistry` at
  all; only the explicit `qualification.register_candidate` bridges a
  finding into the catalog, always at Candidate/PLANNED.
- `sources/qualification.py`: evidence-gated Candidate→Quarantine→
  Evaluation→Trusted→Core promotion, one stage at a time, demoted
  immediately on a DOWN health signal.
- `sources/reputation.py` + `sources/health.py`: the charter's 9 reputation
  dimensions computed from real per-run counters, and automatic detection
  of fetch/auth failures, layout changes, schema drift, and staleness —
  both wired into `CollectionService` on every run, closing the prior gap
  where `SourceRegistry.record_measured_quality()` had nothing calling it.
- `collectors/archive.py` (content-addressed, write-once binary blob store)
  + `collectors/provenance_index.py` (per-value source/collector/raw-doc/
  hash/schema-version trace for price bars and macro observations, not
  just news) + `collectors/replay.py`+`archive_replay.py` (rebuild
  materialized data from archived documents alone when a parser changes,
  with no new fetch).
- Remaining catalogued-but-uncollected sources are blocked on exactly one
  of: endpoint verification (PLANNED — the 12 named official/company/
  regional-news sources from the program's build order; unavailable from
  this no-egress dev sandbox and blocked by this codebase's own
  anti-guessing rule, not a business decision), a user-registered API key
  (NEEDS_KEY — business decision: which paid/free-tier key to obtain), or
  ToS ambiguity around automated collection/redistribution (TOS_REVIEW —
  business/legal decision). None of these are silently skipped; each is
  named in the registry with its blocking reason.

## Acquisition Intelligence Engine (post-Data-Acquisition-Platform, within System 02's scope)

The standing instruction after the platform above: the system must never
require a manually specified endpoint. This phase built the subsystem that
makes that true — `acquisition_intelligence/` (see `docs/DATA_ACQUISITION.md`'s
dedicated section):

- `target.py`: `TargetOrganization` — identity only (name/category/country/
  optional public-brand domain hints), never a hand-picked URL; seeded for
  all 12 of the mission's named organizations, each linked to its existing
  `SourceSpec` catalog entry via `existing_source_id`.
- `domain_resolution.py`: `HeuristicDomainResolver` — every candidate domain
  (hint or name-derived guess) is independently probed for reachability;
  nothing is trusted without a successful probe.
- `legality.py`/`stability.py`/`historical.py`: three independent,
  mechanical verifications per discovered candidate — robots.txt + ToS
  keyword heuristics (scraping never auto-clears), URL-shape + repeated-
  probe consistency, and Wayback Machine snapshot span (a free, no-key,
  decades-stable API, same confidence tier as FRED/World Bank).
- `ranking.py`/`config_generation.py`: legality is a hard gate (never
  scored down and reconsidered); the surviving candidates are ranked by a
  stability/historical-availability composite, and the winner becomes an
  auto-generated `SourceSpec` — collector class suggested where
  unambiguous, but `status` always stays `PLANNED`, never silently flipped
  to `IMPLEMENTED`.
- `engine.py`: `AcquisitionIntelligenceEngine` orchestrates all of the
  above end to end and begins qualification (records an initial
  reachability run, evaluates promotion) on success.
- `continuity.py`: `AcquisitionContinuityMonitor` watches for any source
  gone `HealthStatus.DOWN` and automatically re-runs discovery excluding
  the failed method, to find an alternative.
- `live.py`: the one file wiring real network access (`HttpFetcher` +
  a live Wayback client) for a deployment with egress; every other module
  is network-free and tested with fakes (20 tests in
  `test_acquisition_engine.py` alone, plus per-module coverage for every
  verification step — 51 new tests total this phase, 397 Python tests
  green overall, up from 346).
- `cli.py discover-sources`: runs the engine (and continuity recovery)
  against the full seed target catalog.

**Verified live, honestly**: this development sandbox has no outbound
network egress to arbitrary hosts (`curl`/`WebFetch` both return 403 for
every target site attempted — confirmed directly, not assumed; only PyPI/
npm/anthropic.com are allowlisted). Running `agx discover-sources` against
all 11 non-per-constituent seed targets in this sandbox correctly reports
"no reachable domain found" for each — the domain resolver refusing to
trust an unprobed domain, exactly as designed, not a bug or a fabricated
result. The engine is complete and will perform real, verified discovery
the first time it runs somewhere with outbound internet access.

## Production Execution Pipeline (post-Acquisition-Intelligence-Engine)

The mission after the Acquisition Intelligence Engine was explicit: stop
building architecture and frameworks, wire everything already built into
one production execution pipeline that proves AGX can run an end-to-end
production research cycle, using mock/replay providers standing in for a
live collector (not yet built — that's the next mission).

- `agx_research.production` (new package): `ProductionPipeline` wires
  every stage the mission specifies, in order — Entry Point, Source
  Registry, Discovery Engine, Collector Selection, Collector Execution,
  Raw Archive, Canonical Transformation, Validation, Event Platform,
  Market Memory, Knowledge Base, Research Pipeline, Genome, Investment
  Case Generator, Dashboard Artifact Generator, Mission Control Update,
  Execution Report — by composing `CollectionService`, `DailyResearchPipeline`,
  `RuntimeEngine`, `RecommendationService`, `PortfolioConstructor`,
  `write_dashboard_artifacts`, and the Acquisition Intelligence Engine's
  continuity monitor exactly as they already exist. Nothing was redesigned;
  this closed a real, previously-unnoticed gap instead: `agx collect`
  materialized data into `--data-dir`, but `agx run` always read from a
  separate, static `--mock-data` directory regardless — the two were never
  actually connected. They are now: the pipeline's own `MarketMemory`
  reads from `--data-dir`, the same root its own Collector Execution stage
  writes to.
- **Collector Execution without live collectors**: per the mission's own
  instruction not to build live collectors yet, `collector_plan.py` runs
  the platform's *real* `Collector` subclasses (`StooqPriceCollector`,
  `FredCsvCollector`, `RssNewsCollector`, `WorldBankCollector`) against
  either a `MockFetcher` (clearly-synthetic, wire-format-correct content —
  the same numbers `research/data/mock/` already uses, reformatted into
  each source's real CSV/JSON/RSS shape) or an `ArchiveReplayCollector`
  reading previously-archived documents. `CollectionService.run()` is
  called identically either way — the pipeline cannot tell live data from
  mocked or replayed data, because nothing about the call site changes.
- **Failure isolation**: every stage is wrapped independently
  (`ProductionPipeline.run`'s `execute()` helper); a stage that raises is
  recorded `FAILED` with its error and execution continues to every
  remaining stage regardless, exactly matching `RuntimeEngine.run_day`'s
  existing per-day isolation. `StageStatus.PARTIAL` is the honest middle
  state when some but not all of a stage's work fails (e.g. one collector
  among several).
- **Execution Report** (`execution_report.json`): start/end/duration, every
  stage's status/detail/error, artifacts generated, errors, warnings,
  skipped stages, and knowledge/genome/event count deltas for the run.
- **Mission Control tracking** (`mission_status.json` +
  `PipelineExecutionRepository`, a versioned execution history): pipeline
  status, pipeline version, last successful/failed pipeline, current
  execution mode, execution duration, artifacts produced, knowledge/genome
  updated — computed entirely from `ExecutionReport`s already produced,
  no new computation.
- New artifacts alongside the existing eight dashboard files:
  `investment_cases.json` (the Investment Case Generator — composes the
  already-existing but previously never-wired `RecommendationService` +
  `PortfolioConstructor`), `collector_status.json`, `runtime_status.json`,
  `dashboard_metrics.json`, `mission_status.json`, `execution_report.json`
  — 14 artifacts total, all validated by an extended
  `dashboard.validate.validate_dashboard_artifacts` (the six new ones
  optionally, since `export-dashboard` alone still only produces the
  original eight).
- `agx run` is now the single production entrypoint: one command executes
  the complete chain (previously `run` only executed the research pipeline
  against static mock data, and dashboard export was a separate command).
  `--mode mock` (default) or `--mode replay`; `.github/workflows/
  deploy-pages.yml` now calls this one command instead of two.
- 16 new integration tests (`test_production_pipeline.py`) verify: every
  stage runs in the mission's exact order; collected data actually reaches
  the research pipeline; replay reproduces the same research outcome as
  the original mock run; the raw archive doesn't duplicate documents on
  replay; replay against an empty archive is honest, not fabricated;
  deterministic execution (same inputs -> same collected values -> same
  hypothesis count); failure isolation at both the stage level and the
  per-collector level; every artifact is written and validates; Mission
  Control tracks execution history across runs; the CLI entrypoint works
  end to end. 413 Python tests green overall (up from 397); 33 TypeScript
  tests unaffected; `ruff` clean.

## Production Execution Phase (post-Production-Pipeline)

Architecture, frameworks, and generic abstractions are considered finished
per the project owner's explicit instruction. This phase's job was not to
build more of them, but to advance AGX's actual objective — continuously
discovering statistically valid investment opportunities for EGX30/EGX70 —
strictly in the business-value order the project owner named: EGX official
→ EGX30 Investor Relations → EGX70 Investor Relations → CBE → FRA → CAPMAS
→ Enterprise → Mubasher → Zawya → Reuters → Trading Economics → anything
else the Acquisition Intelligence Engine discovers on its own. World Bank/
IMF/FRED are explicitly demoted to enrichment-only, not primary milestones.

**What closed**: priorities 1 and 4–11 were already seeded
`TargetOrganization`s from the prior mission; priority 2/3 (company
Investor Relations) had only a marker entry with no real per-company
expansion. This phase built:

- `TargetOrganization.priority` + `AcquisitionIntelligenceEngine.
  run_catalog()`: every target now runs in the exact business-value order
  above, lowest-priority-number first.
- `generate_company_ir_targets(companies)`: expands the `company_ir`
  marker into one real target per EGX30 constituent (10 today, from
  `universe.EGX30_UNIVERSE_PLACEHOLDER`; scales automatically to a real,
  complete list with no code change) — deliberately **no fabricated
  domain hints**, since guessing ~10-100 individual corporate domains from
  training-data recall would be exactly the kind of fabrication this
  program's rules forbid (unlike the long-established, unambiguous global
  brand-domain associations already used for Reuters/CBE/etc.).
- `discovery.discover_company_directory_links()`: a new, real discovery
  heuristic that matches anchor text against known company names on an
  already-*fetched* page, letting an exchange's own listed-company
  directory (once reachable) supply genuine per-company hints —
  `run_catalog` wires this so whichever named/official target resolves
  first feeds discovered hints into not-yet-run company targets.
- Fixed a genuine, pre-existing architectural defect discovered while
  building this: `agx_research.discovery` failed to import if it was the
  very first AGX module touched in a fresh process (a real circular
  package dependency between `sources.qualification` and
  `discovery.candidate`, previously unhit because nothing existing imported
  `discovery` first). Fixed with a `TYPE_CHECKING`-guarded import (the
  module already used `from __future__ import annotations`, so this is a
  zero-runtime-behavior-change fix); regression-tested with a fresh-
  subprocess import check.
- `cli.py discover-sources` now runs the full expanded catalog (org
  targets + generated company IR targets, ~20 targets today) through
  `run_catalog` by default, in priority order.
- 14 new tests (427 total, up from 413), all offline.

**Verified live, again, honestly**: the full 21-target priority-ordered
catalog (EGX official + 10 EGX30 company IR targets + 10 named
organizations) was run against the real (blocked) network and correctly
reported "no reachable domain" for every one, in the exact priority order
specified, with no crash — the third independent confirmation across three
missions that this sandbox's network policy blocks arbitrary outbound
hosts uniformly (not source-specific), including domains already
`IMPLEMENTED` and previously believed reachable in principle (`stooq.com`,
`fred.stlouisfed.org`, `api.worldbank.org` were re-checked this phase too).

**Named, real blockers (not engineering gaps)**:
1. No outbound network egress from this sandbox to any arbitrary host —
   an environmental limitation, confirmed directly three times now.
2. No real, complete, verified EGX30/EGX70 constituent list exists in this
   codebase (only a 10-company EGX30 placeholder, no EGX70 list at all) —
   the correct source is EGX's own official site (blocked by #1) or a
   user-supplied verified list (a named business decision, per this
   phase's own stop conditions). Fabricating one from training-data recall
   was deliberately not done.

Everything engineering could complete without those two inputs has been
completed. See `CURRENT_MISSION.md` for the full statement and
`NEXT_MISSIONS.md` for exactly what runs automatically the moment either
clears.

**One more genuinely unblocked item, closed while auditing for further
engineering-closeable work**: TD-16's remaining half (`reputation.py`'s
`latency` dimension permanently `None`) did not depend on either blocker
above — it needed only real request timing inside `HttpFetcher`, testable
offline with a mocked `urlopen`, same as every other test in this suite.
`HttpFetcher.fetch_bytes` now records real elapsed time per successful
request (deliberately excluding rate-limit/backoff sleeps, which aren't
the source's latency) into `self.request_latencies`; `CollectionService.
run()` reads the entries a `Collector.fetch()` call appended and passes
their average into `SourceMetricsRepository.record_run(latency_seconds=...)`.
It still reports `None` in practice until a live (non-mock/replay)
collector actually runs — the mechanism is real, the number it would
produce today would not be. 4 new tests (431 total).

## Universe Engine + Corporate Disclosures Phase (Engineering Ownership handoff)

The project owner handed over full engineering ownership this phase, with
a refined business-priority order (Universe Engine promoted to priority 2,
ahead of the org-source catalog; Corporate disclosures and Financial
Statement Collection added as explicit priorities 4/5; Historical Backfill
and Live Incremental Sync named as explicit priorities 6/7). Two real gaps
closed, one confirmed already-satisfied:

**Universe Engine (priority 2).** `universe.UniverseProvider` had exactly
one implementation, `StaticUniverseProvider` (a fixed placeholder) — no
path existed for a real collected constituent list to ever reach it, even
once one could be collected. Closed:
- `universe.constituent.IndexConstituent`: `{index, ticker, company_name,
  as_of_date}` — a date per row, not one overwritten snapshot, so universe
  queries stay point-in-time-correct (the same no-look-ahead guarantee
  every other query in this platform already gives).
- `CollectionBatch` gained `index_constituents` (and, built in the same
  pass since both needed the same materialization plumbing,
  `corporate_events`); `CollectionService` writes `universe/<INDEX>.csv`
  (merged by `ticker, as_of_date`) and `corporate_events.csv` (merged by
  `ticker, date, event_type`), both with full provenance tracing —
  extending the existing writer pattern (`_write_price_bars`,
  `_write_macro_observations`), not inventing a new one.
- `universe.collected.CollectedUniverseProvider` reads that CSV, returning
  the latest snapshot at-or-before the query date, or `{}` if nothing's
  collected — never fabricated. `FallbackUniverseProvider` composes it with
  `StaticUniverseProvider`, mirroring `data.composite_provider.
  FallbackDataProvider` exactly. Wired into `production.pipeline`'s
  `_stage_market_memory` and `cli.py`'s `discover-sources` universe lookup.
- `collectors.index_constituents.IndexConstituentCollector`: the collection
  half — header-text matching for ticker/name columns (no fixed column
  order assumed), since no real EGX constituent-list export has been
  fetched to verify one (TD-30). Built and fully tested, but **cannot** be
  wired into the live pipeline yet: `egx_official`'s `SourceSpec` stays
  `PLANNED` until its real endpoint is verified (`AD-24`) — exactly the
  same honest boundary as the AlphaVantage/FMP collectors sitting at
  `NEEDS_KEY`.

**Corporate disclosures (priority 4), closing TD-24.** `CorporateEvent` had
a schema (`data.schemas`) and a read path (`MockDataProvider.
get_corporate_events`), but nothing ever produced one — `CorporateEventsAgent`
found nothing from `--data-dir` before this phase. Closed with
`collectors.corporate_event_classifier.classify_corporate_event_type()`: a
declared headline keyword heuristic (dividend/split/merger/acquisition/
buyback/delisting/earnings/guidance/management-change — reusing
`events.adapters._CORPORATE_SUBTYPES`'s exact raw keys, so the existing
adapter needs zero changes to consume it) that `RssNewsCollector`'s new
`classify_corporate_events` flag applies per entry when exactly one ticker
hint matches, populating `batch.corporate_events` **alongside** the
always-produced `NewsItem` — the same disclosure viewed two ways, not two
collector pipelines. Wired into `production.collector_plan.py`'s
`rss_generic` mock/replay collector.

**Verified live** (mock mode, `agx run --mode mock`): the production
pipeline now writes real `COMI,2026-06-09,EARNINGS,...` and
`MFPC,2026-06-04,DIVIDEND,...` rows to `--data-dir/corporate_events.csv`,
derived from the same existing mock RSS headlines `collector_plan.py`
already used for news — a real, working, if narrow, capability, not a
fabricated one. Deliberately headline-only (RSS/ToS terms, TD-12): no
numeric detail (split ratio, dividend amount) is ever guessed, so a
classified event stays correctly informational-only until a fuller-text
source (an IR disclosure PDF) exists — declared as new debt (TD-29).
`CollectionService` materializes corporate events to CSV only; it does not
also register them as Events directly, since `events.adapters.
events_from_corporate_events` (fed by a `DatasetSnapshot` reading the same
CSV) is already the single place that happens — composing with that
existing adapter, not duplicating it.

**Investor Relations discovery (priority 3)**: confirmed already fully
built (two missions ago) and requiring no new engineering this phase —
`generate_company_ir_targets`/`discover_company_directory_links`/
`run_catalog` already scale automatically the moment the Universe Engine
(or a user-supplied list) provides a real constituent set.

**Historical Backfill (priority 6) / Live Incremental Sync (priority 7)**:
confirmed already satisfied by existing design, no code needed — every
collector fetches a source's full available series by construction, and
every materialization writer merges idempotently by natural key. A first
real run is the backfill; every subsequent run is the incremental sync.

31 new tests (462 total, up from 431); `ruff` clean; `contracts/`
unchanged (`IndexConstituent`/`CorporateEvent` additions aren't
API-facing). New technical debt: TD-29 (corporate-event classifier
keyword list, uncalibrated), TD-30 (`IndexConstituentCollector`'s column
detection, unverified against a real EGX export). TD-24 closed.

**The same two named blockers, unchanged**: no outbound network egress
from this sandbox, and no verified EGX30/EGX70 constituent list in this
codebase. Neither blocks what this phase closed — the Universe Engine and
corporate-event classifier are both real, working, engineering-complete
capabilities today; they simply have nothing live to run against yet. See
`CURRENT_MISSION.md` for the full statement.

## Financial Statement Collection (same Engineering Ownership phase)

Continuing directly from the Universe Engine + Corporate Disclosures work
above, in the same autonomous phase: priority 5, Financial Statement
Collection. This closes a real, already-named gap, not speculative
scope — `agents.financial_performance.FinancialPerformanceAgent` has been
an honest `NotImplementedError` stub since System 08 was built, explicitly
documented as needing "a financial statement data source and a defined
fundamental factor set." This phase built the data-source half; the
agent's own fundamental-factor logic remains separate, later Scientist
Framework work.

- New package `financials/`: `FinancialStatementLineItem` — `{ticker,
  period_end_date, period_type, statement_type, line_item, value,
  currency}`. `STANDARD_LINE_ITEMS` names a small, well-known IFRS/GAAP-
  style vocabulary (revenue, net_income, total_assets, etc.) reused where
  possible but never hard-validated — an uncommon real line item is
  preserved verbatim, matching `CorporateEvent.event_type`'s existing
  "never coerce or drop" precedent.
- `financials.FinancialStatementProvider`: a new, small, dedicated ABC
  (mirroring `universe.UniverseProvider`'s shape) rather than adding an
  abstract method to `data.provider.DataProvider` — `DataProvider` is a
  completed, tested interface every implementation depends on the exact
  method set of; growing it for an unrelated concern would be a redesign,
  not an extension. `CollectedFinancialStatementProvider` reads the
  collected CSV, empty (never fabricated) when nothing's been collected.
- `CollectionBatch.financial_statement_line_items` (new field);
  `CollectionService` materializes to `financial_statements/<TICKER>.csv`,
  merged by `(period_end_date, statement_type, line_item)`, with full
  provenance tracing — the same writer pattern as every other record type.
- `collectors.financial_statements.FinancialStatementCollector` (new): a
  generic, header-matching CSV parser for a structured financial-statement
  export (five required columns identified by header text: period end,
  period type, statement type, line item, value; an optional sixth,
  currency). Built and fully tested, but **not yet wireable** into the
  live pipeline — `company_ir`'s `SourceSpec` stays `PLANNED` until its
  real endpoint is verified (`AD-24`), same honest boundary as
  `IndexConstituentCollector` and the AlphaVantage/FMP collectors.
- **Deliberately not built**: a generic PDF-based financial-statement
  extractor. `sources.catalog`'s own `company_ir` notes expect PDF/XBRL
  disclosures to be the more common real case, but a generic numeric-
  extraction heuristic over arbitrary filing layouts risks silently
  reading the *wrong* line item's value — materially worse than a missing
  column, and the exact reason `collectors.pdf.PdfDocumentCollector.
  parse()` already stays abstract. That extraction is left for a
  concrete, source-verified subclass once a real filing layout exists
  (TD-32).

13 new tests (475 total, up from 462); `ruff` clean; `contracts/`
unchanged (`FinancialStatementLineItem` isn't API-facing). New technical
debt: TD-31 (`FinancialStatementCollector`'s column detection,
uncalibrated), TD-32 (PDF-based extraction, deliberately deferred).

**Same two named blockers, unchanged again.** Every sub-phase of this
mission (Universe Engine, Corporate Disclosures, Financial Statement
Collection) is now engineering-complete and ready to execute the moment
either clears. See `CURRENT_MISSION.md` for the current statement and
`NEXT_MISSIONS.md` for what's next in the meantime.

**One more genuinely unblocked item, closed while auditing**:
`production.artifacts.export_collector_status()` reported
`price_bars_written`/`macro_observations_written`/`news_items_written`/
`events_registered` but silently omitted the three newest record-type
counters this mission added — a real dashboard observability gap
(`collector_status.json` blind to genuine capability already built), not
a network/business blocker. Fixed by adding
`corporate_events_written`/`index_constituents_written`/
`financial_statement_line_items_written`; verified live (a mock-mode
`agx run` now correctly reports `corporate_events_written: 2`, matching
the real `COMI/EARNINGS` + `MFPC/DIVIDEND` rows). 2 new tests
(477 total).

## Production-readiness audit for merge into `main`

Full audit performed before merging this branch into `main`: all tests
green (477 Python / 14 API / 19 web), `ruff` clean, `contracts/`
drift-free, no merge conflicts with `main` (`git merge-tree` confirms a
clean fast-forward — `main` hasn't advanced past this branch's base since
work began), no TODO/FIXME/HACK markers or debug prints in source, no
unresolved conflict markers anywhere, no stray scratch files. Spot-checked
CLAUDE.md's core invariants directly: no agent writes to `KnowledgeStore`
directly; every real network fetch goes through `HttpFetcher` (no
`urlopen`/`requests`/`httpx` calls elsewhere); no direct `EventRepository`
write bypasses `EventPlatform.register()`; every schema class (`PriceBar`,
`CorporateEvent`, `IndexConstituent`, `FinancialStatementLineItem`, etc.)
is defined exactly once.

**One real duplication found and fixed**: the same four-line header-
matching helper, and the same "one URL, one text document" `fetch()`
body, had each been written three times over — once in the pre-existing
`RssNewsCollector`, and once more each in this mission's
`IndexConstituentCollector` and `FinancialStatementCollector`.
Consolidated into `collectors/csv_columns.py` (`find_column()`) and
`collectors/raw.py` (`fetch_single_text_document()`); all three
collectors now call the shared helpers. Purely mechanical — same tests,
same assertions, all still passing; no behavior change.

No other issues found. This branch is a clean merge candidate.

## Live Data Activation mission (post-Production-User-Experience)

The project owner's instruction this phase: stop building UI/architecture,
connect the first live production data source, in a strict priority order
(Tier 1: EGX official → EGX30/EGX70 company Investor Relations → CBE;
Tier 2: Enterprise/Mubasher/Zawya/Asharq Business; Tier 3: CAPMAS/Trading
Economics/World Bank/IMF/FRED; Tier 4: anything else the Acquisition
Intelligence Engine discovers), continuing autonomously until blocked by
a genuine external dependency or a business decision.

**Result: blocked immediately at Tier 1, verified directly rather than
assumed** (this is the fifth mission to hit the identical block, but the
first to gather proxy-level evidence rather than relying on curl/WebFetch
403s alone):

- `curl` to every named Tier 1-3 host (`www.egx.com.eg`, `www.cbe.org.eg`,
  `www.mubasher.info`, `www.zawya.com`, `www.tradingeconomics.com`,
  `fred.stlouisfed.org`, `stooq.com`, `api.worldbank.org`,
  `data.worldbank.org`, `www.imf.org`, `www.capmas.gov.eg`,
  `www.enterprise.press`, `asharqbusiness.com`) fails identically:
  `CONNECT tunnel failed, response 403`.
- The session's own egress-proxy status endpoint
  (`$HTTPS_PROXY/__agentproxy/status`) logs each attempt as
  `connect_rejected` — `"gateway answered 403 to CONNECT (policy denial or
  upstream failure)"` — i.e. an explicit organization egress-policy
  denial, uniform across every host tested, including sources this
  registry already lists `IMPLEMENTED` (`fred`/`stooq`/`worldbank`) that
  prior missions could only test with fixtures.
- `WebFetch` independently returns HTTP 403 for the same hosts (a
  different code path than raw `curl`, so this isn't one tool's quirk).
- Running the platform's own `agx discover-sources` against the full
  21-target priority catalog (`AcquisitionIntelligenceEngine.run_catalog`)
  reproduces the same result for all 21: `no-op -- No reachable domain
  found from public brand hints or name-derived guesses` — the
  `HeuristicDomainResolver` correctly refusing to trust an unprobed
  domain, exactly as designed, not a defect.
- This session's instructions explicitly forbid working around a proxy
  policy denial (`/root/.ccr/README.md`: "do not retry or route around
  it — report the blocked host"), so no bypass was attempted.

No engineering-closeable work exists to advance this mission further from
inside this sandbox: every item in `docs/TECHNICAL_DEBT.md` that touches a
real source is explicitly gated on a live fetch happening at least once
(to verify an actual wire format) or a named business decision, and the
Data Acquisition Platform + Acquisition Intelligence Engine already
implement everything needed the moment egress exists — nothing was
rebuilt or changed this phase, matching the "no more architecture" ask.
No code changed. Live-data activation resumes the moment either this
platform runs somewhere with real outbound egress (a System-18 deployment
decision) or the project owner supplies the two named business inputs
(a verified EGX30/EGX70 constituent list; a licensed EGX vendor
selection) — see `MISSION_CONTROL.md` and `CURRENT_MISSION.md`.

## Egyptian Live Data Sprint + Acquisition Strategy phases (post-above, within System 02's scope)

**Superseding the "no egress" framing above**: the GitHub Pages deployment
target (`.github/workflows/deploy-pages.yml`, real GitHub Actions egress —
a different environment from the coding sandbox the section above
describes) has since run the production pipeline live multiple times.
Three phases followed, in order:

1. **Egyptian Live Data Sprint**: `--mode live` became the pipeline's real
   default (was mock-only); fixed a genuine health-engine bug (a collector
   that downloaded data but produced zero parsed/knowledge/event records
   was previously reported `HEALTHY` — now correctly `DEGRADED`/`FAILED`
   with an explicit reason and connection/parse/yield/knowledge/event
   metrics surfaced in Mission Control) and a second bug where a
   fetch-level exception bypassed health/metrics bookkeeping entirely.
   Live evidence: World Bank collects real data (66 Egypt CPI inflation
   observations); Stooq/FRED reachable but blocked
   (Cloudflare-style JS challenge / evidenced separately); the five named
   Egyptian sources (EGX, CBE, Enterprise, Mubasher, Zawya) each fail with
   a distinct, evidenced, source-side reason.
2. **Acquisition Strategy analysis** (`docs/ACQUISITION_STRATEGY.md`):
   given that evidence, determined the acquisition *strategy* itself
   (not the platform) had one identified flaw — "homepage = data source"
   is the correct default only for per-company Investor Relations, not
   for hardened public sites (exchanges, central banks, WAF-protected news
   portals), where a documented API/feed/bulk-download contract should be
   sought first (the World Bank precedent). Closed the concrete gap this
   surfaced: `AcquisitionIntelligenceEngine.run_for_target()` now falls
   back to the sitemaps.org protocol (robots.txt's `Sitemap:` directive,
   then `/sitemap.xml`, following a sitemap-index one level) when a
   homepage's own markup has nothing discoverable — the exact Zawya-class
   gap, and `docs/TECHNICAL_DEBT.md` TD-18's sitemap-index half.
3. **Capability-driven acquisition engine** (this phase): turned that
   analysis into runtime logic. `acquisition_intelligence.capability`
   defines 13 independent `Capability` values (Price Data, Corporate
   Disclosures, Corporate Actions, Financial Statements, Investor
   Relations, News, Macroeconomic, Market Breadth, Trading Calendar,
   Index Constituents, Sector Membership, Economic Releases, Research
   Papers) each mapped to a declared, ranked pool of catalogued
   `SourceSpec` ids — a capability, not a website, is now the primary
   object. `acquisition_intelligence.capability_engine` ranks every
   candidate using registry state + measured reputation
   (`rank_capability_strategies`) and `CapabilityDecisionEngine` executes
   the best collectable one, falling through automatically to the next on
   failure or zero yield (Macroeconomic runs every ready strategy, since
   World Bank's Egypt CPI and FRED's global series are complementary, not
   redundant). Wired into `production/pipeline.py`'s LIVE-mode Collector
   Selection/Execution stages, reusing the exact same `CollectionService`,
   `SourceRegistry`, and reputation engine every mode already used — a
   live-fixture run reproduces every existing collection-result assertion
   unchanged for the sources already solved (stooq/fred/worldbank), while
   every other capability now honestly reports which strategies were
   ranked and why each was skipped, rather than being silently absent from
   LIVE mode. Every decision is persisted as a new `acquisition_decisions.json`
   Mission Control artifact and rendered in the web dashboard's Mission
   Control page, replacing a previous "not yet available" placeholder. See
   `docs/ACQUISITION_STRATEGY.md`'s "Runtime Implementation" and
   "Collector Classification" sections for full detail. 510 backend tests
   pass (34 new this phase); `ruff check` clean; `web`/`api` typecheck and
   build clean. No architecture, pipeline stage sequence, or existing
   collector was redesigned or removed — this phase is additive per its
   own mission constraints.

4. **First real Egyptian market data flowing live** (this phase):
   `enterprise_press` flipped to `IMPLEMENTED`/`TRUSTED`, collecting real
   news from `https://enterpriseam.com/egypt/feed/` (found via standard
   RSS autodiscovery on its own now-reachable homepage, never guessed).
   Verified live: 6 real news items parsed, 6 real events registered in
   the Event Platform, `data_quality_score=0.97`. This is the platform's
   first genuinely EGX-specific live source (World Bank, the only other
   connected source, is macro-level, not EGX-specific). Getting here
   surfaced and fixed four real bugs, none touching architecture: an
   unhandled crash on non-percent-encoded non-ASCII URLs; an unbounded
   `robots.txt` fetch that hung a live run for 90+ minutes
   (`RobotFileParser.read()` has no timeout); an unbounded sitemap-
   candidate count that caused a second ~70-minute hang (a real
   sitemap-index's per-section sitemap can list thousands of URLs); and a
   correctness bug where the discovery stage silently regressed an
   already-`IMPLEMENTED` source back to `PLANNED` on every subsequent run.
   518 backend tests pass (8 new this phase); `ruff check` clean. Every
   other named Egyptian source remains blocked by the same genuine,
   evidenced defensive measures documented in phase 2/3 above — see
   `docs/ACQUISITION_STRATEGY.md`'s "First Live Egyptian Source" section
   and `CURRENT_MISSION.md` for full detail.

## Ticker Data Gap Report (post-acquisition-freeze, System 02 + 13 dashboard layer)

The project owner supplied a fresh, detailed completion plan (in Arabic)
covering EGX disclosures, financial statements, entity resolution, macro
alignment, decision-engine explainability, and source monitoring — framed
around one question per ticker: exactly what evidence is missing, and what
does it take to reach Swing/Investment readiness. Before writing anything
new, this phase audited what the plan asked for against what already
exists, since several items turned out already engineering-complete:

- **Already built, confirmed by re-reading the code, not re-implemented**:
  `meta.readiness.assess_decision_readiness` already computes exactly the
  per-ticker MICRO/SWING/INVESTMENT gates the plan's item 6 asks for
  (price freshness/volume, financial periods, macro series count, news/
  corporate-event presence, active knowledge), with named blockers and
  next actions, exported as `decision_readiness.json` and rendered in the
  Opportunity Center. The plan's item 3 (Financial Statement Collector)
  and item 2 (EGX disclosures → `CorporateEvent`) both already exist
  end to end (`financials/`, `collectors/financial_statements.py`,
  `collectors/corporate_event_classifier.py` — see the "Financial
  Statement Collection" and "Universe Engine + Corporate Disclosures"
  phases above) and are blocked on exactly the same two named business
  inputs every phase since has named: a verified real source endpoint
  (`company_ir` stays `PLANNED`) and this sandbox's lack of network
  egress — not missing engineering. The plan's item 1 (a 101-ticker
  universe) was also already connected (`universe/`, the reviewed
  EGX30+EGX70 seed, 31+70 tickers).
- **The real, closeable gap this phase found**: nothing decomposed
  `decision_readiness.json`'s counts into the plan's own five named
  layers (Financials/Disclosures/News/Macro/Knowledge) with an explicit
  completeness percentage per layer, and nothing published it as a
  reviewable artifact. Closed with `meta.readiness.build_ticker_data_gap_report`
  (`TickerDataGapReport`/`DataLayerGap` models) — a pure re-derivation of
  `assess_decision_readiness`'s own counts and gate thresholds (never a
  second, possibly-disagreeing set of thresholds), exported as
  `production.artifacts.export_ticker_data_gap_report` and wired into
  `ProductionPipeline._stage_dashboard_artifact_generator` right after
  `decision_readiness.json`, writing `ticker_data_gap_report.json` (one
  row per universe ticker, validated in `dashboard/validate.py` for
  schema + universe-membership parity, same as `decision_readiness.json`).
  5 new tests (`test_ticker_data_gap_report.py`); 560 backend tests pass;
  `ruff check` clean.
- **Verified with a real mock-mode run**: `agx run --mode mock` against
  the full 101-ticker EGX30+EGX70 universe honestly shows 99 tickers
  `blocked` (no price history at all in this sandbox's synthetic
  fixtures, which only ever cover COMI/MFPC) and COMI/MFPC `degraded`
  at 53.3% average layer completeness (disclosures/news present,
  financials/knowledge absent, macro at 2 of the required 3 series) —
  0 tickers Swing-ready, 0 Investment-ready, exactly the honest starting
  point the plan's own success criteria describe ("raise Swing-ready
  from zero"). Rendered as a published, filterable/sortable Artifact
  (per-ticker layer completion bars, status pills, primary blocker) so
  the gap is reviewable at a glance without reading raw JSON.
- **Named, deliberately not done this phase**: web/API wiring
  (`api/src/routes/dashboard.ts`, `ApiProvider`/`StaticJsonProvider`,
  `web/src/types.ts`, a dashboard UI section) — see new TD-34. Also not
  done: the plan's item 4 (Arabic/English company-alias entity resolution
  for news) and item 5 (macro frequency alignment/point-in-time
  publication-date discipline) — both real, scoped engineering tasks,
  neither started this phase; named as the next queued items in
  `NEXT_MISSIONS.md` rather than attempted speculatively in the same
  sitting as the gap-report work.
   `enterprise_press` flipped to `IMPLEMENTED`/`TRUSTED`, collecting real
   news from `https://enterpriseam.com/egypt/feed/` (found via standard
   RSS autodiscovery on its own now-reachable homepage, never guessed).
   Verified live: 6 real news items parsed, 6 real events registered in
   the Event Platform, `data_quality_score=0.97`. This is the platform's
   first genuinely EGX-specific live source (World Bank, the only other
   connected source, is macro-level, not EGX-specific). Getting here
   surfaced and fixed four real bugs, none touching architecture: an
   unhandled crash on non-percent-encoded non-ASCII URLs; an unbounded
   `robots.txt` fetch that hung a live run for 90+ minutes
   (`RobotFileParser.read()` has no timeout); an unbounded sitemap-
   candidate count that caused a second ~70-minute hang (a real
   sitemap-index's per-section sitemap can list thousands of URLs); and a
   correctness bug where the discovery stage silently regressed an
   already-`IMPLEMENTED` source back to `PLANNED` on every subsequent run.
   518 backend tests pass (8 new this phase); `ruff check` clean. Every
   other named Egyptian source remains blocked by the same genuine,
   evidenced defensive measures documented in phase 2/3 above — see
   `docs/ACQUISITION_STRATEGY.md`'s "First Live Egyptian Source" section
   and `CURRENT_MISSION.md` for full detail.
