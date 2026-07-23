# Changelog

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
