# AGX — Project Alpha Genome

An autonomous quantitative research platform dedicated exclusively to the
Egyptian Stock Exchange (EGX), focused on EGX30 and EGX70. AGX behaves as a research
organization, not a signal generator: every discovered relationship is
proposed by a research agent, validated statistically, stress-tested,
backtested, peer-validated, and only then promoted into knowledge that can
inform a recommendation — each with a full explanation.

See [`docs/VISION.md`](docs/VISION.md) for the full mission and immutable
principles, and [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) for how the
codebase implements them. [`CLAUDE.md`](CLAUDE.md) has working notes for
anyone (human or agent) developing here. [`MISSION_CONTROL.md`](MISSION_CONTROL.md)
indexes every living status document (current work, roadmap, phase status,
technical debt, risks).

**Status:** all 18 charter systems architecturally complete and tested
except the business-blocked remainder of production infrastructure — see
[`docs/PHASE_STATUS.md`](docs/PHASE_STATUS.md) for the per-system audit.
`agx run` executes the complete production pipeline end to end — data
acquisition through a promotable recommendation and dashboard artifacts —
in one command (see `docs/PHASE_STATUS.md`'s "Production Execution
Pipeline" section), currently against mock/replayed data (a real
free-source Data Acquisition Platform exists, see
[`docs/DATA_ACQUISITION.md`](docs/DATA_ACQUISITION.md), but no live
collector is wired in yet — the current mission, see
[`CURRENT_MISSION.md`](CURRENT_MISSION.md)). A licensed EGX vendor remains
the single gating decision before any output is real research.

## Layout

- `research/` — Python research engine (`agx_research`): data access,
  knowledge base, hypothesis/experiment lifecycle, validation, agents,
  per-horizon models, and the Meta Decision Engine.
- `api/` — TypeScript (Fastify) HTTP layer over the knowledge base.
- `web/` — TypeScript (Vite + React) dashboard.
- `docs/` — vision and architecture documentation.

## Getting started

### Research engine (Python)

```bash
cd research
uv sync
uv run pytest
```

### API (TypeScript)

```bash
npm install
npm run dev -w api
```

### Web dashboard (TypeScript)

```bash
npm install
npm run dev -w web
```

### Personalized decisions (Decision Center)

`decision_service.DecisionService` turns promoted knowledge plus your own
portfolio holdings into a six-way Buy / Increase Position / Hold / Reduce
Position / Exit / No Action decision per ticker — target weight, thesis,
key risks, contradicting evidence, active catalysts, monitoring status, and
an expected review date. It's deliberately stateless-per-call and never
autonomous (a real portfolio's holdings can't be discovered, only supplied
by you), so it's reachable two ways:

- **CLI, always available**: `agx decide --date <ISO date> [--positions positions.json]`
  against any `--data-dir` a real `agx run` was pointed at.
- **Web (Decision Center, `/decisions`), only with a live `api/`**: set
  `DECISION_DATA_DIR` to that same `--data-dir` before starting `api/`
  (`DECISION_DATA_DIR=research/data/your-run-dir npm run dev -w api`). The
  static GitHub Pages build has no backend to compute this against, so
  Decision Center honestly reports itself unavailable there rather than
  fabricating a result — use the CLI, or self-host `api/`, instead.
  For a persistent self-hosted deployment (e.g. a private VPS) rather than
  a local `npm run dev`, see [`deploy/README.md`](deploy/README.md).
