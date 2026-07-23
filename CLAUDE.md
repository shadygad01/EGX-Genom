# AGX — Alpha Genome (EGX Research Platform)

This file orients any Claude session working in this repository. It is not
the vision document itself — that lives in `docs/VISION.md` verbatim — but a
practical guide to how the codebase is organized and what invariants to
protect when touching it. `docs/ARCHITECTURE.md` describes the current
design in more detail; `docs/ARCHITECTURE_AUDIT.md` explains *why* it's
shaped this way (a full audit against the vision, done deliberately early
while the codebase was still cheap to restructure).

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
  This is implemented as a configurable gate pipeline
  (`hypotheses/pipeline.py`), not a hardcoded sequence — but whatever
  pipeline a hypothesis uses, gates still cannot be skipped or reordered at
  runtime. Do not add a shortcut that lets an agent write directly into
  "promoted" knowledge.
- **Agents propose, they never decide.** `agents/` produces `ResearchFinding`
  objects from a `DatasetSnapshot`. Only the validation + promotion
  pipeline may turn a finding (via a `Hypothesis`) into a `KnowledgeObject`,
  and only the Meta Decision Engine may turn knowledge into a
  recommendation. `KnowledgeStore.promote()` depends on a structural
  `PromotableEvidence` protocol rather than importing `Hypothesis`
  directly — preserve that decoupling rather than reaching for the
  concrete class.
- **Everything is versioned and explainable.** Knowledge objects,
  hypotheses, features, models, datasets, and predictions all carry an ID,
  a version, and a `Provenance` linking back to whatever produced them
  (see `domain/provenance.py`). Every store composes
  `storage.JsonFileRepository` rather than hand-rolling persistence — reuse
  it for any new versioned entity instead of writing a new JSON
  read/write loop.

## Current state (foundation scaffold)

This is an early scaffold, not a working research pipeline. Statistical
validation, backtesting, and the individual research agents are stubs with
clear interfaces and `NotImplementedError`/TODO markers — they define the
contract future sessions implement against. Do not read the presence of a
file as evidence the underlying research logic exists yet.

Layout:

- `docs/` — vision, architecture, and the architecture audit.
- `research/` — Python package (`agx_research`) containing the research
  engine. See `docs/ARCHITECTURE.md`'s component map for the full
  subpackage breakdown (`domain/`, `storage/`, `universe/`, `data/`,
  `features/`, `knowledge/`, `hypotheses/`, `validation/`, `agents/`,
  `horizons/`, `meta/`, `explainability/`, `orchestration/`).
- `api/` — TypeScript (Fastify) service exposing the knowledge base over
  HTTP. Currently reads a JSON knowledge store; has no business logic of
  its own by design (logic lives in `research/`).
- `web/` — TypeScript (Vite + React) dashboard, currently a minimal viewer
  for knowledge objects returned by `api/`.
- `contracts/` — JSON Schema generated from the pydantic models `api/`
  serves, regenerated via `research/scripts/export_schemas.py`. CI fails if
  this drifts from the schema; `api/src/types.ts` and `web/src/types.ts`
  are hand-maintained TS mirrors that must be updated alongside it.

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
- Universe membership (EGX30 constituents) is a placeholder snapshot behind
  `universe.StaticUniverseProvider`, not a live feed. Do not treat it as
  authoritative market data; a real feed should be a new
  `UniverseProvider` implementation, not a change to `config.py` (which
  intentionally holds only the stable `Horizon` enum).
- The market data provider (`agx_research.data.provider.DataProvider`) is
  implemented today only by `MockDataProvider`, which reads local CSVs
  under `research/data/mock/`. A real EGX vendor integration is future work
  — do not hardcode assumptions about a specific vendor's API shape into
  code outside `data/`.
- Agents, experiments, and validators consume a `DatasetSnapshot`
  (`data/snapshot.py`), never a live `DataProvider` directly — this is what
  makes findings/experiments reproducible and prevents look-ahead bias.
  Don't reintroduce direct `DataProvider` calls in those layers.
- New versioned entities (predictions, dataset registries, whatever comes
  next) should get a thin repository composing
  `storage.JsonFileRepository`, following the pattern in
  `knowledge/store.py` and `hypotheses/repository.py` — not a new bespoke
  persistence mechanism.

## What NOT to do

- Do not let an agent write to the "promoted" knowledge store directly.
- Do not implement a "black box" model with no explanation object attached
  — every prediction needs an `Explanation` (see `explainability/`), and
  every persisted entity in the discovery chain needs a `Provenance`.
- Do not treat this scaffold's stub statistical validators as real
  validation — they intentionally raise/return placeholders until real
  statistical tests are implemented.
- Do not hardcode a new validation gate into `Hypothesis` or its stage
  logic — add or reorder `GateSpec`s in a pipeline instead.
