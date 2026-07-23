# AGX — Project Alpha Genome

An autonomous quantitative research platform dedicated exclusively to the
Egyptian Stock Exchange (EGX), focused on EGX30. AGX behaves as a research
organization, not a signal generator: every discovered relationship is
proposed by a research agent, validated statistically, stress-tested,
backtested, peer-validated, and only then promoted into knowledge that can
inform a recommendation — each with a full explanation.

See [`docs/VISION.md`](docs/VISION.md) for the full mission and immutable
principles, and [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) for how the
codebase implements them. [`CLAUDE.md`](CLAUDE.md) has working notes for
anyone (human or agent) developing here.

**Status:** foundation scaffold. Interfaces, the knowledge lifecycle, and
project structure are in place; real data ingestion, statistical validation,
and modeling are stubs to be built out.

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
