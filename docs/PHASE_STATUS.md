# Phase Status Audit — Against MASTER_PROMPT.md's 18-System Architecture

`MASTER_PROMPT.md` establishes a strict rule: build the 18 named systems in
order, never starting a later one before the earlier one's Definition of
Done (DoD) is met. No DoD was specified per system, so defining one for
each — precisely, and honestly — is the first job under this charter. This
document is that definition, plus a truthful mapping of what Epoch I and
Epoch II actually built against it.

**This mapping surfaces a real process problem, stated plainly rather than
hidden:** Epoch I and Epoch II were executed under an earlier, less strict
charter and built real, tested pieces of systems 02 through 12 *before*
this strict gate existed — system 01 itself wasn't even fully closed out
(real data-quality checks and corporate-action price adjustment, both part
of 02's DoD below, didn't exist until this session). Under
`MASTER_PROMPT.md`'s rule, that ordering was wrong. The work itself is not
being discarded — it's real, tested, and valuable — but from this point
forward, the gate is enforced: no new work starts on a system whose
predecessors aren't DONE, and this document is updated every time a
system's status changes.

Status legend: **DONE** (DoD fully met) / **PARTIAL** (real, tested work
exists; DoD not fully met — gaps listed) / **NOT STARTED**.

## 01 — Foundation

**DoD:** stable domain primitives (time horizons, identifiers), a generic
versioned-repository abstraction reused by every store, a provenance model
reused by every entity in the discovery chain, and a working test/CI setup
for both the Python engine and the TypeScript surface.

**Status: DONE.**

- `config.py` (Horizon), `domain/` (`new_id`, `Provenance`/`ProvenanceRef`),
  `storage/` (`Repository[T]`/`JsonFileRepository[T]`).
- Reused, without modification, by every store added in Epoch II
  (`EventRepository`, `FeatureCandidateRepository`, `GeneRepository`,
  `PaperRepository`, the Knowledge Graph's node/edge repositories) — the
  strongest evidence this abstraction actually holds up.
- CI (`.github/workflows/ci.yml`) runs `pytest`/`ruff` for `research/` and
  build/test for `api/`/`web/`, plus a schema-drift check against
  `contracts/`.

## 02 — Data Platform

**DoD:** a `DataProvider` interface with a working reference implementation;
an immutable, content-hashed, point-in-time `DatasetSnapshot`; a mechanical
data-quality validation layer (structurally impossible OHLCV data must be
caught, not silently fed into statistics); corporate-action price
adjustment (splits/dividends must not corrupt return calculations); a
versioned repository for snapshots; and an explicit seam for combining
multiple data sources. Real, licensed EGX vendor integration is **excluded**
from this DoD — which vendor to license is a business decision
(cost, coverage, contract terms), not an engineering one, and is flagged
below for the user rather than decided unilaterally.

**Status: now DONE** (was PARTIAL entering this session — see "Closed this
session" below).

- `data/provider.py` (`DataProvider` ABC), `data/mock_provider.py`
  (`MockDataProvider`), `data/snapshot.py` (`DatasetSnapshot`,
  `build_snapshot()`) — from Epoch I.
- `universe/` (`UniverseProvider`, `SectorProvider` + static placeholders)
  — from Epoch II, reasonably attributed to this phase in hindsight (it's
  reference/classification data, not event or research-cycle logic).

**Closed this session** (see "Files changed" below for the concrete list):
- `data/quality.py` — mechanical OHLCV/date/volume sanity checks.
- `data/adjustments.py` — real split/dividend-adjusted close computation
  (standard backward-adjustment convention), now wired into
  `features.correlation` and `hypotheses.experiment_factory` so every
  return calculation in the system uses adjusted prices.
- `data/snapshot_repository.py` — `DatasetSnapshotRepository`.
- `data/composite_provider.py` — `FallbackDataProvider` (ordered
  multi-source composition).

**Explicitly deferred, flagged for the user, not an engineering decision:**
which real EGX data vendor to license (e.g. Refinitiv, Mubasher, an EGX
official feed) — cost, coverage, and licensing terms determine this, and
it's a business call. `FallbackDataProvider` is the seam a real vendor
integration drops into once that decision is made.

## 03 — Event Platform

**DoD:** a canonical, versioned `Event` schema covering the named event
categories, with adapters deriving real events from the data platform
(not fabricated), and a versioned repository.

**Status: PARTIAL** (built in Epoch II, ahead of strict order; not
touched this session since 02 was this session's gate).

- `events/` — `Event`/`EventType`/`EventSeverity`, `EventRepository`,
  adapters for Corporate, Macroeconomic, News, and Market events derived
  from real `DatasetSnapshot` data.
- **Gap:** Political and Technical event adapters have no data source yet
  (no political news feed; no computed technical indicators).

## 04 — Market Memory

**DoD:** a single sanctioned way to reconstruct any historical day's full
state (prices, macro, news, corporate events, universe/sector composition,
trading-calendar status) with no path for reading "today" by mistake.

**Status: PARTIAL** (built in Epoch II, ahead of strict order).

- `market_memory/` — `MarketState`, `MarketMemory.reconstruct(as_of)`,
  a real (if simple) EGX trading-week rule.
- **Gap:** no public-holiday calendar (weekend-only trading-day logic).

## 05 — Knowledge Graph

**DoD:** versioned node/edge storage, and a mechanism that keeps the graph
from becoming a second, driftable source of truth.

**Status: PARTIAL** (built in Epoch II, ahead of strict order).

- `graph/` — `NodeType`/`GraphNode`/`GraphEdge`, `KnowledgeGraph`,
  `edges_from_provenance()` (mechanically derives edges from `Provenance`).
- **Gap:** no path-finding/subgraph queries beyond direct neighbors; no
  visualization.

## 06 — Alpha Genome

**DoD:** an immutable knowledge-lineage layer — genes are never overwritten,
mutation always forks and marks the parent superseded, and lineage is
walkable end to end.

**Status: PARTIAL** (built in Epoch II, ahead of strict order).

- `genome/` — `Gene`, `GeneRepository`, `AlphaGenome` (`promote_to_gene`,
  `mutate`, `lineage`, status transitions).
- **Gap:** `mutate()` only supports single-parent lineage; no `merge()` for
  a gene synthesizing evidence from multiple prior genes.

## 07 — Research Operating System

**DoD:** every trading day is a first-class, replayable session owning its
dataset snapshot, an explicit task execution graph, and every artifact
produced.

**Status: PARTIAL** (built in Epoch II, ahead of strict order).

- `orchestration/` — `TaskGraph`, `Artifact`/`ArtifactRepository`,
  `ResearchSession`, `ResearchOrchestrator.run_session()`.
- **Gap:** no end-to-end wiring chaining every phase (04 through 12) into
  one daily run — each phase is independently real and tested, but nothing
  yet runs them all together for one trading day.

## 08 — Scientist Framework

**DoD:** every named research responsibility (market structure, macro,
corporate events, financial performance, news, liquidity, technical
structure, historical patterns) has an agent producing evidence-carrying
findings, plus the Adversarial Scientist attacking those findings' eventual
promotion.

**Status: PARTIAL.**

- `agents/` — one real implementation (`MarketStructureAgent`); seven
  named-responsibility stubs (Epoch I).
- `adversarial/` — `AdversarialScientist`, 4 of 9 attacks real
  (`SmallSampleBias`, `TimeLeakage`, `LookAheadBias`,
  `WeakEconomicRationale`); 5 need infrastructure that doesn't exist yet
  (permutation testing, multi-regime historical data).
- **Gap:** 7 of 8 agents are stubs; this is the least-built phase relative
  to its DoD and should be prioritized once 03–06 close.

## 09 — Feature Discovery

**DoD:** features are searched for autonomously across the universe, not
hand-picked one at a time, with each candidate versioned and evidenced.

**Status: PARTIAL** (built in Epoch II, ahead of strict order).

- `features/discovery.py` — `FeatureCandidate`, `FeatureGenerator`,
  `PairwiseCorrelationGenerator`, `FeatureDiscoveryEngine`.
- **Gap:** exactly one generator exists (pairwise correlation); no
  momentum, volatility, or macro-linked generators.

## 10 — Experiment Factory

**DoD:** every hypothesis automatically generates every applicable
experiment type, each a versioned artifact.

**Status: PARTIAL** (built in Epoch II, ahead of strict order).

- `hypotheses/experiment_factory.py` — 7 experiment classes; 4 real
  (cross-validation, bootstrap, walk-forward, out-of-sample, all
  `scipy`-backed), `StressTestExperiment` adapts an interface with no
  concrete implementation yet, 2 explicit placeholders
  (sensitivity analysis, Monte Carlo).
- **Gap:** all four real experiments are hardcoded to exactly two
  `affected_assets` treated as a correlation pair — will need to
  generalize once Feature Discovery produces more feature types.

## 11 — Validation Framework

**DoD:** the hypothesis lifecycle's statistical/stress/backtest gates are
real, auditable, and reject weak evidence rather than rubber-stamping it.

**Status: PARTIAL** (Epoch I + II).

- `validation/` — `SignificanceThresholdValidator` (real),
  `StatisticalEvidence` (structured, not a bare float);
  `StressTester`/`Backtester` interfaces with no concrete implementation.
- **Gap:** no concrete stress tester or backtester exists at all — this is
  arguably the biggest open gap in the whole platform, since Principle 2
  ("no pattern enters production before statistical validation") is only
  half-enforced without it.

## 12 — Review Board

**DoD:** no discovery is promoted automatically; every configured reviewer
produces structured evidence; approval requires every reviewer that ran to
pass, and zero working reviewers must never approve anything.

**Status: PARTIAL** (built in Epoch II, ahead of strict order).

- `review/` — `PromotionCandidate`, `StatisticianReviewer`/`RiskReviewer`
  (real), 3 stub reviewers (Economist/Historical/PeerValidator),
  `ScientificReviewBoard`.
- `causal/` — `EconomicRationaleGate`, a real, narrow gate (not causal
  inference) rejecting correlation-only promotion candidates.
- **Gap:** the board isn't wired into any promotion call site yet
  (`KnowledgeStore.promote()` still callable directly, by design, from
  Epoch I call sites) — nothing *enforces* the board runs first at the
  code level today.

## 13 — Runtime Engine

**DoD:** a scheduled, production-grade execution of the daily research
cycle — retries, monitoring, alerting, failure isolation between tasks.

**Status: NOT STARTED.** `orchestration.TaskGraph` (07) provides the
execution primitive this would be built on, but no scheduler, retry logic,
or production runtime exists.

## 14 — Prediction Intelligence

**DoD:** real, trained per-horizon models producing genuine predictions.

**Status: PARTIAL, essentially interface-only.** `horizons/` (Epoch I) —
`HorizonModel`/`Prediction` with `model_id`/`model_version`, all three
concrete classes (`MicroAlphaModel`/`SwingAlphaModel`/`InvestmentAlphaModel`)
raise `NotImplementedError` in `predict()`. No model has ever been trained.

## 15 — Portfolio Intelligence

**DoD:** position sizing, risk budgeting, and portfolio-level construction
across multiple simultaneous recommendations.

**Status: NOT STARTED.** `meta.MetaDecisionEngine` (Epoch I) combines
per-ticker, per-horizon predictions into a single-ticker recommendation —
there is no cross-ticker portfolio view at all.

## 16 — Explainability Engine

**DoD:** every recommendation answers all six explainability questions the
vision document specifies, backed by structured evidence references, not
prose alone.

**Status: PARTIAL.** `explainability/` (Epoch I) — `Explanation` with
`evidence_refs`; used by `MetaDecisionEngine`. **Gap:** `similar_historical_cases`
is never populated by anything (Market Memory (04) and the Knowledge Graph
(05) both exist and could support this — an obvious next integration once
Prediction Intelligence produces real predictions to explain).

## 17 — Continuous Learning

**DoD:** promoted knowledge is re-evaluated on an ongoing basis; weak
knowledge is automatically retired; the platform's aggregate predictive
performance is tracked over time.

**Status: NOT STARTED**, beyond the manual `transition_status()`/
`record_performance()` calls `KnowledgeStore` and `AlphaGenome` expose
(Epoch I/II) — nothing calls them on a schedule or automatically decides
"this knowledge has degraded, retire it."

## 18 — Production Infrastructure

**DoD:** deployment, monitoring, secrets management, authentication,
backup/restore for the knowledge/gene/event stores.

**Status: NOT STARTED**, and correctly so — building this before
anything upstream is real would be pure waste.

## Immediate next step

Per the strict-order rule, system **03 (Event Platform)** is next: it's
the earliest PARTIAL system, and its gaps (Political/Technical event
adapters) are both blocked on data sources that don't exist yet, not
engineering work that can proceed today — meaning **04 (Market Memory)**
is next in practice as the earliest phase with closeable, engineering-only
gaps, once 03 is confirmed to have no other closeable gap. This will be
reassessed at the start of the next session rather than decided
speculatively here.
