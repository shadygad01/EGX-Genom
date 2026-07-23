# agx_research

Python research engine for AGX. See the repository root
[`README.md`](../README.md), [`CLAUDE.md`](../CLAUDE.md), and
[`docs/ARCHITECTURE.md`](../docs/ARCHITECTURE.md) for context.

## Setup

```bash
uv sync
uv run pytest
```

## Package layout

- `agx_research.config` — the stable `Horizon` enum only.
- `agx_research.domain` — cross-cutting primitives: `new_id()`, `Provenance`/`ProvenanceRef`.
- `agx_research.storage` — generic, versioned `Repository[T]` / `JsonFileRepository[T]`.
- `agx_research.universe` — `UniverseProvider` interface + placeholder EGX30 snapshot.
- `agx_research.data` — `DataProvider` interface, `MockDataProvider`, and
  `DatasetSnapshot` (point-in-time, content-hashed data bundles).
- `agx_research.features` — versioned `FeatureDefinition` registry.
- `agx_research.knowledge` — `KnowledgeObject` schema, lifecycle, store.
- `agx_research.hypotheses` — `Hypothesis`, its configurable gate `pipeline`,
  `Experiment` machinery, and `HypothesisRepository`.
- `agx_research.validation` — statistical validation (incl. `StatisticalEvidence`)
  / stress test / backtest interfaces.
- `agx_research.agents` — research agents (propose findings from a
  `DatasetSnapshot`, never publish knowledge).
- `agx_research.horizons` — Micro / Swing / Investment model interfaces.
- `agx_research.meta` — Meta Decision Engine.
- `agx_research.explainability` — `Explanation` object required on every
  prediction/recommendation.
- `agx_research.orchestration` — `ResearchCycle` + `ResearchOrchestrator`,
  the first-class "one trading day's research run."

## Regenerating the API contract

`api/` and `web/` mirror `KnowledgeObject` by hand in TypeScript. After
changing that schema, regenerate the checked-in JSON Schema and update both
mirrors to match:

```bash
uv run python scripts/export_schemas.py
```

CI fails if `contracts/` doesn't match what this produces.
