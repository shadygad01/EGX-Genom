# Mission Control

The top-level index into AGX's living status documents, plus the
always-current answers to the questions that matter most. Update the
detail in the file it points to; update the answers below in the same
commit whenever the fact they state changes.

## Status at a glance

- **Merge readiness:** The prior branch (backend/data-acquisition mission)
  passed a full production-readiness audit and merged into `main`. This
  branch has since restarted from `main` for the frontend mission below —
  see `CHANGELOG.md` for what's landed since.
- **Where the project is:** All 18 charter systems remain architecturally
  complete and tested (17 fully DONE, the 18th DONE for everything
  engineering can close without a cloud/vendor/secrets decision) — see
  `docs/PHASE_STATUS.md`. The project owner has declared the backend,
  research engine, and production pipeline complete and paused further
  backend work; every research conclusion the platform can currently
  produce is still scoped to placeholder/mock data — no live source is
  connected yet (unchanged from the prior mission).
- **Current mission:** Complete Production User Experience rebuild — a
  routed, 9-section institutional research platform (AI Briefing,
  Opportunity Center, Company Research Workspace, Market Intelligence,
  Research Center, Knowledge Graph, Mission Control, Source Intelligence,
  System Administration), consuming existing dashboard artifacts only, no
  frontend-side calculation. See `CURRENT_MISSION.md`.
- **Progress this mission:** Frontend audit complete. Six new backend
  dashboard artifacts (genes, papers, hypotheses, knowledge graph,
  financial statements, source reputation) exported to close gaps the
  9-section spec needed. Design system, primitive component library, and
  routed application shell built. AI Briefing (the landing page) fully
  built and verified in both themes. Remaining 8 sections are honest
  "under construction" placeholders. See `NEXT_MISSIONS.md` for the
  section-by-section build order.
- **Overall completion (backend, unchanged from prior mission):** ~99.5%
  of everything engineering-closeable without a business/vendor decision.
  See `docs/PHASE_STATUS.md`/`docs/ROADMAP.md` for the backend detail —
  paused, not abandoned, during this frontend phase.
- **Connected live sources: 0** — blocked, not unbuilt. Every mechanism
  needed (discovery, verification, ranking, registration, qualification,
  collection, archival, validation, universe membership, corporate-event
  classification, financial-statement collection) is built and tested;
  zero are connected because this sandbox has no outbound network egress
  to arbitrary hosts (confirmed directly and repeatedly across four
  missions).
- **Historical coverage:** 0 real trading days from any live source (same
  blocker — no source has ever been reachable to backfill from). No
  separate backfill mechanism is needed or exists; every collector
  (including `IndexConstituentCollector`/`FinancialStatementCollector`)
  already fetches a source's full available series by construction, so a
  source's first live run *is* its backfill.
- **Knowledge growth:** 0 real `KnowledgeObject`s promoted from live data.
  The full validation → promotion pipeline is proven correct against mock
  data (the production pipeline's daily research cycle produces real
  hypotheses, gates, and — when evidence clears the bar — promotions;
  it now also produces real, if headline-classified, corporate events),
  but every promoted object today traces back to placeholder CSVs, not a
  licensed or verified live feed.
- **Genome growth:** 0 real `Gene`s from live evidence, for the same
  reason — `AlphaGenome` correctly creates genes from mock-data knowledge
  promotions today; nothing yet exists to create one from real EGX
  evidence.
- **Known blockers:** (1) No outbound network egress from this development
  sandbox — an external/environmental dependency, not an engineering gap.
  (2) No verified, complete EGX30/EGX70 constituent list exists in this
  codebase (only a 10-company EGX30 placeholder, no EGX70 list at all) —
  a business decision reserved for the project owner, since fabricating
  ~90 ticker/company-name pairs from training-data recall would itself
  violate the platform's anti-fabrication principle. (3) A licensed EGX
  market data vendor has not been selected — the standing gate on treating
  any output as real research (`docs/ROADMAP.md`).
- **Estimated remaining work:** Near-zero engineering effort once either
  blocker (1) or (2) above clears — `agx discover-sources`,
  `generate_company_ir_targets()`, `IndexConstituentCollector`, and
  `FinancialStatementCollector` are all already built to scale
  automatically. From there, each newly-resolved source needs one concrete
  collector (small, per-source, following the existing `Collector`
  pattern) before it's `IMPLEMENTED`. System 18's remaining deployment/
  secrets/scheduling work is separately blocked on a hosting/vendor
  decision.

## Where to look

| Question | Document |
|---|---|
| What is AGX, and what are its immutable principles? | `docs/VISION.md` |
| What's the operating charter (role, 18-system build order)? | `MASTER_PROMPT.md` |
| How is the codebase laid out, and why? | `docs/ARCHITECTURE.md` (+ `docs/ARCHITECTURE_AUDIT.md`, `docs/EPOCH_II_DESIGN.md`/`EPOCH_II_REPORT.md` for the "why") |
| What is currently being worked on? | `CURRENT_MISSION.md` |
| What's next, in order? | `NEXT_MISSIONS.md` |
| Where does each of the 18 charter systems stand? | `docs/PHASE_STATUS.md` |
| What's the latest snapshot of progress against the whole charter? | `PROJECT_PROGRESS.md` |
| What did the most recently finished body of work actually deliver? | `COMPLETION_REPORT.md` |
| What's on the roadmap, and what's business- vs. engineering-blocked? | `docs/ROADMAP.md` |
| What known debts exist, and what would trigger repaying them? | `docs/TECHNICAL_DEBT.md` |
| What load-bearing decisions were made, and why? | `docs/ARCHITECTURE_DECISIONS.md` |
| What risks are being tracked? | `docs/RISK_REGISTER.md` |
| What changed, release by release? | `CHANGELOG.md` |
| How does the Data Acquisition Platform work? | `docs/DATA_ACQUISITION.md` |
| How does the production pipeline (`agx run`) work end to end? | `docs/PHASE_STATUS.md`'s "Production Execution Pipeline" section + `docs/ARCHITECTURE.md`'s `production/` entry |
| What did the last `agx run` actually do? | `<dashboard-out>/execution_report.json` + `mission_status.json` (generated per run, not checked into the repo) |

## Standing invariant

Per `MASTER_PROMPT.md`'s charter, a later system's work does not start
while an earlier one still has closeable (non-business-blocked) gaps.
`docs/PHASE_STATUS.md` is the check before starting anything new.

## Update discipline

Every one of these documents is meant to be updated *as part of* the work
that changes its answer, in the same commit — not as a follow-up task.
`CURRENT_MISSION.md`/`NEXT_MISSIONS.md`/`PROJECT_PROGRESS.md`/
`COMPLETION_REPORT.md` are the fast-moving ones; `docs/PHASE_STATUS.md`,
`docs/ROADMAP.md`, `docs/TECHNICAL_DEBT.md`, `docs/RISK_REGISTER.md`, and
`docs/ARCHITECTURE_DECISIONS.md` change less often but are still touched
whenever the relevant fact changes, not on a schedule.
