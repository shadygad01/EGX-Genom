# Epoch II Design: The Scientific Core

Epoch I built a foundation scaffold: interfaces, the knowledge lifecycle,
provenance, versioned repositories, and point-in-time datasets. Epoch II
turns that scaffold into a research operating system — every phase below
extends what exists rather than replacing it. Nothing in `docs/ARCHITECTURE.md`
that Epoch I established changes meaning; this document only adds.

This is a design document written before implementation, per the brief's
"design first" instruction. Depth intentionally varies by phase: some parts
of this epoch (task graphs, event schemas, market memory, feature discovery,
genome lineage) are load-bearing enough to justify real, tested logic today.
Others (full causal inference, Monte Carlo simulation, several adversarial
attacks) are explicitly named in the brief as architecture-only — building
a fake version of these would be worse than an honest `NotImplementedError`,
so they get real interfaces with one or two genuinely-working illustrative
paths, following the exact pattern Epoch I used for
`SignificanceThresholdValidator` and `MarketStructureAgent`.

## Cross-cutting decisions

- **No existing public interface changes meaning.** `ResearchCycle`,
  `KnowledgeStore.promote()`, `Hypothesis`, `DatasetSnapshot`,
  `storage.Repository[T]` keep their exact contracts. Epoch II adds new
  types and new optional entry points around them
  (`ResearchOrchestrator.run_session()` alongside the existing `run()`,
  a Review Board step *before* `promote()` rather than inside it, etc.).
- **Every new versioned entity reuses `storage.Repository[T]`.** No new
  persistence mechanism is introduced anywhere in this epoch.
- **Every new entity that participates in the discovery chain carries
  `Provenance`.** This epoch's Knowledge Graph (Phase 8) is largely a
  *materialization* of provenance that already exists, not a new source of
  truth.
- **Python remains the only place with research logic.** Nothing in this
  epoch touches `api/` or `web/` — the brief is explicit that this phase is
  scientific core only.

## Phase 1 — Research Operating System

- `orchestration/task_graph.py`: `Task` (id, version, dependencies, inputs,
  outputs, artifact ids, `TaskStatus`, timing, `reproducibility` metadata —
  a hash of its inputs) and `TaskGraph` (topological execution, independent
  rerun of any single task given its recorded inputs).
- `orchestration/artifacts.py`: `Artifact` — a versioned, provenance-carrying
  wrapper (kind, id, version, payload reference, producing task id) around
  anything a task produces (`DatasetSnapshot`, `FeatureMatrix`,
  `CorrelationMatrix`, `ExperimentResult`, `ValidationReport`,
  `KnowledgePublication`, `RecommendationReport`) plus `ArtifactRepository`.
- `orchestration/session.py`: `ResearchSession` — owns one immutable
  `DatasetSnapshot`, one `TaskGraph`, the `Artifact`s produced, the
  `ResearchFinding`s, `Hypothesis`es, promoted knowledge, and
  recommendations for one trading day. Sessions are replayable: nothing in
  a session may read data outside its snapshot.
- `orchestration/orchestrator.py` gains `run_session()`, building a session
  around a small default task graph (build snapshot → run agents → done),
  additive to the existing `run()` (which still returns a bare
  `ResearchCycle` for anything that only needs findings).

## Phase 2 — Event Engine

- `events/event.py`: canonical `Event` (id, `EventType`, entities, timestamp,
  source, confidence, severity, `relationships` — links to other event ids
  — metadata) covering Corporate / Macro / Political / Market / Technical /
  News event types.
- `events/repository.py`: `EventRepository` (versioned, same pattern as
  every other store).
- `events/adapters.py`: `derive_events_from_snapshot()` converts a
  `DatasetSnapshot`'s raw `CorporateEvent`/`NewsItem`/`MacroObservation`
  records into canonical `Event`s. This is the seam: existing
  `DatasetSnapshot` fields are untouched (agents built in Epoch I still
  work unmodified), but the stated end-state — "no downstream component
  consumes raw news directly" — is satisfied by routing new consumption
  through `Event`s. Migrating `MarketStructureAgent` itself to consume
  events is listed as a gap (see report) since it currently only needs
  price bars, which have no event equivalent yet.

## Phase 3 — Market Memory

- `market_memory/state.py`: `MarketState` — the full reconstructable state
  for one day: `DatasetSnapshot` + universe constituents (from
  `UniverseProvider.constituents(as_of)`) + sector classification.
- `market_memory/memory.py`: `MarketMemory.reconstruct(as_of)` is the single
  sanctioned way to get historical state; it is what backtesting-style
  experiments (Phase 5) are required to call instead of touching
  `DataProvider` or "today" in any form.
- This phase deliberately doesn't invent a new point-in-time mechanism —
  `DatasetSnapshot` already guarantees no data after `as_of` by
  construction (Epoch I). Market Memory composes that guarantee with
  universe/sector state into one queryable historical reconstruction.

## Phase 4 — Feature Discovery Engine

- `features/discovery.py`: `FeatureCandidate` (id, definition, expression,
  dependencies, creator, discovery date, evidence, importance, lifecycle
  status, version, retirement info) and `FeatureGenerator` (ABC:
  `generate(market_state) -> list[FeatureCandidate]`), with
  `PairwiseCorrelationGenerator` as the one concrete, working generator —
  it enumerates ticker pairs in the universe and proposes a candidate for
  each pair whose |correlation| clears a threshold, using the existing
  `pairwise_return_correlation` feature rather than new math.
  `FeatureDiscoveryEngine` runs every registered generator and records
  candidates via `FeatureRegistry`/a new `FeatureCandidateRepository`.
  This is the existing static registry (Epoch I) turned autonomous: instead
  of a human calling `compute_pairwise_return_correlation` for one hardcoded
  pair, the engine searches the whole universe.

## Phase 5 — Experiment Factory

- `hypotheses/experiment_factory.py`: `ExperimentFactory.generate(hypothesis)
  -> list[Experiment]` returns instances of seven `Experiment`
  implementations (all satisfying the existing `Experiment` ABC — no
  interface change):
  - `CrossValidationExperiment` — real: k-fold split of the snapshot's
    price history, reusing `pairwise_return_correlation`.
  - `BootstrapExperiment` — real: resamples daily returns with replacement
    to build a confidence interval on the correlation statistic.
  - `WalkForwardExperiment` — real: rolling-window re-evaluation of the
    same statistic across sequential sub-windows of the snapshot.
  - `OutOfSampleExperiment` — real: splits the snapshot's window in two and
    checks the statistic's sign/magnitude holds on the held-out half.
  - `StressTestExperiment` — thin adapter running a supplied `StressTester`
    (Epoch I interface) and repackaging its result as an `ExperimentResult`.
  - `SensitivityAnalysisExperiment` — interface + `NotImplementedError`:
    needs a defined parameter space per hypothesis type, which is a
    research decision, not scaffolding.
  - `MonteCarloExperiment` — explicitly a placeholder interface per the
    brief; raises `NotImplementedError`.
- Every `ExperimentResult` produced this way is wrapped as an `Artifact`
  (Phase 1), giving experiments identity and version as artifacts, per the
  brief's "experiments become versioned artifacts."

## Phase 6 — Alpha Genome

- `genome/gene.py`: `Gene` — immutable, versioned, with `parent_gene_ids`,
  `child_gene_ids`, `mutation_notes`, `evidence`, `performance_history`,
  `GeneStatus` (PROPOSED, PROMOTED, MONITORING, RETIRED, REPLACED),
  `knowledge_id` (the `KnowledgeObject` it wraps — Epoch I's
  `KnowledgeStore`/`KnowledgeObject` are untouched and still the system of
  record for the promotion gate; `Gene` is the evolutionary lineage layer on
  top).
- `genome/repository.py`: `GeneRepository`.
- `genome/service.py`: `promote_to_gene(knowledge)` creates generation-0
  genes; `mutate(parent_gene, new_knowledge, mutation_notes)` creates a new
  gene referencing its parent — the previous gene is never overwritten,
  only ever superseded (`GeneStatus.REPLACED`) with a `child_gene_ids` link
  forward.

## Phase 7 — Causal Engine

- `causal/assessment.py`: `CandidateCause`, `Confounder`,
  `AlternativeExplanation`, `CausalAssessment` (bundles all of the above +
  confidence + economic rationale).
- `causal/reasoner.py`: `CausalReasoner` ABC (`assess(hypothesis) ->
  CausalAssessment`); one concrete, real gate —
  `EconomicRationaleGate` — which is not causal inference but *is* a real,
  enforceable check: it rejects (returns a `CausalAssessment` with
  `confidence=0.0` and a note) any hypothesis whose promotion would rely on
  correlation alone (no economic rationale text, no candidate cause). This
  operationalizes "correlation alone must never be enough" as an actual
  gate rather than a slogan, without pretending to do causal inference.

## Phase 8 — Knowledge Graph

- `graph/nodes.py` / `graph/edges.py`: `GraphNode` (typed: Company, Sector,
  Market, Event, Hypothesis, Experiment, Feature, Gene, ResearchPaper,
  Prediction, Recommendation) and `GraphEdge` (versioned, like every other
  entity).
- `graph/knowledge_graph.py`: `KnowledgeGraph` — add/query nodes and edges,
  backed by two `Repository[T]`s (nodes, edges), consistent with the rest
  of the system.
- `graph/builder.py`: `edges_from_provenance()` mechanically turns any
  entity's `Provenance.inputs` into `GraphEdge`s — the graph is largely a
  *view* over provenance that Epoch I already produces, not a new,
  separately-maintained source of truth (avoiding the classic bug of a
  graph that drifts from the data it's supposed to represent).

## Phase 9 — Research Paper Generator

- `papers/paper.py`: `ResearchPaper` with the ten required sections as
  typed fields (not free-form markdown), `PaperRepository`.
- `papers/generator.py`: `generate_paper(gene, hypothesis, experiments,
  causal_assessment)` mechanically assembles every section from the actual
  evidence objects already produced upstream — no free-text generation
  divorced from data; every sentence traces to a field on an input object.

## Phase 10 — Scientific Review Board

- `review/reviewer.py`: `ReviewerRole` enum, `ReviewFinding`/`ReviewReport`,
  `Reviewer` ABC.
- `review/reviewers.py`: `StatisticianReviewer` (real: checks
  `StatisticalEvidence`/experiment results against significance and sample
  size thresholds), `RiskReviewer` (real: checks `expected_risk` against a
  configurable ceiling), `EconomistReviewer`, `HistoricalReviewer`,
  `PeerValidatorReviewer` (interfaces + `NotImplementedError` — each needs
  a domain-specific rubric that's a research decision).
- `review/board.py`: `ScientificReviewBoard.review(...) -> BoardDecision`
  requires every registered reviewer to pass. This runs *before*
  `KnowledgeStore.promote()` in the intended production flow — it does not
  change `promote()`'s signature, so existing direct callers/tests are
  unaffected; new code should call the board first and only promote on
  `BoardDecision.approved`.

## Phase 11 — Adversarial Scientist

- `adversarial/attacks.py`: `AttackType` enum covering all nine attacks
  named in the brief, `AttackResult`.
- `adversarial/scientist.py`: `AdversarialScientist.attack(hypothesis,
  experiments, snapshot) -> list[AttackResult]`. Real, mechanical attacks:
  `SmallSampleBias` (sample size threshold), `TimeLeakage`/`LookAheadBias`
  (any referenced date after the snapshot's `as_of`), `WeakEconomicRationale`
  (delegates to the Phase 7 gate). `Overfitting`, `ParameterInstability`,
  `RegimeDependency`, `OutOfSampleDegradation`, `RandomCoincidence` are real
  interfaces raising `NotImplementedError` — each needs either a
  permutation-test harness or multi-regime historical data this scaffold
  doesn't have yet. `apply_adversarial_review(confidence, attack_results)`
  is real and tested: successful attacks reduce confidence, failed attacks
  (mechanically, ones that ran and didn't find a problem) strengthen it.

## What this design deliberately does not do

- Does not implement real statistical inference for cross-validation,
  bootstrap, walk-forward, etc. beyond the simplest correct version of
  each over the one existing feature (`pairwise_return_correlation`).
  Extending these to arbitrary features/models is future work once more
  features exist.
- Does not implement a real graph database, causal inference engine, or
  Monte Carlo simulator — all three are explicitly named in the brief as
  interface-only for this epoch.
- Does not change any Epoch I public contract.
