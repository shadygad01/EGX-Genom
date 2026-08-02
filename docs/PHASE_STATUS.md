# Phase Status — MASTER_PROMPT.md's 18 Systems

The living audit the charter requires. Updated whenever a system's status
changes. Status: **DONE** (Definition of Done met, with any remaining gaps
being external/business-blocked and named) / **PARTIAL** / **NOT STARTED**.

Cross-cutting note on what DONE means here: the *architecture and
engineering* are production-shaped and fully tested; the platform still
runs on placeholder market data for the gaps the free-source Acquisition
Program hasn't closed yet. The licensed-vendor question is no longer open:
per the project owner's 2026-07-27 decision (`docs/ARCHITECTURE_DECISIONS.md`'s
AD-32), no paid/licensed data vendor will ever be used — every remaining
data gap, including per-company fundamentals, must be closed exclusively
through free, publicly-reachable sources. See `docs/ROADMAP.md`.

Current acquisition registry, after removing every `NEEDS_KEY` source per
the project owner's no-API-key-sources decision, and after the
Decision-Centric Redesign's removal of 11 sources with zero mapping in
`acquisition_intelligence.capability.CAPABILITY_STRATEGIES` (2026-07-30 —
see `docs/DECISION_CENTRIC_AUDIT_2026-07-30.md`/
`docs/ARCHITECTURE_ADVERSARIAL_REVIEW.md`) and addition of 4 new Sovereign
& Credit Context / Amwal Al Ghad candidates: **48 sources
(16 IMPLEMENTED / 23 PLANNED / 0 NEEDS_KEY / 1 TOS_REVIEW / 8 DISABLED)**.
This current count supersedes older counts embedded in the long-form
phase evidence below.

| # | System | Status | Evidence / remaining gaps |
|---|--------|--------|---------------------------|
| 01 | Foundation | **DONE** | `domain/`, `storage/`, `config.py`; reused unmodified by every later store; CI green. |
| 02 | Data Platform | **DONE** | Provider/fallback interfaces, snapshots(+repo), quality checks, split/dividend adjustment, plus the full Data Acquisition Platform (`sources/`+`discovery/`+`collectors/`+`acquisition_intelligence/`, see `docs/DATA_ACQUISITION.md`): a 55-source registry (16 IMPLEMENTED / 28 PLANNED / 0 NEEDS_KEY / 1 TOS_REVIEW / 10 DISABLED — per the project owner's explicit decision, no `NEEDS_KEY` source is catalogued at all, see `docs/DATA_ACQUISITION.md`'s "No API-key sources"; the 10 `DISABLED` sources each carry a specific dead-end evidence citation, e.g. a quoted ToS prohibition, a WAF/403, a robots.txt disallow, or a paid-tier-only requirement, rather than sitting as `PLANNED` indefinitely — see that doc's status-policy section) across 9 categories with three independent state axes (status/lifecycle_state/health_status); a discovery engine that proposes candidates from RSS-autodiscovery/PDF-repository/structured-dataset/sitemap/API-doc scans without ever trusting them; an evidence-gated Candidate→Quarantine→Evaluation→Trusted→Core qualification pipeline; a 9-dimension reputation engine and health monitor wired into every collection run; real collectors for Stooq, FRED, World Bank, UN Statistics SDG (macro), GDELT, and generic RSS/Atom (news), including live-verified Enterprise, FRA, Al Borsa and Masrawy Economy configurations; generic collector-type frameworks for PDF, Excel, Filesystem, Browser-automation (honest stub), and Archive Replay. A content-addressed Raw Archive stores binary artifacts forever; a per-value Provenance Index traces every materialized price bar/macro observation back to its source/collector/raw-document/hash/schema-version; a Historical Replay engine rebuilds materialized data from archived documents alone when a parser changes. **New this phase: the Acquisition Intelligence Engine** (`acquisition_intelligence/`) — given only an organization's identity (never a manually supplied URL), it resolves a verified-reachable domain, discovers candidate acquisition methods, verifies legality (robots.txt + ToS heuristics, scraping never auto-clears)/stability (URL-shape + probe consistency)/historical availability (Wayback Machine APIs), ranks and selects the best, auto-generates a still-`PLANNED` `SourceSpec`, registers it, and begins qualification; `AcquisitionContinuityMonitor` re-runs discovery automatically for any source whose health goes `DOWN`. Fully tested with fakes (20 tests covering the complete pipeline); wired into `cli.py`'s `discover-sources` subcommand. Blocked-external: licensed EGX vendor for guaranteed-accurate real-time/official data (business decision) remains the gap this doesn't close; the engine itself performs live, verified discovery wherever the target permits access. **New this phase: priority-ordered catalog processing** (`AcquisitionIntelligenceEngine.run_catalog`, `TargetOrganization.priority`) matching the project owner's explicit business-value order (EGX official → EGX30/EGX70 company Investor Relations → CBE/FRA/CAPMAS/Enterprise/Mubasher/Zawya/Reuters/Trading Economics → everything else discovered), plus `generate_company_ir_targets()` (one real target per EGX30 constituent, expanding the previously-inert `company_ir` marker entry) and `discover_company_directory_links()` (extracts a company's own homepage link from an already-fetched directory page by real anchor-text matching, letting a resolved exchange/regulator homepage supply real per-company hints instead of guessing ~100 corporate domains). See "Production Execution Phase" below. **New: a third `domain_hints` source** — `discovery.web_search_hints.load_web_search_domain_hints()` reads a reviewed, evidenced web-search snapshot for EGX30 (26/31 tickers; 5 deliberately left unresolved), wired into `cli.py discover-sources` to fill tickers Wikidata misses (TD-38). Not yet run live — this session's sandbox denies egress to every external host tested, EGX30 official sites included — so the resulting `domain_hints` are unverified by `HeuristicDomainResolver` until the next run with real network egress. **New: the per-company Financial Source Registry** (TD-39) — `discovery.financial_document.classify_financial_document()` (generic annual/quarterly/statements/presentation/disclosure/IR-home classifier), `discovery.engine.discover_financial_documents()`, `discovery.company_financial_registry.CompanyFinancialSourceRegistry` (resumable, versioned, one record per company — `is_resumable_skip()` only skips `VALIDATED`), and `discovery.company_financial_discovery.discover_company_financial_sources()` (fetch → scan → classify → recommend a collector via `config_generation.suggest_collector`). `scripts/build_financial_source_registry.py` runs it across the full EGX30+EGX70 universe and is wired into `.github/workflows/discovery.yml`. Run for real against all 101 companies this session: 0 `DISCOVERED`/`VALIDATED`, 26 `BLOCKED` (real fetch attempts against the 26 TD-38 hostname hints, real proxy-403 evidence), 75 `HOMEPAGE_UNRESOLVED` — honest, not a shortfall: no environment this platform has run in from inside this sandbox has ever had network egress to these hosts. The registry mechanism and CI wiring are complete; populating real data needs a `discovery.yml` run with egress. **New: `GdeltDocCollector` historical backfill mode** (TD-41) — real windowed `startdatetime`/`enddatetime` queries around GDELT DOC 2.0's 250-articles-per-response cap, alongside its unchanged relative-`timespan` daily-live behavior; wired into `cli.py collect --source gdelt` and a new `.github/workflows/news-history-backfill.yml` (`workflow_dispatch`, real egress, PR-gated into `main` under `research/data/news_history/`). Investigating this also surfaced, then closed, TD-40: the daily production pipeline had no cross-run persistence (`deploy-pages.yml` never restored/committed its `--data-dir`, unlike `discovery.yml`) — very likely the dominant reason live-mode rarely surfaced confident cross-day-corroborated findings. **Closed same session**: `deploy-pages.yml` now uses `--data-dir data/production`, restored from and committed back to a `production/state-latest` branch around each run (auto, never PR-gated), with a `RunRecordRepository`-backed same-date check that skips the whole job (research pipeline, dashboard build, Pages deploy) rather than duplicating a date's hypotheses/knowledge if triggered twice in one day. See `docs/ROADMAP.md`'s "Closed: daily cross-run persistence" section. |
| 03 | Event Platform | **DONE** | Fingerprint identity, taxonomy/ontology, entity resolution, dedup/conflict/lifecycle, `EventPlatform` sole write path, graph projection. Blocked-external: political/technical feeds, NLP entity linking. |
| 04 | Market Memory | **DONE** | `MarketState` (snapshot+universe+sectors+events+session), `TradingCalendar` (fixed holidays as rules; movable as explicit placeholder table). Blocked-external: authoritative movable-holiday dates. |
| 05 | Knowledge Graph | **DONE** | Versioned nodes/edges, provenance-derived builder, shortest-path + n-hop subgraph queries. Deferred by choice: dedicated graph DB (swap behind `Repository[T]` when scale demands). |
| 06 | Alpha Genome | **DONE** | Immutable genes, `mutate()` (single-parent), `merge()` (multi-parent synthesis), lineage walk, status machine; never overwrites. |
| 07 | Research OS | **DONE** | TaskGraph/Artifacts/Sessions plus `DailyResearchPipeline` — the full 8-gate walk wired to real validators, board, causal gate, adversarial scientist, genome, papers, graph. End-to-end tested incl. rejection honesty and determinism. |
| 08 | Scientist Framework | **DONE** (8 of 8 agents real) | MarketStructure, Macro, CorporateEvents, Liquidity, TechnicalStructure, NewsIntelligence, HistoricalPatterns, **and now FinancialPerformance** real. HistoricalPatternsAgent closed once `data/snapshot.py` gained a `pattern_lookback_days`-windowed `long_price_history` (the same "one field needs its own window" pattern `macro_lookback_days` already established) — LIVE mode's `egx_price_composite` collector already returns full (Yahoo `range=max`) history on every run, so the data existed; only the agent's own analog-matching methodology (mean-centered Euclidean distance over a sliding return window, non-overlapping top-k historical episodes, honest abstain below a directional-agreement threshold) was missing. **FinancialPerformanceAgent closed in the Decision-Centric Redesign (2026-07-30)** the same way: `data/snapshot.py` gained a `financials_provider`-populated `financial_statements` field (mirroring the `pattern_lookback_days` precedent exactly — "one field needs its own window/source", not a `DataProvider` redesign), and the agent computes real revenue-growth-trend and leverage-trend findings from whatever periods a collector actually reports, `min_periods=4` matching `meta.readiness`'s own INVESTMENT floor. Zero findings in practice today (only `telecom_egypt_ir`/`orascom_ir` are `IMPLEMENTED`, both with 1-2 real collected periods, below the 4-period floor) — honest, not fabricated; the mechanism is real and ready the moment more periods accumulate. Adversarial: 6 of 9 attacks real; 3 data/harness-blocked, reported `attempted=False`. |
| 09 | Feature Discovery | **DONE** | Three autonomous generators (pairwise correlation, momentum, volatility) over three registered feature definitions; candidates versioned+evidenced. |
| 10 | Experiment Factory | **DONE** | Statistic dispatch by asset arity; CV/bootstrap/walk-forward/OOS/sensitivity real (scipy-backed); stress adapter; Monte Carlo now a real block-bootstrap simulator (`MonteCarloBlockBootstrapStressTester`), not a placeholder. |
| 11 | Validation Framework | **DONE** | `SignificanceThresholdValidator`, `NaiveDirectionalBacktester` (costs explicitly out of scope, stated), `HistoricalWorstWindowStressTester` (scenario located in real data, not simulated). Deferred: cost-aware portfolio-level backtesting (with 15's future optimizer). |
| 12 | Review Board | **DONE** (4 of 5 reviewers real) | Statistician, Risk, Economist (structural coherence, not economic truth — stated), PeerValidator (independent replication). Historical reviewer data-blocked. Board wired into the pipeline before `promote()`. |
| 13 | Runtime Engine | **DONE** | `RuntimeEngine.run_range`: deterministic, per-day failure isolation, non-trading days recorded not skipped silently, persistent run ledger. Now the core of `production.pipeline.ProductionPipeline`'s Research Pipeline stage — see "Production Execution Pipeline" below. OS-level scheduling = deployment config (18). |
| 14 | Prediction Intelligence | **DONE** (v1) | `KnowledgeWeightedHorizonModel`: predictions derived exclusively from promoted knowledge; no knowledge → no prediction. Trained statistical models deferred until years of real data exist (data-blocked, would otherwise be fabricated science). |
| 15 | Portfolio Intelligence | **DONE** (v1) | `PortfolioConstructor`: risk-adjusted confidence-discounted scoring, capped proportional weights, cash fallback, full explanation. Deferred: covariance-based optimization (needs real data depth). |
| 16 | Explainability Engine | **DONE** | Six-question `Explanation` with structured `evidence_refs` everywhere; `similar_historical_cases` populated from real recorded events via the Event Platform. |
| 17 | Continuous Learning | **DONE** (v1) | `ContinuousLearningMonitor`: realized performance recorded on knowledge+genes from real later-window data; mechanical sign-disagreement retirement policy with audited reasons. |
| 18 | Production Infrastructure | **PARTIAL** | The public-deployment cloud-provider question is now **permanently decided, not blocked** (AD-57, 2026-08-01): zero-cost, GitHub Actions + GitHub Pages only, no VPS/paid hosting/always-on backend ever for the public site — `deploy-pages.yml` + `ProductionPipeline` already fully implement this. Engineering-closeable parts done: integrity-checked backup/verify/restore, CLI (`run`/`status`/`shadow-fund`/`backup`/`restore`/`discover-sources`/`collect`), the first production execution pipeline (`agx run` — see "Production Execution Pipeline" below), Dockerfile (local/self-hosted use only, not part of the zero-cost public pipeline), CI. Still business-blocked, unchanged by AD-57: secrets management service, managed scheduling (e.g. for `discover-sources`), API authentication context, monitoring/alerting stack — none of these are about the public site's hosting target, which is now closed. Named in `docs/ROADMAP.md`. |

## What Production 1.0 still needs (all business-blocked, except #1 which is decided)

1. ~~Licensed EGX market data vendor~~ — **decided against, permanently**
   (AD-32): no paid vendor of any kind. Closing #4 below (fundamentals,
   news NLP, long-history) is now engineering-only work against free
   sources, principally finishing the `egx_official` → per-company
   `company_ir` domain-resolution chain in `acquisition_intelligence/`.
2. Cloud/deployment target + secrets management + scheduler (18).
3. Authoritative EGX holiday calendar + universe/sector feeds (04/02).
4. Free-source-only data feeds still needed to unlock the remaining stubs:
   a working news NLP source, real per-company financial-statement
   collection, long-history archive (08/12 stragglers).

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

## Bilingual EN/AR dashboard, full RTL (post-Data-Acquisition-Program)

Also a presentation-layer capability, not a new charter system: the web
dashboard now ships an EN/AR language toggle (`i18next`/`react-i18next`,
one JSON namespace per page under `web/src/i18n/locales/`) with full RTL
layout for Arabic, achieved mostly through CSS logical properties rather
than per-component overrides. Translation is scoped to UI chrome and
closed backend enum vocabularies (`web/src/types.ts` unions, via
`useEnumLabel()`); free-form backend-generated prose (explanations,
evidence, headlines, notes, company names, macro series ids,
financial-statement line items) intentionally stays English rather than
risk fabricating financial/legal Arabic terminology. Numeric/ticker data
always renders LTR regardless of language. See `CHANGELOG.md`'s 0.29.0
entry for the full design.

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
- 52 sources catalogued across all 9 named categories (Official, Company,
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
  for news); item 5 (macro frequency alignment) was later closed — see
  below.
- **Item 5 closed, live-verified**: a live production run showed every one
  of the 23 `LIVE_MACRO_SERIES_IDS` (FRED/World Bank/UN SDG) with zero
  observations — `_stage_market_memory`'s single `lookback_days=30`
  windowed World Bank/UN SDG's annual (often 1-2 year publication lag) and
  CAPMAS's monthly observations the same as daily prices, so an annual
  point almost never falls inside the last 30 days. `data.snapshot.build_snapshot`
  now takes an independent `macro_lookback_days` (`DatasetSnapshot` gained
  the field for explainability); `MarketMemory` and `ProductionPipeline`
  thread it through, with LIVE mode using a new `LIVE_MACRO_LOOKBACK_DAYS`
  constant (900 days). Also closed the separate gap where
  `LIVE_CAPMAS_INDICATORS`' local ids were never added to
  `LIVE_MACRO_SERIES_IDS` at all. `MacroAgent` (the only agent turning
  macro data into SWING-horizon knowledge) now has real macro observations
  to correlate against in a live run.
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

## Provider-Leg Health Measurement Accuracy (System 02 accuracy review)

The project owner reviewed the live source dashboards produced by prior
sessions and flagged, correctly, that the picture was honest but
incomplete: dozens of catalogued sources are still `PLANNED` pending a
verified endpoint (real, business/engineering-blocked, see "What's still
blocked" in `docs/DATA_ACQUISITION.md`), `NEEDS_KEY` sources have no
credential yet (a business action, not code — see `docs/DATA_ACQUISITION.md`'s
source catalog policy), no scheduled recurring discovery/collection runs
yet (System-18 scheduling, TD-23's own named repayment trigger), and —
the one genuinely closeable engineering gap this phase found — a source
integrated as a provider leg inside a composite collector
(`yahoo_finance`/`stockanalysis`/`mubasher` inside
`EgxCompositePriceCollector`, via `SourceSpec.integrated_via`) could show
`health_status: unknown` / `data_quality_score: null` in
`source_registry.json` even while actively serving real traffic through
the composite, because `CollectionService` only ever recorded metrics/
health against the parent collector's id, never against the specific
provider id a document was actually attributable to. A prior session's
`export_collector_status` fix addressed this for the dashboard's derived
per-run status table only (by borrowing the parent's `health_status` as
a stand-in for display) — the registry's own per-provider fields were
never actually measured, so any consumer reading `source_registry.json`
directly (not just the dashboard's derived view) still saw a permanently
unmeasured leg.

Closed: `collectors.service.CollectionService._record_provider_outcome`
now records `SourceMetrics`/`HealthStatus` against a provider leg's own
registry id from the same per-document quality assessment already
computed for that document (each raw document a `provider_for_document`-
aware collector produces is already attributable to exactly one
provider) — on both the success and parser-failure paths, mirroring the
existing collector-level `_record_run_outcome` exactly. `export_collector_status`
no longer overwrites a provider row's `health_status` with the parent's
value; it now reads the provider's own, correctly-measured status like
every other source. New test:
`test_provider_leg_health_and_reputation_are_measured_directly`
(`test_collection_service.py`). 567 backend tests pass (1 new); `ruff
check` clean.

Everything else the owner named stays correctly deferred, not chased:
converting a `PLANNED` source to `IMPLEMENTED` needs a verified real
endpoint (this dev sandbox has no arbitrary outbound egress, though the
GitHub Actions production deployment does — see `CURRENT_MISSION.md`);
`NEEDS_KEY` sources need the user's own API key, a credential/business
action this codebase never fabricates or bypasses; and a real periodic
discovery/collection scheduler needs System 18's managed-scheduling
decision (cloud target + secrets + scheduler), which remains
business-blocked exactly as `docs/ROADMAP.md`/TD-23 already name. None of
these are re-opened by this phase — this phase closed only the
measurement-accuracy defect in sources already integrated.

## Weekly Discovery Workflow (System 02 continuous verification)

The project owner pushed back on the previous phase's "still needs
network egress" framing as an unfinished-sounding non-answer: this dev
sandbox has none, but the GitHub Actions production deployment does, and
nothing was scheduled to actually use it. Presented the concrete design
choice via `AskUserQuestion` (separate scheduled workflow vs. adding the
step into the fast production deploy vs. just documenting the plan); the
project owner chose a dedicated weekly workflow with durable, PR-reviewed
evidence and gave a full specification (scope limited to `PLANNED`/
`CANDIDATE` sources; real evidenced verification; three named JSON
artifacts; incremental caching; promotion through the existing
qualification pipeline; PR only, never a direct commit to `main`).

Closed: `.github/workflows/discovery.yml` runs the new
`discover-planned-report` CLI subcommand
(`acquisition_intelligence.discovery_report`) weekly (plus manual
`workflow_dispatch`), reusing the unmodified `AcquisitionIntelligenceEngine.
run_for_target` (its own qualification-pipeline promotion already
applies — no new promotion mechanism was needed). A TTL + input-
fingerprint incremental cache (`DiscoveryHistoryRepository`) means an
unchanged source is not re-probed weekly; evidence lands on a dedicated
`discovery/latest` branch and one standing PR against `main`, never a
direct commit, and the workflow never flips a `SourceSpec.status` itself
— that stays a reviewed, manual engineering step per `AD-16`/`AD-24`,
exactly the same gate every prior source promotion in this codebase went
through. 9 new tests (`test_discovery_report.py`), all fake-backed; 568
backend tests pass; `ruff check` clean. Smoke-tested directly against
this sandbox's real (egress-less) network: an honest first run reports
`no_reachable_domain` for the 14 in-scope, targeted sources and
`not_targeted` for the 20 catalogued sources with no `TargetOrganization`
yet (~82s); a second run within the TTL served every result from cache
with zero new probes (~0.002s) — the caching behavior verified working,
not just asserted by a unit test.

See `docs/DATA_ACQUISITION.md`'s "Discovery workflow" section for the
full design, `CURRENT_MISSION.md` for the mission narrative, and
`NEXT_MISSIONS.md` for what's genuinely next (per-organization
`TargetOrganization` research for the 20 still-untargeted sources; wiring
`AcquisitionContinuityMonitor`'s DOWN-recovery into the same schedule;
reviewing the first real scheduled run's PR once GitHub Actions produces
one, which this session cannot verify directly).

## Frontend accuracy pass: surfacing already-computed data (Mission Control + Source Intelligence)

The project owner reviewed the live `/mission-control` and `/sources`
pages and reported real, computed backend data with no frontend path to
it at all — verified by reading the React components against the exact
artifacts feeding them, not by guessing.

Closed: Mission Control's Collectors table gained Breakdown (per-record-
type counts `collector_status.json` already carried, previously summed
into one "Yield" number)/Withheld/Reputation columns; Source
Intelligence's Reputation Dimensions block gained the 3 of 9 charter
dimensions that were computed but never rendered (`correction_rate`,
`duplicate_rate`, `historical_usefulness`) plus a composite-score stat
tile; and the weekly Discovery workflow (see the "Weekly Discovery
Workflow" section above) is now wired end to end — new TS types, new
`DashboardDataProvider`/`ArtifactsReader`/API-route methods, a new
"Weekly Discovery" Mission Control section, and a "Discovery Evidence"
block on Source Intelligence's detail panel — where it previously had
zero frontend path despite existing on disk. `deploy-pages.yml` copies
`research/data/discovery/*.json` into the dashboard data directory when
present (a plain file copy, not a Python re-export, since the Discovery
workflow already writes them in final shape). `npm run build`/`test`
clean for both `api` and `web` workspaces (required a fresh `npm install`
in this session first — `node_modules` had never been installed).

## TD-34: `ticker_data_gap_report.json` web/API wiring (System 13 dashboard layer)

Closes the last purely-engineering item on the post-freeze punch list
(TD-34): the backend artifact existed and was tested, but had no route,
no provider method, no TS type, and no UI surface.

Closed, following `financial_statements.json`'s exact existing wiring as
the template: `api/src/artifactsStore.ts`'s `tickerDataGapReport()`,
`api/src/routes/dashboard.ts`'s `GET /ticker-data-gap-report`,
`web/src/data/{DataProvider,ApiProvider,StaticJsonProvider}.ts`'s
`getTickerDataGapReport()`, and `web/src/types.ts`'s
`TickerDataGapReport`/`DataLayerGap` interfaces (hand-mirrored from
`meta.readiness`'s pydantic models — no `contracts/` schema exists for
this artifact, matching `financial_statements.json`'s own precedent).

UI: rather than a new page, Opportunity Center's existing "Decision
Readiness" table gained `onRowClick`, paired with a new "Data Coverage"
detail `Card` — the same click-to-select-plus-detail-panel pattern the
Opportunities table above it already uses for its "Evidence" panel. The
detail card renders the 5 named layers (Financials/Disclosures/News/
Macro/Knowledge) as meter cards, plus overall completeness,
Swing/Investment readiness flags, blockers, and next actions.

**Verified live in a real headless browser** (not just `tsc`/build/test
green): a real mock-mode `agx run` output was served through a
production Vite build, and clicking a Decision Readiness row (`ABUK`)
correctly populated the Data Coverage panel with its real 5-layer
breakdown (each showing 0% / "Below the readiness threshold for this
layer" — the honest current state of this sandbox's own data, not a
placeholder). `npm run lint`/`build`/`test` clean for both `api` and
`web` workspaces (added `getTickerDataGapReport` to the test suite's
`fakeProvider` fixture, the one other place implementing the full
`DashboardDataProvider` contract).

## Monte Carlo stress simulator (System 10, Experiment Factory)

Closes the one Experiment Factory gap `docs/PHASE_STATUS.md`/
`NEXT_MISSIONS.md` had explicitly named as a design decision, not a data
blocker: `MonteCarloExperiment` had been an honest `NotImplementedError`
placeholder since Experiment Factory was built.

Closed: `validation.stress_test.MonteCarloBlockBootstrapStressTester` —
a real block bootstrap, staying faithful to
`HistoricalWorstWindowStressTester`'s own stated philosophy ("the
adverse scenario is not simulated... but located"). Every simulated path
is built by resampling contiguous *blocks* (not single observations, the
distinction from the existing `BootstrapExperiment`) of the hypothesis's
real observed returns with replacement, preserving real short-run
autocorrelation the way actual bad runs cluster — never a parametric or
fabricated distribution. Recomputes the hypothesis's statistic over many
simulated paths and checks whether the adverse-tail percentile keeps the
full-sample statistic's sign. `block_size` auto-shrinks to fit short
series (mirroring the historical tester's own `window = min(self.window,
n)`), so it never raises for any series length the DATA_COLLECTION gate
already admitted; `seed` makes every run deterministic, the same
convention `BootstrapExperiment` already uses.

Wired in two places: `MonteCarloExperiment` (`hypotheses/
experiment_factory.py`) is now a real adapter over this tester (mirroring
`StressTestExperiment`'s exact adapter shape) instead of raising, so it
now counts toward the EXPERIMENT stage's real-results total and is stored
as a versioned artifact like every other experiment; `orchestration.
pipeline.DailyResearchPipeline`'s STRESS_TEST gate now requires *both* the
historical worst-window and the Monte Carlo block-bootstrap tester to pass
— surviving one adverse method isn't evidence the other wouldn't flip it.

**Verified**: a real mock-mode `agx run` against the same 4-ticker
scenario earlier phases used produces the identical 5 hypotheses as
before this change — the combined gate doesn't regress what already
passed. 8 new tests (616 total, up from 608); `ruff check` clean.

## Macro frequency alignment + no-look-ahead discipline (System 08/14)

Closes `NEXT_MISSIONS.md` item 2 (the project owner's own completion
plan item 5): `MacroAgent` aligned macro observations to trading days by
*exact date equality* — since daily/monthly/quarterly/annual series
almost never land on the same date as a trading day, every
lower-frequency macro series was silently starved of correlation
evidence entirely (a distinct gap from the earlier "Item 5" fix, which
only widened the *lookback window* size, not the *alignment* method).
Separately, nothing distinguished a macro value's `observation_date`
(the period it describes) from when it actually became publicly known —
treating a value as usable starting on its own period-end date is real
look-ahead bias.

Closed, as two independent pieces:

- **Frequency alignment**: `agents/macro.py`'s `_forward_fill_onto()`
  carries each macro observation's percentage change forward onto every
  trading day up to (never before) the next observation — standard
  last-observation-carried-forward step alignment, replacing the exact
  date-equality intersection. Never looks ahead: a trading day is only
  ever assigned a change from an observation dated on or before it.
- **No-look-ahead discipline**: new `data/point_in_time.py`
  (`is_knowable`/`known_as_of`) applies a declared, deliberately
  conservative per-source-class publication-lag floor (new debt, TD-37 —
  not a cited real average, picked low enough to never contradict this
  codebase's own live-verified evidence of a ~165-day-old real World Bank
  observation being collectible) and `data.snapshot.build_snapshot()`
  gained an optional `macro_series_sources` param that drops any
  observation not yet knowable as of the snapshot's own `as_of` before it
  ever reaches an agent. `production.pipeline.ProductionPipeline` wires
  the real mapping (`production.collector_plan.LIVE_MACRO_SERIES_SOURCES`,
  built from the same series-id groupings `LIVE_MACRO_SERIES_IDS` already
  uses) only in LIVE mode; mock/replay default to no filtering change
  (0 assumed lag), so no existing test's behavior shifted unless it
  explicitly opts in.

**One real regression caught and fixed before merging**: an initial,
more aggressive 365-day World Bank/UN SDG lag assumption directly
contradicted this codebase's own already-live-verified evidence (a real
collected World Bank observation only ~165 days old) — it would have
silently discarded genuinely-available real data, the opposite of the
goal. Scaled back to a 30-day floor, verified against the exact
regression test that first caught it
(`test_live_mode_collects_real_endpoints_and_reports_unavailable_sources`).

8 new tests (608 total, up from 600); `ruff check` clean.

## Entity resolution for news-to-ticker matching (System 02/08)

Immediate follow-up to NewsIntelligenceAgent, closing `NEXT_MISSIONS.md`
item 1: `RssNewsCollector`/`GdeltDocCollector`'s ticker attribution was a
bare case-insensitive **substring** check (`ticker.lower() in
title.lower()`), the exact "VLMR matches inside VLMRA" false-positive risk
the project owner's own completion plan named.

Closed: `universe.entity_resolution.resolve_ticker_mentions()` (new
module) matches a ticker only as its own word/token (never a substring of
a longer one) and, when a real company display name is available, also
matches the company's full name via the same conservative
"every-significant-token-present" discipline `discover_company_directory_links()`
already uses (reusing its exact `significant_tokens()` helper — one
definition, not a parallel one). `RssNewsCollector`/`GdeltDocCollector`
now accept `ticker_hints` as either a `{ticker: company_name}` mapping
(full entity resolution) or a plain `list[str]` (ticker-only, still
upgraded from substring to exact-token matching) — fully backward
compatible. `production.pipeline.ProductionPipeline` gained
`_ticker_companies()` (reads the same `UniverseProvider` `_tickers()`
already uses) and threads real company names from
`research/data/universe/EGX30.csv`/`EGX70.csv` (the reviewed, EGX-sourced
101-ticker seed — real English display names + ISINs, already present in
this codebase) all the way through `production.collector_plan.
build_collector_plan`/`build_live_collector` into both news collectors.

Deliberately no Arabic alias list (new debt, TD-36) — no verified
Arabic-language source for EGX30/EGX70 names exists in this codebase, and
guessing transliterations would risk a wrong match, worse than a missed
one.

**Verified live** (mock mode, real seed data): a real `agx run` against
the actual `research/data/universe/EGX30.csv` seed correctly resolves
"COMI reports strong Q2 net income growth" → `COMI` via the seeded
constituent list's real English name path, honestly reports `[]` for the
same news item when queried at a date before the seed's own `as_of_date`
(no look-ahead — `CollectedUniverseProvider`'s existing point-in-time
guarantee, not a regression). 600 backend tests pass (8 new, up from
592); `ruff check` clean.

## NewsIntelligenceAgent: real news sentiment now produces findings (System 08)

`NEXT_MISSIONS.md` named `agents.news_intelligence.NewsIntelligenceAgent`
as "the most directly-unblocked stub in the codebase" — it had been an
honest `NotImplementedError` stub only because no real Egyptian news flow
existed to research, and that stopped being true once `enterprise_press`/
`fra_egypt` started producing real, dated `NewsItem`/`CorporateEvent`
records every live run (see "First real Egyptian market data flowing
live" above).

Closed: implemented as a real, mechanical event-study-lite, mirroring
`CorporateEventsAgent`'s exact structure — for each ticker's news item,
`agents.news_sentiment.classify_headline_sentiment()` (a declared,
headline-only positive/negative keyword heuristic, same honesty tier as
`collectors.corporate_event_classifier`, new debt TD-35) classifies
sentiment; unclassifiable headlines are silently skipped, never guessed.
For sentiment-classified items with enough return history on both sides,
the agent compares mean adjusted return after the item to before it and
proposes a MICRO-horizon post-news-drift hypothesis when the shift clears
a threshold. Wired into `production.pipeline.ProductionPipeline`'s
Research Pipeline stage alongside the other five real agents (System 08 is
now 6 of 8 agents real).

**One real, previously-latent bug found and fixed while building this**:
`collectors.service._append_news` was the only per-record materialization
writer that blindly appended instead of merging idempotently by natural
key, unlike every sibling writer (`_write_price_bars`/
`_write_macro_observations`/`_write_corporate_events`/index constituents)
— collecting the same feed twice (a mock run followed by a replay run
reading the same archive, the exact scenario `test_production_pipeline.py`'s
mock/replay-determinism test exercises) silently duplicated every news
row. Harmless as long as nothing consumed `news.csv` for hypothesis
generation; caught immediately once `NewsIntelligenceAgent` did (the
existing determinism test failed 5 vs. 7 hypotheses on identical input
the moment the agent was wired in). Fixed by merging on
`(date, source, headline)`, matching every sibling writer exactly.

**Verified live** (mock mode): a real MFPC finding ("MFPC exhibits
downward price drift following positive news") flowed all the way through
`DailyResearchPipeline` into `hypotheses.json`, sourced from the existing
mock RSS headline "MFPC board declares dividend" — a genuine, if
uncalibrated, new research signal, not a fabricated one. 24 new tests (592
total, up from 568); `ruff check` clean.

## TargetOrganization coverage: 14 of 20 untargeted PLANNED sources (System 02)

The first real, live `agx discover-planned-report` run (2026-07-27, manual
`workflow_dispatch`, see the "Weekly Discovery Workflow" section above)
produced real evidence: of 34 in-scope sources, 1 verified reachable
(`skynews_arabia_economy`, a real RSS feed with 500 Wayback snapshots), 5
legality-blocked (a real candidate existed but robots.txt/ToS disallowed
it — a hard, non-negotiable stop, not something this codebase or this
assistant will bypass regardless of a "make it 100%" ask), 7 with no
reachable domain, 1 with no discoverable candidates, and 20 `not_targeted`
— no `TargetOrganization` entry existed for the engine to even attempt.

Closed: added `TargetOrganization` entries for 14 of those 20 — every one
with a single, unambiguous, publicly-known organization domain (IMF,
OECD, Egypt's Ministry of Finance, Egypt's Open Data portal, the Suez
Canal Authority, Investing.com, TradingView, Google Trends, the Wikimedia
Foundation, arXiv, SSRN, NBER, Google Scholar, ResearchGate) — same
public-knowledge category as every existing target, independently
re-verified for reachability before anything is trusted. Verified
locally (no egress in this sandbox, so all 28 now-targeted sources
honestly report `no_reachable_domain` — the point is they're attempted at
all now). 568 backend tests pass; `ruff check` clean.

Left `not_targeted` on purpose: `github_releases`, `company_social_official`,
`public_telegram`, `patents`, `hiring_signals` (each names more than one
candidate organization or is inherently per-company/per-channel — picking
one would be a fabricated guess), plus `company_ir`'s own per-constituent
marker (already correctly handled by `generate_company_ir_targets`).

See `CURRENT_MISSION.md`'s "target the closeable half of not_targeted"
entry and `NEXT_MISSIONS.md` for what's genuinely next.

## Decision-Centric Redesign implementation (2026-07-30)

The project owner authorized full implementation of the roadmap four
research/architecture documents produced this same day settled on
(`docs/DECISION_CENTRIC_AUDIT_2026-07-30.md` →
`docs/FREE_DECISION_DATA_BLUEPRINT.md` →
`docs/DECISION_EVIDENCE_MATRIX.md` →
`docs/ARCHITECTURE_ADVERSARIAL_REVIEW.md`'s final revised roadmap),
explicitly instructed to keep challenging those documents during
implementation rather than follow them mechanically. What actually
shipped, and where it deliberately deviated from the prior documents
under further scrutiny:

- **Registry cleanup**: removed the 11 sources with zero mapping in
  `acquisition_intelligence.capability.CAPABILITY_STRATEGIES`
  (`wikipedia_pageviews`/`google_trends`/`github_releases`/
  `company_social_official`/`public_telegram`/`patents`/`hiring_signals`/
  `google_scholar`/`researchgate`/`investing_com`/`tradingview`) and, once
  that emptied `SourceCategory.ALTERNATIVE` entirely, removed the enum
  value itself rather than leave a permanently-empty category — a
  deviation the prior documents didn't call for but the "eliminate
  unnecessary abstractions" mandate justified once the removal made it
  visible. Merged `Capability.ECONOMIC_RELEASES` into `MACROECONOMIC`
  (same source pool, no independent consumer). Added `moodys_ratings`/
  `sp_global_ratings`/`fitch_ratings` (Sovereign & Credit Context,
  `PLANNED`) and `amwal_alghad` (Egypt-specific news, `PLANNED`) as new
  catalogued sources and matching `TargetOrganization` entries for the
  existing, unmodified Acquisition Intelligence Engine to resolve.
- **`DatasetSnapshot.financial_statements`** (new field, populated only
  when `build_snapshot()` is given a `financials_provider`, mirroring the
  `pattern_lookback_days` precedent exactly): the correct way to give
  `FinancialPerformanceAgent` fundamentals data without breaking "agents
  never touch a live provider directly" — considered and rejected an
  alternative (inject `FinancialStatementProvider` straight into the
  agent's constructor) specifically because that would have violated the
  rule every other agent already follows.
- **`FinancialPerformanceAgent`** (System 08, above): real revenue-growth-
  trend and leverage-trend findings, mirroring `CorporateEventsAgent`'s
  event-study-lite structure. Deliberately *not* split into three
  separately-maintained "Reads" (Valuation/Growth/Balance-Sheet Safety) as
  `docs/DECISION_EVIDENCE_MATRIX.md` had implied — one extraction pass,
  two related findings, closing the three-way-disagreement risk the
  Adversarial Review's Section 1.9 named. Valuation (Q1) deliberately not
  attempted in this agent at all: it needs a current price *and* a peer/
  own-history multiple band, which is a decision-time computation (the
  Decision Service), not a research-time finding.
- **`decision_service/`** (new package — `country_risk.py`,
  `liquidity_floor.py`, `position.py`, `service.py`): the position-aware
  Decision Service, built exactly to the Adversarial Review's final
  architecture (Part 3) — a continuous target weight per ticker (extending
  `PortfolioConstructor`'s existing scoring), Buy/Increase/Hold/Reduce/
  Exit/No Action derived as a label from target-vs-current weight, a hard
  hard country-risk-crisis override and a hard liquidity-floor override
  (both short-circuit to target weight zero, never a votable weight), and
  an Abstain overlay resolving to Hold (if held) or No Action (if not).
  Deliberately its own package, never a stage inside
  `orchestration.pipeline.DailyResearchPipeline` or
  `production.pipeline.ProductionPipeline` — the daily pipeline's
  determinism guarantee and a position-aware decision's dependency on
  externally-supplied, non-autonomously-discoverable `PositionState` need
  to stay structurally separate (Section 1.10 of the Adversarial Review).
  Exposed as a read-only, on-demand `agx decide --date ...
  [--positions positions.json]` CLI command (TD-47, closed same
  session) — reconstructs a real `MarketState` from `--data-dir`,
  computes real `Recommendation`s via the existing `RecommendationService`,
  and prints the resulting position-aware decisions as JSON. Never wired
  into `production.pipeline.ProductionPipeline`'s autonomous stage list.
- **`assess_country_risk()`**: `CRISIS` severity requires a real, discrete
  `SovereignRatingAction` (a downgrade) — never inferred from a currency/
  macro move alone, since no collector exists yet for rating actions and
  a currency move of any declared threshold is exactly the kind of number
  this platform's anti-fabrication discipline says shouldn't stand in for
  a real event. Honestly unreachable in a real run today; the mechanism
  is real and ready the moment `moodys_ratings`/`sp_global_ratings`/
  `fitch_ratings` go `IMPLEMENTED`.
- **`meta.readiness.assess_decision_readiness`** extended (not duplicated
  — R2 of the Adversarial Review) with two new checks reusing the exact
  same `compute_illiquid_tickers`/`has_sufficient_currency_data` mechanisms
  the Decision Service uses: a liquidity-floor blocker (all three
  horizons) and a country-risk-currency-data-presence blocker (INVESTMENT
  only, checking for EGP/USD coverage under *either* the mock (`EGP_USD`)
  or real production (`egypt_official_fx_egp_per_usd`) series id — see
  TD-50/AD-49 below for the bug this closed — a real refinement over the
  existing generic "fewer than 3 macro series" check, which doesn't verify
  *which* series are present).
- One deliberate, named non-deviation: the Evidence Matrix's 31-row
  Critical/High/Medium/Low weight table was **not** implemented as a
  coded scoring formula (per the Adversarial Review's R1) — every score
  in this redesign still comes from the existing, transparent
  `confidence * expected_return / risk`-style formula
  `HorizonDecision`/`PortfolioConstructor` already compute, extended only
  by the two hard overrides above.
- 41 new tests (`test_country_risk.py`, `test_decision_service.py`, new
  cases in `test_scientist_agents.py`/`test_dataset_snapshot.py`/
  `test_decision_readiness.py`, plus `test_capability_catalog.py` and new
  `test_source_registry.py` regression cases); 734 backend tests pass;
  `ruff check` clean; a real mock-mode `agx run` end to end confirms no
  regression.

See `docs/MISSION_COMPLETION_REVIEW.md` for the full final system review
against the mission's eight completion criteria.

## Post-mission investor walkthrough: two real bugs closed (2026-07-31, TD-50/AD-49/AD-50)

An investor-perspective walkthrough of the live system (project owner
request, Arabic: "put yourself in an investor's place opening the system
to make a short/medium/long-term investment decision") found the system
correctly abstains on every ticker today, but surfaced two genuine,
previously-unnoticed implementation bugs behind part of that abstention
— distinct from the already-known, honestly-disclosed data gaps (no
licensed EGX vendor, no sector/peer data, no rating-agency collector):

- `decision_service.country_risk`'s country-risk-data-presence check
  hardcoded the mock fixture's currency-series id (`EGP_USD`), which never
  matched real production's actual World Bank series id
  (`egypt_official_fx_egp_per_usd`, from `production/collector_plan.py`'s
  `LIVE_WORLDBANK_INDICATORS`) — every real LIVE run reported "no currency
  data available" even though World Bank's FX series had been collected
  successfully every single run. Fixed by resolving against a declared
  alias list (`resolve_currency_series`/`has_sufficient_currency_data`,
  reused by `meta.readiness` rather than redeclared). Verified directly
  against real, already-persisted `production/state-latest` data (not
  assumed): the check now correctly reports `True`, and
  `assess_country_risk()` reports `DETERIORATING` (EGP moved +8.67% over
  the real ~2.5-year lookback window) where it previously reported
  nothing at all.
- `fred` was actively wired into every LIVE run's `MACROECONOMIC`
  capability pool despite timing out in 3 consecutive real
  `deploy-pages.yml` runs, with zero FRED series ever appearing in real
  persisted production data — a catalogued, `IMPLEMENTED` source that was
  never actually a working live dependency. Removed from the live
  ranking pool and from `production.collector_plan`'s live-wired source
  set; `FredCsvCollector`, its `SourceSpec`, and its own unit tests are
  untouched (a live-dependency change, not a legal/code deletion —
  reversible the moment a real fetch succeeds again).
- `agents.macro._SERIES_MECHANISMS` gained real production series ids
  (`DCOILBRENTEU`, `egypt_official_fx_egp_per_usd`, etc.) alongside the
  mock ids, so real findings get a real mechanism sentence instead of a
  generic fallback — a quality gap, not a correctness one, but directly
  relevant to explanation readability for a real investor.

Confirmed explicitly out of scope, not silently skipped: paid-only
sources (consensus estimates, forward EGP rate, CDS spreads, order-book
depth, full rating reports, XBRL) and already-`DISABLED` free-but-blocked
sources (`egx_official`, `cbe`, `imf`, `yahoo_finance`, `mubasher`,
`investing_com`) needed no code change — they were already structurally
un-depended-upon by `SourceStatus != IMPLEMENTED` refusing collector
construction. Real sector/peer-comparison data and a working
sovereign-rating collector remain genuine, disclosed gaps, not something
this pass could close without fabrication.

5 new regression tests; 741 backend tests pass; `ruff check` clean.

## Fix hardcoded Arabic backend prose (investor walkthrough, 2026-07-31)

A second investor-perspective walkthrough of the live system (same request
framing as TD-50/AD-49/AD-50 above), this time driven end to end in a real
headless browser against a real mock-mode `agx run`'s dashboard artifacts
(not just read from source), found a genuine, previously-unnoticed bug of
its own: `meta.publication_gate`, `meta.readiness`, and
`meta.decision_engine` had Arabic-language strings hardcoded directly into
backend-generated content (`PublicationGateCheck.label`/`blocker`,
`DecisionReadiness.blockers`/`horizon_blockers`, and every field of
`Explanation`/`HorizonDecision` produced by the decision engine) — a direct
violation of this repository's own documented rule (`CLAUDE.md`'s
"Bilingual EN/AR dashboard" section) that free-form backend prose stays
English so `i18next` is the only translation layer. In the live browser
walkthrough this rendered as raw, untranslated Arabic mixed into an
otherwise-English "Publication gate is blocking risk deployment" card —
precisely the text a fund manager reads first to understand why no
decision is being surfaced. Closed by translating every affected string to
English (meaning, thresholds, and currency figures preserved exactly),
updating the two test files that asserted on the old Arabic substrings
(one test, `test_executable_decision_language_is_arabic`, had directly
asserted the language *was* Arabic — renamed and rewritten, confirming this
was a deliberate prior choice, not an accidental leak), and correcting a
stale `cli.py` comment. `collectors/corporate_event_classifier.py`'s Arabic
keyword list is untouched — it matches real Arabic-language news headlines
from Enterprise/FRA/Al Borsa/Masrawy, which is a different concern
entirely (pattern-matching input, not generating output prose). Verified
live in a headless browser in both English and Arabic dashboard modes:
Publication Gate, Opportunity Center, and Company Workspace all render
correctly now, with backend prose staying English in both language modes
exactly as designed. 748 backend tests pass; `ruff check` clean; `api`/
`web` builds and test suites (18 + 41 tests) unaffected.

## Price-vs-fair-value as an explicit decision-quality criterion (2026-07-31)

Project owner request: compute fair value per ticker with multiple
methods, take the average, measure how far the current price sits from
it, and add that as one of the criteria determining the quality of the
current price for the decision. The native fair-value engine
(`valuation.engine.FairValueEngine`, seven models, weighted average of
whichever ≥3 survive) already existed and already blended into
INVESTMENT-horizon `expected_return` at a 20% weight
(`meta.recommendation_service.RecommendationService`) — but the gap
between price and fair value itself was never a visible, named criterion:
`meta.readiness.DecisionReadiness` only ever exposed a boolean
`fair_value_available` (could a fair value be computed at all), and the
20% blend silently folded the gap into a single combined `expected_return`
number with no separate signal for "is this specific price actually
attractive."

**Closed**: `DecisionReadiness` gained `price_vs_fair_value_pct`
((current close − `weighted_fair_value`) / `weighted_fair_value`, `None`
when no fair value could be computed) computed in
`assess_decision_readiness` from the same `FairValueEngine.value()` call
that already fed `fair_value_available` (no duplicate calculation). A new
declared threshold, `MAX_PRICE_ABOVE_FAIR_VALUE_PCT = 0.20` (AD-51,
TD-51 — same "declared, uncalibrated, named repayment trigger" posture as
every other threshold in this codebase's Decision Service), blocks
INVESTMENT-horizon readiness with an explicit reason ("Current price is
+NN% vs. the calculated fair value (weak entry quality).") both per-horizon
and in the overall blocker/next-action lists, exactly mirroring how
liquidity and country-risk-data-presence already gate this same horizon.
`RecommendationService`'s existing fair-value evidence string now also
states the gap explicitly ("current price=X.XX is +Y.Y% vs. fair value"),
not just the fair value figure and included models. Web:
`web/src/types.ts`'s `DecisionReadiness` interface gained both
`fair_value_available` (previously missing entirely, a small pre-existing
gap fixed alongside the new field) and `price_vs_fair_value_pct`, rendered
as a new "Price vs. Fair Value" column on Opportunity Center's Decision
Readiness table (red when the price is above fair value, green when
below), bilingual EN/AR (`opportunityCenter.json` in both locales) — no
`api`-side change needed since `artifactsStore.ts` already passes
`decision_readiness.json` through generically.

**Verified**: 3 new backend tests — two in `test_decision_readiness.py`
(price far above fair value blocks INVESTMENT readiness with the new
reason; price near fair value does not) using a hand-built financials
fixture scaled to land on either side of COMI's real mock closing price,
and one in `test_runtime_and_intelligence.py` proving the expected-return
blend actually shifts and the evidence text carries the new gap language,
via a hand-seeded INVESTMENT-horizon `KnowledgeObject` (bypassing the
promotion gate the same way `test_dashboard.py` already does for export
tests). 751 backend tests pass (up from 748); `ruff check` clean;
`npm run build`/`test` clean for both `api` and `web` (41 web tests,
including a fixture update for the two now-required `DecisionReadiness`
fields); verified live in a headless browser against a real mock-mode
`agx run`'s regenerated dashboard artifacts — the new column renders "N/A"
honestly for tickers with no computed fair value (this sandbox's local
mock data has no financial-statement fixtures), never a fabricated
percentage.

## Market Breadth artifact (post-price-vs-fair-value)

`NEXT_MISSIONS.md`'s own "genuinely next" list, after the Decision-Centric
Redesign, named one item that wasn't gated on external evidence or a
business decision: "Market Breadth artifact — derivable from already-
collected Price Data; additive dashboard/analytics work, still not built."
Market Intelligence's own "Market Breadth & Liquidity" card had carried an
honest empty-state placeholder for the same reason since the frontend
audit phase ("Breadth and liquidity require a backend-computed artifact...
this platform doesn't export yet"). This phase closed it.

**Closed**: new `market_memory.breadth.compute_market_breadth()` /
`MarketBreadthReport` — advancers/decliners/unchanged, an advance/decline
ratio (`None` when there are zero decliners, never a fabricated "infinite"
ratio), average daily return, and a count of tickers trading above/below
their own trailing-20-trading-day average volume (`TRAILING_VOLUME_WINDOW_DAYS`,
TD-52 — a declared, uncalibrated window, same posture as every other
declared threshold in this codebase). Computed entirely from a
`MarketState`'s own `dataset_snapshot.price_history`, through
`data.adjustments.adjusted_dated_returns()` — CLAUDE.md's return-adjustment
rule ("never raw `[bar.close for bar in bars]`") applies here exactly as it
does to every agent/experiment, so a stock split or dividend on the
reconstruction date can't masquerade as an advance or decline. Wired into
`production.pipeline.ProductionPipeline._stage_dashboard_artifact_generator`
as a new, optional `market_breadth.json` artifact (`None` until a
`MarketState` has actually been reconstructed — the same honest-absence
convention `runtime_status.json` already established), validated by
`dashboard.validate.validate_dashboard_artifacts`. `api`/`web`: a new
`GET /market-breadth` route + `ArtifactsReader.marketBreadth()`, and both
`ApiProvider`/`StaticJsonProvider` gained `getMarketBreadth()`. Market
Intelligence's breadth card now renders real advancers/decliners/unchanged/
ratio/average-return/volume-breadth stat tiles instead of the placeholder,
bilingual EN/AR — Market Regime stays an honest gap (no classification
artifact exists upstream).

**Verified**: hand-computed against the real mock CSVs
(`research/data/mock/prices/COMI.csv`/`MFPC.csv`) rather than asserted
blind — on 2026-06-09, COMI's close rose (69.30→69.90) and its volume
(1,720,000) exceeded its own trailing average while MFPC's close fell
(222.10→220.80) on below-average volume (280,000), giving a predictable
1 advancer / 1 decliner / 1 above-average / 1 below-average result the new
tests assert directly. 7 new backend tests (4 in `test_market_breadth.py`,
2 in `test_production_artifacts.py`, 1 in `test_production_pipeline.py`,
plus assertions added to 2 existing pipeline tests); 758 backend tests
pass (up from 751); `ruff check` clean; `api` (19 tests, up from 18) and
`web` (41 tests) build/test suites clean, including a fixture update for
the new `getMarketBreadth` method in `App.test.tsx`'s fake provider.

## The real DATA_COLLECTION-starvation bug and dead-source retirement (post-Market-Breadth)

The project owner reviewed the merged, deployed dashboard and reported
three things in one message: still no clear investment decision reachable,
still sources that look unconnected, still sources that look like they add
no value. Rather than answer from memory or from the mock-mode fixtures
this codebase's tests usually run against, this phase pulled the real
persisted production state (`production/state-latest`, restored/committed
by every scheduled `deploy-pages.yml` run per debt #40) and investigated
against it directly.

**Finding 1, the real reason no decision was ever reachable.** Real
persisted `hypotheses.json` showed **777 hypotheses, every single one
stuck at `DATA_COLLECTION`**, none ever advancing further. The stage
history recorded the exact reason: `"19 aligned observations (min 60)"` —
`orchestration.pipeline.PipelineConfig.min_observations = 60`. That number
looked odd next to real persisted `prices/COMI.csv`, which has **118 real
collected trading days spanning 2026-01-28 to 2026-07-30** — clearly more
than 60. The actual bug: `production.pipeline.ProductionPipeline
._stage_market_memory` passed a hardcoded `lookback_days=30` (*calendar*
days) for every mode's standard `price_history`/`corporate_events`/`news`
window, with no LIVE-mode override — unlike `macro_lookback_days`/
`pattern_lookback_days`, which already got their own LIVE-only wider
windows (`LIVE_MACRO_LOOKBACK_DAYS`/`LIVE_PATTERN_LOOKBACK_DAYS`) for
exactly this class of problem. EGX trades Sun-Thu (5 of 7 days), so 30
calendar days yields only ~19-21 real trading days — a structural ceiling
strictly below 60 that no amount of real accumulated history could ever
cross, regardless of how many months a source had been collecting.

**Verified directly against real data, not asserted.** Exported the real
`production/state-latest` data tree and re-ran the actual research
pipeline (`DailyResearchPipeline`, the real agents) against it, unmodified
except for the lookback window:
- At the original `lookback_days=30`: 337 findings, **0 progressed past
  DATA_COLLECTION** — reproducing the exact real production failure.
- At a new `lookback_days=180`: the identical real data produced 194
  findings, of which 96 reached BACKTEST, 5 reached PEER_VALIDATION and
  **were genuinely promoted to `KnowledgeObject`s** — proof the fix, not
  just the diagnosis, is correct.

**Closed**: `production.collector_plan.LIVE_PRICE_LOOKBACK_DAYS = 180`
(new constant, same file as the other two LIVE-only windows), deferred
through `ProductionPipeline.__init__`/`.run()` the identical way
`macro_lookback_days` already is (`price_lookback_days` constructor
override → mode-based default in `run()` → threaded into
`_stage_market_memory`'s `MarketMemory(...)` call). MOCK/REPLAY keep the
original 30-day default unchanged, so no existing test fixture or
assertion was affected — confirmed by the full suite passing unmodified.
180 days (not the bare 60-trading-day minimum) was chosen for real margin
against holidays and two tickers' series not perfectly overlapping, while
staying a bounded, explainable "recent regime" window rather than
reaching for years of history the way the pattern-search window
deliberately does. New debt: TD-53 (the window itself is a declared,
uncalibrated margin choice, and one shared window across every horizon
and agent is a simplification worth revisiting once real decision history
exists).

**Finding 2, sources that "add no value" were never actually removed.**
The Decision-Centric Redesign's "registry cleanup" claimed to remove 11
sources with zero `Capability` mapping (`docs/DECISION_CENTRIC_AUDIT_2026-07-30.md`
section 3.5). Confirmed the code-level deletion genuinely happened — none
of the 11 ids appear anywhere in the current `sources/catalog.py`. But
diffing the real persisted `source_registry.json` against the current
catalog found **all 11 still present**, 9 of them still `PLANNED`
(`company_social_official`, `github_releases`, `google_scholar`,
`google_trends`, `hiring_signals`, `patents`, `public_telegram`,
`researchgate`, `wikipedia_pageviews` — the other 2, `investing_com`/
`tradingview`, were already `DISABLED` from an earlier, unrelated
ToS/403 finding). The mechanism: `sources.catalog.seed_registry()` only
ever *adds* a source id it doesn't already have — nothing ever re-derives
the registry's full membership from the current catalog, so a code-level
deletion is invisible to any deployment that had already persisted that
source before the deletion shipped. The redesign's own claim was accurate
about the code; it was never true for the live, continuously-running
deployment.

**Closed**: `sources.registry.SourceRegistry.retire_removed(current_catalog_ids)`
(new method) transitions any already-persisted source whose id is absent
from `current_catalog_ids` to `SourceStatus.DISABLED` (which
`default_lifecycle_for_status` already maps to `ActivationStatus.RETIRED`)
via a new revision — never an edit or deletion, so the full prior history
stays intact — and skips anything already `DISABLED`. Wired into
`seed_registry()` (`current_ids` collected from `seed_sources()` during
the existing add-loop, then `registry.retire_removed(current_ids)`
called once at the end), so it runs on every pipeline execution from now
on: any future catalog deletion reaches a live deployment on its very
next run, closing this gap structurally rather than just for today's 9.
Verified directly against the real registry: all 9 stale sources
correctly retired with a clear `notes` reason, while every genuinely
still-catalogued-but-unmapped source (`fred` — deliberately kept per
debt #50, `global_benchmarks`, `rss_generic`, and the `stockanalysis`/
`yahoo_finance`/`mubasher` provider legs) was left completely untouched —
`fred`'s revision didn't even bump. New debt: TD-54 (this only catches an
outright catalog deletion, not a still-catalogued source silently
orphaned from every capability's candidate pool).

**Finding 3, the third complaint (sources still unconnected) is not a new
gap.** No new evidence contradicted the extensive, already-documented
state (`docs/ACQUISITION_STRATEGY.md`, this file's own history above):
most `PLANNED` sources remain blocked by a real network/ToS/anti-bot wall
or a named, already-decided business call (a licensed vendor, explicitly
declined per AD-32) — not a code gap this phase could close without
fabricating a connection or bypassing a legal/ToS rule.

**Verified**: 6 new backend tests (4 in `test_source_registry.py`
covering `retire_removed`'s three behaviors plus `seed_registry`'s
integration, 2 in `test_production_pipeline.py` covering LIVE vs.
MOCK/REPLAY price-lookback behavior and the constructor override); 764
backend tests pass (up from 758); `ruff check` clean. No `api`/`web`
changes this phase (backend-only). See `CHANGELOG.md`'s matching entry
and `docs/ARCHITECTURE_DECISIONS.md`'s AD-52/AD-53 for the full reasoning.

**Not verified in this phase, named as the immediate next check**: this
phase's evidence comes from re-running the real research pipeline against
a locally re-exported copy of the real persisted data, not from watching
an actual live `deploy-pages.yml` run produce a promoted `KnowledgeObject`
end to end. That's the next scheduled (or manually triggered) run's job —
see `NEXT_MISSIONS.md`.

## Decision object completeness + live Decision Center (2026-08-01)

The project owner's mission brief restated AGX's purpose as producing a
complete institutional investment decision (Decision, Target Portfolio
Weight, Investment Horizon, Confidence, Investment Thesis, Supporting
Evidence, Contradicting Evidence, Key Risks, Active Catalysts, Monitoring
Events, Invalidation Conditions, Expected Review Date) as its primary,
reachable output. Auditing `decision_service.PositionAwareDecision`
against that exact field list (not from memory -- a fresh read of
`service.py`, `cli.py`, `api/`, and `web/`) found 4 of 12 fields present
(action, target_weight, confidence, invalidation_conditions via
`explanation`), 1 partial (thesis folded into `why_this_stock`/`why_now`
prose with no dedicated field), and 6 missing outright (horizon,
contradicting_evidence, key_risks, active_catalysts, monitoring_events,
expected_review_date) -- and, separately, that `decision_service` was
completely unreachable from `api/`/`web/`: no route, no TS type, no page,
confirmed by grep returning zero matches for `PositionAwareDecision`
anywhere outside `research/`.

**Closed, both halves:**

- **The missing fields, all derived from data this service already
  computes or is handed -- never fabricated.** `horizon` (always
  `Horizon.INVESTMENT`, now explicit). `investment_thesis`: one
  deterministic sentence built only from the decision's own numbers.
  `key_risks`: the horizon's own `risk_metric`/`expected_risk`, any
  sibling (MICRO/SWING) horizon signaling AVOID, plus the existing
  liquidity/country-risk override `reasons`. `contradicting_evidence`: a
  sibling horizon disagreeing in direction with the INVESTMENT thesis,
  plus `CountryRiskAssessment.reasons` whenever severity is not `NORMAL`
  (not only `CRISIS`) -- deliberately distinct from
  `invalidation_conditions` (hypothetical future conditions), which
  `OpportunityCenter.tsx` had been mislabeling as "Contradicting
  Evidence" for the *unrelated* 4-way `Recommendation` object; this fix is
  scoped to the new 6-way `PositionAwareDecision` object only, not a
  change to that existing page. `active_catalysts`: real, already-
  collected upcoming `CorporateEvent`s per ticker (`decide_portfolio()`
  gained an optional `corporate_events` param, wired from
  `snapshot.corporate_events` in `cli.py`) -- same event source and same
  `event_date >= as_of` filter `OpportunityCenter.tsx`'s catalysts panel
  already uses, so it inherits the same honest limitation (the collection
  window itself never extends past `as_of`, so this is realistically
  same-day events only until a real forward-dated announcement source
  exists). `monitoring_events`: which of a decision's own evidence
  references are a `KnowledgeObject` currently in
  `KnowledgeStatus.MONITORING` (`decide_portfolio()` gained an optional
  `knowledge_store` param) -- real continuous-learning state, not a
  generic reminder. `expected_review_date`: `HorizonDecision.valid_until`,
  now copied onto the decision directly. 12 new tests in
  `test_decision_service.py`, 778 backend tests pass (up from 764);
  `ruff check` clean. `contracts/position_aware_decision.schema.json`
  added to `research/scripts/export_schemas.py`'s served-model set; `api/`
  and `web/` `types.ts` mirrors updated to match.

- **The reachability gap.** `decision_service` is deliberately
  stateless-per-call, queried on demand, and must never be wired into a
  scheduled/autonomous run (existing rule, unchanged) -- and production is
  a static GitHub Pages site with no live backend by design, so a
  precomputed artifact was never an option without violating that rule.
  The correct fix, matching how `agx decide` already reaches this
  service: a new `POST /decisions` route (`api/src/routes/decisions.ts`)
  that shells out to the *same* `agx decide` CLI invocation
  (`uv run --project <researchDir> python -m agx_research.cli --data-dir
  <DECISION_DATA_DIR> ... decide --date ... [--positions <tmpfile>]`) on
  each HTTP request -- an HTTP request triggering a fresh on-demand
  computation is the same "queried on demand" semantics as a CLI
  invocation, not a second autonomous path. No business logic moved into
  TypeScript: the route only shapes the request into the CLI call and
  returns its stdout. `DECISION_DATA_DIR` has no default -- an
  unconfigured route reports `501` honestly rather than guessing a
  directory that might disagree with the rest of the dashboard. New web
  page **Decision Center** (`/decisions`): a positions editor (ticker,
  current weight, optional average cost -- never stored, entered only for
  the query) plus a "flat-portfolio read" shortcut, rendering the full
  decision (action, weights, thesis, key risks, contradicting evidence,
  catalysts, monitoring events, invalidation conditions, supporting
  evidence, review date) per ticker. `StaticJsonProvider.postDecisions()`
  always throws a typed `DecisionCenterUnavailableError` with a specific,
  actionable message (never a fabricated result) -- the GitHub Pages
  build has no backend to compute this against by design. A prominent
  card on the AI Briefing landing page ("Want a decision for your own
  portfolio?") links to it, so the mission's "what should I do today"
  question has a real, reachable answer path from the landing page for
  the first time, not just a CLI command mentioned in a doc. Verified live
  end to end: a real mock-mode `agx run` + `export-dashboard`, `api/`
  started with `DECISION_DATA_DIR` pointed at it, and Decision Center
  driven in a real headless browser (Playwright/Chromium) -- submitting a
  held COMI position with no fresh evidence correctly returned an
  abstained Hold with the right key-risk reason, zero console errors. 23
  `api` tests pass (4 new, covering the 501/400 paths without requiring a
  live subprocess), 46 `web` tests pass (7 new, covering `postDecisions`
  on both providers and the new route/page/CTA-link); both workspaces'
  `build`/`lint` clean.

**Not done, named as genuinely next**: Market Regime classification
remains a confirmed, real gap (`grep -rn "MarketRegime"` across
`research/src/` returns nothing) -- named again here since the mission
brief's landing-page checklist asks for it explicitly; no artifact or
model exists upstream yet, and building one was out of scope for this
session's two closed items above. See `NEXT_MISSIONS.md`.

## Market Regime classification (2026-08-01, immediate follow-up)

`NEXT_MISSIONS.md`'s top-priority item after the decision-object work above:
Market Regime was a confirmed, real gap (`grep -rn "MarketRegime"` across
`research/src/` returned nothing) and the mission brief's landing-page
checklist names "current market regime" explicitly as item 1.

**Closed**: new `market_memory.regime.compute_market_regime()`, built the
same way `market_memory.breadth.compute_market_breadth()` already is --
adjusted, equal-weighted returns across the universe
(`data.adjustments.adjusted_dated_returns()`, never a raw close-to-close
calculation), no live lookups (derives everything from an already-
reconstructed `MarketState`). Reports **two independent axes** rather than
one fused combinatorial label (`R5`'s "a label over a continuous number,
never a lookup table" discipline, the same reasoning
`decision_service.service` and `assess_country_risk` already follow):
`trend` (bullish/bearish/neutral, from the cumulative equal-weighted
return over a trailing window) and `volatility` (low/elevated/high, from
that same window's realized daily standard deviation). Declared,
uncalibrated thresholds (new debt TD-56, same posture as TD-6/17/20/33/
44/45/46/51/52/53 -- no real multi-year EGX regime history exists yet to
calibrate against).

Wired end to end exactly like Market Breadth: `production.artifacts.
export_market_regime()` → `market_regime.json` (every `agx run`, mock or
live) → `dashboard.validate`'s optional-artifact validator → new
`GET /market-regime` route (`api/`) → `DashboardDataProvider.
getMarketRegime()` (both providers) → rendered on **both** the AI Briefing
landing page (a new banner card, first thing under the disclaimer, with a
link into Market Intelligence for detail) and Market Intelligence's
existing "Market Regime" card, which previously rendered a permanent
empty state. Verified live end to end: a real mock-mode `agx run` +
`export-dashboard`, `api/` served from it, and both pages driven in a real
headless browser (Playwright/Chromium) -- zero console errors, consistent
with the sibling Market Breadth card's own honest-empty-state behavior
under the same run.

10 new backend tests (`test_market_regime.py`, covering bullish/bearish/
neutral trend classification, high volatility independent of trend,
insufficient-data honesty, and the lookback window boundary, plus 2 in
`test_production_artifacts.py` and 1 in `test_production_pipeline.py`);
788 backend tests pass (up from 778); `ruff check` clean. 24 `api` tests
pass (1 new); 46 `web` tests pass, build/lint clean for all three
workspaces.

**Not done, named as next**: the sibling gap this section's title also
used to name -- Market Regime & **Historical Comparison** -- remains open;
historical-analog comparison needs a historical-regime database
(`HistoricalReviewer`, System 12) that's genuinely blocked on years of
real trading history not yet collected, per the existing, unchanged System
12 status. The Market Intelligence card's title was narrowed from "Market
Regime & Historical Comparison" to "Market Regime" specifically so the now
real content doesn't imply the still-missing half is also available.

## Institutional Investment Validation (2026-08-01)

The project owner redefined the mission: engineering implementation is no
longer primary. The objective became proving -- with real evidence, not
more features -- that the platform's decision engine is internally
consistent, explainable, and economically meaningful, answering 10 named
questions (rank the full EGX30/EGX70 universe, explain every ranking,
reject every stock if appropriate, recommend holding cash, build a
complete portfolio, compare against a benchmark, detect thesis failure,
identify why a recommendation changed, trace every decision to evidence),
via repeatable scenarios that actively attempt to falsify the platform's
own conclusions -- explicitly not a request for more passing software
tests.

**Delivered**: a new `institutional_validation/` package (deliberately
separate from `validation/`, MASTER_PROMPT.md System 11's *statistical*
hypothesis validator -- this package validates the *decision engine's*
aggregate behavior once hypotheses are already knowledge, and imports
System 11's siblings rather than duplicating any of their logic):

- `scenarios.py` -- repeatable, deterministic scenario builders exercising
  real platform classes (`KnowledgeStore`, `RecommendationService`,
  `PortfolioConstructor`, `DecisionService`, `ContinuousLearningMonitor`,
  `DecisionLedger`) against both the real, checked-in 101-ticker
  EGX30+EGX70 universe (`real_universe_tickers()`) and clearly-labeled
  synthetic data built to stress mechanisms mock data can't otherwise
  reach at scale (a full 101-ticker synthetic universe spanning every
  decision outcome; a zero-evidence universe; an all-reject universe; a
  maximal-conviction-vs-country-crisis override attempt; a declining-vs-
  confirming thesis-lifecycle pair; a hand-verifiable benchmark scenario;
  a hypothesis-to-decision evidence chain).
- `diffing.py` -- a genuinely new capability Q9 revealed was missing:
  `diff_knowledge_history()`/`diff_knowledge_revisions()`, built entirely
  on `KnowledgeStore.revisions_for()` (already-existing versioning, no new
  storage path), reconstructing a human-readable "what changed and why"
  timeline for a knowledge object. Scoped honestly: only `KnowledgeObject`
  is diffable, because it's the only decision-chain entity actually
  persisted with a version history -- `Recommendation`/
  `PortfolioRecommendation` are recomputed fresh every run and never
  stored with one, named as a real limitation rather than silently built
  around.
- `checks.py`/`report.py`/`runner.py` -- one check function per question,
  each graded PASS/PARTIAL/BLOCKED/FAIL (never a bare boolean -- BLOCKED
  means the mechanism is real and correct but data coverage can't yet
  demonstrate it, distinct from FAIL, a genuine defect) with concrete
  evidence and named findings, assembled into a `ValidationReport`
  (JSON + Markdown) by `run_institutional_validation()`.
- New `agx validate-investment` CLI command (self-contained -- no
  `--data-dir` setup needed, every scenario builds in memory), exit code 2
  only on a genuine FAIL.

**A real defect was found and fixed during development, by the
framework's own falsification attempt**, not left in place: the first
version of the full-universe synthetic scenario hand-set
`publication_status=PUBLICATION_READY` directly, which left every
`HorizonDecision.max_position_pct` at its default `0.0` (that field is set
*only* by `meta.publication_gate.apply_publication_gate()`, never by
`MetaDecisionEngine`) -- silently making every synthetic BUY_CANDIDATE
portfolio-ineligible despite scoring positive. `check_complete_portfolio`
caught it (26 positions, weight sum `0.0000`) by refusing to accept that
contradiction. Fixed by calling the real `apply_publication_gate()`
instead of hand-setting one of its two outputs -- the platform code itself
had no bug; the validation scenario did, and the framework's own
discipline caught it before it could produce a false PASS.

**Report as of this session** (`agx validate-investment`, run against the
real EGX30/EGX70 lists plus the scenarios above): 3 PASS (Q3 explain,
Q4 reject, Q5 hold cash, Q6 complete portfolio -- 4 actually PASS), 4
PARTIAL (Q1/Q2 universe ranking -- mechanism proven at full 101-ticker
scale, real mock coverage is 1/31 EGX30 and 1/70 EGX70 tickers today,
data-blocked not code-blocked; Q8 thesis-failure detection -- mechanism
proven correct in both directions, not autonomously wired, new TD-57; Q9
change attribution -- new capability proven for knowledge, not for
recommendations, named limitation), 1 BLOCKED (Q7 benchmark comparison --
math proven correct with synthetic data, no real EGX30-index-level price
series exists to evaluate against today, new TD-58), 0 FAIL. Overall
verdict: PARTIAL (no genuine defect remains). 807 backend tests pass (up
from 788, 21 new); `ruff check` clean.

**Not done, named as next**: the two BLOCKED/named-gap findings (TD-57,
TD-58) are real, scoped follow-up items, not silently left implicit in a
prose report only.

## Investment Proof Framework (2026-08-01)

The project owner's final mission for this phase: acting simultaneously as
CIO/CRO/Head of Research/Principal Architect, build the complete
architecture to answer "would a rational institutional investment
committee trust this system with capital?" -- 10 phases, 10 non-negotiable
rules (free data only, never fabricate missing information or historical
performance, every decision explainable and evidence-traceable, every
module justified, complexity removed where unjustified, determinism
preserved, all validation reproducible), and an explicit instruction that
missing *data* (not missing *engineering*) should be reported as `READY
FOR DATA` and never block the work.

**Delivered**: new `research/src/agx_research/investment_proof/` package,
composing `institutional_validation/` (Mission 3's framework) rather than
duplicating it --

- `categories.py` -- the Macro/Sector/Quality/Value/Catalyst/Risk/
  Liquidity/Portfolio/Execution/Technical taxonomy and the real
  `creator_agent -> Category` map (`AGENT_CATEGORY_MAP`) every engine
  below shares, plus `RETURN_CONTRIBUTING_CATEGORIES`/`MODIFIER_CATEGORIES`
  distinguishing additive return contributors from gate/multiplier
  modifiers.
- `attribution.py` (`DecisionAttributionEngine`) -- Phase 3. Decomposes a
  real `KnowledgeWeightedHorizonModel` + `FairValueEngine` expected return
  into named category contributions, computed with the exact same code the
  platform uses for a real decision (not an approximation). `attribution_
  residual` (`final_expected_return - sum(contributions)`) is a real
  consistency check, verified ~1e-18 (exact) against real knowledge-weighted
  predictions.
- `counterfactual.py` (`CounterfactualEngine`) -- Phase 4. Real ablation:
  removes every knowledge object in one category and recomputes the
  prediction and decision with the same real `KnowledgeWeightedHorizonModel`
  + `MetaDecisionEngine` calls, reporting which categories are actually
  `decisive` (their removal flips the action) rather than assumed
  important. A real bug was found and fixed during development: the first
  version never applied `reference_price` to the counterfactual prediction,
  structurally forcing every would-be BUY_CANDIDATE to ABSTAIN.
- `committee_validation.py` (`CommitteeValidationEngine`) -- Phase 8.
  Aggregates attribution + counterfactual results across a ticker batch
  into per-category agreement/disagreement/decisiveness rates.
  `historical_usefulness_status` is honestly `ready_for_data` for every
  committee (new TD-60) -- correlating a committee's opinion with later
  realized outcomes needs `DecisionRecord` to know which categories
  contributed to each recorded decision, which it does not yet.
- `portfolio_validation.py` (`PortfolioValidationEngine`) -- Phase 7.
  Herfindahl concentration index, top-3 weight, sector exposure (when a
  sector map is supplied), weight reconciliation (invested + cash == 1.0),
  an explicitly-named `expected_downside_proxy` (a weighted-average
  `expected_risk`, never presented as a true VaR -- a real covariance
  matrix this platform doesn't have), and decision-conflict detection
  between the position-unaware (`PortfolioConstructor`) and position-aware
  (`DecisionService`) construction paths.
- `stability.py` (`DecisionStabilityEngine`) -- Phase 9. Calls
  `RecommendationService.recommend()`/`DecisionService.decide_portfolio()`
  multiple times against identical `KnowledgeStore` state and diffs the
  results (stripping only `produced_at` timestamps, the one field expected
  to differ) -- determinism measured directly, not assumed from code
  reading.
- `calibration.py` (`ConfidenceCalibrationFramework`) -- Phase 5. Brier
  score, a 10-bin reliability curve, and expected calibration error (ECE)
  over real `DecisionLedger` records. Honestly returns
  `sample_status="insufficient"` with every statistic `None` below the
  same 30-record floor `DecisionLedger.performance_summary()` already
  uses -- never a fabricated number standing in for a real sample.
- `walk_forward.py` (`WalkForwardInfrastructure`) -- Phase 2. The genuinely
  missing driver connecting `RecommendationService.recommend()` +
  `DecisionLedger.record_recommendations()` across a real trading-day
  range (`StaticEGXCalendar`), with per-day exception isolation matching
  `RuntimeEngine.run_range()`'s own discipline. Proven against 8 real mock
  trading days, 80 recommendations recorded, 0 errors. `required_datasets()`
  names exactly what real EGX history is still needed (multi-year real
  price history, a real EGX30-index-level series, daily promoted-knowledge
  snapshots at scale), each honestly `ready_for_data` today -- never
  claimed available before it is.
- `thesis_survival.py` (`ThesisSurvivalEngine`) -- Phase 6. Compares an
  original `PositionAwareDecision` against a later re-evaluation of the
  same ticker: `broken_assumptions` (cited knowledge later `RETIRED`,
  looked up via `KnowledgeStore.latest()`), new contradicting evidence,
  lapsed/remaining catalysts, and review-date discipline -- a mechanical
  `ThesisStatus` (ALIVE/WEAKENING/BROKEN/EXPIRED), never a sentiment guess.
- `capital_trust.py` (`InvestmentProofEngine`/`CapitalTrustReport`) --
  Phase 10, and the top-level orchestrator for Phases 1-9. Runs
  `institutional_validation.run_institutional_validation()` plus every
  engine above against one shared, real-code-driven scenario (a capped
  subset of the real EGX30 universe, `synthetic_full_universe()`, plus a
  dedicated INVESTMENT-horizon thesis-lifecycle scenario --
  `institutional_validation.scenarios.thesis_lifecycle_scenario()` uses
  SWING, which `DecisionService` never acts on per AD-35, so this phase
  builds its own INVESTMENT-horizon analogue with the same real classes).
  `overall_verdict` (YES/NO/PARTIALLY) is computed mechanically from the
  per-dimension `CheckVerdict`s -- any FAIL anywhere forces NO; no FAIL but
  at least one BLOCKED forces PARTIALLY; only if every dimension clears
  does it reach YES. Never asserted independently of the dimensions
  driving it.

New `agx investment-proof` CLI command (JSON + optional Markdown Capital
Trust Report, same `--out`/`--markdown-out`/exit-code-2-on-genuine-FAIL
shape `validate-investment` already established).

**Two real, pre-existing production bugs found and fixed** while directly
exercising the CLI decision path the mission required (not introduced by
this mission, and not found by the framework's own checks -- found by
using `agx decide` and `DecisionService` the way an investor actually
would): (1) `DecisionService.decide_portfolio()` never referenced
`HorizonDecision.max_position_pct` in its `target_weight` formula, so
identical evidence sized a position ~6x larger through the position-aware
path than through `PortfolioConstructor` (which already applied it
correctly); (2) `agx decide`/`cli.py` never called
`meta.publication_gate.apply_publication_gate()` at all, so every real
`agx decide`/Decision Center call always silently reported
`no_action`/zero weight with no reason naming the cause -- a Rule 5
("every decision must be explainable") defect on the CLI/web decision path
built in an earlier mission, not merely a sizing bug. Both fixed; the
zero-weight *outcome* itself remains correct today (no real EGX vendor is
licensed yet, per `docs/DECISION_SYSTEM_ACCEPTANCE.md`) -- what was
missing was the cap and the explanation. See TD-59/AD-55.

**Capital Trust Report, current run** (`agx investment-proof`, 15-ticker
real-EGX30-derived scenario): `decision_stability` PASS, `decision_
attribution` PASS (residual ~1e-18), `counterfactual_analysis` PASS,
`committee_validation` PASS (historical_usefulness honestly ready_for_data,
TD-60), `portfolio_validation` PASS, `thesis_survival` PASS,
`confidence_calibration` BLOCKED (0 real benchmark-evaluated
`DecisionLedger` records, 30 required), `walk_forward_backtest` BLOCKED (0
real trading days of the 252 a meaningful replay needs). Overall verdict:
**PARTIALLY** -- every mechanism the platform can run today is
architecturally complete and passes; the two BLOCKED dimensions are
honestly gated on real, licensed EGX history that does not exist yet, not
on any remaining engineering work. 833 backend tests pass (up from 809, 24
new: `test_investment_proof.py`, `test_cli_investment_proof.py`); `ruff
check` clean.

**Not done, named as next**: `InvestmentProofDashboard` (the mission's
10th named deliverable, alongside `CapitalTrustReport`) exists today as
the JSON/Markdown `agx investment-proof` CLI output only -- no dedicated
`api`/`web` route or dashboard page was built this session, matching this
codebase's "dashboard data goes through `agx_research.dashboard.export`
plus a matching route" convention, which a `CapitalTrustReport` web
surface would need to follow but does not yet. TD-59/TD-60 (both new) are
real, scoped follow-up items, not silently left implicit.

## EGX-Genom Final Product Mission — Institutional Investment Operating System (2026-08-01)

The project owner redefined AGX from a research platform into an
institutional-grade Investment Operating System: research becomes an
internal capability, investment decisions are the product. Ten
non-negotiable constraints carried over unchanged from every prior
mission (free/legal data only, never fabricate, every recommendation
explainable and traceable, determinism preserved). New, mission-specific
requirements: a strict Product Law ("every screen answers exactly one
primary investment question"), an Information Hierarchy (Decision →
Investment Case → Evidence → Research), a 5-section CIO Desk landing
page, a 19-section Investment Case page, portfolio-aware thinking
everywhere, a 7-item navigation hierarchy with Research never the default
destination, and an explicit, mandatory product audit before completion.
Full implementation authorization: redesign page hierarchy/navigation,
merge/remove pages, refactor frontend/APIs, reuse the existing decision
engine — "do not preserve existing UI if it conflicts with the new
mission."

**Backend — 3 new dashboard artifacts, reusing existing engines rather
than computing anything new**:

- `dashboard.portfolio_summary.build_portfolio_summary()` (new
  `PortfolioSummaryReport`) wraps `investment_proof.portfolio_validation
  .PortfolioValidationEngine` (Mission 4) and adds a weighted-average
  `expected_return`. Answers "is my capital allocated correctly?" with
  cash/invested weight, sector exposure, concentration, liquidity
  violations, decision conflicts.
- `dashboard.monitoring.build_warnings()` (new `MonitoringWarningsReport`,
  `WarningCategory` — broken_thesis/macro_risk_increased/
  catalyst_expired/liquidity_deterioration/portfolio_concentration/
  review_required) scans the *whole* `KnowledgeStore`, not just current
  positions, since a broken thesis is exactly what makes a ticker drop
  out of the model portfolio in the first place
  (`KnowledgeWeightedHorizonModel.predict()` excludes `RETIRED`
  knowledge) — an initial version that only checked held tickers would
  have silently missed every retirement-driven warning.
- `dashboard.committee_summary.build_committee_summary()` (new
  `CommitteeSummaryReport`, `CommitteeOpinion`) wraps
  `investment_proof.committee_validation.CommitteeValidationEngine`
  (Mission 4) for the 6 return-contributing committees, adds Risk/
  Portfolio committees derived from `PortfolioValidationResult`, and a
  mechanical `chief_investment_officer` tally row — no new judgment logic,
  just aggregation of committees that already exist.

All three are wired into `production.pipeline.ProductionPipeline`'s
existing dashboard-artifact stage, `None`-safe on non-trading days
(matching `market_breadth.json`'s honest-absence convention), covered by
`dashboard.validate.validate_dashboard_artifacts()`, and exported to
`contracts/*.schema.json`. 7 new tests
(`test_cio_desk_artifacts.py`). 840 backend tests pass (up from 833);
`ruff check` clean.

**API layer**: `GET /portfolio-summary`, `GET /warnings`,
`GET /committee-summary` (same `readJsonOrDefault(path, null)` passthrough
pattern as every existing route — no new business logic in `api/`).
Removed one confirmed-dead duplicate route
(`GET /ticker-data-gap-report`, superseded by the already-wired
`/ticker-data-gaps`, never called by any page, never tested) rather than
carry it forward unaudited. 27 `api` tests pass (3 new); clean build.

**Frontend — full navigation and page-hierarchy redesign**, exercising
the mission's explicit authorization to remove/merge/redesign rather than
preserve the prior IA:

| New page | Route | Primary question | Built from |
|---|---|---|---|
| `CIODesk` | `/` | What should I do today? | Reused Market Regime banner (from the old AI Briefing) + live `POST /decisions` (position-aware) or model-portfolio fallback (position-unaware) + the 3 new artifacts above |
| `Portfolio` | `/portfolio` | Is my capital allocated correctly? | Holdings editor (new `usePortfolioPositions` localStorage hook) + the full decision table/detail panel reused from the old Decision Center |
| `InvestmentCases` | `/cases` | Which companies are candidates? | Reused from the old Opportunity Center's ranked list, minus the tables now living on Research |
| `InvestmentCaseDetail` | `/cases/:ticker` | Why should I own this company? | The mission's 19 named sections; reused from the old Company Research Workspace, extended with 2 previously-dead artifact calls (`getDecisionHistory` — implemented since an earlier mission, never called by any page until now) |
| `Monitoring` | `/monitoring` | What changed since my last decision? | New filterable warnings feed + reused "Since the Last Run"/knowledge-change feed from the old AI Briefing + `getDecisionHistory` again (universe-wide) |
| `MarketIntelligence` | `/market` | What is the investment environment? | Unchanged |
| `ResearchCenter` | `/research` | (internal capability, not a decision screen) | Extended in place with Decision Readiness/Data Coverage (absorbed from Opportunity Center) + links to Knowledge Graph/Source Intelligence |
| `Settings` | `/settings` | (operational status, not a decision screen) | Merges the old Mission Control + System Administration into one two-group page, including a single unified Execution History table replacing two redundant ones |

`KnowledgeGraphPage`/`SourceIntelligence` are unchanged but demoted off
the top-level nav (reachable only via a "More Research Tools" card on
Research) — real capabilities, but neither answers a daily-decision
question on its own.

**Deleted outright** (not kept as parallel dead code):
`AIBriefing.tsx`, `DecisionCenter.tsx`, `OpportunityCenter.tsx`,
`CompanyWorkspace.tsx`, `MissionControlPage.tsx`,
`SystemAdministration.tsx` (all + their `.module.css`), and the
already-dead `ComingSoon.tsx` (confirmed unreferenced both before and
after this mission). i18n: 6 old namespaces deleted, 5 new ones added
(`cioDesk`, `portfolio`, `investmentCases`, `monitoring`, `settings`,
bilingual EN/AR), `common.json`'s `nav`/`enums`/`table` blocks extended.
`App.tsx`/`Sidebar.tsx`/`TopBar.tsx` fully rewired to the new routes.

**Mandatory Product Audit** (per the mission's explicit instruction —
every screen/widget/nav item/API endpoint/report, asking "does this
improve investment decisions?"):

- *Screens*: every one of the 9 reachable pages maps to exactly one
  primary question (table above) — none answers more than one, none was
  found to answer zero. The audit's main finding was negative-space: the
  old 9-section IA had **two pages that existed only to display data
  without driving a decision** (Mission Control, System Administration) —
  both merged into one Settings page rather than kept as two nav slots,
  since neither individually justified top-level placement once measured
  against the Product Law.
- *Widgets*: CIO Desk's 5 sections were built to the mission's exact spec
  (no 6th section was added; a "recent knowledge" feed that existed on
  the old AI Briefing was deliberately dropped from CIO Desk and now
  lives only on Monitoring/Research, since "what changed" and "what
  should I do" are different questions the Product Law says shouldn't
  share a screen). The old AI Briefing's giant per-ticker/per-horizon
  abstain table (101 rows × 3 horizons, mostly "abstain") was removed
  entirely rather than migrated anywhere — it never drove a decision, it
  only demonstrated the platform's honesty about not having enough real
  data yet, which the CIO Desk's "Today's Actions" empty/fallback states
  already communicate more directly.
- *Nav items*: 7 top-level (down from 9); Knowledge Graph and Source
  Intelligence demoted to reachable-not-top-level (see table above) —
  the only two demotions, since every other former top-level page maps
  cleanly onto one of the 7.
- *API endpoints*: 3 added (all decision-relevant: portfolio state,
  warnings, committee agreement), 1 confirmed-dead duplicate removed
  (`GET /ticker-data-gap-report`). Every other existing route was
  reviewed and still backs a real page.
- *Reports/artifacts*: the 3 new artifacts each back a CIO Desk/Monitoring
  section directly. The audit surfaced one gap worth naming rather than
  silently accepting: `getRuntimeStatus()`/`getSourceTruth()`/
  `getEndpointCandidates()` (three real, already-implemented provider
  methods) are called by zero pages even after the redesign — recorded as
  **TD-61** rather than force-built into a screen that would fail the
  "does this improve a decision" test on its own, or silently dropped.

**Verified live** (real running `api`+`web` dev servers against a
hand-assembled, real-service-computed demo dataset — headless Chromium via
Playwright, both English and Arabic/RTL): Market Regime, Today's Actions
in both the model-portfolio and live personalized-decision paths,
Portfolio Summary, Warnings, Investment Committee Summary, the full
Portfolio holdings-entry -> live-decision -> detail-panel flow, the full
19-section Investment Case detail page, Monitoring's filterable feed, the
merged Research and Settings hubs, Market, Knowledge Graph, Source
Intelligence. One real RTL CSS bug found and fixed during this
verification: `.thesisCell`/`.riskCell` in `CIODesk.module.css` were
`<span>` (inline) elements with `max-width`/no width constraint at all —
CSS `max-width` has no effect on `display: inline` elements, so their
unwrapped English sentences forced the Arabic-mode table's auto-layout to
size those columns to full content width, overflowing the page. Fixed by
making both `display: block` with an explicit `width` +
`overflow: hidden` + `text-overflow: ellipsis`; re-verified via a real
`boundingBox()`/`scrollWidth` check that the page-level horizontal
overflow is gone in both directions.

47 `web` tests pass (`App.test.tsx` fully rewritten: new 7-label sidebar
check, new CIO Desk describe block, routes updated to the new paths, the
old giant abstain-table test block removed since that content is
intentionally gone). `npx tsc --noEmit` clean; `npm run build -w web`
clean.

**Acceptance criteria** (verified against the mission's own 10-item
list): a user can determine today's actions within 30 seconds (CIO
Desk's Today's Actions is the first content section after the regime
banner); every recommendation includes decision/allocation/confidence/
thesis/evidence/risks/monitoring (both `PositionAwareDecision` and the
`InvestmentCaseDetail` 19-section page carry all 12 fields, unchanged
from the earlier decision-object-completeness mission); every
recommendation links to a complete Investment Case (`/cases/:ticker`);
research is never the first destination (`/` is CIO Desk, Research sits
6th in the nav); every screen has exactly one primary purpose (audit
above); no page exists solely to display data without contributing to a
decision (Mission Control/System Administration merged, the abstain table
removed); existing decision engine capabilities reused, not duplicated
(`DecisionService`, `PortfolioConstructor`,
`investment_proof.portfolio_validation`/`committee_validation` all
composed, none reimplemented); existing tests remain green (840 backend /
27 `api` / 47 `web`); documentation updated to match (this section,
`docs/ARCHITECTURE.md`, `CLAUDE.md`, `CHANGELOG.md`, `NEXT_MISSIONS.md`).

**Not done, named as next**: `InvestmentProofDashboard` (still CLI-only,
unchanged from the mission above); TD-61 (three unused provider methods,
named rather than force-fit into a screen); TD-59/TD-60's own
next-steps (unchanged).

## Capital Allocation Intelligence (2026-08-01)

The project owner redefined the platform again: no longer a research
system, no longer only a decision system -- a capital allocation system.
The controlling instruction reframed the primary question from "is this
stock good?" to "is this the best use of capital available today?" and
mandated: capital as the primary input (every recommendation is a
proposal *requesting* capital), a global opportunity ranking (never score
a ticker in isolation -- every opportunity competes against every other
opportunity, existing holdings, and cash), a new Opportunity Cost Engine,
a Capital Deployment Queue replacing isolated recommendations, Capital
Recycling (every released pound gets an explicit destination), relative
decision-making (never output BUY without "better than what?", never
SELL without "replace with what?"), 7 new CIO Desk sections, and an
explicit prohibition on local (per-stock) optimization in favor of global
portfolio optimization. Explicit instruction to reuse `DecisionService`/
`PortfolioConstructor`/`investment_proof`, never duplicate logic or build
a parallel architecture, and to perform a mandatory final review before
declaring completion.

**Grounding, not guessing**: `DecisionService.decide_portfolio()`
(Decision-Centric Redesign mission) already evaluated the *entire*
INVESTMENT-horizon universe jointly -- every ticker with a `Recommendation`
unioned with every currently-held ticker, normalized against one shared
`total_positive_score` budget, hard-capped by `max_position_weight`/
`max_position_pct`. `MetaDecisionEngine`'s own `Recommendation.explanation
.why_not_others` already stated "comparison against other stocks happens
at the market-wide ranking stage" -- naming exactly where this mission's
work belongs. The gap was never the underlying competition (it already
existed); it was that the competition was implicit, invisible, and had no
opportunity-cost or recycling narrative attached to it.

**Delivered**:

- `PositionAwareDecision` (`decision_service/service.py`) gained 3
  additive fields -- `opportunity_score`, `expected_return`,
  `expected_risk` -- exposing the exact score/return/risk
  `decide_portfolio()` already computed internally as first-class,
  machine-readable numbers instead of only prose. No new scoring logic;
  every downstream consumer (including the new engine below) reads these
  rather than re-deriving the eligibility/scoring rule.
- New `capital_allocation/` package (`CapitalAllocationEngine`,
  `models.py`) -- a read-only ranking/opportunity-cost/recycling layer
  strictly *on top of* `decide_portfolio()`'s output:
  - `_rank()`: every decision (funded, rejected, held, abstained) gets a
    `RankedOpportunity` with a global rank 1..N by `opportunity_score` --
    the Global Opportunity Ranking, covering the *entire* universe
    `decide_portfolio()` evaluated, not only the winners.
  - `_match_capital_flows()`: a deterministic bipartite matching --
    demanders (BUY/INCREASE, ranked best-first) draw from idle cash
    first, then from suppliers (REDUCE/EXIT, ranked *weakest*-first --
    the least attractive holding is displaced before a stronger one ever
    would be). Idle cash is always drawn before any holding is touched,
    so a holding is only ever named as a capital source when idle cash
    genuinely wasn't enough -- the engine never fabricates a "should this
    replace another investment" conflict where none exists. Every unit of
    capital is a `CapitalFlow` (from/to ticker or cash, amount) -- one
    ledger backing the Capital Deployment Queue's `capital_sources`,
    Capital Released Today's `destinations`, and the Capital Recycling
    list, so there is no second, divergent bookkeeping.
  - Real bug caught by this mission's own tests, fixed before shipping:
    `decide_portfolio()` deliberately labels an abstained held ticker
    `hold` (never `exit`, so an evidence *gap* is never read as a sell
    signal) but still reports `target_weight=0.0` for it (no fresh
    evidence to score). The engine's first draft read that raw 0.0 as a
    real capital release, fabricating a "sell to fund something else"
    movement nothing actually recommends. Fixed with `_effective_target()`
    (`current_weight` for an abstained decision, the real `target_weight`
    otherwise) -- caught by `test_cli_allocate_capital.py`'s own
    end-to-end run against real mock pipeline output, not just a unit
    fake.
  - `CapitalAllocationPlan`: `ranking`, `queue` (`CapitalQueueEntry` --
    priority, target allocation, capital delta, expected contribution,
    marginal benefit, marginal risk, capital sources, a human
    `required_action` sentence, and an `opportunity_cost_note` naming the
    best-ranked idea currently without capital -- the mission's "better
    than what?" answer, structurally, not just in prose),
    `capital_released_today`/`capital_recycled` (the "replace with what?"
    answer for every REDUCE/EXIT), `best_new_opportunities`,
    `highest_opportunity_cost` (real, evidence-backed ideas that received
    zero capital today because a higher-ranked idea claimed the budget),
    `allocation_changes` (every mover, one flat list), `cash_waiting`
    (idle cash before/after with an honest reason -- "no additional
    ticker currently clears a positive score" vs. "fully deployed").
  - 13 new tests (`test_capital_allocation.py`) covering ranking order,
    full-universe inclusion (not only funded tickers), cash-drawn-first
    behavior, weakest-holding-displaced-first behavior, the abstention
    fix specifically, opportunity-cost attribution, best-new-opportunities
    exclusion of top-ups, allocation-change sorting, cash-waiting
    accounting, and the empty-universe case.
- CLI: `agx allocate-capital --date ... [--positions positions.json]`
  (`cli.py`), composing `decide`'s own real evidence via a new shared
  helper (`build_position_aware_decisions()`, factored out of `decide`'s
  own command body so neither command re-derives the market-state/
  positions/publication-gate setup a second time) rather than
  reconstructing it. 2 new tests (`test_cli_allocate_capital.py`),
  including one that reproduces the abstention bug end-to-end against a
  real mock pipeline run.
- API: `POST /capital-allocation` (`routes/decisions.ts`), the exact same
  live-bridge shape as `POST /decisions` (shells out to the CLI, no
  business logic in TypeScript) -- factored `runCli()` helper shared by
  both routes rather than duplicating the shell-out/temp-positions-file/
  error-handling logic a second time. 4 new tests (`app.test.ts`).
- `contracts/capital_allocation_plan.schema.json` (+ `position_aware_
  decision.schema.json` regenerated for the 3 new fields), `api/src/
  types.ts`/`web/src/types.ts` mirrors kept in sync per the established
  convention.
- Frontend: `DashboardDataProvider.postCapitalAllocation()`
  (`ApiProvider` calls the live route; `StaticJsonProvider` always
  rejects with `LiveDecisionsUnavailableError`, same honest-unavailable
  posture as `postDecisions` -- there is nothing to rank or recycle
  without a real portfolio, so this can never be a static artifact).
  CIO Desk's former "Today's Actions" section is now "Capital
  Allocation," rendering the mission's 7 named sub-sections from a live
  `CapitalAllocationPlan` when holdings are entered (fetched in parallel
  with `postDecisions` via one `Promise.all`, sharing the same request);
  when no live plan exists, the deployment queue falls back to the
  existing decisions table (now explicitly labeled as a degraded view)
  and Best New Opportunities falls back to the model portfolio's own
  already-ranked positions, while the other 5 sub-sections honestly state
  they need real holdings rather than fabricating a competition. 6 tests
  added/updated (`App.test.tsx`'s "5 mandated sections" assertion text,
  a new live-rendering test exercising all 7 sub-sections with a
  realistic populated plan including the `required_action` sentence;
  `ApiProvider.test.ts`/`StaticJsonProvider.test.ts` mirror
  `postDecisions`'s existing coverage for the new method: 4 new `web`
  tests total (1 `App.test.tsx` live-rendering test, 2 `ApiProvider`, 1
  `StaticJsonProvider`), plus 1 existing `App.test.tsx` assertion updated
  for the renamed section.

**Live-verified** against real demo data (a seeded `KnowledgeStore` +
real mock-mode collected prices, the same environment prior missions used)
via headless Chromium, both English and Arabic/RTL: all 7 Capital
Allocation sub-sections render correctly with the platform's real,
honest current state -- an empty plan, since no real EGX vendor is
licensed and the publication gate correctly blocks every decision
(`docs/DECISION_SYSTEM_ACCEPTANCE.md`'s "research-only decisions display
zero position" requirement, unchanged). No page-level horizontal overflow
in either direction; no new console errors beyond the pre-existing benign
favicon 404. The *populated* rendering path (a real deployment queue with
sourced capital and an opportunity-cost note) is covered by
`test_capital_allocation.py`'s engine-level tests (proven-correct
matching algorithm against hand-built scenarios) and `App.test.tsx`'s new
live-rendering test (a realistic `CapitalAllocationPlan` fixture rendered
through the real component tree) -- fabricating a populated live screenshot
would have required bypassing the real publication gate with invented
"live EGX data" evidence, which this platform's own anti-fabrication
principle forbids even for a demo.

**Mandatory Final Review** (per the mission's explicit instruction):

- *Does every recommendation compete against every other opportunity?*
  Yes, structurally, not just in prose: `_rank()` assigns a global rank to
  every ticker `decide_portfolio()` evaluated (funded, rejected, held, or
  abstained) from the one shared `opportunity_score` field every ticker
  now carries. Nothing is scored or displayed in isolation --
  `RankedOpportunity.rank` is visible on every list (queue, best-new,
  highest-opportunity-cost).
- *Does every allocation have an explicit opportunity cost?* Yes: every
  `CapitalQueueEntry.opportunity_cost_note` names the specific best-ranked
  alternative currently without capital, or explicitly states none exists
  ("every ticker with a positive opportunity score is already funded").
  `highest_opportunity_cost` surfaces this system-wide, not just per-entry.
- *Is every capital movement justified?* Yes: `capital_sources`/
  `destinations` name the exact ticker (or "cash") behind every unit of
  capital, `required_action` states it as a sentence, and the abstention
  fix means no movement is ever attributed to an evidence gap that wasn't
  a real decision to sell.
- *Never output BUY without "better than what?", never SELL without
  "replace with what?"* Satisfied structurally by `opportunity_cost_note`
  (BUY/INCREASE) and `capital_released_today[].destinations`
  (REDUCE/EXIT) -- both are typed fields on the response, not just prose
  a UI could drop.
- *Capital as the primary input, never local optimization.* No new
  per-stock scoring was added anywhere in this mission -- `opportunity_
  score` is exactly `decide_portfolio()`'s own already-global,
  already-jointly-normalized score, read, never recomputed. CIO Desk's
  primary section is now named "Capital Allocation," not a stock list.
- *Reuse, not duplication.* `capital_allocation/` imports
  `decision_service.service.PositionAwareDecision`/`PositionAction`
  only -- zero re-implementation of `MetaDecisionEngine`'s scoring,
  `DecisionService`'s eligibility rules, or `PortfolioConstructor`'s
  weighting. The CLI shares one setup helper across `decide`/
  `allocate-capital`; the API shares one shell-out helper across
  `/decisions`/`/capital-allocation`.
- *Named, not silently left out*: the position-*unaware* path (CIO Desk
  with no holdings entered) deliberately does **not** get ranking/
  opportunity-cost/recycling treatment. This is an architectural
  consequence of the same rule `decision_service/` already lives by
  (CLAUDE.md: never wire a real-portfolio-dependent computation into an
  autonomous run) -- there is nothing to displace, release, or recycle
  without real capital and real holdings; a model portfolio has neither.
  The fallback view is honest (existing decisions table + a ranked
  preview from the model portfolio) rather than a fabricated competition.
  `Portfolio.tsx` (the dedicated holdings page) was not extended with
  capital-allocation UI in this pass -- CIO Desk was the mission's
  explicit target ("what should I do today"); see `NEXT_MISSIONS.md`.

855 backend tests pass (up from 840, 15 new); 31 `api` tests pass (up
from 27, 4 new); 51 `web` tests pass (up from 47, 4 new); `ruff check`/
`tsc --noEmit`/production builds all clean.

**Not done, named as next**: capital-allocation UI on `Portfolio.tsx`
itself (new TD-62); the position-unaware/model-portfolio path staying
deliberately un-ranked (architectural, not a gap -- named above); every
other already-open item (TD-59/TD-60/TD-61, confidence calibration,
walk-forward backtesting) is unchanged by this mission.

## EGX Investment Methodology (2026-08-01)

The project owner declared software implementation no longer the primary
mission and the platform architecture complete, and asked for the
investment methodology itself: a permanent constitution governing every
future decision, a situational playbook, exact minimum decision
standards, portfolio construction standards, and a complete operational
handbook detailed enough for another engineering team to rebuild the
investment process without reading the source. Explicit instruction: not
documentation in the descriptive sense — a governing doctrine; no code
changes unless the writing process revealed a real architectural
inconsistency requiring correction.

**Method**: every claim in the five new documents is grounded in a real,
already-implemented mechanism, read directly from source rather than
inferred or assumed, and cited by exact module and threshold. Read in
full for this mission: `decision_service/service.py`,
`meta/decision_engine.py`, `meta/publication_gate.py`, `meta/readiness.py`,
`meta/decision_ledger.py`, `decision_service/country_risk.py`,
`decision_service/liquidity_floor.py`, `portfolio/constructor.py`,
`capital_allocation/*.py`, `investment_proof/{categories,
committee_validation,calibration,thesis_survival,stability,
counterfactual,attribution,walk_forward}.py`, `learning/monitor.py`,
`valuation/engine.py`, `dashboard/monitoring.py`, `knowledge/lifecycle.py`,
`hypotheses/pipeline.py`, `market_memory/{regime,breadth}.py`,
`causal/reasoner.py`, `review/{board,reviewers}.py`,
`adversarial/attacks.py`, `horizons/knowledge_weighted.py`, `config.py`.
One real gap in the mission's own working understanding was caught and
corrected mid-write, not left in the delivered doctrine: the prediction
model's confidence aggregation was initially assumed to be a genuine
confidence-weighted mean; re-reading `horizons/knowledge_weighted.py`
directly showed `total_weight / len(relevant)` is mathematically the
plain arithmetic mean of confidences (the weight term cancels), and that
a separate, real, previously-undocumented mechanism exists alongside it —
active, corroborated events within 30 days apply a severity-weighted
multiplicative penalty to both `expected_risk` (inflating it) and
`confidence` (deflating it), capped at a combined 50%. Both documents
were corrected to state the real formula rather than the assumed one.
No code was changed — the mechanism was already correct; only the
mission's own prior understanding of it, mid-draft, was wrong.

**Delivered** (all under `docs/`, all cross-linked, all bound by the
Constitution's own amendment rule — a numbered `docs/
ARCHITECTURE_DECISIONS.md` entry required to ever contradict one):

- `INVESTMENT_CONSTITUTION.md` — 11 articles (Why Invest, Why Reject,
  When to Hold Cash/Increase/Reduce/Exit, How Capital Is Allocated, How
  Confidence Is Interpreted, How Evidence Is Evaluated, How Conflicting
  Evidence Is Handled, How Mistakes Are Reviewed) plus a preamble and an
  amendment clause. Every article traces to a real mechanism -- e.g. "Why
  Reject" enumerates every real trigger for `AVOID`/`WATCH`/`ABSTAIN`
  rather than asserting a philosophy disconnected from
  `MetaDecisionEngine`'s actual code.
- `INVESTMENT_PLAYBOOK.md` -- 12 market situations (bull/bear markets,
  interest-rate cycles, currency/inflation shocks, political risk,
  liquidity crises, strong/weak earnings, sector rotation, market
  panic/euphoria), each with Expected Behaviour/Decision Priorities/
  Capital Allocation Priorities/Risk Adjustments/Monitoring Priorities.
  Every entry explicitly separates **real, mechanically detected today**
  (Market Regime's trend/volatility axes, Country & Macro Risk severity,
  the liquidity floor, Market Breadth) from **doctrine awaiting a
  detector that doesn't exist yet** (interest-rate cycles, inflation
  shocks, sector rotation each name the real gap -- no dedicated
  collector/classifier exists -- rather than pretending automated
  detection where none exists).
- `DECISION_STANDARDS.md` -- the exact minimum bar for Buy/Increase/
  Hold/Reduce/Exit/No Action/Abstain, restating
  `DecisionService._resolve_action`'s real logic as an auditable
  standard, including the one subtlety most likely to be misread: there
  is no seventh `PositionAction` value called "abstain" -- it is a
  boolean modifier determining which of `hold`/`no_action` applies, and
  documented as such explicitly to prevent future confusion.
- `PORTFOLIO_STANDARDS.md` -- maximum concentration (Herfindahl 0.25,
  sector 0.40, and the real, confidence-scaled 1-5% per-position ceiling
  that actually binds on published decisions, distinct from the 25%
  structural maximum), diversification, liquidity, cash, position sizing,
  and capital recycling, each grounded in the exact real formula/
  constant.
- `INVESTMENT_HANDBOOK.md` -- a 13-chapter, rebuild-without-source-code
  operational walkthrough (data foundations through agents, the 8-gate
  pipeline plus 3 independent scrutiny layers, knowledge lifecycle and
  prediction, readiness/publication gates, position-aware decisions,
  capital allocation, portfolio construction, monitoring, continuous
  learning, institutional validation/proof), closing with a glossary of
  every real numeric constant this platform's decisions depend on.

**No code changed.** The writing process surfaced one real documentation
gap in the mission's own draft (the confidence-formula
misunderstanding above), corrected before delivery, and zero architectural
inconsistencies in the platform itself requiring a code fix -- the
existing decision/capital-allocation/validation architecture (across
every prior mission in this platform's history) was found, on direct
re-reading, to already implement exactly the discipline this doctrine
now states permanently. 855 backend / 31 `api` / 51 `web` tests remain
unaffected (no source touched); `ruff check` unaffected.

**Not done, named as next**: the playbook's three explicitly-named
detector gaps (interest-rate cycles, inflation shocks, sector rotation)
are real future engineering work, each already carrying its own honest
"doctrine, not yet a dedicated detector" label in
`INVESTMENT_PLAYBOOK.md` rather than a silent absence -- see
`NEXT_MISSIONS.md`.

## Zero-Cost Production Deployment + Shadow Fund (2026-08-01)

The project owner redefined the production deployment architecture mid-
session, superseding an in-progress exploration of a Render-hosted live
`api/` backend (to make `Portfolio.tsx`'s personalized-decision feature
work on the public GitHub Pages site): permanently free, GitHub Actions +
GitHub Pages only, explicitly no VPS/Render/Railway/Fly.io/always-on
backend/live decision generation/POST endpoints on the public deployment,
ever. Within that architecture, required a persistent, continuously-
managed virtual institutional portfolio -- the "Shadow Fund" -- as one of
nine required daily artifacts, explicitly defined as distinct from
`meta.decision_ledger.DecisionLedger` (why decisions were made) and
`investment_cases`/`investment_proof` (reasoning/validation): "DecisionLedger
becomes only one input to the Shadow Fund... the Shadow Fund is the owner
of portfolio state." An initial ambiguity (rename `DecisionLedger` vs.
build only a NAV curve vs. the full portfolio-state architecture
ultimately specified) was resolved via `AskUserQuestion`, then further
clarified by the project owner directly rather than guessed.

**Audited first, before building anything**: most of the mission's nine
required outputs (data collection, complete methodology, autonomous
investment decisions, CIO Desk/Investment Cases/Monitoring artifacts,
static-JSON-via-GitHub-Pages publishing) were already fully satisfied by
the existing `deploy-pages.yml` + `ProductionPipeline` architecture --
confirmed by reading the actual workflow and pipeline code, not assumed.
The static GitHub Pages build already issued zero network POST requests
before this mission (`StaticJsonProvider.postDecisions()`/
`postCapitalAllocation()` throw `LiveDecisionsUnavailableError`
synchronously, before any `fetch()` call reaches the network) -- the one
real gap was Investment Proof (`agx investment-proof`, CLI-only, already
named as "genuinely next" in `NEXT_MISSIONS.md` before this mission, not
newly discovered), left out of this pass's scope by the project owner's
own redirection toward the Shadow Fund specifically. The only genuinely
new capability required was the Shadow Fund itself.

**Delivered**: new `research/src/agx_research/shadow_fund/` package --
`models.py` (`ShadowFundPosition`/`ShadowFundClosedPosition`/
`ShadowFundTransaction`/`ShadowFundRiskMetrics`/
`ShadowFundAttributionEntry`/`ShadowFundNavPoint`/`ShadowFundSnapshot`/
`ShadowFundPublicState`/`ShadowFundHistory`), `engine.py`
(`advance()` -- the one state transition), `repository.py`
(`ShadowFundLedger`, a single continuously-versioned entity whose
`history()` doubles as the daily NAV time series, no separate unbounded
per-day store), `export.py` (`export_shadow_fund`/
`export_shadow_fund_history`, deriving the two dashboard artifacts from
the ledger). See AD-56 for the full architectural rationale, in
particular why autonomously driving `DecisionService.decide_portfolio()`
here is safe and correct (the fund's own, fully platform-controlled,
reproducible-from-inception state -- never a real investor's holdings)
despite `decision_service/__init__.py`'s standing "never wire
decision_service into a scheduled run" rule. Reuses rather than
duplicates: `DecisionService.decide_portfolio()` for every target weight
(no new decision engine), `capital_allocation.CapitalAllocationEngine.build()`
for the fund's own capital-deployment/recycling view,
`data.adjustments.compute_adjusted_closes()` for mark-to-market (never a
raw close), `meta.decision_ledger.DEFAULT_TRANSACTION_COST_BPS` for the
identical transaction-cost assumption (extracted to a shared constant
rather than duplicated). Wired into
`production.pipeline.ProductionPipeline._stage_dashboard_artifact_generator`
as a new step, reusing the same `gated_recommendations`/`country_risk`/
`illiquid_tickers`/`knowledge_store` inputs `decision_ledger` already
computes there; skips cleanly (matching every other stage's convention)
on a non-trading day.

Tracks, per the mission's exact field list: current holdings, cash,
target vs. realized weights, entry dates/prices, market value, unrealized/
realized P/L, closed and open positions, portfolio NAV, daily NAV history,
daily allocation/capital-deployment/capital-recycling/rebalancing history
(every buy/increase/reduce/exit is a `ShadowFundTransaction`; `hold`/
`no_action` never are, since nothing changed), benchmark history,
portfolio attribution (a real contribution-to-return decomposition --
daily weight x daily ticker return, compounded in NAV-currency terms and
carried forward as small, universe-bounded rolling state, not
recomputed by replaying the full NAV history each day), and risk metrics
(annualized volatility, max drawdown, a "Sharpe-like" ratio explicitly
not called Sharpe since no risk-free rate is fabricated, Herfindahl
concentration, largest position) -- all honestly gated by sample size
(`sample_status`), same posture as `DecisionPerformanceSummary`. An
abstained held ticker's `target_weight=0.0` is never treated as a real
exit signal (mirrors `capital_allocation`'s existing exclusion rule
exactly) -- caught and fixed by the mission's own tests before shipping
(see below). A declared `REBALANCE_THRESHOLD_PCT = 0.01` avoids
manufacturing daily transaction noise out of `decide_portfolio`'s
continuous score wobble; `INCEPTION_NAV = 100.0` is an explicit notional
NAV-per-unit index convention, not a fabricated real capital figure.

**End-to-end wiring**: two new dashboard artifacts (`shadow_fund.json` --
current state, `shadow_fund_history.json` -- NAV series + all-time
transaction log, growth bounded by real trading activity rather than
elapsed-time x universe-size, the specific axis that made
`provenance_index.json` unbounded per TD-63); new
`dashboard.validate._validate_optional_shadow_fund`/
`_validate_optional_shadow_fund_history` (the same CI gate every other
optional artifact gets); new JSON Schema contracts
(`contracts/shadow_fund.schema.json`/`shadow_fund_history.schema.json`,
generated the same way as every other resource); new `agx shadow-fund`
read-only CLI command; new `GET /shadow-fund`/`GET /shadow-fund-history`
API routes (`api/src/artifactsStore.ts`/`routes/dashboard.ts`); full
`DashboardDataProvider` wiring (`getShadowFund()`/`getShadowFundHistory()`
on both `StaticJsonProvider` and `ApiProvider`, hand-maintained TS mirrors
in both `api/src/types.ts` and `web/src/types.ts`); a new Shadow Fund
section on the Monitoring page (NAV/cumulative-return/benchmark-return/
excess-return/cash-allocation stat tiles, volatility/max-drawdown/
Sharpe-like risk tiles with an honest "insufficient sample" state, an
open-positions table, a recent-transactions table), bilingual EN/AR i18n
including a new shared `table.weight` key.

**Two real bugs found and fixed by the mission's own tests before
shipping, neither assumed**: (1) a unit-convention bug -- every `_pct`
field was initially pre-multiplied by 100 (percent-scale), inconsistent
with every other `_pct`-suffixed field in this codebase (e.g.
`MAX_PRICE_ABOVE_FAIR_VALUE_PCT = 0.20`, a fraction) and with the shared
`formatPercent()`/`formatSignedPercent()` frontend formatters, which
multiply by 100 themselves for display -- caught before any web wiring
consumed the values, fixed by removing every `* 100.0`/`/ 100.0` in
`engine.py`. (2) a real correctness bug -- an abstained held ticker (no
current INVESTMENT-horizon evidence) was initially liquidated by the
rebalance loop because its `target_weight=0.0` looked like a genuine
target, contradicting `capital_allocation`'s own documented rule that an
abstained ticker's zero target is an evidence gap, never a real sell
signal; a new `test_abstained_held_ticker_is_preserved_not_liquidated`
test caught it, fixed with an explicit `abstained_held` guard that
carries the position forward unchanged instead.

**Verified live, not just unit-tested**: ran the real CLI end to end
(`agx run --mode mock` then `agx shadow-fund`) and confirmed a real,
correctly-shaped `shadow_fund.json` (100% cash, NAV 100.0, honest
`insufficient_sample` risk state -- correct given zero promotions in a
single-day mock run). Built the production web bundle, served it, and
drove it with a real headless Chromium session (not assumed): the
Monitoring page's Shadow Fund section renders correctly in both English
and Arabic/RTL (`الصندوق الظِلّي`), zero console errors, zero unexpected
404s, correct empty-state rendering for open positions/transactions with
no trading history yet. All verification scripts/artifacts used for this
check were removed afterward, not committed.

**Result**: 867 backend tests pass (up from 855, 12 new -- 9 in
`test_shadow_fund.py`, 3 in `test_shadow_fund_repository_export.py`);
`ruff check` clean; 33 `api` tests pass (up from 31, 2 new); 53 `web`
tests pass (up from 51, 2 new); `tsc -b`/production builds clean for both
`api` and `web`. See AD-56 (Shadow Fund architecture)/AD-57 (permanent
zero-cost deployment decision, closing System 18's cloud-provider
business-blocker for the *public* deployment specifically -- secrets
management, managed scheduling for `discover-sources`, and monitoring/
alerting remain open exactly as before) and TD-64 (benchmark tracking
stays flat pending a real EGX30 index feed, same root cause as TD-58;
declared-not-calibrated rebalance-threshold/risk-sample-size constants;
no NAV-history line chart yet on Monitoring, though the data contract
already exists and is already fetched).

**Not done, named as next**: `InvestmentProofDashboard` (CLI-only Capital
Trust Report, unchanged from every prior mission's note) remains the one
item from `NEXT_MISSIONS.md`'s prioritized list this mission's redirection
did not reach. A NAV-history line chart on Monitoring (TD-64) is a scoped,
low-risk follow-up. Extending `Portfolio.tsx` with the same Shadow-Fund-
style state view is not planned -- `Portfolio.tsx` remains the real
investor's own personalized, position-aware page (local/self-hosted `api/`
only, by design, per AD-57), structurally distinct from the Shadow Fund's
autonomous, platform-owned state.

## Investment Operating System review: full-universe evidence, DCF/EBITDA/EV/P-B (2026-08-02)

The project owner, acting as the fund's own investment manager, asked for
a full review: connect every research report to a real decision, fix or
remove disconnected/dead sources, add missing valuation metrics (DCF/
EBITDA/EV/P-B), and confirm the full ~100-ticker universe (EGX30+EGX70) is
in scope with no silently-missing data — explicitly free/legal sources
only, full authority to restructure. Framed as continuing whatever the
owner's own tooling ("Codex") had already done that session.

**Found already done, same day, on `main`** (commits `4799994`, `72cd2f8`,
`479ffc0`, none yet reflected in `CURRENT_MISSION.md`/`CHANGELOG.md`/this
file before this entry): two new `IMPLEMENTED` sources —
`egxpilot_fundamentals` (`EgxPilotFundamentalsCollector`, live-verified
against 100/101 AGX tickers per its own catalog note, derives
`shares_outstanding` from `market_cap`/`last_price` when the API omits it)
and `chief_egx_financials` (`ChiefFinancialsCollector`, discovers whichever
companies Chief Capital currently publishes and states `total_equity`/
`total_debt`/`ebitda`/`SharesOutstanding` directly) — close the exact gap
TD-55 named as blocking every ticker's fair value ("no combination of
currently-collectable fields reaches the 3-model floor without
`shares_outstanding`"). New `valuation.metrics.compute_valuation_metrics()`
/`ValuationMetrics` (`enterprise_value`, `ev_to_ebitda`, `price_to_book`,
`dcf_per_share`, market P/E/EPS/dividend-yield/beta, all `None` with a
named `unavailable_reasons` entry rather than fabricated when a reported
field is missing) is now exposed on `DecisionReadiness.valuation` and
rendered on the Investment Case page's Valuation section.
`meta.recommendation_service.RecommendationService` now generates a
valuation-only INVESTMENT `Prediction` (`multi_model_fair_value`) when no
knowledge-weighted model produces one, and blends a bounded market-P/E
earnings-yield "carry" into `expected_return`; `meta.readiness
.assess_decision_readiness` now allows `decision_allowed` from
`fair_value_available` alone, not only an active `KnowledgeObject` — so a
ticker with real reported fundamentals but no promoted research finding
can still reach a real Investment-horizon decision instead of silently
reporting nothing. A new full-universe opportunities table on `/cases`
(`InvestmentCases.tsx`) ranks every constituent by
`combined_expected_return` across all three horizons with a per-ticker
data-coverage/blocker column — the "read the market, rank every
opportunity top to bottom" view the mission asked for. `479ffc0`
separately fixed a real event-risk double-counting bug: market-wide news
headlines sharing one taxonomy subtype no longer each independently
penalize every stock's confidence (kept to one representative event per
subtype/channel, ticker-specific and market-wide channels weighted and
capped independently).

**This review's own contribution**: read every changed line across all
three commits, ran the full test/lint/build matrix (887 backend tests,
`ruff check`, 33 `api` tests, 53 `web` tests, both production builds,
`contracts/` regeneration — zero drift anywhere), and found two real,
previously-unnoticed defects. (1) `decision_service.macro_overlay
.assess_macro_overlay()` summed raw `importance_weight` floats into
`available_weight` with no rounding (`0.20+0.20+0.15+0.05 =
0.6000000000000001` in IEEE-754 arithmetic), breaking a `==` test
assertion and risking the same float noise reaching the exported
dashboard artifact. Fixed with `round(available_weight, 6)` at the point
of computation. (2) A hardcoded 2-page pagination cap in
`ChiefFinancialsCollector.fetch()` — see below for the full real-evidence
finding and fix. Both — see `docs/TECHNICAL_DEBT.md`'s updated TD-55.

Also audited every `DISABLED` source in the registry
(`egx_official`/`cbe`/`yahoo_finance`/`stockanalysis`/`mubasher`/
`investing_com`/`investing_news`/`imf`/`trading_economics`) against the
project owner's explicit "delete truly dead sources" instruction. None
were deleted: each carries a real, live-evidenced blocker (a network-level
anti-bot TCP reset, an explicit ToS automation prohibition, a robots.txt
disallow, or a free tier too limited to be a genuine source) rather than
being abandoned dead code, and three (`yahoo_finance`/`stockanalysis`/
`mubasher`) are already load-bearing fallback legs inside the real,
`IMPLEMENTED` `egx_price_composite` collector via their `integrated_via`
field — the standalone catalog entry exists only to document that role.
Deleting any of them would erase the audit trail this codebase's own
architecture explicitly protects (the `SourceCategory.ALTERNATIVE`
incident is the standing cautionary precedent), for zero decision-quality
gain.

**This sandbox's own network egress is fully blocked** (confirmed directly
against the agent proxy's `recentRelayFailures`: `connect_rejected`/403
for `stockanalysis.com`/`enterprise.press`/`api.stlouisfed.org`), the same
constraint essentially every prior mission in this log has hit — but
`deploy-pages.yml` (real GitHub Actions egress) had already run twice
against today's commits before this review started, so rather than assert
anything, this review fetched the real `production/state-latest` branch
(commit `c3aa5c9`, 2026-08-02 12:39 UTC) and ran `FairValueEngine`/
`compute_valuation_metrics()` directly against its real collected data.

Real, evidenced findings, not projections: `egxpilot_fundamentals` really
did fetch both endpoints for all 100 non-AIDC universe tickers (200 real
URLs present in the real `raw_documents.json`); `financial_statements/
*.csv` exists for all 100 universe tickers. But only **4 of 100** tickers
currently clear the 3-of-7-model fair-value floor: `cash_and_equivalents`
is missing for 100/100, `ebitda` for 98/100, `total_debt` for 99/100,
`total_equity` for 95/100. Tracing the root cause in the same real
`raw_documents.json`: `chief_egx_financials` only ever discovered **5**
real companies (ARCC/COMI/CIEB/EXPA/ETEL) because
`ChiefFinancialsCollector.fetch()` had a hardcoded 2-page index-pagination
cap — not a real site limit. **Fixed**: it now walks `page/3/`, `page/4/`,
... until a page adds no new company link or a fetch itself fails (bounded
at 20 pages as a runaway guard only), with a new regression test. Also
confirmed directly from the real CSV headers quoted in `raw_documents.json`
(e.g. ARCC: `Year,Assets,Liabilities,BookValue,Revenue,GrossProfit,
NetProfit,...,SharesOutstanding,...,P/E,P/BV,ClosingPrice,...`) that
`EBITDA`/`TotalDebt`/`Cash` genuinely have no column in Chief Capital's
real per-company export for the 5 companies seen so far, and bank CSVs
report `CustomerDeposits` rather than `TotalDebt` (correctly not treated
as equivalent) — a real data-availability gap this platform will not
fabricate around, not a code defect. See `docs/TECHNICAL_DEBT.md`'s
updated TD-55 for the complete real-evidence breakdown and next steps
(re-run this same check against the next `production/state-latest` once
the pagination fix has had a live run; a genuinely new free balance-sheet
source is the real fix if coverage stays low after that).

**Result**: 888 backend tests pass (1 bug fixed, 1 new regression test);
`ruff check` clean; 33 `api` tests pass; 53 `web` tests pass; both `npm run
build` clean; `contracts/` regeneration produced zero diff. See
`CURRENT_MISSION.md`'s matching entry for the full narrative.
