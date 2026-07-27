# Changelog

## 0.25.0 — Real entity resolution for news-to-ticker matching

`RssNewsCollector`/`GdeltDocCollector` attributed news to a ticker via a
bare case-insensitive substring check (`ticker.lower() in
title.lower()`) — the exact "VLMR matches inside VLMRA" false-positive
risk named in the project owner's own completion plan. New module
`universe/entity_resolution.py` (`resolve_ticker_mentions`) fixes this:
ticker matching is now a real word/token match, and when a real company
display name is available, the full name is matched too via the same
conservative "every significant token present" discipline
`discover_company_directory_links()` already uses (shared
`significant_tokens()` helper, not a parallel implementation).

`production.pipeline.ProductionPipeline._ticker_companies()` threads real
company names from `research/data/universe/EGX30.csv`/`EGX70.csv` (the
already-reviewed, EGX-sourced 101-ticker seed with real English names and
ISINs) through `collector_plan.build_collector_plan`/`build_live_collector`
into both news collectors, so live/mock runs get genuine entity
resolution, not a ticker-only guess. Both collectors stay backward
compatible with a plain `ticker_hints: list[str]` for callers with no
company-name data (still upgraded from substring to exact-token
matching). No Arabic alias list yet — no verified Arabic-language EGX
source exists in this codebase (new debt, TD-36); inventing
transliterations would risk a wrong match, worse than a missed one.

8 new tests (600 total, up from 592); `ruff check` clean.

## 0.24.0 — NewsIntelligenceAgent: real news sentiment now produces findings

`agents.news_intelligence.NewsIntelligenceAgent` was an honest
`NotImplementedError` stub since System 08 was built, correctly deferred
because no real Egyptian news flow existed to research. That stopped being
true once `enterprise_press`/`fra_egypt` started producing real, dated
`NewsItem` records every live run (see `docs/PHASE_STATUS.md`'s "Egyptian
Live Data Sprint" phase) — this was the most directly-unblocked stub in
the codebase, named explicitly in `NEXT_MISSIONS.md`.

Implemented as a real, mechanical event-study-lite, mirroring
`CorporateEventsAgent` exactly: `agents.news_sentiment.classify_headline_sentiment()`
is a declared, headline-only keyword heuristic (positive/negative phrase
lists, negative checked first) — the same honesty tier as
`collectors.corporate_event_classifier`, never a fabricated NLP/sentiment
score (new debt, TD-35). For each ticker's sentiment-classified news item
with enough return history on both sides, the agent compares mean adjusted
return after the item to before it and proposes a MICRO-horizon
post-news-drift hypothesis when the shift clears a threshold. Wired into
`production.pipeline.ProductionPipeline`'s Research Pipeline stage
alongside the other five real agents.

Building this surfaced and fixed a real, previously-latent bug:
`collectors.service._append_news` was the only per-record materialization
writer that blindly appended instead of merging idempotently by natural
key (unlike prices/macro/corporate-events/index-constituents) — collecting
the same feed twice (e.g. a mock run followed by a replay run reading the
same archive) silently duplicated every news row. Harmless while nothing
consumed `news.csv` for hypothesis generation; caught immediately once
`NewsIntelligenceAgent` did, via `test_production_pipeline.py`'s existing
mock/replay-determinism test (5 vs. 7 hypotheses on the same input). Fixed
by merging on `(date, source, headline)`, matching every sibling writer.

24 new tests (592 total, up from 568); `ruff check` clean.

## 0.23.0 — Macro data now reaches the decision engine in live runs

A live production run's `investment_cases.json` showed all 62 published
recommendations at MICRO horizon only, and the Macro Dashboard showed all
23 `LIVE_MACRO_SERIES_IDS` (FRED/World Bank/UN SDG) with zero observations.
Root cause: `_stage_market_memory` used one `lookback_days=30` window for
prices, news, corporate events, *and* macro series — but World Bank/UN
SDG report annually (often with a 1-2 year publication lag) and CAPMAS
monthly, so an annual observation almost never falls inside the last 30
days. Since `DailyResearchPipeline` (the agents feeding the Meta Decision
Engine) reconstructs from this exact same snapshot, `MacroAgent` — the
only agent that turns macro data into SWING-horizon knowledge — had
nothing to correlate against in any live run.

`data.snapshot.build_snapshot()` now takes an independent
`macro_lookback_days` (default: `lookback_days`, so mock-mode callers are
unaffected); `DatasetSnapshot` gained the field so the window actually used
is explainable, not just assumed. `MarketMemory` and `ProductionPipeline`
thread it through; LIVE mode uses a new `LIVE_MACRO_LOOKBACK_DAYS = 900`
constant. Also closed a separate, independent gap: `LIVE_CAPMAS_INDICATORS`'
local ids were never added to `LIVE_MACRO_SERIES_IDS` at all, so CAPMAS
data was structurally excluded regardless of window size.

This does not create SWING/INVESTMENT recommendations by itself — it
removes the specific reason `MacroAgent` was structurally starved of data.
INVESTMENT horizon still has no agent implemented at all
(`FinancialPerformanceAgent` remains an honest `NotImplementedError`,
blocked on a fundamentals data source).

`contracts/market_state.schema.json` regenerated; `api/src/types.ts` and
`web/src/types.ts` updated to match. 4 new/extended backend tests; 584
backend tests pass.

## 0.22.0 — TargetOrganization entries for 14 previously-untargeted sources

The first real, live `agx discover-planned-report` run (2026-07-27, manual
`workflow_dispatch`) reported 20 catalogued `PLANNED` sources as
`not_targeted`. Of those, 14 have a single, unambiguous, publicly-known
organization domain (the same category of public knowledge already used
for every existing target — Reuters is reuters.com, CBE is cbe.org.eg —
independently re-verified for reachability before anything is trusted,
never asserted): IMF, OECD, Egypt's Ministry of Finance, Egypt's Open
Data portal, the Suez Canal Authority, Investing.com, TradingView,
Google Trends, the Wikimedia Foundation, arXiv, SSRN, NBER, Google
Scholar, ResearchGate.

The remaining 6 (`github_releases`, `company_social_official`,
`public_telegram`, `patents`, `hiring_signals`, plus `company_ir`'s own
per-constituent marker) stay untargeted on purpose: each names more than
one candidate organization or is inherently per-company/per-channel
(which of EPO vs. WIPO, which Telegram channel, which company's own
career page) — picking one for the catalog would be exactly the kind of
guess this program's own rules forbid.

Reduces the report's `not_targeted` count from 20 to 5 (`company_ir`'s
marker is separately, correctly excluded). 568 backend tests pass; `ruff
check` clean.

## 0.21.0 — Surface already-computed data the dashboard was hiding

The project owner reviewed the live Mission Control and Source
Intelligence pages and found real, already-computed backend data with no
frontend path to it at all.

- **Mission Control's Collectors table**: added a "Breakdown" column
  (`collector_status.json`'s per-record-type counts -- price bars, macro
  observations, news, corporate events, index constituents, financial
  statement line items -- previously collapsed into one summed "Yield"
  number), a "Withheld" column (quality-rejected batches, previously
  shown nowhere), and a "Reputation" column (the composite score,
  previously computed but never rendered).
- **Source Intelligence's Reputation Dimensions**: added the 3 of the
  charter's 9 dimensions that were computed (`compute_reputation()`) and
  typed but never rendered (`correction_rate`, `duplicate_rate`,
  `historical_usefulness`), plus a "Composite Reputation" stat tile for
  the overall score.
- **Weekly Discovery workflow wired into both pages** (previously zero
  frontend path at all): new `discovery_report.json`/`discovery_metrics.json`/
  `endpoint_candidates.json` types, `DashboardDataProvider` methods,
  `ArtifactsReader`/API routes, `StaticJsonProvider`/`ApiProvider`
  implementations. Mission Control gets a new "Weekly Discovery" section
  (metrics + per-source verification table); Source Intelligence's detail
  panel gets a "Discovery Evidence" block for the selected source, when
  available. `deploy-pages.yml` copies the three files from
  `research/data/discovery/` into the dashboard data directory if present
  (a plain file copy -- they're already final-shaped JSON committed by
  the Discovery workflow's PR, not reprocessed); an honest empty state
  renders until the first such PR merges.
- `npm run build`/`test` clean for both `api` and `web` workspaces.

## 0.20.0 — Weekly Discovery workflow

Closes "dozens of sources stay PLANNED, waiting on network egress" for
real: this dev sandbox has none, but the GitHub Actions production
deployment does, and nothing was scheduled to use it for discovery until
now.

- New `acquisition_intelligence/discovery_report.py`: `plan_discovery_targets`
  scopes the catalog to `PLANNED`/`CANDIDATE` sources with a real
  `TargetOrganization`, excluding per-constituent markers and provider
  legs already wired via `integrated_via`; `run_discovery_report` runs the
  existing `AcquisitionIntelligenceEngine.run_for_target` (unmodified —
  its own qualification-pipeline promotion already applies) with a
  TTL + input-fingerprint incremental cache; `build_discovery_metrics`
  aggregates counts. 9 new tests, all fake-backed.
- New CLI subcommand `discover-planned-report` writing
  `discovery_report.json`/`discovery_metrics.json`/`endpoint_candidates.json`.
- New `.github/workflows/discovery.yml`: weekly cron + `workflow_dispatch`,
  entirely separate from `deploy-pages.yml` (never blocks or slows the
  production deploy). Commits evidence only to a dedicated `discovery/latest`
  branch and opens/updates one PR against `main` — never a direct commit,
  never an automatic `SourceSpec.status` flip.
- New `research/data/discovery/README.md`; new
  `research/scripts/build_discovery_pr_summary.py` (PR body from the
  committed JSON, no second source of truth).
- Smoke-tested directly: a cold run against the real (egress-less) sandbox
  honestly reports `no_reachable_domain`/`not_targeted` for all 34
  in-scope sources (~82s); a second run within the TTL served every
  result from cache with zero new probes (~0.002s).
- Updated `docs/DATA_ACQUISITION.md` ("Discovery workflow" section),
  `docs/ROADMAP.md`, `docs/TECHNICAL_DEBT.md` (TD-23 partially closed).
- 568 backend tests pass; `ruff check` clean.

## 0.19.0 — No-API-key-sources policy: remove NEEDS_KEY entirely

The project owner made an explicit, permanent policy call: the platform
relies exclusively on genuinely free, no-registration sources, so waiting
on a `NEEDS_KEY` credential serves no goal — if a capability's only real
solution is a keyed API, drop it rather than leave it catalogued and idle.

- Removed the four `NEEDS_KEY` seed catalog entries (`fmp`,
  `alphavantage`, `polygon`, `tiingo`) from `sources/catalog.py`.
- Deleted `AlphaVantageCollector`/`FmpCollector` and their tests — dead
  code once their only catalog entries were removed.
- Dropped their ids from `acquisition_intelligence/capability.py`'s
  `CAPABILITY_STRATEGIES` pools (`PRICE_DATA`, `FINANCIAL_STATEMENTS`).
- Updated `test_capability_engine.py`'s synthetic fallback tests to use a
  still-catalogued id instead of the removed `fmp` placeholder (those
  tests exercise the generic ranking/fallback engine, not FMP itself).
- Registry is now 51 sources (14 IMPLEMENTED / 37 PLANNED / 0 NEEDS_KEY /
  0 TOS_REVIEW). `SourceStatus.NEEDS_KEY` stays in the enum as a
  structural classification — no seed source uses it, and any future
  source proposal needing a credential should be rejected the same way.
- Updated `docs/DATA_ACQUISITION.md`, `docs/ARCHITECTURE.md`,
  `docs/ROADMAP.md`, `docs/TECHNICAL_DEBT.md` (TD-21), and
  `docs/ACQUISITION_STRATEGY.md` (an inline note over the now-historical
  FMP/AlphaVantage analysis, preserving the original text).
- 559 backend tests pass; `ruff check` clean.

## 0.18.0 — Provider-leg health/reputation measured directly

The project owner flagged, from a review of the live source dashboards,
that a source integrated as a provider leg inside a composite collector
(`yahoo_finance`/`stockanalysis`/`mubasher` inside
`EgxCompositePriceCollector`, via `SourceSpec.integrated_via`) could show
`health_status: unknown`/`data_quality_score: null` in `source_registry.json`
even while actively serving real traffic through the composite — because
`CollectionService` only ever recorded metrics/health against the parent
collector's own id, never against the provider id a document was actually
attributed to (`Collector.provider_for_document`). The previous session's
`export_collector_status` fix addressed this for the dashboard's derived
per-run status table only (COLLECTED/STANDBY rows), by borrowing the
parent composite's `health_status` as a stand-in — the registry's own
`SourceSpec.health_status`/`reputation_score`/`data_quality_score` for
each provider leg were untouched and any consumer reading the registry
directly still saw permanently `unknown`/`null` fields.

- `CollectionService._record_provider_outcome` (new): records
  `SourceMetrics`/`HealthStatus` against a provider leg's own registry id,
  using the same per-document quality assessment already computed for
  that document (each raw document is already attributable to exactly one
  provider) — called alongside the existing collector-level
  `_record_run_outcome` for every document a `provider_for_document`-aware
  collector produces, on both the success and parser-failure paths.
- `production.artifacts.export_collector_status` no longer overwrites a
  provider-leg row's `health_status` with the parent composite's value —
  `_collector_status_row`'s own `registry.latest(provider_id)` lookup
  already returns the provider's own, now-measured status.
- New test: `test_provider_leg_health_and_reputation_are_measured_directly`
  (`test_collection_service.py`) — a good and a bad provider leg wired
  behind one stub composite collector each get their own, independently
  correct metrics/health, not a shared or borrowed value.
- 567 backend tests pass (1 new); `ruff check` clean. No new source,
  collector, or acquisition-architecture change — this is strictly a
  measurement-accuracy fix for sources already integrated, so it does not
  reopen the acquisition-architecture freeze (see `NEXT_MISSIONS.md`).

## 0.17.0 — Ticker Data Gap Report

- `meta.readiness.build_ticker_data_gap_report` decomposes
  `assess_decision_readiness`'s per-ticker counts into five named data
  layers (Financials/Disclosures/News/Macro/Knowledge), each with an
  explicit completeness percentage — a pure re-derivation of the existing
  readiness gates, never a second set of thresholds.
- New `ticker_data_gap_report.json` dashboard artifact
  (`production.artifacts.export_ticker_data_gap_report`), wired into
  `ProductionPipeline._stage_dashboard_artifact_generator` and validated
  in `dashboard/validate.py` for schema + universe-membership parity.
- Verified with a real mock-mode run against the full 101-ticker
  EGX30+EGX70 universe: 99 tickers `blocked`, 2 `degraded`, 0 Swing-ready,
  0 Investment-ready — the honest starting point, published as a
  filterable/sortable Artifact.
- 5 new tests (`test_ticker_data_gap_report.py`); 560 backend tests pass.
- New debt: TD-34 (no web/API wiring for the new artifact yet).

## 0.16.0 — Frontend: the remaining 8 sections (Opportunity Center through System Administration)
Completes the Production User Experience mission's 9-section rollout
(0.15.0 delivered the shell and AI Briefing). Every section composes only
from existing dashboard artifacts, per the mission's no-frontend-
calculation constraint.

- **Opportunity Center** — recommendations ranked by confidence,
  master/detail: ranked table + full `Explanation` breakdown (research/
  risk summary, supporting/contradicting evidence, historical similar
  cases, per-ticker upcoming catalysts) for the selected row.
- **Company Research Workspace** (`/company/:ticker`) — investment
  thesis, upcoming catalysts, knowledge timeline, research papers and
  gene lineage (cross-referenced via knowledge object ids), financial
  statements, corporate actions, news timeline. Market Regime & Macro
  Exposure is an honest "not yet available" gap.
- **Market Intelligence** — universe/sector composition, macro
  dashboard, market-wide corporate actions. Market Breadth & Liquidity
  and Market Regime & Historical Comparison are honest gaps — the
  frontend must not compute returns from raw price bars itself.
- **Research Center** — the 8-gate hypothesis pipeline (master/detail:
  ranked list + full stage history), covering "Experiments,"
  "Validation Queue," "Active Research," and "Discovery History" as
  views over the same `Hypothesis.stage_history`; Knowledge Objects;
  Scientific Papers. Review Board is an honest gap.
- **Knowledge Graph** — interactive, searchable, pan/zoomable rendering
  of `getKnowledgeGraph()`. New `web/src/lib/forceLayout.ts`: a small,
  dependency-free Fruchterman-Reingold-style force simulation, chosen
  over adding a graph-rendering library for a single page.
- **Mission Control** — mission status, pipeline health (stage-by-
  stage), knowledge/genome status, collectors, source health rollup,
  current blockers, execution history. Discovery Engine detail is an
  honest gap.
- **Source Intelligence** — every registered source, master/detail:
  health, lifecycle, reputation dimensions (availability, coverage,
  freshness, latency, accuracy, schema stability) as meters, joined
  across the source registry, source metrics, and the most recent
  collector run.
- **System Administration** — runtime/versions, configuration, replay
  capability, artifact inventory, per-stage performance (slowest
  first), execution history with error/session detail. Logs is an
  honest gap.
- Every page verified in a headless browser (dark theme) against real
  artifacts from a mock-mode `agx run` or a synthetic fixture where the
  mock pipeline currently produces no data (e.g. zero promoted
  knowledge/recommendations).
- 25 web tests total (was 19 after 0.15.0), all green. `npm run build`
  (`tsc -b && vite build`) passes clean.

## 0.15.0 — Frontend: design system, routed app shell, AI Briefing landing page
Start of the Production User Experience mission: the backend, research
engine, and production pipeline are declared complete by the project
owner; the remaining work is the complete frontend rebuild across 9
sections (AI Briefing, Opportunity Center, Company Research Workspace,
Market Intelligence, Research Center, Knowledge Graph, Mission Control,
Source Intelligence, System Administration).

- New institutional dark-theme-first design token system
  (`web/src/styles/tokens.css`) plus a shared primitive library: `Card`,
  `Badge`, `StatTile`, `Meter`, `DataTable`, `Section`,
  `EmptyState`/`LoadingState`/`ErrorState` — every page builds from these,
  no bespoke per-page styling.
- `AppShell`/`Sidebar`/`TopBar` (new): a persistent left-nav-across-9-
  sections layout with a live system-health status strip, replacing the
  single hardcoded knowledge table `App.tsx` previously rendered.
- `react-router-dom` v7.18 wired for all 9 sections; 8 render as honest
  "under construction" placeholders pending their own milestones.
- `useArtifact` hook (new): the one seam every page uses to pull data
  through `DashboardDataProvider` with consistent loading/error states —
  no page calls the provider directly.
- **AI Briefing** (landing page, fully built): System Health, Changes
  Since Yesterday (from `ExecutionReport`'s before/after counts), Market
  Summary, Top Opportunities, Biggest Risks, Most Important News,
  Upcoming Catalysts, Knowledge Changes, Scientific Discoveries, and
  Portfolio — composed entirely from existing dashboard artifacts with no
  frontend-side calculation, per the mission's explicit constraint.
- Fixed a real test-infra gap found while rewriting `App.test.tsx`:
  `@testing-library/react`'s `cleanup()` was never registered as a global
  `afterEach`, so previous tests' rendered DOM silently accumulated across
  tests in the same file — invisible before because no two tests' fixtures
  ever shared literal text. Fixed in `web/test/setup.ts`.
- 18 web tests green (was 5); `tsc --noEmit` and `vite build` both clean.

## 0.14.0 — Backend: dashboard artifacts for genes, papers, hypotheses, knowledge graph, financial statements, source reputation
Thin `model_dump(mode="json")` exports (no new calculations) for six
domain models that already existed but had no dashboard artifact:
`genes.json`, `papers.json`, `hypotheses.json`, `knowledge_graph.json`,
`financial_statements.json`, `source_metrics.json`. Wired into
`production/pipeline.py`'s dashboard-artifact stage and
`dashboard/validate.py` (optional — absent is not a failure).

- Fixed a real pre-existing bug while wiring the knowledge graph export:
  `ProductionPipeline._stage_research_pipeline` never passed a persisted
  `KnowledgeGraph` into `DailyResearchPipeline`, so graph edges were
  computed every run but silently discarded, never reaching
  `knowledge_graph.json`. Fixed by pointing it at `<data-dir>/graph_nodes.json`
  / `graph_edges.json`, matching how `hypothesis_repository`/
  `paper_repository`/`genome` are already wired.
- Extended both `StaticJsonProvider` and `ApiProvider` (`web/`/`api/`) with
  12 new `DashboardDataProvider` methods, and closed a pre-existing parity
  gap: the 6 "bonus" production-pipeline artifacts from the prior mission
  (`investment_cases`, `collector_status`, `runtime_status`,
  `dashboard_metrics`, `mission_status`, `execution_report`) were only ever
  wired into `StaticJsonProvider`, never into `api/`'s `ArtifactsReader` or
  routes — both providers now serve the full 18-method interface.
- 487 Python tests total, all green; `ruff` clean.

## 0.13.2 — Production-readiness audit for merge into main
Full audit before merging this branch into `main`: all tests green (477
Python / 14 API / 19 web), `ruff` clean, `contracts/` drift-free, no merge
conflicts with `main` (confirmed via `git merge-tree` — a clean
fast-forward, `main` hadn't moved), no TODO/FIXME/debug artifacts, no
unresolved conflict markers, no architecture-invariant violations found
(agents never write to `KnowledgeStore` directly; every real fetch goes
through `HttpFetcher`; no direct `EventRepository` writes bypass
`EventPlatform.register()`; every schema class defined exactly once).

One real duplication found and fixed: the same four-line header-matching
helper and the same single-URL-fetch-and-wrap pattern had been written
three times over (`RssNewsCollector`, plus this mission's
`IndexConstituentCollector` and `FinancialStatementCollector`).
Consolidated:
- `collectors/csv_columns.py` (new): `find_column()`, the shared
  header-text column matcher.
- `collectors/raw.py`: `fetch_single_text_document()` (new), the shared
  "one URL, one text document" `fetch()` body.

All three collectors now call the shared helpers instead of carrying
their own copies; behavior is unchanged (same tests, same assertions,
all still passing). No functional changes, no new features — a pure
deduplication refactor ahead of merge.

## 0.13.1 — Dashboard observability fix: report every collected record type
- `production/artifacts.py`'s `export_collector_status()` reported
  `price_bars_written`/`macro_observations_written`/`news_items_written`/
  `events_registered` but silently omitted `corporate_events_written`,
  `index_constituents_written`, and `financial_statement_line_items_written`
  — a real observability gap found while auditing for unblocked
  engineering work after Financial Statement Collection: `collector_status.json`
  was blind to genuine capability the platform already had (confirmed via
  a mock-mode `agx run`: `corporate_events_written` now correctly reports
  `2`, matching the real `COMI/EARNINGS` + `MFPC/DIVIDEND` rows already
  being written). Fixed by adding all three fields.
- 2 new tests (477 total); `ruff` clean.

## 0.13.0 — Financial Statement Collection
- `financials/` (new package): `FinancialStatementLineItem` — `{ticker,
  period_end_date, period_type, statement_type, line_item, value,
  currency}`; `STANDARD_LINE_ITEMS` (a small IFRS/GAAP-style vocabulary,
  reused where possible, never hard-enforced). `FinancialStatementProvider`
  (new, small ABC — mirrors `universe.UniverseProvider` rather than
  growing `data.provider.DataProvider`'s existing method set) +
  `CollectedFinancialStatementProvider` (reads collected CSV, empty when
  nothing's collected).
- `collectors/base.py`: `CollectionBatch` gained
  `financial_statement_line_items`. `collectors/service.py`:
  `CollectionService` materializes to `financial_statements/<TICKER>.csv`
  (merged by `period_end_date,statement_type,line_item`), provenance-traced,
  matching the existing writer pattern. `collectors/quality.py` counts the
  new record type.
- `collectors/financial_statements.py` (new): `FinancialStatementCollector`
  — a generic, header-matching CSV parser for a structured financial-
  statement export. Built and tested; not yet wireable into the live
  pipeline (`company_ir` stays `PLANNED` until its real endpoint is
  verified, `AD-24`).
- Deliberately **not** built: a generic PDF-based statement extractor —
  real filing layouts vary enough that a generic heuristic risks silently
  reading the wrong line item's value, the same reason
  `PdfDocumentCollector.parse()` stays abstract for every other PDF source.
- Confirms this closes a real, already-named gap:
  `agents.financial_performance.FinancialPerformanceAgent` has been an
  honest `NotImplementedError` stub since System 08, explicitly waiting on
  "a financial statement data source." The agent's own fundamental-factor
  logic remains separate, later work.
- 13 new tests (475 total, up from 462); `ruff` clean; `contracts/`
  unchanged. New technical debt: TD-31 (column detection, uncalibrated),
  TD-32 (PDF extraction, deliberately deferred). New risk: R-21 (guard
  against a future generic PDF-numeric-extraction attempt).

## 0.12.0 — Universe Engine + Corporate Disclosures
- `universe/constituent.py` (new): `IndexConstituent` — `{index, ticker,
  company_name, as_of_date}`, point-in-time correct (a date per row, not
  one overwritten snapshot).
- `collectors/base.py`: `CollectionBatch` gained `index_constituents` and
  `corporate_events`. `collectors/service.py`: `CollectionService` now
  materializes both (`universe/<INDEX>.csv` merged by `ticker,as_of_date`;
  `corporate_events.csv` merged by `ticker,date,event_type`), with full
  provenance tracing, matching the existing price/macro writer pattern.
  `collectors/quality.py`'s `produced`/`completeness_score` counts both.
- `universe/collected.py` (new): `CollectedUniverseProvider` (reads the
  collected CSV, latest snapshot at-or-before the query date, `{}` if
  nothing collected) + `FallbackUniverseProvider` (mirrors
  `FallbackDataProvider` exactly). Wired into `production.pipeline`'s
  `_stage_market_memory` and `cli.py`'s `discover-sources`.
- `collectors/index_constituents.py` (new): `IndexConstituentCollector` —
  a generic, header-text-matching CSV parser for a constituent-list
  export (ticker/name columns found by header content, not fixed order).
  Built and tested; not yet wireable into the live pipeline since
  `egx_official` stays `PLANNED` until its real endpoint is verified
  (`AD-24`) — same honest boundary as the AlphaVantage/FMP collectors.
- `collectors/corporate_event_classifier.py` (new): headline keyword
  heuristic (dividend/split/merger/acquisition/buyback/delisting/
  earnings/guidance/management-change), reusing `events.adapters.
  _CORPORATE_SUBTYPES`'s exact raw keys. `RssNewsCollector` gained a
  `classify_corporate_events` flag applying it per entry (exactly one
  ticker match required), populating `batch.corporate_events` alongside
  the always-produced `NewsItem` — closes TD-24.
- `production/collector_plan.py`: `rss_generic`'s mock/replay collector
  now runs with `classify_corporate_events=True`. Verified live: a
  mock-mode `agx run` now writes real `COMI/EARNINGS` and `MFPC/DIVIDEND`
  rows to `corporate_events.csv` from the existing mock RSS headlines.
- 31 new tests (462 total, up from 431); `ruff` clean; `contracts/`
  unchanged. New technical debt: TD-29 (classifier keyword list,
  uncalibrated), TD-30 (`IndexConstituentCollector`'s column detection,
  unverified against a real EGX export). TD-24 closed. New risk: R-20
  (classifier misclassification and the `events_from_corporate_events`
  confidence-modeling mismatch it exposes).

## 0.11.0 — Priority-Ordered Live Source Connection
- `acquisition_intelligence/target.py`: new `TargetOrganization.priority`
  field (and `company_ticker`) carrying the project owner's explicit
  business-value order — EGX official (1), EGX30/EGX70 company Investor
  Relations (2/3), CBE (4), FRA (5), CAPMAS (6), Enterprise (7), Mubasher
  (8), Zawya (9), Reuters (10), Trading Economics (11), anything else
  discovered (12, catch-all default). World Bank/IMF/FRED demoted to
  enrichment-only per the re-prioritization; every seeded target reassigned
  accordingly.
- `generate_company_ir_targets(companies)` (new): expands the prior
  `company_ir` per-constituent marker into one real `TargetOrganization`
  per EGX30 constituent — deliberately **no fabricated domain hints**;
  scales automatically to a real EGX30/EGX70 list the moment one exists,
  with zero code changes.
- `discovery/engine.py`: `discover_company_directory_links()` (new) —
  extracts a company's own homepage link from an already-fetched directory
  page via real anchor-text token matching against the company's name (not
  a guess), plus a `_PageLinkParser` extension to track anchor text.
  `AcquisitionIntelligenceEngine.run_catalog()` (new) processes targets in
  priority order and feeds any company hints discovered from an earlier
  target (e.g. EGX's own directory) into not-yet-run company IR targets.
- `cli.py discover-sources` now runs the full expanded catalog (named
  organizations + generated company IR targets) through `run_catalog`, in
  priority order, by default.
- Fixed a real pre-existing circular-import bug: `agx_research.discovery`
  failed to import if it was the first AGX module touched in a fresh
  process (`sources.qualification` imported `discovery.candidate.
  SourceCandidate` at module level while `discovery.candidate` imports
  `sources.spec`). Fixed with a `TYPE_CHECKING`-guarded import; regression-
  tested with a fresh-subprocess import test.
- Verified: the full 21-target priority-ordered catalog runs correctly
  end to end, in exact priority order, with an honest "no reachable
  domain" for every target (this sandbox still has no outbound network
  egress) — no crash, no fabrication.
- 14 new tests (427 Python tests total, up from 413); `ruff` clean;
  `contracts/` unchanged (no new pydantic model exposed to the API).
- New technical debt: TD-28 (company-directory-match heuristic
  uncalibrated against a real page). New risk: R-19 (guard against
  future fabrication of domain hints/constituent lists).
- Closed TD-16's remaining half: `HttpFetcher.fetch_bytes` now times each
  real request (excluding rate-limit/backoff sleeps); `CollectionService.
  run()` feeds the average into `SourceMetricsRepository.record_run()`.
  `reputation.py`'s `latency` dimension stays honestly `None` until a live
  collector runs, but the mechanism no longer needs building later. 4 new
  tests (431 Python tests total).

## 0.10.0 — First Production Execution Pipeline
- `agx_research.production` (new package): `ProductionPipeline` wires every
  stage the mission specifies, in order — Entry Point, Source Registry,
  Discovery Engine, Collector Selection, Collector Execution, Raw Archive,
  Canonical Transformation, Validation, Event Platform, Market Memory,
  Knowledge Base, Research Pipeline, Genome, Investment Case Generator,
  Dashboard Artifact Generator, Mission Control Update, Execution Report —
  by composing `CollectionService`, `DailyResearchPipeline`, `RuntimeEngine`,
  `RecommendationService`, `PortfolioConstructor`, `write_dashboard_artifacts`,
  and the Acquisition Intelligence Engine's continuity monitor. Nothing
  redesigned; this closed a real gap instead — `agx collect` wrote to
  `--data-dir` but `agx run` always read from a separate static
  `--mock-data` directory. They're connected now.
- `production/collector_plan.py`: the platform's *real* collectors
  (`StooqPriceCollector`, `FredCsvCollector`, `RssNewsCollector`,
  `WorldBankCollector`) run against a `MockFetcher` (execution mode
  `mock`, clearly-synthetic wire-format-correct content — the same
  numbers `research/data/mock/` uses, reformatted) or an
  `ArchiveReplayCollector` reading previously-archived documents
  (mode `replay`). `CollectionService.run()` is called identically either
  way — no live collector was built yet, per the mission's own instruction.
- `production/stages.py`+`report.py`: `StageResult`/`ExecutionReport` —
  every stage's status (`succeeded`/`partial`/`failed`/`skipped`),
  duration, detail, and error; per-stage failure isolation (a raised
  exception becomes a `FAILED` result, execution continues regardless).
- `production/mission_control.py`: `mission_status.json`, derived purely
  from `ExecutionReport` history (`PipelineExecutionRepository`) — pipeline
  status/version, last successful/failed pipeline, current execution mode,
  duration, artifacts produced, knowledge/genome updated.
- `production/artifacts.py`: `investment_cases.json` (the Investment Case
  Generator — composes the existing but previously-unwired
  `RecommendationService` + `PortfolioConstructor`), `collector_status.json`,
  `runtime_status.json`, `dashboard_metrics.json`.
- `collectors/fetcher.py`: `HttpFetcher.robots_status()` reused; no change
  needed there this phase beyond what Acquisition Intelligence already added.
- `cli.py`: `run` is now the single production entrypoint (`--mode mock`/
  `replay`, `--dashboard-out`); `build_engine()` (whose only caller this
  replaced) deleted along with its now-unused imports.
- `dashboard/validate.py`: extended to optionally validate the six new
  artifacts when present, without changing `export-dashboard`'s existing
  eight-artifact contract.
- `.github/workflows/deploy-pages.yml`: now calls the single `run` command
  instead of separate `run` + `export-dashboard` steps.
- 16 new integration tests (`test_production_pipeline.py`): full stage
  order, collected-data-reaches-research proof, replay reproduces the same
  research outcome, no duplicate archiving on replay, honest empty-replay
  behavior, deterministic execution, failure isolation (stage-level and
  per-collector), artifact generation + validation, Mission Control history
  tracking, CLI entrypoint. 413 Python tests green (up from 397); 33
  TypeScript tests unaffected; `ruff` clean; `contracts/` unchanged.

## 0.9.0 — Acquisition Intelligence Engine
- `acquisition_intelligence/` (new package): given only a `TargetOrganization`'s
  identity (name/category/country/public-brand domain hints — never a
  manually supplied URL), autonomously discovers how to legally acquire its
  data:
  - `domain_resolution.py`: `HeuristicDomainResolver` probes every hint and
    name-derived guess for actual reachability before trusting a domain.
  - `legality.py`: robots.txt (three-state, via new `HttpFetcher.robots_status`)
    + ToS red/green-flag keyword heuristics -> `ALLOWED`/`AMBIGUOUS`/`BLOCKED`;
    `HTML_SCRAPE` can never auto-clear to `ALLOWED`.
  - `stability.py`: URL-shape heuristics (canonical extension vs. session
    token/opaque id) + repeated-probe status-code consistency.
  - `historical.py`: Wayback Machine `available`/CDX API client + pure
    parsers, scored by archived-snapshot span.
  - `ranking.py`/`config_generation.py`: legality as a hard gate, composite
    ranking of the rest, auto-generated `SourceSpec` (collector suggested
    where unambiguous) that always stays `PLANNED` — never silently
    `IMPLEMENTED`.
  - `engine.py`: `AcquisitionIntelligenceEngine` orchestrates all of the
    above and begins qualification (records a reachability run, evaluates
    promotion) on success.
  - `continuity.py`: `AcquisitionContinuityMonitor` re-runs discovery,
    excluding the failed method, for any source whose health goes `DOWN`.
  - `live.py`: the one file wiring real network access for deployment;
    every other module is network-free and tested with fakes.
- `sources.catalog` seeded with 12 `TargetOrganization`s (EGX, Company IR,
  Reuters, Mubasher, Zawya, Enterprise, Asharq Business, CNBC Arabia, CBE,
  FRA, CAPMAS, Trading Economics), each linked to its existing `SourceSpec`
  catalog entry.
- `cli.py`: new `discover-sources` subcommand runs the engine (and
  continuity recovery) against the seed target catalog.
- `collectors/fetcher.py`: `HttpFetcher.robots_status()` — a three-state
  robots.txt check (allowed/disallowed/unreachable) distinct from the
  existing permissive-by-default `fetch_bytes` behavior.
- Verified directly (not assumed) that this development sandbox has no
  outbound network egress to arbitrary hosts (`curl`/`WebFetch` 403 on
  every target site attempted); a live `agx discover-sources` run
  correctly reports "no reachable domain" for all 12 named targets — the
  engine is complete and will perform real discovery the first time it
  runs somewhere with egress.
- 51 new Python tests (397 total, up from 346), all offline (fakes only);
  33 TypeScript tests unaffected; ruff clean.

## 0.8.0 — AGX Data Acquisition Platform
- `sources/`: `SourceSpec` gains three independent state axes —
  `lifecycle_state` (`LifecycleState`: Candidate/Quarantine/Evaluation/
  Trusted/Core), `health_status` (`HealthStatus`), `activation_status`
  (`ActivationStatus`) — plus `country`, `priority`, `reputation_score`.
  New `qualification.py` (evidence-gated promotion pipeline, one stage at a
  time, demoted on a DOWN health signal), `reputation.py` (`SourceMetrics`
  counters -> the charter's 9 reputation dimensions -> a composite score,
  finally wiring `SourceRegistry.record_measured_quality()`), `health.py`
  (`HealthMonitor`/`HealthAlert`: consecutive-failure/layout-change/schema-
  drift/staleness detection).
- `discovery/` (new package): `DiscoveryEngine` — RSS autodiscovery,
  PDF-repository scan, structured-dataset scan, sitemap scan, API-doc-link
  scan -> `SourceCandidate`. Pure function of already-fetched HTML/XML, no
  import of `SourceRegistry` — structurally cannot register or trust a
  source; `qualification.register_candidate` is the only bridge, always at
  Candidate/PLANNED with conservative priors.
- `collectors/archive.py` (new): `RawArchive`, a content-addressed,
  write-once binary blob store for PDF/Excel/image payloads that don't fit
  `RawDocument.content_text`; `RawDocument` gains `is_binary` and
  `build_binary_raw_document()`. `HttpFetcher` gains `fetch_bytes()`.
- `collectors/provenance_index.py` (new): `ProvenanceIndexRepository` — a
  per-value trace (source/collector/raw-document/hash/schema-version) for
  every materialized price bar and macro observation, closing the gap
  where only news items carried this forward. Wired automatically into
  `CollectionService`.
- `collectors/replay.py` + `archive_replay.py` (new): `ArchiveReplayCollector`
  (an ordinary `Collector` whose `fetch()` returns already-archived
  documents) + `HistoricalReplayEngine` — rebuild materialized data from
  the Raw Archive alone after a parser change, with no new fetch.
  `CollectionService.run()` is now idempotent about re-adding an
  already-stored `RawDocument`, and records `SourceMetrics`/`HealthMonitor`/
  registry health+reputation on every run (including parser exceptions,
  now caught and withheld rather than propagated).
- New generic collector-type frameworks: `PdfDocumentCollector` (pypdf-
  backed text extraction), `ExcelSeriesCollector` (openpyxl-backed,
  column-mapped macro series), `FilesystemCollector` (real, network-
  independent — ingests manually-placed files), `BrowserAutomationCollector`
  (honest `NotImplementedError` stub, no ToS-cleared target exists yet).
- New concrete collectors: `WorldBankCollector` (World Bank v2 API,
  IMPLEMENTED — Egypt macro indicators); `AlphaVantageCollector` and
  `FmpCollector` (code-complete and tested against each API's documented
  JSON shape, catalogued `NEEDS_KEY` — no fabricated/bypassed credentials).
- `contracts/source_spec.schema.json` regenerated; `api/src/types.ts` and
  `web/src/types.ts` updated to match the new `SourceSpec` fields.
- New dependencies: `pypdf`, `openpyxl` (both pure/near-pure-Python, no
  native extensions).
- 346 Python tests green (up from 273); TypeScript suite unchanged (33).

## 0.7.0 — Dual-provider dashboard architecture (static + API)
- `web/src/data/`: `DashboardDataProvider` interface with two
  implementations — `StaticJsonProvider` (reads JSON artifacts published
  alongside the static site) and `ApiProvider` (reads from a hosted
  `api/`). `web/src/data/factory.ts` selects one via `VITE_DATA_PROVIDER`
  (`web/.env.production` = static, `web/.env.development` = api); no
  component imports either implementation directly. `App` now takes an
  optional `provider` prop for testability.
- `research/src/agx_research/dashboard/`: `export_*()`/`write_dashboard_artifacts()`
  produce `knowledge.json`, `events.json`, `patterns.json`,
  `recommendations.json`, `market_state.json`, `runtime_metrics.json`,
  `system_status.json`, and `source_registry.json` — each a
  `model_dump(mode="json")` of an existing domain model, no duplicated
  schemas. `validate_dashboard_artifacts()` re-parses every file through
  its pydantic model before publishing, and hard-fails if `patterns.json`
  is ever non-empty (`HistoricalPatternsAgent` isn't implemented, so it
  must stay honestly empty). New CLI subcommands: `export-dashboard`,
  `validate-dashboard`.
- `contracts/`: `export_schemas.py` now emits schemas for `Event`,
  `Recommendation`, `MarketState`, `RunRecord`, `SourceSpec`, and the new
  `DashboardSystemStatus`, alongside `KnowledgeObject`; `api/src/types.ts`
  and `web/src/types.ts` extended to match.
- `api/`: new routes `/events`, `/patterns`, `/recommendations`,
  `/market-state`, `/runtime-metrics`, `/system-status`,
  `/source-registry` alongside the existing `/knowledge`. Events/runtime
  metrics flatten the same raw versioned-repository files `/knowledge`
  already does; the other five read the same generated snapshot files
  `StaticJsonProvider` reads, refreshed on a schedule in a real deployment
  (System 18 scheduling remains business-blocked).
- `cli.py`: events now persist to `data_dir/events.json` (previously
  in-memory only) via a shared `build_market_memory()` helper, so
  `export-dashboard` sees the same events any `run` produced.
- `.github/workflows/deploy-pages.yml`: now runs the real daily research
  pipeline against mock data (`agx run --date 2026-06-14`), generates and
  validates the dashboard artifacts into `web/public/data/`, then builds
  and publishes `web/`. Root-caused and fixed why the site was serving
  GitHub's default content: the repo's legacy branch-based Pages builder
  was still enabled alongside the Actions workflow and always won the
  race; `actions/configure-pages@v5` now fails the build loudly instead if
  that regresses.
- 17 new Python tests (273 total) and a new web test suite (19 tests,
  first `vitest`+`@testing-library/react`+`jsdom` setup for `web/`) plus 5
  new API tests (14 total) covering both providers, provider switching,
  App rendering with static artifacts, and "no `/api/*` calls happen in
  GitHub Pages mode."
- Docs synced: `MASTER_PROMPT.md` (new "Dashboard Data Architecture"
  section), `ARCHITECTURE.md`, `ROADMAP.md`, `TECHNICAL_DEBT.md`,
  `PHASE_STATUS.md`, `CLAUDE.md`.

## 0.6.1 — GitHub Pages deployment for the web dashboard
- `.github/workflows/deploy-pages.yml`: builds `web/` and publishes
  `web/dist` to GitHub Pages on push to `main` (paths-filtered to
  `web/**`), at `https://shadygad01.github.io/EGX-Genom/`.
- `web/vite.config.ts`: `base: "/EGX-Genom/"` for production builds only
  (dev server unaffected) so a GitHub Pages project site resolves assets
  correctly.
- Known limitation, documented in `docs/ARCHITECTURE.md`: GitHub Pages is
  static-only, so `api/`'s Fastify server isn't deployed alongside it —
  the dashboard renders but its knowledge fetch shows the existing "Error
  loading knowledge" state until `api/` is hosted somewhere reachable and
  `web/src/api.ts` is pointed at it.

## 0.6.0 — Production Data Acquisition Program (System 02 extension)
- `sources/`: `SourceSpec`/`SourceRegistry` — a 51-source declarative
  catalog spanning all 9 charter categories (Official, Company, Market
  Data, News, Arabic News, Macroeconomic, Global Markets, Alternative,
  Research), each with reliability/freshness priors, retry/rate-limit
  policy, license, conflict priority, and an honest status
  (IMPLEMENTED/PLANNED/NEEDS_KEY/TOS_REVIEW/DISABLED).
- `collectors/`: `RawDocument` provenance envelope (content-hash-derived
  id, append-only normalization/validation history); `HttpFetcher`
  enforcing robots.txt, per-source rate limits, and bounded exponential
  backoff in code, not just policy; `Collector` ABC that refuses to run
  against any non-IMPLEMENTED source; three real collectors — Stooq
  (EGX + global daily OHLCV), FRED (macro series), generic RSS/Atom
  (news, layout-tolerant); `collectors.quality.assess_quality()` computing
  the charter's 7 quality scores mechanically; `CollectionService`
  orchestrating fetch → parse → score → materialize-or-withhold → register
  (news candidates route through the existing `EventPlatform`, never a new
  write path).
- `data.mock_provider.LocalCsvDataProvider` — a clearer alias for
  `MockDataProvider` now that it also serves real collected data through
  the same CSV layout.
- CLI: new `collect` subcommand dispatching to the right collector by
  source id.
- `docs/DATA_ACQUISITION.md` — full design doc; `PHASE_STATUS`/`ROADMAP`/
  `TECHNICAL_DEBT` updated; 53 new tests (256 total), all offline against
  recorded-format fixtures (this environment has no outbound network
  egress; live fetching is validated only in deployment).

## 0.5.0 — Autonomous execution epoch: systems 04–18
- Market Memory: EGX trading calendar (fixed holidays as rules, movable as
  explicit placeholder table); canonical events wired into `MarketState`.
- Knowledge Graph: shortest-path and n-hop subgraph queries.
- Alpha Genome: multi-parent `merge()` alongside single-parent `mutate()`.
- Experiment Factory: claim statistic unified in `hypotheses/statistic.py`
  (pair→correlation, single→mean return); sensitivity analysis now real;
  only Monte Carlo remains a placeholder.
- Validation: `NaiveDirectionalBacktester` and
  `HistoricalWorstWindowStressTester` (first concrete gate implementations).
- Review Board: Economist (structural coherence) and PeerValidator
  (independent replication) reviewers real; findings carry proposed
  rationales for downstream judgment.
- Research OS: `DailyResearchPipeline` — the full 8-gate end-to-end chain
  with derived confidence, adversarial adjustment, genome/paper/graph
  output, and honest per-gate rejection.
- Scientist Framework: Macro, CorporateEvents, Liquidity,
  TechnicalStructure agents real (5 of 8); adversarial RandomCoincidence
  (seeded permutation test) and ParameterInstability real (6 of 9).
- Feature Discovery: momentum and volatility generators + definitions.
- Runtime Engine: deterministic date-range runner, per-day failure
  isolation, persistent run ledger, non-trading-day records.
- Prediction/Portfolio/Explainability/Learning v1: knowledge-weighted
  horizon models (no knowledge → no prediction), recommendation service,
  portfolio constructor with cash fallback, historical cases from real
  events, continuous-learning monitor with mechanical retirement.
- Infrastructure: integrity-checked backup/verify/restore, CLI
  (`run`/`status`/`backup`/`restore`), Dockerfile.
- Project management docs: ROADMAP, TECHNICAL_DEBT,
  ARCHITECTURE_DECISIONS, RISK_REGISTER, CHANGELOG; PHASE_STATUS rewritten.

## 0.4.0 — Event Platform production architecture (system 03)
- Fingerprint identity, taxonomy/ontology, entity resolution,
  dedup/conflict/lifecycle, `EventPlatform` sole write path, graph
  projection.

## 0.3.0 — MASTER_PROMPT charter adoption; Data Platform closure (02)
- Data quality validation, split/dividend adjustment (with a real caught
  bug: dividend factor from the last cum-dividend close), snapshot
  repository, fallback provider; PHASE_STATUS audit created.

## 0.2.0 — Epoch II: the scientific core
- Sessions/task graphs/artifacts, event layer, market memory, feature
  discovery, experiment factory, Alpha Genome, causal architecture,
  knowledge graph, paper generator, review board, adversarial scientist.

## 0.1.1 — Architectural audit and refactor
- Generic repositories, provenance chain, configurable gate pipeline,
  point-in-time snapshots, feature registry, contracts drift check.

## 0.1.0 — Foundation scaffold
- Python research engine skeleton, knowledge lifecycle, TS api/web
  viewers, CI.
