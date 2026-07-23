# Completion Report — First Production Execution Pipeline

## Mission

Stop building architecture and generic frameworks; wire every completed
system into the first production execution pipeline, proving AGX can run
an end-to-end production research cycle. The pipeline must represent the
exact execution path a live deployment (GitHub Actions, Cloudflare) will
later run unchanged — collectors stay mock/replay for now, by explicit
instruction; only the data source changes later.

## Delivered

New package `research/src/agx_research/production/`:

| Module | Delivers |
|---|---|
| `collector_plan.py` | `ExecutionMode` (mock/replay), `MockFetcher` (drop-in for `HttpFetcher.fetch_text`, canned wire-format content), `build_collector_plan()` — selects and constructs real `Collector`s (`StooqPriceCollector`, `FredCsvCollector`, `RssNewsCollector`, `WorldBankCollector`) backed by mock content or `ArchiveReplayCollector`. |
| `stages.py` | `StageName` (the mission's 17 stages, in order), `StageStatus` (succeeded/partial/failed/skipped), `StageResult`. |
| `report.py` | `ExecutionReport`, `derive_overall_status()`, `PipelineExecutionRepository` (versioned execution history). |
| `mission_control.py` | `MissionControlStatus` + `build_mission_control_status()` — derived entirely from `ExecutionReport` history. |
| `artifacts.py` | `export_investment_cases()` (composes `RecommendationService` + `PortfolioConstructor`, previously never wired together), `export_collector_status()`, `export_runtime_status()`, `export_dashboard_metrics()`. |
| `pipeline.py` | `ProductionPipeline` — the orchestrator; every stage isolated, every stage's result recorded. |

## The gap this closed

`agx collect` materialized data into `--data-dir`; `agx run` always read
from a separate, static `--mock-data` directory. Nothing connected the
two — collected data was invisible to research, silently, in the existing
codebase. `ProductionPipeline` builds its own `MarketMemory` pointed at
`--data-dir`, so what Collector Execution writes is what Research Pipeline
reads. Verified directly: a fresh run's Stooq/FRED/RSS/World Bank mock
collectors write `prices/COMI.csv`, `macro/BRENT_USD.csv`, `news.csv` into
`--data-dir`, and the same run's Research Pipeline stage produces a real
hypothesis from exactly that data (not from `research/data/mock/`).

## Verification

- 413 Python tests (up from 397), 16 new (`test_production_pipeline.py`),
  all offline. Covers: every one of the 17 stages runs in the mission's
  exact order; collected data reaches the research pipeline; replay mode
  reproduces the identical research outcome as the original mock run; the
  raw archive doesn't duplicate documents between a mock run and a
  following replay; replay against an empty archive is honest (reports 0
  documents, doesn't fabricate); deterministic execution (same inputs
  produce byte-identical collected CSVs and identical hypothesis counts
  across two independent pipeline instances); failure isolation at both
  the stage level (a monkeypatched failing stage doesn't stop later
  stages) and the collector level (one broken collector among several
  degrades to `PARTIAL`, not total failure); every one of the 14 output
  artifacts is written and validates against its schema; Mission Control
  correctly tracks execution history (`total_executions`, last successful/
  failed) across repeated runs; the CLI `run` command works end to end.
- `contracts/` unchanged (no pydantic schema drift this phase);
  `ruff check` clean; 33 TypeScript tests unaffected; both TS packages
  build clean.
- `.github/workflows/deploy-pages.yml` updated to call the single `run`
  command and verified locally to reproduce the exact same sequence
  (`run` → `validate-dashboard`) the workflow now performs.

## What did not change, deliberately

- No live collector was built — the mission explicitly deferred that to
  the next one. `collector_plan.py`'s `MockFetcher`/`ArchiveReplayCollector`
  seam is designed so adding one later touches only that module.
- `DailyResearchPipeline`, `RuntimeEngine`, `CollectionService`,
  `RecommendationService`, `PortfolioConstructor`, and
  `write_dashboard_artifacts` are all called exactly as they already
  existed — zero lines changed in any of them. The only supporting change
  outside `production/` was extending `dashboard/validate.py` to
  optionally validate the six new artifacts, and deleting `cli.build_engine()`
  (dead code once `run` was repurposed — its only caller).
- `cli.py`'s `export-dashboard`/`collect`/`status`/`discover-sources`
  subcommands are untouched and still work exactly as before, for
  lower-level/manual use.

## Follow-through

`CURRENT_MISSION.md` is now set to **implement the first live production
collector** — World Bank recommended as the first candidate (already
`IMPLEMENTED`, tested, a stable free no-key API), per the stop condition's
explicit instruction. See `NEXT_MISSIONS.md` for the full prioritized list.
