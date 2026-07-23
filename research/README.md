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

- `agx_research.config` — horizons, EGX30 universe placeholder.
- `agx_research.data` — `DataProvider` interface and `MockDataProvider`.
- `agx_research.knowledge` — `KnowledgeObject` schema, lifecycle, store.
- `agx_research.hypotheses` — `Hypothesis` and `Experiment` machinery.
- `agx_research.validation` — statistical validation / stress test /
  backtest interfaces (stubs).
- `agx_research.agents` — research agents (propose findings, never publish
  knowledge).
- `agx_research.horizons` — Micro / Swing / Investment model interfaces.
- `agx_research.meta` — Meta Decision Engine.
- `agx_research.explainability` — `Explanation` object required on every
  prediction/recommendation.
