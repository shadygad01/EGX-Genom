# AGX — Alpha Genome (EGX Research Platform)

This file orients any Claude session working in this repository. It is not
the vision document itself — that lives in `docs/VISION.md` verbatim — nor
the operating charter, which is `MASTER_PROMPT.md` (role, non-negotiable
principles, and the strict 18-system build order). This file is the
practical guide to how the codebase is organized and what invariants to
protect when touching it. `docs/ARCHITECTURE.md` describes the current
design in more detail; `docs/ARCHITECTURE_AUDIT.md` (Epoch I) and
`docs/EPOCH_II_DESIGN.md`/`docs/EPOCH_II_REPORT.md` (Epoch II) explain *why*
it's shaped this way. `docs/PHASE_STATUS.md` is the living, must-be-updated
audit of where every one of `MASTER_PROMPT.md`'s 18 systems actually
stands — check it before starting new work: per the charter, a later
system's work should not start while an earlier one still has closeable
gaps.

## What this repository is

AGX is an autonomous quantitative research platform scoped exclusively to the
Egyptian Stock Exchange (EGX), with EGX30 as the primary focus. It is not a
signal generator or a recommendation bot — it is scaffolding for a research
organization: hypotheses are proposed, validated against evidence, and only
promoted to influence a recommendation after surviving statistical scrutiny.

Read `docs/VISION.md` for the full mission and the eight immutable
principles. Every design decision in this codebase should be traceable back
to one of them. In particular:

- **Nothing skips the lifecycle.** A discovered relationship always moves
  Observation → Hypothesis → Experiment → Statistical Validation → Stress
  Test → Backtest → Peer Validation → Promotion → Monitoring → Retirement.
  This is implemented as a configurable gate pipeline
  (`hypotheses/pipeline.py`), not a hardcoded sequence — but whatever
  pipeline a hypothesis uses, gates still cannot be skipped or reordered at
  runtime. Do not add a shortcut that lets an agent write directly into
  "promoted" knowledge.
- **Agents propose, they never decide.** `agents/` produces `ResearchFinding`
  objects from a `DatasetSnapshot`. Only the validation + promotion
  pipeline may turn a finding (via a `Hypothesis`) into a `KnowledgeObject`,
  and only the Meta Decision Engine may turn knowledge into a
  recommendation. `KnowledgeStore.promote()` depends on a structural
  `PromotableEvidence` protocol rather than importing `Hypothesis`
  directly — preserve that decoupling rather than reaching for the
  concrete class.
- **Everything is versioned and explainable.** Knowledge objects,
  hypotheses, features, models, datasets, and predictions all carry an ID,
  a version, and a `Provenance` linking back to whatever produced them
  (see `domain/provenance.py`). Every store composes
  `storage.JsonFileRepository` rather than hand-rolling persistence — reuse
  it for any new versioned entity instead of writing a new JSON
  read/write loop.

## Current state

All 18 charter systems are architecturally complete and tested except
the business-blocked remainder of 18 (deployment/secrets/scheduling) —
see `docs/PHASE_STATUS.md` for the per-system audit. The platform runs a
real end-to-end daily research cycle (`orchestration/pipeline.py` →
`runtime/engine.py` → `cli.py`): agents propose, the 8-gate pipeline
validates with concrete statistics/backtests/stress tests, the review
board and adversarial scientist judge, promoted knowledge becomes genes
and papers, knowledge-weighted models produce predictions, and the
continuous-learning monitor retires degraded knowledge. The critical
caveat: it all runs on placeholder mock data until a real EGX vendor is
licensed (a business decision reserved for the user) — no output is real
research until then. A handful of components remain honest
`NotImplementedError` stubs where their data source doesn't exist; the
gap inventory lives in `docs/PHASE_STATUS.md` and `docs/TECHNICAL_DEBT.md`.
`agents.financial_performance.FinancialPerformanceAgent` is no longer one
of those stubs (Decision-Centric Redesign, 2026-07-30) — it produces real
revenue-growth-trend and leverage-trend findings from
`DatasetSnapshot.financial_statements`.

Layout:

- `MASTER_PROMPT.md` — the operating charter (role, non-negotiable
  principles, strict 18-system build order).
- `docs/` — vision, architecture, the Epoch I/II audit and design docs,
  `PHASE_STATUS.md` (current status of all 18 systems against the
  charter), plus the management set the charter mandates: `ROADMAP.md`,
  `TECHNICAL_DEBT.md`, `ARCHITECTURE_DECISIONS.md`, `RISK_REGISTER.md`
  (and `CHANGELOG.md` at the repo root). Keep all of them current when
  making changes.
- `research/` — Python package (`agx_research`) containing the research
  engine. See `docs/ARCHITECTURE.md`'s component map for the full
  subpackage breakdown (Epoch I: `domain/`, `storage/`, `universe/`,
  `data/`, `knowledge/`, `hypotheses/`, `validation/`, `agents/`,
  `horizons/`, `meta/`, `explainability/`; Epoch II adds `orchestration/`,
  `events/`, `market_memory/`, `features/` extensions, `genome/`,
  `causal/`, `graph/`, `papers/`, `review/`, `adversarial/`; the Data
  Acquisition Program adds `sources/` and `collectors/`, see
  `docs/DATA_ACQUISITION.md`; the Decision-Centric Redesign (see
  `docs/DECISION_CENTRIC_AUDIT_2026-07-30.md`,
  `docs/FREE_DECISION_DATA_BLUEPRINT.md`,
  `docs/DECISION_EVIDENCE_MATRIX.md`,
  `docs/ARCHITECTURE_ADVERSARIAL_REVIEW.md`) adds `decision_service/`).
- `api/` — TypeScript (Fastify) service exposing the knowledge base over
  HTTP. Currently reads a JSON knowledge store; has no business logic of
  its own by design (logic lives in `research/`). Epoch II added no new
  API surface — it was scoped exclusively to the Python research core.
- `web/` — TypeScript (Vite + React) dashboard, currently a minimal viewer
  for knowledge objects returned by `api/`. Untouched in Epoch II.
- `contracts/` — JSON Schema generated from the pydantic models `api/`
  serves, regenerated via `research/scripts/export_schemas.py`. CI fails if
  this drifts from the schema; `api/src/types.ts` and `web/src/types.ts`
  are hand-maintained TS mirrors that must be updated alongside it.

## Working conventions

- Python: managed with `uv`/`pyproject.toml` under `research/`. Run tests
  with `cd research && uv run pytest`.
- TypeScript: `api/` and `web/` are independent npm workspaces at the repo
  root (`package.json` defines the workspaces). `npm install` at the root,
  then `npm run dev -w api` / `npm run dev -w web`.
- Time horizons are always one of `MICRO` (1–3 trading days), `SWING`
  (1–4 weeks), or `INVESTMENT` (1–6 months) — see
  `research/src/agx_research/config.py`. Each horizon has independent
  models; do not merge them into a single model without the Meta Decision
  Engine combining their outputs.
- Universe membership (EGX30 constituents) is a placeholder snapshot behind
  `universe.StaticUniverseProvider`, not a live feed. Do not treat it as
  authoritative market data; a real feed should be a new
  `UniverseProvider` implementation, not a change to `config.py` (which
  intentionally holds only the stable `Horizon` enum).
- The market data provider (`agx_research.data.provider.DataProvider`) is
  implemented today only by `MockDataProvider`, which reads local CSVs
  under `research/data/mock/`, and `FallbackDataProvider`, which composes
  multiple `DataProvider`s in priority order. A real, licensed EGX vendor
  integration is a business decision (which vendor, cost, coverage) — flag
  it to the user rather than picking one; don't hardcode assumptions about
  a specific vendor's API shape into code outside `data/`.
- Real (non-mock) market/macro/news data comes from `sources/`+`collectors/`,
  not a new `DataProvider`. Every source is a `sources.SourceSpec` in the
  `SourceRegistry`; a source is only collectable (its `Collector` will
  construct at all) once its status is `IMPLEMENTED` — `PLANNED`,
  `NEEDS_KEY`, and `TOS_REVIEW` sources must stay blocked until the user
  clears the reason (endpoint verified, API key supplied, ToS reviewed).
  A `Collector.fetch()` only wraps payloads as a `RawDocument`
  (`collectors/raw.py`) and `.parse()` only turns one `RawDocument` into a
  canonical `CollectionBatch` — no source-specific logic belongs anywhere
  else. `collectors.service.CollectionService` is the only path from a
  batch into the platform: it scores the batch with
  `collectors.quality.assess_quality()` and materializes it into the same
  local-CSV layout `LocalCsvDataProvider` reads only if confidence clears
  the floor, otherwise withholds it — "no downstream system may ignore
  data quality" is enforced by withholding, not by passing degraded data
  through. Derived news candidates are registered via
  `events.service.EventPlatform.register()`, the same as any other event
  source — never a parallel write path. `HttpFetcher` enforces robots.txt,
  per-source rate limits, and retry/backoff in code; do not add a fetch
  path that bypasses it. Prefer official/RSS/structured-API/downloadable
  sources over HTML scraping; scraping is last-resort only and must
  tolerate layout changes.
- Agents, experiments, and validators consume a `DatasetSnapshot`
  (`data/snapshot.py`), never a live `DataProvider` directly — this is what
  makes findings/experiments reproducible and prevents look-ahead bias.
  Don't reintroduce direct `DataProvider` calls in those layers.
- Return calculations always go through `data.adjustments.adjusted_returns_for_ticker()`,
  never raw `[bar.close for bar in bars]` — a stock split or dividend
  would otherwise look like a huge fake return. If you add a new place
  that computes returns from prices, wire it through this function, not a
  new inline calculation.
- New raw price data (a new mock ticker, a future real feed) should be run
  through `data.quality.validate_price_bars()` before being trusted by
  anything downstream. Corporate events with a `split_ratio` or
  `dividend_amount` in `details` are the only ones `data.adjustments`
  acts on — other event types are informational only.
- New versioned entities (predictions, dataset registries, whatever comes
  next) should get a thin repository composing
  `storage.JsonFileRepository`, following the pattern in
  `knowledge/store.py` and `hypotheses/repository.py` — not a new bespoke
  persistence mechanism.
- `KnowledgeObject`/`KnowledgeStore` remain the system of record for the
  promotion gate. `genome.Gene`/`AlphaGenome` are the lineage layer *on
  top* — don't fold gene fields into `KnowledgeObject` or vice versa.
- `genome.AlphaGenome.mutate()` is the only way an existing discovery's
  understanding changes; it always creates a new `Gene` and marks the
  parent `REPLACED`. Never add a path that edits a gene's `knowledge_id`,
  `evidence`, or lineage fields in place.
- The `review.ScientificReviewBoard` and `causal.EconomicRationaleGate` are
  meant to run *before* `KnowledgeStore.promote()`, not inside it —
  `promote()`'s signature is unchanged from Epoch I on purpose. Wire new
  promotion flows as "board reviews, then promote," not by modifying
  `promote()` to take reviewers as an argument.
- `graph.KnowledgeGraph` edges should come from `graph.edges_from_provenance()`
  (or, for events, `events.graph_integration.project_event()`) wherever
  possible, not be hand-constructed from scratch — the graph is a view
  over `Provenance` and event data, and hand-built edges are exactly the
  kind of parallel source of truth that drifts.
- `events.EventPlatform.register()` is the only path for persisting an
  event. Adapters (and future real data providers) only *build candidates*
  via `events.service.build_candidate_event()`, which derives the id from
  a content fingerprint — never mint an event id with `new_id()` or write
  to `EventRepository` directly, or deduplication and cross-source
  corroboration silently stop working. A factual correction is
  `EventPlatform.supersede()` (a new event linked to the old), never an
  in-place edit.
- `decision_service/` is the position-aware layer between promoted
  knowledge and a Buy/Increase Position/Hold/Reduce Position/Exit/No
  Action action — deliberately its own package, never a new stage inside
  `orchestration.pipeline.DailyResearchPipeline` or
  `production.pipeline.ProductionPipeline`. Those pipelines' core, tested
  property is determinism; a position-aware decision depends on
  externally-supplied `PositionState`, which no autonomous run can
  discover (a real portfolio's holdings are inherently the investor's own
  data). `DecisionService.decide_portfolio()` is stateless-per-call,
  queried on demand — do not wire it into a scheduled/autonomous run. It
  computes one continuous target weight per ticker (extending
  `portfolio.constructor.PortfolioConstructor`'s existing risk-adjusted,
  confidence-discounted scoring) and derives the six-way action as a
  *label* from comparing that target to the current weight — never build
  a discrete lookup table over signal-strength buckets instead; that was
  tried and rejected under adversarial review for combinatorial-growth
  risk. Only the INVESTMENT horizon drives an action here (`AD-35`'s
  existing "never blend horizons into one action" rule), since this
  layer exists for the long-term-investor mission specifically.
- `decision_service.country_risk.assess_country_risk()` classifies
  Country & Macro Risk severity (NORMAL/DETERIORATING/CRISIS) from macro
  series data. `CRISIS` must never be inferred from a currency/macro move
  alone — it requires a real, discrete `SovereignRatingAction` (a
  downgrade). No collector for that exists yet
  (`moodys_ratings`/`sp_global_ratings`/`fitch_ratings` are `PLANNED`), so
  `CRISIS` is honestly unreachable in a real run today; do not lower that
  bar to make the override "do something" before real evidence exists.
  `decision_service.liquidity_floor.compute_illiquid_tickers()` is a
  second, symmetric hard override (a ticker below the floor caps out at
  target weight zero regardless of thesis strength) — both overrides are
  reused as-is by `meta.readiness.assess_decision_readiness`'s gate
  extension; do not build a second, parallel readiness/gate mechanism
  alongside the existing one.
- `data.snapshot.DatasetSnapshot.financial_statements` (populated only
  when `build_snapshot()` is given a `financials_provider`) is how
  `agents.financial_performance.FinancialPerformanceAgent` sees financial
  statements — the same "agents never touch a live provider directly"
  rule every other agent already follows, extended, not bypassed. Don't
  have an agent call `FinancialStatementProvider` directly.
- The web dashboard reads every resource through `DashboardDataProvider`
  (`web/src/data/DataProvider.ts`); components never call `fetch()` or
  import `StaticJsonProvider`/`ApiProvider` directly — only
  `web/src/data/factory.ts` does, picking one via `VITE_DATA_PROVIDER`.
  New dashboard data goes through `agx_research.dashboard.export`
  (a `model_dump(mode="json")` of an existing pydantic model, not a new
  bespoke shape) plus a matching route in `api/src/routes/dashboard.ts` —
  never a one-off fetch wired straight into a component. See
  `docs/ARCHITECTURE.md`'s "Dashboard data providers" section.

## What NOT to do

- Do not let an agent write to the "promoted" knowledge store directly.
- Do not implement a "black box" model with no explanation object attached
  — every prediction needs an `Explanation` (see `explainability/`), and
  every persisted entity in the discovery chain needs a `Provenance`.
- Do not treat this scaffold's stub statistical validators as real
  validation — they intentionally raise/return placeholders until real
  statistical tests are implemented.
- Do not hardcode a new validation gate into `Hypothesis` or its stage
  logic — add or reorder `GateSpec`s in a pipeline instead.
- Do not fake a result for an unimplemented experiment, reviewer, or
  adversarial attack. Every stub in `ExperimentFactory`,
  `review.reviewers`, and `AdversarialScientist` raises
  `NotImplementedError` (or, for attacks, reports `attempted=False`) —
  preserve that honesty rather than returning a plausible-looking but
  fabricated number.
- Do not let `ScientificReviewBoard` or `AdversarialScientist` silently
  treat a skipped/unimplemented check as a pass. A board with zero working
  reviewers must never approve anything.
- Do not compute a dividend adjustment factor from the close *on* the
  ex-date — use the last *cum*-dividend close, strictly before it (a real
  bug caught by this codebase's own tests; see `data/adjustments.py`).
- Do not populate `patterns.json` with invented entries. It stays `[]`
  until a dedicated `Pattern` pydantic model/contract exists for its
  dashboard-specific shape (TD-15); `validate_dashboard_artifacts()`
  enforces this and fails the build if it's ever non-empty.
  `agents.historical_patterns.HistoricalPatternsAgent` itself is
  implemented and its findings already flow through the normal
  finding/hypothesis/knowledge pipeline like any other agent's — this
  restriction is only about the separate raw-pattern display artifact.
