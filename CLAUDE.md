# AGX — Alpha Genome (EGX Research Platform)

This file orients any Claude session working in this repository. It is not
the vision document itself — that lives in `docs/VISION.md` verbatim — but a
practical guide to how the codebase is organized and what invariants to
protect when touching it.

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
  Do not add a shortcut that lets an agent write directly into "promoted"
  knowledge.
- **Agents propose, they never decide.** `agents/` produces `ResearchFinding`
  objects. Only the validation + promotion pipeline may turn a finding into
  a `KnowledgeObject`, and only the Meta Decision Engine may turn knowledge
  into a recommendation.
- **Everything is versioned and explainable.** Knowledge objects, features,
  models, datasets, and predictions all carry an ID, a version, and enough
  evidence to answer "why this, why now, why not something else, what
  invalidates it."

## Current state (foundation scaffold)

This is an early scaffold, not a working research pipeline. Statistical
validation, backtesting, and the individual research agents are stubs with
clear interfaces and `NotImplementedError`/TODO markers — they define the
contract future sessions implement against. Do not read the presence of a
file as evidence the underlying research logic exists yet.

Layout:

- `docs/` — vision document and architecture notes.
- `research/` — Python package (`agx_research`) containing the actual
  research engine: data provider interfaces, the knowledge base schema and
  lifecycle, hypothesis/experiment machinery, per-horizon model interfaces,
  the Meta Decision Engine, and the agent base classes.
- `api/` — TypeScript (Fastify) service exposing the knowledge base and
  recommendations over HTTP. Currently reads a JSON knowledge store; has no
  business logic of its own by design (logic lives in `research/`).
- `web/` — TypeScript (Vite + React) dashboard, currently a minimal viewer
  for knowledge objects returned by `api/`.

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
- The EGX30 constituent list in `config.py` is a placeholder snapshot, not
  a live feed. Do not treat it as authoritative market data.
- The market data provider (`agx_research.data.provider.DataProvider`) is
  implemented today only by `MockDataProvider`, which reads local CSVs
  under `research/data/mock/`. A real EGX vendor integration is future work
  — do not hardcode assumptions about a specific vendor's API shape into
  code outside `data/`.

## What NOT to do

- Do not let an agent write to the "promoted" knowledge store directly.
- Do not implement a "black box" model with no explanation object attached
  — every prediction needs an `Explanation` (see `explainability/`).
- Do not treat this scaffold's stub statistical validators as real
  validation — they intentionally raise/return placeholders until real
  statistical tests are implemented.
