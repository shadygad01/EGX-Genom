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

| # | System | Status | Evidence / remaining gaps |
|---|--------|--------|---------------------------|
| 01 | Foundation | **DONE** | `domain/`, `storage/`, `config.py`; reused unmodified by every later store; CI green. |
| 02 | Data Platform | **DONE** | Provider/fallback interfaces, snapshots(+repo), quality checks, split/dividend adjustment, plus the full Data Acquisition Platform (`sources/`+`discovery/`+`collectors/`+`acquisition_intelligence/`, see `docs/DATA_ACQUISITION.md`): a 51-source registry (5 IMPLEMENTED / 34 PLANNED / 4 NEEDS_KEY / 8 TOS_REVIEW) across 9 categories with three independent state axes (status/lifecycle_state/health_status); a discovery engine that proposes candidates from RSS-autodiscovery/PDF-repository/structured-dataset/sitemap/API-doc scans without ever trusting them; an evidence-gated Candidate→Quarantine→Evaluation→Trusted→Core qualification pipeline; a 9-dimension reputation engine and health monitor wired into every collection run; real collectors for Stooq, FRED, World Bank (macro), and generic RSS/Atom (news), plus AlphaVantage/FMP code-complete pending a user API key; generic collector-type frameworks for PDF, Excel, Filesystem, Browser-automation (honest stub), and Archive Replay. A content-addressed Raw Archive stores binary artifacts forever; a per-value Provenance Index traces every materialized price bar/macro observation back to its source/collector/raw-document/hash/schema-version; a Historical Replay engine rebuilds materialized data from archived documents alone when a parser changes. **New this phase: the Acquisition Intelligence Engine** (`acquisition_intelligence/`) — given only an organization's identity (never a manually supplied URL), it resolves a verified-reachable domain, discovers candidate acquisition methods, verifies legality (robots.txt + ToS heuristics, scraping never auto-clears)/stability (URL-shape + probe consistency)/historical availability (Wayback Machine APIs), ranks and selects the best, auto-generates a still-`PLANNED` `SourceSpec`, registers it, and begins qualification; `AcquisitionContinuityMonitor` re-runs discovery automatically for any source whose health goes `DOWN`. Fully tested with fakes (20 tests covering the complete pipeline); wired into `cli.py`'s `discover-sources` subcommand. Blocked-external: licensed EGX vendor for guaranteed-accurate real-time/official data (business decision) remains the gap this doesn't close; a live run of the engine against the 12 named official/company/regional-news targets reports "no reachable domain" in this specific sandbox because it has no outbound network egress to arbitrary hosts (confirmed directly; only PyPI/npm/anthropic.com are allowlisted) — the engine itself is complete and will do real, verified discovery the moment it runs somewhere with egress. |
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
(413 Python tests + 33 TypeScript tests green).

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
