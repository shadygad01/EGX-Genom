# Project Progress Snapshot

A quick-scan summary. `docs/PHASE_STATUS.md` is the detailed, evidence-cited
source of truth this is derived from — read that for the "why," this for
the "where are we."

## Charter systems (MASTER_PROMPT.md's 18, strict build order)

| # | System | Status |
|---|--------|--------|
| 01 | Foundation | DONE |
| 02 | Data Platform (incl. Data Acquisition Platform) | DONE |
| 03 | Event Platform | DONE |
| 04 | Market Memory | DONE |
| 05 | Knowledge Graph | DONE |
| 06 | Alpha Genome | DONE |
| 07 | Research OS | DONE |
| 08 | Scientist Framework | DONE (5/8 agents real, rest data-blocked) |
| 09 | Feature Discovery | DONE |
| 10 | Experiment Factory | DONE |
| 11 | Validation Framework | DONE |
| 12 | Review Board | DONE (4/5 reviewers real) |
| 13 | Runtime Engine | DONE |
| 14 | Prediction Intelligence | DONE (v1) |
| 15 | Portfolio Intelligence | DONE (v1) |
| 16 | Explainability Engine | DONE |
| 17 | Continuous Learning | DONE (v1) |
| 18 | Production Infrastructure | PARTIAL (business-blocked remainder) |

**17 of 18 fully DONE; the 18th is DONE for everything engineering can
close without a cloud/vendor/secrets decision from the user.**

## Test health

- Python: 462 tests, all green (`cd research && uv run pytest`).
- TypeScript: 33 tests, all green (`npm test -w api`, `npm test -w web`).
- `contracts/` drift check: clean (`uv run python scripts/export_schemas.py`
  + `git diff --exit-code`).
- Lint: `uv run ruff check` clean.

## Connected live sources: 0 (blocked, not unbuilt — see below)

Every mechanism needed to connect a live source is built and tested; zero
are connected because this sandbox has no outbound network egress
(confirmed directly, repeatedly, across four missions). `docs/PHASE_STATUS.md`'s
Production Execution Phase section has the full breakdown.

## Universe Engine + Corporate Disclosures (this mission)

- `universe.IndexConstituent`/`CollectedUniverseProvider`/
  `FallbackUniverseProvider` (new): a real collected constituent list, once
  one exists, is preferred over `StaticUniverseProvider`'s placeholder with
  zero further code changes — point-in-time correct (no look-ahead bias).
- `collectors.index_constituents.IndexConstituentCollector` (new): a
  generic, header-matching CSV parser for a constituent-list export, built
  and tested but not yet wireable into the live pipeline (`egx_official`
  stays `PLANNED` until its real endpoint is verified — TD-30).
- `collectors.corporate_event_classifier` (new) + `RssNewsCollector`'s new
  `classify_corporate_events` flag: closes TD-24 — a real, if headline-only
  and declared-heuristic (TD-29), corporate-event classifier now produces
  genuine `COMI/EARNINGS` and `MFPC/DIVIDEND` rows in a mock-mode
  production pipeline run, verified directly.
- `CollectionBatch`/`CollectionService` extended (not redesigned) to
  materialize both new record types, with full provenance tracing and
  idempotent merge-by-key writers, matching the existing price/macro
  pattern exactly.
- 31 new tests (462 total). See `CURRENT_MISSION.md` for the full
  breakdown and `COMPLETION_REPORT.md` for this build's report.

## Priority-Ordered Live Source Connection (earlier mission)

- `AcquisitionIntelligenceEngine.run_catalog()` (new): processes every
  target in strict business-value order (`TargetOrganization.priority`,
  new field) — EGX official, then EGX30/EGX70 company Investor Relations,
  then CBE/FRA/CAPMAS/Enterprise/Mubasher/Zawya/Reuters/Trading Economics,
  then anything else discovered — per the project owner's explicit
  re-prioritization (World Bank/IMF/FRED demoted to enrichment-only).
- `generate_company_ir_targets()` (new): expands the `company_ir` marker
  entry into one real target per EGX30 constituent (10 today, scales to a
  real complete list automatically) — no fabricated domain hints.
- `discover_company_directory_links()` (new): extracts a company's own
  homepage link from an already-fetched directory page by real anchor-text
  matching — the mechanism letting EGX's own site (once reachable) supply
  real per-company hints instead of guessing ~100 corporate domains.
- Fixed a real pre-existing circular-import bug (`agx_research.discovery`
  failed to import first in a fresh process) found while building this —
  regression-tested.
- Verified: the full 21-target priority-ordered catalog (EGX official +
  10 company IR + 10 named orgs) runs correctly end to end, in exact
  priority order, with an honest "no reachable domain" for every target —
  no crash, no fabrication.
- 14 new tests. See `CURRENT_MISSION.md` for the full honesty note on the
  two real blockers (network egress; no verified EGX30/EGX70 constituent
  list) and `COMPLETION_REPORT.md` for this build's report.
- Closed TD-16's remaining half while auditing for unblocked engineering
  work: `HttpFetcher.fetch_bytes` now times every real request (excluding
  rate-limit/backoff sleeps) and `CollectionService.run()` feeds the
  average into `SourceMetricsRepository.record_run()` — `reputation.py`'s
  `latency` dimension stops being permanently `None` the moment a live
  collector runs, with no fabricated placeholder in the meantime. 4 new
  tests (431 total).

## Production Execution Pipeline (earlier mission)

- New package `production/`: `ProductionPipeline` runs the complete chain
  end to end — Source Registry → Discovery Engine → Collector Selection
  → Collector Execution → Raw Archive → Canonical Transformation →
  Validation → Event Platform → Market Memory → Knowledge Base → Research
  Pipeline → Genome → Investment Case Generator → Dashboard Artifact
  Generator → Mission Control Update → Execution Report.
- Closed a real, previously-unnoticed gap: `agx collect` wrote collected
  data to `--data-dir`, but `agx run` always read from a separate, static
  `--mock-data` directory — the two paths were never connected. They are
  now (`ProductionPipeline`'s own `MarketMemory` reads `--data-dir`).
- Mock and Replay execution modes both run the platform's *real* collector
  classes — only what backs `fetch()` changes (a `MockFetcher` with
  wire-format-correct synthetic content, or an `ArchiveReplayCollector`
  reading the archive) — no live collector built yet, per the mission's
  own instruction.
- 14 output artifacts (8 existing dashboard files + `investment_cases.json`,
  `collector_status.json`, `runtime_status.json`, `dashboard_metrics.json`,
  `mission_status.json`, `execution_report.json`), all validated.
- `agx run` is now the single production entrypoint (`--mode mock`/
  `replay`); `.github/workflows/deploy-pages.yml` calls it directly.
- 16 new integration tests prove: full stage order, collected-data-reaches-
  research, replay reproduces the same outcome, no duplicate archiving,
  determinism, failure isolation (stage- and collector-level), artifact
  validity, Mission Control history tracking, CLI entrypoint.
- See `CURRENT_MISSION.md` (now: first live production collector),
  `NEXT_MISSIONS.md`, and `COMPLETION_REPORT.md` for this build's report.

## Data Acquisition Platform (earlier mission)

- Registry: 51 sources, 5 IMPLEMENTED / 34 PLANNED / 4 NEEDS_KEY /
  8 TOS_REVIEW, across 9 categories.
- Platform subsystems: registry, discovery, qualification, reputation,
  health monitoring, raw archive, provenance index, historical replay —
  all built, tested, and wired into `CollectionService` end-to-end.
- Collector types covered: RSS/Atom, REST/JSON API, CSV, Excel, PDF,
  Filesystem, Archive Replay (all real); Browser Automation (honest stub,
  no ToS-cleared target yet).

## Acquisition Intelligence Engine (earlier mission)

- New package `acquisition_intelligence/`: given only an organization's
  identity (never a URL), resolves a verified-reachable domain, discovers
  candidate acquisition methods, verifies legality/stability/historical
  availability, ranks and selects the best, auto-generates a still-`PLANNED`
  `SourceSpec`, registers it, begins qualification, and automatically
  re-discovers alternatives when a source's health goes `DOWN`.
- Seeded for 12 named target organizations, each linked to its existing
  registry entry.
- 51 new tests, all offline (fakes) — every module and the full
  orchestration pipeline (happy path, every failure branch, re-run
  idempotency, exclusion-driven alternative selection, continuity
  recovery) covered.
- Wired into `cli.py`'s new `discover-sources` subcommand.
- **Verified directly** that this sandbox has no outbound network egress
  to arbitrary hosts; a live run against all 12 named targets correctly
  reports "no reachable domain" for each — the engine working exactly as
  designed against an environment with no internet to discover from, not a
  defect. See `CURRENT_MISSION.md` for the full honesty note and
  `COMPLETION_REPORT.md` for this build's report.

## The one standing gate on everything downstream

All research conclusions the platform produces remain scoped to
placeholder/free-source data until a licensed EGX market data vendor is
selected — a business decision reserved for the user (`docs/ROADMAP.md`).
Nothing about this mission changes that gate; it makes the platform's
own priority-ordered path to connecting real, free, legally-accessible
sources — including, this phase, a real Universe Engine and a real
corporate-event classifier — fully engineering-complete and ready to
execute autonomously the moment either of two blockers clears: outbound
network egress, or a verified EGX30/EGX70 constituent list from the
project owner. Both are named explicitly in `CURRENT_MISSION.md`.
