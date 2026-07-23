# agx_research

Python research engine for AGX. See the repository root
[`README.md`](../README.md), [`CLAUDE.md`](../CLAUDE.md),
[`docs/ARCHITECTURE.md`](../docs/ARCHITECTURE.md), and
[`docs/PHASE_STATUS.md`](../docs/PHASE_STATUS.md) (the strict-order phase
audit against `MASTER_PROMPT.md`) for context.

## Setup

```bash
uv sync
uv run pytest
```

## Package layout

- `agx_research.config` — the stable `Horizon` enum only.
- `agx_research.domain` — cross-cutting primitives: `new_id()`, `Provenance`/`ProvenanceRef`.
- `agx_research.storage` — generic, versioned `Repository[T]` / `JsonFileRepository[T]`.
- `agx_research.universe` — `UniverseProvider`/`SectorProvider` interfaces + placeholder data.
- `agx_research.data` — `DataProvider` interface, `MockDataProvider`,
  `FallbackDataProvider` (multi-source composition), `DatasetSnapshot` +
  `DatasetSnapshotRepository`, `quality` (mechanical OHLCV sanity checks),
  and `adjustments` (split/dividend-adjusted returns — used by every
  correlation/experiment calculation instead of raw closes).
- `agx_research.features` — versioned `FeatureDefinition` registry plus
  `discovery` (`FeatureCandidate`/`FeatureGenerator`/`FeatureDiscoveryEngine`,
  autonomous search rather than hand-picked features).
- `agx_research.knowledge` — `KnowledgeObject` schema, lifecycle, store.
- `agx_research.hypotheses` — `Hypothesis`, its configurable gate `pipeline`,
  `HypothesisRepository`, and `experiment_factory` (7 experiment types).
- `agx_research.validation` — statistical validation (incl. `StatisticalEvidence`)
  / stress test / backtest interfaces.
- `agx_research.agents` — research agents (propose findings from a
  `DatasetSnapshot`, never publish knowledge).
- `agx_research.events` — the Event Platform: canonical `Event` schema,
  subtype taxonomy + impact-horizon ontology, entity resolution,
  fingerprint-based identity, dedup/conflict resolution, lifecycle,
  `EventPlatform` (the sole write path), snapshot adapters, and Knowledge
  Graph projection.
- `agx_research.market_memory` — `MarketState` + `MarketMemory`, the
  sanctioned way to reconstruct any historical day.
- `agx_research.genome` — `Gene` (immutable lineage) + `AlphaGenome` service.
- `agx_research.causal` — `CausalAssessment` shapes + `EconomicRationaleGate`.
- `agx_research.graph` — `KnowledgeGraph` (nodes/edges) +
  `edges_from_provenance()`.
- `agx_research.papers` — `ResearchPaper` schema + mechanical generator.
- `agx_research.review` — `PromotionCandidate`, reviewers, `ScientificReviewBoard`.
- `agx_research.adversarial` — `AdversarialScientist`, 9 named attack types.
- `agx_research.horizons` — Micro / Swing / Investment model interfaces.
- `agx_research.meta` — Meta Decision Engine.
- `agx_research.explainability` — `Explanation` object required on every
  prediction/recommendation.
- `agx_research.orchestration` — `TaskGraph`, `Artifact`/`ArtifactRepository`,
  `ResearchSession` + `ResearchOrchestrator`, and `DailyResearchPipeline`
  (the end-to-end 8-gate research chain).
- `agx_research.runtime` — `RuntimeEngine`: date-range execution with
  per-day failure isolation and a persistent run ledger.
- `agx_research.portfolio` — cross-ticker `PortfolioConstructor`.
- `agx_research.learning` — `ContinuousLearningMonitor`: realized
  performance recording + mechanical retirement.
- `agx_research.infrastructure` — integrity-checked backup/verify/restore.
- `agx_research.cli` — `python -m agx_research.cli run|status|backup|restore`.

## Regenerating the API contract

`api/` and `web/` mirror `KnowledgeObject` by hand in TypeScript. After
changing that schema, regenerate the checked-in JSON Schema and update both
mirrors to match:

```bash
uv run python scripts/export_schemas.py
```

CI fails if `contracts/` doesn't match what this produces.
