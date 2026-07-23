# AGX Architecture (Foundation Scaffold)

This describes the current shape of the codebase and how it is intended to
grow. It is a foundation scaffold: interfaces and lifecycle machinery are in
place; most research logic is stubbed pending real data access and model
development.

## Component map

```
research/        Python package `agx_research` — the research engine
  data/           Market data access (DataProvider interface + mock impl)
  knowledge/      KnowledgeObject schema, lifecycle state machine, store
  hypotheses/     Hypothesis + Experiment machinery (the scientific method)
  validation/     Statistical validation / stress test / backtest interfaces
  agents/         Research agents (one responsibility each, propose only)
  horizons/       Per-horizon model interfaces (Micro / Swing / Investment)
  meta/           Meta Decision Engine — combines horizon outputs + knowledge
  explainability/ Explanation object required on every prediction

api/              TypeScript (Fastify) — HTTP surface over the knowledge base
web/              TypeScript (Vite + React) — dashboard for knowledge/recs
```

## Data flow (target state)

1. `data.DataProvider` implementations fetch OHLCV, corporate events, macro
   series, and news for the EGX universe.
2. `agents.*` each consume a slice of that data and produce
   `ResearchFinding` objects — an observation plus a proposed hypothesis.
   Agents never write to the knowledge store.
3. `hypotheses.Hypothesis` wraps a finding and moves it through the
   lifecycle stages defined in `hypotheses.hypothesis.HypothesisStage`.
4. `validation.*` implements the Statistical Validation, Stress Test, and
   Backtest stages. A hypothesis only advances if it passes the stage's
   gate.
5. A hypothesis that survives Peer Validation is promoted into a
   `knowledge.KnowledgeObject` via `knowledge.store.KnowledgeStore`. This is
   the only path by which knowledge is created — there is no direct write
   path from `agents/`.
6. `horizons.*` model interfaces consume promoted knowledge relevant to
   their horizon (Micro/Swing/Investment) and produce per-horizon
   predictions.
7. `meta.decision_engine.MetaDecisionEngine` combines the three horizons'
   predictions with risk assessment and produces a `Recommendation`, which
   must carry an `explainability.Explanation`.
8. `api/` reads knowledge objects and recommendations (currently from a
   JSON-backed store) and exposes them over HTTP; `web/` renders them.

## Why the split between `research/` (Python) and `api/`+`web/` (TypeScript)

The research engine — data science, statistics, modeling — is Python
because that's where the EGX quant/ML ecosystem lives (pandas, statsmodels,
scikit-learn, and later deep learning frameworks). The API and dashboard are
TypeScript so the presentation layer can evolve independently and be
consumed by other tooling without every consumer needing a Python runtime.
`api/` intentionally contains no research logic — it is a thin read layer
over whatever `research/` has published to the knowledge store.

## Boundaries that must hold as this grows

- **Agents propose, never publish.** Enforced today by `ResearchAgent`
  returning `ResearchFinding` (not writing to `KnowledgeStore` directly) —
  see `agents/base.py`.
- **No promotion without passing every validation gate.** Enforced by
  `hypotheses.hypothesis.HypothesisStage` being a strictly ordered
  progression, and `KnowledgeStore.promote()` requiring a hypothesis
  already at `PEER_VALIDATION` stage with a passing result.
- **No horizon leakage.** `horizons/micro_alpha.py`,
  `swing_alpha.py`, and `investment_alpha.py` implement the same
  `HorizonModel` interface but are independent models; only
  `meta/decision_engine.py` is allowed to combine their outputs.
- **No black-box predictions.** `HorizonModel.predict()` and
  `MetaDecisionEngine.decide()` return objects that require an attached
  `Explanation`.

## What is intentionally not built yet

- Real EGX market data ingestion (vendor TBD) — `MockDataProvider` reads
  local CSVs as a stand-in so the rest of the pipeline has something to run
  against.
- Actual statistical tests in `validation/statistical.py`,
  `stress_test.py`, `backtest.py` — these currently define the interface
  and raise `NotImplementedError` where real logic belongs.
- Real agent research logic in `agents/*.py` beyond
  `market_structure.py`'s illustrative example — each is a stub
  implementing `ResearchAgent` with a `TODO`.
- Persistence beyond local JSON/CSV (a real database for the knowledge
  store, time-series store for market data, etc.).
- Authentication/authorization on `api/` — not needed until this is
  exposed beyond local development.
