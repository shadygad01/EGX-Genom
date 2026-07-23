# AGX Architecture (Foundation Scaffold)

This describes the current shape of the codebase and how it is intended to
grow. It is a foundation scaffold: interfaces and lifecycle machinery are in
place; most research logic is stubbed pending real data access and model
development. See `docs/ARCHITECTURE_AUDIT.md` for the reasoning behind the
design choices below — this document is the resulting shape, the audit is
the "why."

## Component map

```
research/        Python package `agx_research` — the research engine
  domain/         Cross-cutting domain primitives: id minting, Provenance
  storage/        Generic versioned Repository[T] used by every store
  universe/       UniverseProvider interface + placeholder EGX30 snapshot
  data/           DataProvider interface, mock impl, point-in-time DatasetSnapshot
  features/       Versioned FeatureDefinition registry (Principle 5: Features)
  knowledge/      KnowledgeObject schema, lifecycle state machine, store
  hypotheses/     Hypothesis + configurable gate pipeline + Experiment machinery
  validation/     Statistical validation / stress test / backtest interfaces
  agents/         Research agents (one responsibility each, propose only)
  horizons/       Per-horizon model interfaces (Micro / Swing / Investment)
  meta/           Meta Decision Engine — combines horizon outputs + knowledge
  explainability/ Explanation object required on every prediction
  orchestration/  ResearchCycle + ResearchOrchestrator — one research run

api/              TypeScript (Fastify) — HTTP surface over the knowledge base
web/              TypeScript (Vite + React) — dashboard for knowledge/recs
contracts/        Generated JSON Schema for API-facing pydantic models
```

## Data flow (target state)

1. `data.build_snapshot()` materializes an immutable, content-hashed
   `DatasetSnapshot` from a `DataProvider` for a fixed `as_of` + lookback
   window. Everything downstream operates on this snapshot, not on live
   provider calls, so a finding, experiment, or hypothesis can always be
   traced back to the exact data it saw (Principle 5: Datasets are
   versioned; and it rules out look-ahead bias by construction).
2. `orchestration.ResearchOrchestrator.run(as_of)` builds that snapshot and
   runs every registered `agents.*` agent against it, returning a
   `ResearchCycle` — the auditable record of one trading day's research.
3. Each agent consumes a slice of the snapshot (via versioned
   `features.*` where applicable) and produces `ResearchFinding` objects —
   an observation plus a proposed hypothesis, carrying `Provenance` back to
   the snapshot and features used. Agents never write to the knowledge
   store.
4. `hypotheses.Hypothesis.from_finding()` wraps a finding and walks it
   through its `pipeline` (a list of named `GateSpec`s — see
   `hypotheses/pipeline.py`; the default mirrors the vision document's
   scientific method, but is data, not hardcoded logic, so different
   hypothesis tracks can use different gates). Every revision is persisted
   via `hypotheses.HypothesisRepository`, including hypotheses that fail
   and are never promoted — the organization has to remember what it
   already tried.
5. `validation.*` implements the Statistical Validation, Stress Test, and
   Backtest gates against a `DatasetSnapshot`. A hypothesis only advances
   if it passes its current gate.
6. A hypothesis that reaches its pipeline's final gate is promoted into a
   `knowledge.KnowledgeObject` via `knowledge.store.KnowledgeStore`. This is
   the only path by which knowledge is created — there is no direct write
   path from `agents/`. `KnowledgeStore.promote()` depends on a structural
   `PromotableEvidence` protocol, not the concrete `Hypothesis` class, so
   future evidence sources aren't foreclosed.
7. `horizons.*` model interfaces consume promoted knowledge relevant to
   their horizon (Micro/Swing/Investment) and produce per-horizon
   `Prediction`s, each tagged with the exact `model_id`/`model_version`
   that produced it.
8. `meta.decision_engine.MetaDecisionEngine` combines the three horizons'
   predictions with risk assessment and produces a `Recommendation`, which
   must carry an `explainability.Explanation` with structured
   `evidence_refs`, not just prose.
9. `api/` reads knowledge objects (currently from a JSON-backed store) and
   exposes them over HTTP; `web/` renders them.

## Why the split between `research/` (Python) and `api/`+`web/` (TypeScript)

The research engine — data science, statistics, modeling — is Python
because that's where the EGX quant/ML ecosystem lives (pandas, statsmodels,
scikit-learn, and later deep learning frameworks). The API and dashboard are
TypeScript so the presentation layer can evolve independently and be
consumed by other tooling without every consumer needing a Python runtime.
`api/` intentionally contains no research logic — it is a thin read layer
over whatever `research/` has published to the knowledge store.

`api/src/types.ts` and `web/src/types.ts` are hand-maintained mirrors of the
pydantic schema `api/` serves. `contracts/knowledge_object.schema.json` is
generated from the pydantic model (`research/scripts/export_schemas.py`)
and checked in; CI regenerates it and fails if it doesn't match what's
committed, which is the forcing function to keep the TS mirrors honest
until the schema surface is large enough to justify full codegen.

## Boundaries that must hold as this grows

- **Agents propose, never publish.** Enforced by `ResearchAgent` returning
  `ResearchFinding` (not writing to `KnowledgeStore` directly) — see
  `agents/base.py`.
- **No promotion without passing every gate.** Enforced by
  `Hypothesis.advance()` walking `pipeline` strictly in order (gates can't
  be skipped), and `KnowledgeStore.promote()` requiring
  `is_ready_for_promotion`.
- **No horizon leakage.** `horizons/micro_alpha.py`, `swing_alpha.py`, and
  `investment_alpha.py` implement the same `HorizonModel` interface but are
  independent models; only `meta/decision_engine.py` is allowed to combine
  their outputs.
- **No black-box predictions.** `HorizonModel.predict()` and
  `MetaDecisionEngine.decide()` return objects that require an attached
  `Explanation`, and every persisted entity in the discovery chain
  (`ResearchFinding` → `Hypothesis` → `KnowledgeObject` → `Prediction` /
  `Recommendation`) carries `Provenance` linking to its inputs by id.
- **No live-data coupling.** Agents, experiments, and validators take a
  `DatasetSnapshot`, never a live `DataProvider` — reproducibility and
  point-in-time correctness depend on this.
- **Storage is one mechanism, not N.** Every versioned store
  (`KnowledgeStore`, `HypothesisRepository`, and any future one) composes
  `storage.JsonFileRepository`, so swapping the backing store later is a
  new `Repository[T]` implementation, not a rewrite of every call site.

## What is intentionally not built yet

- Real EGX market data ingestion (vendor TBD) — `MockDataProvider` reads
  local CSVs as a stand-in so the rest of the pipeline has something to run
  against. Same for `universe.StaticUniverseProvider` — a placeholder for
  a live EGX30 membership feed.
- Actual statistical tests in `validation/statistical.py`,
  `stress_test.py`, `backtest.py` beyond `SignificanceThresholdValidator` —
  these currently define the interface and raise `NotImplementedError`
  where real logic belongs.
- Real agent research logic in `agents/*.py` beyond
  `market_structure.py`'s illustrative example — each is a stub
  implementing `ResearchAgent` with a `TODO`.
- Real per-horizon models — `horizons/*.py` declare `model_id`/
  `model_version` but `predict()` raises `NotImplementedError`.
- A real database backend. The `storage.Repository[T]` abstraction is the
  actual fix for this; a new implementation is additive whenever there's
  enough scale to justify one.
- Full schema codegen for `api/`/`web/` — see the drift-detection tripwire
  above; revisit once the schema surface grows.
- Orchestration scheduling, retries, distributed execution — out of scope
  until there's more than one agent worth parallelizing.
- Authentication/authorization on `api/` — not needed until this is
  exposed beyond local development.
