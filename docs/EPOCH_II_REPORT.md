# Epoch II Report: The Scientific Core

Companion to `docs/EPOCH_II_DESIGN.md` (written before implementation) —
this is the after-the-fact account of what was actually built, what's real
vs. interface-only, and what Epoch III should do first.

## Architecture decisions

1. **Nothing from Epoch I changed meaning.** `ResearchCycle`,
   `KnowledgeStore.promote()`, `Hypothesis`, `DatasetSnapshot`,
   `storage.Repository[T]` all kept their exact contracts. New capability
   was added alongside (`ResearchOrchestrator.run_session()` next to
   `run()`) rather than by mutating existing call sites.
2. **Every new versioned entity reuses `storage.Repository[T]`.** No new
   persistence mechanism was introduced anywhere — `HypothesisRepository`'s
   pattern from Epoch I was copied for `EventRepository`,
   `FeatureCandidateRepository`, `GeneRepository`, `PaperRepository`, and
   the Knowledge Graph's node/edge repositories.
3. **Provenance, not new coupling, is how subsystems connect.**
   `graph.edges_from_provenance()` builds the Knowledge Graph mechanically
   from `Provenance` objects that already exist on every entity, rather
   than each subsystem hand-maintaining graph edges as a second source of
   truth that could drift.
4. **`KnowledgeObject` stays the system of record; `Gene` is a layer on
   top.** Alpha Genome doesn't replace or restructure `KnowledgeObject` —
   it wraps promoted knowledge in an immutable lineage (`parent_gene_ids`/
   `child_gene_ids`), so "genes are immutable, new discoveries create new
   genes" holds without touching Epoch I's promotion gate.
5. **The Review Board and Causal Gate run before promotion, not inside
   it.** `KnowledgeStore.promote()`'s signature is unchanged; new
   production flows are expected to call `ScientificReviewBoard.review()`
   and `EconomicRationaleGate.assess()` first and only promote on approval.
   This keeps existing direct callers/tests of `promote()` working.
6. **Honesty over fabrication for anything statistically hard.** Four of
   `ExperimentFactory`'s experiments are real, deliberately simple
   statistics over the one existing feature
   (`pairwise_return_correlation`) using `scipy.stats` for actual
   significance tests (`ttest_1samp`, `pearsonr`) rather than hand-rolled
   approximations. Sensitivity analysis, Monte Carlo, three of five
   reviewers, and five of nine adversarial attacks raise
   `NotImplementedError` or report `attempted=False` rather than returning
   a plausible-looking fabricated result. This is the same discipline
   Epoch I used for `SignificanceThresholdValidator`/`MarketStructureAgent`.
7. **A "skip, don't fake" convention for batch runners.**
   `ExperimentFactory.run_all()`, `ScientificReviewBoard.review()`, and
   `AdversarialScientist.attack()` all skip components that raise
   `NotImplementedError` rather than treating that as failure — but a
   board or attack run with *zero* working components can never approve
   anything or find a false sense of safety (`ScientificReviewBoard`
   requires at least one report; `AdversarialScientist` still reports all
   nine attack types, marking unimplemented ones explicitly rather than
   omitting them).
8. **Point-in-time correctness extended from dataset to full market
   state.** `market_memory.MarketMemory.reconstruct(as_of)` composes the
   existing `DatasetSnapshot` guarantee with universe/sector state and a
   real (if simple) EGX trading-calendar rule, giving backtesting-style
   code one call that can never see "today."

## Files changed

New Python packages under `research/src/agx_research/`:

| Package | Purpose |
|---|---|
| `orchestration/task_graph.py`, `artifacts.py`, `session.py` | Task Graph, versioned Artifacts, ResearchSession (extends `orchestrator.py`, `__init__.py`) |
| `events/` | Canonical `Event` schema, `EventRepository`, snapshot adapters |
| `market_memory/` | `MarketState`, `MarketMemory`, EGX trading-day rule |
| `features/discovery.py` | `FeatureCandidate`, `FeatureGenerator`, `PairwiseCorrelationGenerator`, `FeatureDiscoveryEngine` |
| `hypotheses/experiment_factory.py` | `ExperimentFactory` + 7 experiment classes |
| `genome/` | `Gene`, `GeneRepository`, `AlphaGenome` service |
| `causal/` | `CausalAssessment` shapes, `EconomicRationaleGate` |
| `graph/` | `NodeType`, `GraphNode`, `GraphEdge`, `KnowledgeGraph`, provenance-driven builder |
| `papers/` | `ResearchPaper`, `PaperRepository`, mechanical generator |
| `review/` | `PromotionCandidate`, reviewers, `ScientificReviewBoard` |
| `adversarial/` | `AttackType`/`AttackResult`, `AdversarialScientist` |

Modified (additive, no contract changes):
`features/correlation.py` (privates made public: `daily_returns`,
`pearson_correlation`, reused by the experiment factory),
`features/__init__.py`, `hypotheses/__init__.py`, `universe/__init__.py`
(+`universe/sector.py`), `orchestration/__init__.py`, `orchestration/orchestrator.py`
(added `run_session()` alongside `run()`), `docs/ARCHITECTURE.md`,
`CLAUDE.md`.

New docs: `docs/EPOCH_II_DESIGN.md`, `docs/EPOCH_II_REPORT.md` (this file).

Untouched, as scoped: `api/`, `web/`, `contracts/` (verified no schema
drift), all Epoch I modules' public contracts.

## Tests added

24 new test files, 108 tests total passing (up from 91 at the end of
Epoch I), `ruff check` clean. Coverage per phase:

- `test_task_graph.py` — dependency ordering, cycle detection, status/timing,
  independent rerun, downstream result passing.
- `test_artifacts.py` — minting vs. versioning the same logical artifact,
  pydantic payload storage.
- `test_events.py` — all four implemented event types derive correctly,
  provenance links to the snapshot, threshold behavior for market events.
- `test_market_memory.py` — real EGX weekend rule, snapshot/universe/sector
  bundling, no-lookahead, determinism.
- `test_feature_discovery.py` — generator finds/skips candidates correctly,
  engine persists via the repository.
- `test_experiment_factory.py` — each real experiment's actual statistics,
  the two placeholders raising `NotImplementedError`, the factory's
  skip-not-implemented behavior, and experiment results storable as
  artifacts.
- `test_alpha_genome.py` — genesis genes, mutation creating a new gene
  while marking the parent `REPLACED` (with history preserved), lineage
  walking, status-transition validation.
- `test_causal_reasoner.py` — all four combinations of
  rationale/candidate-cause presence, confidence capped at 0.5 even when
  passing.
- `test_knowledge_graph.py` — node/edge CRUD, provenance-kind skip
  behavior, and a full walkable chain from a real promoted `KnowledgeObject`
  back to its `Hypothesis`.
- `test_research_paper.py` — every section populated from real evidence,
  graceful behavior with no dataset id/causal assessment/experiments.
- `test_review_board.py` — both concrete reviewers' pass/fail behavior,
  board approval requiring all *run* reviewers to pass, and the critical
  "zero working reviewers never approves" case.
- `test_adversarial_scientist.py` — all nine attack types always reported,
  unimplemented ones marked `attempted=False`, the three real attacks'
  actual trigger conditions, and `apply_adversarial_review`'s confidence
  math including clipping.
- `test_orchestrator.py` (extended) — `run_session()`'s task graph, agent
  versions, and artifact persistence.

Two real bugs were caught by this test suite before being fixed: a missing
`LOOK_AHEAD_BIAS` attack (the test asserting all nine `AttackType`s were
reported caught its absence), and `_attack_weak_economic_rationale`
incorrectly requiring a candidate cause it was never given (inherited from
misusing `EconomicRationaleGate`, decoupled once the test caught the
false-positive).

## Remaining gaps

Named explicitly rather than left implicit:

- **Event Engine adapters** only cover Corporate, Macroeconomic, News, and
  Market events from existing snapshot data. Political and Technical events
  have no data source yet (no political news feed; no computed technical
  indicators — `agents.technical_structure` is still a stub).
- **Feature Discovery** has exactly one generator
  (`PairwiseCorrelationGenerator`). Momentum, volatility, mean-reversion,
  and cross-asset/macro-linked generators don't exist yet.
- **Experiment Factory**: `SensitivityAnalysisExperiment` and
  `MonteCarloExperiment` are placeholder interfaces per the brief.
  `StressTestExperiment` adapts `StressTester`, but no concrete
  `StressTester` exists (Epoch I gap, still open).
- **Causal Engine** is one narrow gate, not causal inference. No
  confounder detection, no alternative-explanation generation — those
  fields on `CausalAssessment` exist but nothing populates them
  automatically yet.
- **Review Board**: only `StatisticianReviewer` and `RiskReviewer` are
  real. `EconomistReviewer`, `HistoricalReviewer`, `PeerValidatorReviewer`
  are `NotImplementedError` — meaning today's board can only ever check
  statistics and risk ceiling, not economic plausibility, historical
  analogs, or independent peer judgment.
- **Adversarial Scientist**: `RandomCoincidence`, `Overfitting`,
  `ParameterInstability`, `RegimeDependency`, `OutOfSampleDegradation` all
  need infrastructure that doesn't exist (permutation testing, multi-model
  comparison, labeled regime history, a live monitoring feed).
- **Knowledge Graph** has no query beyond direct neighbors/edges-between —
  no path-finding, no subgraph extraction, no visualization.
- **Research Paper Generator** produces structured text sections; there is
  no search/indexing over papers yet beyond `PaperRepository.all_latest()`.
- **No end-to-end wiring**: there is no single "run a full day" function
  that chains orchestrator → feature discovery → hypothesis creation →
  experiment factory → causal gate → review board → adversarial scientist
  → genome promotion → paper generation → graph update. Every phase is
  independently real and tested, but integrating them into one daily
  pipeline is Epoch III work (see recommendations).
- **`market_memory`'s trading calendar** only encodes the EGX weekend
  (Friday/Saturday), not public holidays.

## Technical debt

- `ProvenanceRef.kind` is a free string, informally kept in sync with
  `graph.NodeType`'s values by convention, not enforced by the type system.
  A typo in a new `kind=` call site would silently produce no graph edge
  rather than an error. Worth a shared enum or a test asserting the two
  vocabularies stay in sync as more `kind` strings get added.
  `edges_from_provenance()` already documents this and skips unrecognized
  kinds rather than mislabeling, which limits the damage, but doesn't
  eliminate the risk.
- `ExperimentFactory`'s real experiments are all specific to
  `pairwise_return_correlation` (two-ticker correlation). As more features
  exist, these experiment classes will need to generalize beyond "exactly
  two `affected_assets`, treated as a ticker pair" — right now that's
  hardcoded via `_tickers_from_hypothesis()`.
- `FeatureDiscoveryEngine`/`PairwiseCorrelationGenerator`'s pairwise search
  is O(n²) in universe size with no caching; fine at EGX30 scale (30
  choose 2 = 435 pairs), would need attention if the universe grows to
  "all listed Egyptian companies" per the vision document.
- `AlphaGenome.mutate()` assumes single-parent lineage
  (`parent_gene_ids` is a list but only ever populated with one entry).
  Multi-parent mutation (a gene synthesizing evidence from two prior genes)
  isn't supported by `mutate()`'s current signature, even though the
  `Gene` schema itself doesn't prevent multiple parents.
- No dedicated `DatasetSnapshotRepository`/`PredictionRepository` yet, even
  though the storage pattern would support them trivially — they weren't
  needed by anything built this epoch, so weren't added speculatively.

## Recommendations before Epoch III

1. **Build the end-to-end daily pipeline** chaining every phase built this
   epoch (see "No end-to-end wiring" above). This is the highest-leverage
   next step — it's what would surface integration issues between phases
   that unit tests, by design, don't catch.
2. **Add a second `FeatureGenerator`** (momentum or volatility) before
   adding more Event types or Reviewer roles — proving the
   `FeatureGenerator`/`Experiment` abstractions generalize beyond one
   feature is more valuable right now than breadth in adjacent areas.
3. **Implement `EconomistReviewer`** next among the stub reviewers — it's
   the most tractable of the three (checking `economic_explanation`
   substance and cross-referencing sector/macro context that already
   exists in `MarketState`), and closes the biggest gap in the Review
   Board's real coverage.
4. **Decide the multi-parent `Gene` question explicitly** before any
   feature depends on it — either commit to single-parent lineage (simpler,
   matches biological "mutation" framing) or extend `mutate()`/add a
   `merge()` operation now, before callers start working around the
   ambiguity.
5. **Do not build a real causal inference engine, real Monte Carlo
   simulator, or the remaining adversarial attacks speculatively.** Each
   needs either more data (multi-regime history, a monitoring feed) or a
   research decision (which causal framework, which permutation-test
   design) that should be driven by what the end-to-end pipeline in
   recommendation 1 actually needs, not built ahead of that need.
