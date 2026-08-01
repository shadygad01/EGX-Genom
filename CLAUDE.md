# AGX — Alpha Genome (EGX Research Platform)

This file orients any Claude session working in this repository. It is not
the vision document itself — that lives in `docs/VISION.md` verbatim — nor
the operating charter, which is `MASTER_PROMPT.md` (role, non-negotiable
principles, and the strict 18-system build order). Nor is it the
investment doctrine: `docs/INVESTMENT_CONSTITUTION.md` (permanent
principles — why invest/reject, when to hold cash/increase/reduce/exit,
how capital is allocated, how confidence and evidence are interpreted,
how conflicts and mistakes are handled), `docs/INVESTMENT_PLAYBOOK.md`
(situational doctrine for 12 market regimes), `docs/DECISION_STANDARDS.md`
(the exact minimum bar for each of the six-way action labels), and
`docs/PORTFOLIO_STANDARDS.md` (concentration/liquidity/cash/sizing/
recycling rules) are the permanent governing law for *how AGX decides*,
produced by the EGX Investment Methodology mission (2026-08-01) — every
one of them is grounded in real, already-implemented mechanisms and cited
by exact module/threshold, never free-floating policy; `docs/
INVESTMENT_HANDBOOK.md` is the complete operational walkthrough tying
them together, detailed enough to rebuild the investment process without
reading source. This file is the practical guide to how the *codebase* is
organized and what invariants to protect when touching it. `docs/
ARCHITECTURE.md` describes the current design in more detail; `docs/
ARCHITECTURE_AUDIT.md` (Epoch I) and `docs/EPOCH_II_DESIGN.md`/`docs/
EPOCH_II_REPORT.md` (Epoch II) explain *why* it's shaped this way. `docs/
PHASE_STATUS.md` is the living, must-be-updated audit of where every one
of `MASTER_PROMPT.md`'s 18 systems actually stands — check it before
starting new work: per the charter, a later system's work should not
start while an earlier one still has closeable gaps.

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
  charter), the investment doctrine set (`INVESTMENT_CONSTITUTION.md`,
  `INVESTMENT_PLAYBOOK.md`, `DECISION_STANDARDS.md`,
  `PORTFOLIO_STANDARDS.md`, `INVESTMENT_HANDBOOK.md`), plus the
  management set the charter mandates: `ROADMAP.md`, `TECHNICAL_DEBT.md`,
  `ARCHITECTURE_DECISIONS.md`, `RISK_REGISTER.md` (and `CHANGELOG.md` at
  the repo root). Keep all of them current when making changes — in
  particular, a change to any decision-affecting threshold or gate
  (`meta.decision_engine`, `meta.publication_gate`, `meta.readiness`,
  `decision_service/`, `capital_allocation/`, `investment_proof/`) must be
  reflected in the doctrine set in the same change, per the doctrine's own
  amendment rule (`docs/INVESTMENT_CONSTITUTION.md`'s closing article):
  numbered decision, stated reason, permanent record — never a silent
  drift between what the code does and what the doctrine says it does.
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
  `docs/ARCHITECTURE_ADVERSARIAL_REVIEW.md`) adds `decision_service/`; the
  Institutional Investment Validation mission adds
  `institutional_validation/` — deliberately separate from `validation/`
  (System 11, which statistically validates one *hypothesis* before
  promotion): `institutional_validation/` validates the *decision
  engine's* aggregate behavior via repeatable, falsification-attempting
  scenarios (`agx validate-investment`), and imports `validation/`'s
  siblings rather than duplicating any of their logic. Never confuse the
  two when extending either; the Zero-Cost Production Deployment mission
  (2026-08-01) adds `shadow_fund/` — the persistent, autonomous virtual-
  portfolio state, deliberately distinct from `meta.decision_ledger`
  (why decisions were made) and `investment_cases`/`investment_proof`
  (reasoning/validation): the Shadow Fund owns portfolio state, nothing
  else does. See the `shadow_fund/` working-conventions bullet below).
- `api/` — TypeScript (Fastify) service exposing the knowledge base and
  dashboard artifacts over HTTP; almost every route only reads a
  pre-produced JSON artifact. The one exception is `POST /decisions`
  (`routes/decisions.ts`), which shells out to the `agx decide` CLI on
  each request for a live, position-aware decision — still no business
  logic of its own (it only shapes the HTTP call, all computation stays in
  `research/`), and still never autonomous (queried on demand, exactly
  like the CLI it wraps).
- `web/` — TypeScript (Vite + React) Investment Operating System (the IOS
  mission, 2026-08-01: research is an internal capability, investment
  decisions are the product; extended by the Capital Allocation
  Intelligence mission, 2026-08-01: every recommendation competes for the
  same finite capital rather than being scored in isolation). 7 top-level
  routed sections in the mission-mandated hierarchy — CIO Desk (`/`, the
  landing page; exactly 5 sections: Market Regime, Capital Allocation,
  Portfolio Summary, Warnings, Investment Committee Summary — never more,
  per the Product Law that every screen answers exactly one primary
  investment question), Portfolio (`/portfolio`, holdings entry + the live
  six-way decision table), Investment Cases (`/cases`, `/cases/:ticker` —
  the 19-section thesis-first case page), Monitoring (`/monitoring`),
  Market (`/market`), Research (`/research` — the internal-capability hub,
  absorbing the former Opportunity Center's Decision Readiness/Data
  Coverage tables and linking out to Knowledge Graph/Source Intelligence,
  which stay reachable but off the primary nav), Settings (`/settings`,
  merging the former Mission Control + System Administration). Each page
  reads real dashboard artifacts through `DashboardDataProvider` — see
  `docs/ARCHITECTURE.md`'s "Dashboard data providers" and "Frontend:
  Institutional Investment Operating System" sections. Portfolio is one of
  two pages that write (`POST /decisions`); it only works against a live
  `api/` (`StaticJsonProvider` honestly reports itself unavailable on the
  static GitHub Pages build, never fabricating a decision). CIO Desk's
  Capital Allocation section (Capital Deployment Queue, Capital Recycling,
  Capital Released Today, Best New Opportunities, Highest Opportunity
  Cost, Allocation Changes, Capital Waiting For Better Opportunities — the
  mission's 7 named sub-sections) calls both `POST /decisions` and the
  second live-write endpoint, `POST /capital-allocation`, when the
  investor has entered holdings via `usePortfolioPositions`
  (localStorage-only — the backend never stores real portfolio data), and
  otherwise falls back to the existing position-unaware decisions table
  plus a ranked "Best New Opportunities" preview from the model portfolio
  — the other 6 sub-sections honestly state they need real holdings rather
  than fabricating a capital competition that doesn't exist without real
  capital. The prior 9-section IA (AI Briefing, Decision Center,
  Opportunity Center, Company Research Workspace, Mission Control, System
  Administration) was retired outright, not kept as parallel dead code —
  see `docs/PHASE_STATUS.md`'s IOS section for the full page-by-page
  mapping.
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
  `PositionAwareDecision.opportunity_score`/`expected_return`/
  `expected_risk` (Capital Allocation Intelligence mission) expose the
  same score/return/risk `decide_portfolio()` already computes internally
  as first-class fields — any future consumer needing to rank tickers
  against each other reads these, never re-derives the eligibility/
  scoring rule a second time.
- `capital_allocation/` (`CapitalAllocationEngine`) is the read-only
  ranking/opportunity-cost/recycling layer *on top of*
  `decision_service.DecisionService.decide_portfolio()`'s output — it
  never rescoring or reweighs anything `decide_portfolio()` already
  computed, only attributes each unit of requested capital to a source
  (idle cash, or a specific lower-ranked holding whose reduction/exit
  released it) and each unit of released capital to a destination (a
  specific higher-ranked demander, or back to cash). Idle cash is always
  drawn before any holding is displaced, so a holding is only ever named
  as a capital source when idle cash genuinely wasn't enough — never
  fabricate a "should this replace another investment" conflict where
  idle cash alone would have covered it. A ticker whose `PositionAwareDecision.abstained`
  is `True` never participates in capital-flow matching even if its raw
  `target_weight` differs from `current_weight` — `decide_portfolio()`
  deliberately reports `target_weight=0.0` for an abstained held ticker to
  keep its own scoring simple, but labels the *action* `hold` specifically
  so an evidence gap is never read as a sell signal; treating that raw
  number as a real capital release would fabricate a movement nothing
  recommends. Same architectural posture as `decision_service/` itself:
  stateless-per-call, queried on demand only (`agx allocate-capital`,
  `POST /capital-allocation`), never wired into
  `production.pipeline.ProductionPipeline` — there is nothing to rank or
  recycle without the investor's own real `PositionState`.
- `shadow_fund/` (`shadow_fund.engine.advance()`, `ShadowFundLedger`) is
  the **one deliberate exception** to "never wire `decision_service` into
  a scheduled run": it drives `DecisionService.decide_portfolio()`
  autonomously, inside `production.pipeline.ProductionPipeline`, every
  day. This is safe and correct — unlike `capital_allocation/`/`decision_service`'s
  real-investor case above — because the `PositionState` fed in is always
  the Shadow Fund's *own* prior-day state, never a real investor's
  holdings: fully platform-controlled and reproducible from an all-cash
  inception plus every day's own autonomous decisions. Do not generalize
  this exception to any path that could ever receive a real investor's
  positions. Never a new decision engine: every target weight comes from
  the same `decide_portfolio()` call every other position-aware consumer
  uses; `capital_allocation.CapitalAllocationEngine.build()` is reused
  as-is for the fund's own capital-deployment/recycling view, never
  reimplemented. `ShadowFundLedger` is a single continuously-versioned
  entity (not one entity per date) so `history()` doubles as the daily NAV
  time series with no separate, unboundedly-growing per-day store — the
  TD-63 mistake this package deliberately avoids. An abstained held
  ticker's `target_weight=0.0` is never treated as a real exit — same
  exclusion rule `capital_allocation/` already follows above; the fund
  holds it unchanged instead of fabricating a liquidation nothing
  recommended. Every `_pct`-suffixed field here is a fraction (e.g.
  `0.0432` = 4.32%), matching every other `_pct` field in this codebase
  (`MAX_PRICE_ABOVE_FAIR_VALUE_PCT = 0.20`) and the shared
  `formatPercent()`/`formatSignedPercent()` frontend formatters — never
  pre-multiply by 100 in Python.
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
