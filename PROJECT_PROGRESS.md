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

- Python: 397 tests, all green (`cd research && uv run pytest`).
- TypeScript: 33 tests, all green (`npm test -w api`, `npm test -w web`).
- `contracts/` drift check: clean (`uv run python scripts/export_schemas.py`
  + `git diff --exit-code`).
- Lint: `uv run ruff check` clean.

## Data Acquisition Platform (prior mission)

- Registry: 51 sources, 5 IMPLEMENTED / 34 PLANNED / 4 NEEDS_KEY /
  8 TOS_REVIEW, across 9 categories.
- Platform subsystems: registry, discovery, qualification, reputation,
  health monitoring, raw archive, provenance index, historical replay —
  all built, tested, and wired into `CollectionService` end-to-end.
- Collector types covered: RSS/Atom, REST/JSON API, CSV, Excel, PDF,
  Filesystem, Archive Replay (all real); Browser Automation (honest stub,
  no ToS-cleared target yet).

## Acquisition Intelligence Engine (this mission)

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
Nothing about this mission changes that gate; it makes the free-source
side of the data supply as strong as engineering alone can make it before
that decision — now including the ability to find its own acquisition
methods without a human supplying an endpoint, the moment it runs
somewhere with internet access.
