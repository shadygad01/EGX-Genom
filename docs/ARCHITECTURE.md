# AGX Architecture

This describes the current shape of the codebase and how it is intended to
grow. See `docs/ARCHITECTURE_AUDIT.md` (Epoch I), `docs/EPOCH_II_DESIGN.md`
(Epoch II), and `docs/PHASE_STATUS.md` (the strict-order phase audit
against `MASTER_PROMPT.md`'s 18-system architecture) for the reasoning
behind the design choices below — this document is the resulting shape,
those are the "why," and `PHASE_STATUS.md` is the current source of truth
for what's actually done vs. partial vs. not started per system.

Epoch I built a foundation scaffold: interfaces, the knowledge lifecycle,
provenance, versioned repositories, point-in-time datasets. Epoch II
("the Scientific Core") turned that into a research operating system:
sessions/task graphs/artifacts, an event layer, market memory, autonomous
feature discovery, an experiment factory, the Alpha Genome lineage, a
causal-reasoning architecture, a knowledge graph, research paper
generation, a scientific review board, and an adversarial scientist. Real
statistical/ML logic is still deliberately thin in most of these — see
"What is intentionally not built yet" below and the epoch design docs for
what's real vs. interface-only in each piece.

## Component map

```
research/        Python package `agx_research` — the research engine

  # Epoch I: foundation
  domain/         Cross-cutting primitives: id minting, Provenance
  storage/        Generic versioned Repository[T] used by every store
  universe/       UniverseProvider + SectorProvider interfaces (placeholder data)
  data/           DataProvider/FallbackDataProvider, mock impl, point-in-time
                  DatasetSnapshot(+repository), quality checks, split/dividend
                  adjustment
  knowledge/      KnowledgeObject schema, lifecycle state machine, store
  hypotheses/     Hypothesis + configurable gate pipeline + Experiment machinery
  validation/     Statistical validation / stress test / backtest interfaces
  agents/         Research agents (one responsibility each, propose only)
  horizons/       Per-horizon model interfaces (Micro / Swing / Investment)
  meta/           Meta Decision Engine — combines horizon outputs + knowledge
  explainability/ Explanation object required on every prediction

  # Epoch II: scientific core
  orchestration/  Task Graph, Artifacts, ResearchSession, ResearchOrchestrator
  events/         Event Platform: canonical schema, taxonomy/ontology,
                  entity resolution, fingerprint identity, dedup/conflict
                  resolution, lifecycle, EventPlatform write path, adapters,
                  graph projection (see docs/EVENT_PLATFORM_DESIGN.md)
  market_memory/  MarketState + MarketMemory (point-in-time reconstruction)
  features/       (extended) FeatureCandidate + FeatureDiscoveryEngine
  genome/         Gene (immutable lineage) + AlphaGenome service
  causal/         CausalAssessment + CausalReasoner architecture
  graph/          Knowledge Graph: nodes, edges, provenance-driven builder
  papers/         ResearchPaper schema + mechanical generator
  review/         Scientific Review Board: reviewers + board decision
  adversarial/    AdversarialScientist: attacks against a hypothesis

  # Data Acquisition Program: the free-source collection framework
  sources/        SourceSpec/SourceRegistry — the declarative catalog of
                  every known data source (id, access method, status,
                  reliability/freshness priors, retry/rate-limit policy,
                  license, conflict priority); see docs/DATA_ACQUISITION.md
  collectors/     RawDocument provenance envelope, Collector ABC
                  (fetch -> RawDocument, parse -> CollectionBatch as a pure
                  function), HttpFetcher (robots.txt + rate limit + retry),
                  per-source collectors (Stooq, FRED, generic RSS/Atom),
                  QualityAssessment scoring, CollectionService
                  (materialize-if-above-confidence-floor, else withhold;
                  routes derived news events through EventPlatform.register())

api/              TypeScript (Fastify) — HTTP surface over the knowledge base
web/              TypeScript (Vite + React) — dashboard for knowledge/recs
contracts/        Generated JSON Schema for API-facing pydantic models
```

## Web dashboard deployment (GitHub Pages)

`.github/workflows/deploy-pages.yml` builds `web/` and publishes `web/dist`
to GitHub Pages on every push to `main` that touches `web/`, at
`https://shadygad01.github.io/EGX-Genom/`. `web/vite.config.ts` sets
`base: "/EGX-Genom/"` for production builds only (the dev server still
serves at `/`) so asset URLs resolve correctly as a project site.

GitHub Pages is static hosting: it can serve `web/`'s built assets but not
`api/`'s Fastify server. `web/src/api.ts` still calls the relative path
`/api/knowledge` (the dev-only Vite proxy target), which has nothing to
resolve to once deployed statically — the page loads and renders correctly,
but shows its existing "Error loading knowledge" state
(`web/src/App.tsx`) rather than fabricating data. Making the dashboard
functional end-to-end on Pages needs `api/` deployed somewhere reachable
over HTTPS and `web/src/api.ts` pointed at it (e.g. via a build-time env
var) — a hosting decision out of scope for a static-only deployment target.

## Data flow

1. `market_memory.MarketMemory.reconstruct(as_of)` (or the lower-level
   `data.build_snapshot()`) materializes an immutable, content-hashed
   `DatasetSnapshot`/`MarketState` for a fixed `as_of` + lookback window —
   nothing downstream may read data outside it. `events.derive_events_from_snapshot()`
   turns its raw records into canonical `Event`s.
2. `orchestration.ResearchOrchestrator.run_session(as_of)` builds that
   snapshot through an explicit `TaskGraph` (dependencies, status, timing,
   reproducibility hash per task) and runs every registered `agents.*`
   agent against it, returning a `ResearchSession` that owns every
   `Artifact` produced. (`run()` remains for callers that only need a bare
   `ResearchCycle` of findings.)
3. `features.FeatureDiscoveryEngine` searches a `MarketState` autonomously
   for candidate features (e.g. `PairwiseCorrelationGenerator` over every
   ticker pair) rather than a human hardcoding one. Agents consume a slice
   of the snapshot/features and produce `ResearchFinding`s — never writing
   to the knowledge store.
4. `hypotheses.Hypothesis.from_finding()` wraps a finding and walks its
   configurable gate `pipeline`. `hypotheses.ExperimentFactory` generates
   every applicable experiment type (cross-validation, bootstrap,
   walk-forward, out-of-sample, stress-test adapter; sensitivity analysis
   and Monte Carlo are explicit `NotImplementedError` placeholders) against
   a `DatasetSnapshot`. Every `Hypothesis` revision persists via
   `HypothesisRepository`, including ones that fail and are never promoted.
5. `causal.EconomicRationaleGate` and (eventually) the full
   `review.ScientificReviewBoard` run *before* promotion — a candidate must
   state an economic rationale and candidate cause, and pass every
   configured reviewer, or it doesn't reach `KnowledgeStore.promote()`.
   `adversarial.AdversarialScientist` then attacks the resulting
   confidence, reducing it for successful attacks and reinforcing it for
   failed ones.
6. A hypothesis that clears its pipeline's final gate is promoted into a
   `knowledge.KnowledgeObject`. `genome.AlphaGenome.promote_to_gene()` wraps
   it as a generation-0 `Gene`; later re-discoveries call
   `AlphaGenome.mutate()`, which never overwrites the parent gene — it
   creates a new child gene and marks the parent `REPLACED`.
7. `papers.generate_paper()` mechanically assembles a `ResearchPaper` from
   the gene/hypothesis/knowledge/experiment evidence — every section
   traces to an input field, never free-generated prose.
8. `graph.edges_from_provenance()` turns any entity's `Provenance` into
   `GraphEdge`s in the `KnowledgeGraph` — the graph is a view over
   provenance Epoch I/II already produce, not a separately maintained
   structure that can drift from it.
9. `horizons.*` and `meta.decision_engine.MetaDecisionEngine` are unchanged
   from Epoch I: independent per-horizon predictions combined into an
   explainable `Recommendation`.
10. `api/` reads knowledge objects (currently from a JSON-backed store)
    and exposes them over HTTP; `web/` renders them. Epoch II added no new
    API surface — the scientific core is Python-only so far.
11. Upstream of all of the above: `collectors.Collector.fetch()` wraps
    every payload as a `RawDocument` (source, collector, content hash,
    license — the provenance envelope), `.parse()` turns it into a
    `CollectionBatch` of canonical `PriceBar`/`MacroObservation`/`NewsItem`
    candidates, and `collectors.service.CollectionService` scores it with
    `assess_quality()` before deciding whether to materialize it into the
    same local-CSV layout `data.mock_provider.LocalCsvDataProvider` (an
    alias of `MockDataProvider`) reads, or withhold it. Derived news
    candidates are registered through `events.service.EventPlatform`,
    never written directly — identity/dedup/corroboration/conflict
    resolution apply exactly as they do to any other event source. Only
    sources marked `IMPLEMENTED` in the `sources.SourceRegistry` are
    collectable at all; `Collector.__init__` enforces this.

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
  `is_ready_for_promotion`. In the intended production flow, the
  `review.ScientificReviewBoard` and `causal.EconomicRationaleGate` both
  run before that promote call.
- **No horizon leakage.** `horizons/micro_alpha.py`, `swing_alpha.py`, and
  `investment_alpha.py` implement the same `HorizonModel` interface but are
  independent models; only `meta/decision_engine.py` is allowed to combine
  their outputs.
- **No black-box predictions.** `HorizonModel.predict()` and
  `MetaDecisionEngine.decide()` return objects that require an attached
  `Explanation`, and every persisted entity in the discovery chain
  (`ResearchFinding` → `Hypothesis` → `KnowledgeObject`/`Gene` →
  `Prediction` / `Recommendation`) carries `Provenance` linking to its
  inputs by id.
- **No live-data coupling.** Agents, experiments, and validators take a
  `DatasetSnapshot`, never a live `DataProvider` — reproducibility and
  point-in-time correctness depend on this. `market_memory.MarketMemory`
  is the sanctioned way to reconstruct any historical day.
- **Storage is one mechanism, not N.** Every versioned store composes
  `storage.JsonFileRepository`, so swapping the backing store later is a
  new `Repository[T]` implementation, not a rewrite of every call site.
- **Knowledge is never overwritten, only superseded.** `AlphaGenome.mutate()`
  always creates a new gene and marks its parent `REPLACED`; the parent's
  full revision history remains in `GeneRepository.history()`.
- **The Knowledge Graph is a view, not a second source of truth.**
  `graph.edges_from_provenance()` derives edges mechanically from
  `Provenance` objects that already exist; nothing should hand-maintain
  graph edges that duplicate what provenance already encodes.
- **Returns are always adjusted, never computed from raw closes.**
  `features.correlation` and `hypotheses.experiment_factory` compute
  returns via `data.adjustments.adjusted_returns_for_ticker()`, which
  applies split/dividend adjustment using each ticker's
  `DatasetSnapshot.corporate_events`. A stock split or dividend would
  otherwise look like a huge fake return and corrupt every statistic
  downstream — do not reintroduce `[bar.close for bar in bars]` return
  calculations that bypass this.

## What is intentionally not built yet

- A licensed, real-time EGX market data vendor integration —
  `MockDataProvider` reads local CSVs as a stand-in, and
  `data.FallbackDataProvider` is the composition seam a real vendor drops
  into. *Which* vendor to license is a business decision (cost, coverage,
  contract terms), not an engineering one — see `docs/PHASE_STATUS.md`.
  Same caveat for `universe.StaticUniverseProvider`/`SectorProvider` —
  placeholders for live EGX30 membership/sector feeds.
- Actual statistical tests beyond `SignificanceThresholdValidator` and the
  four real `ExperimentFactory` experiments — `SensitivityAnalysisExperiment`
  and `MonteCarloExperiment` are explicit placeholders; `stress_test.py`/
  `backtest.py` still have no concrete implementation.
- Real agent research logic beyond `market_structure.py`'s illustrative
  example; real per-horizon models (`horizons/*.py` still raise
  `NotImplementedError` in `predict()`).
- Real causal inference — `causal.EconomicRationaleGate` is a real,
  narrow gate, not the structural/causal modeling the brief explicitly
  scoped out of this epoch.
- Four of `AdversarialScientist`'s nine attacks (`Overfitting`,
  `ParameterInstability`, `RegimeDependency`, `OutOfSampleDegradation`) plus
  `RandomCoincidence` — each needs a permutation-test harness or
  multi-regime historical data this scaffold doesn't have yet.
- Three of the five `review.reviewers` (`EconomistReviewer`,
  `HistoricalReviewer`, `PeerValidatorReviewer`) — each needs a
  domain-specific rubric that's a research decision.
- Political and Technical `Event` adapters — no data source for either yet.
- A real graph database, real database backend generally, full schema
  codegen for `api/`/`web/`, orchestration scheduling/retries/distributed
  execution, and API authentication — all as in Epoch I, still deferred
  for the same reasons (see `docs/ARCHITECTURE_AUDIT.md`).

See `docs/EPOCH_II_REPORT.md` for the full gap/technical-debt inventory and
recommendations before Epoch III.
