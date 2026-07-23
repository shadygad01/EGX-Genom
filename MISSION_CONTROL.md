# Mission Control

The top-level index into AGX's living status documents, plus the
always-current answers to the questions that matter most. Update the
detail in the file it points to; update the answers below in the same
commit whenever the fact they state changes.

## Status at a glance

- **Where the project is:** All 18 charter systems are architecturally
  complete and tested (17 fully DONE, the 18th DONE for everything
  engineering can close without a cloud/vendor/secrets decision). A real
  production execution pipeline runs the full chain end to end
  (`agx run`); the Acquisition Intelligence Engine can discover, verify,
  rank, and register a live source for the entire business-value priority
  catalog; a real Universe Engine, a real corporate-event classifier
  (closing TD-24), and now real Financial Statement Collection
  infrastructure (`financials.*` + `collectors.financial_statements.
  FinancialStatementCollector`) are all built and tested — the last of
  these closes the data-source half of `agents.financial_performance.
  FinancialPerformanceAgent`'s long-standing honest stub. Every research
  conclusion the platform can currently produce is still scoped to
  placeholder/mock data — no live source is connected yet.
- **Current mission:** Engineering ownership handoff — close every
  remaining engineering-closeable gap toward real Egyptian market data, in
  business-priority order: EGX official → Universe Engine → Investor
  Relations discovery → Corporate disclosures → Financial statement
  collection → Historical backfill → Live incremental sync → CBE/FRA/
  CAPMAS/Enterprise/Mubasher/Zawya/Reuters/Trading Economics → anything
  else discovered. See `CURRENT_MISSION.md`.
- **Next mission:** Priorities 1 through 7 are now all engineering-complete
  (blocked only where named below); the remaining engineering-closeable
  work — richer PDF-based extraction (corporate disclosures and financial
  statements alike) once a real filing layout can be inspected, and
  calibration passes once real data exists — is queued but itself gated on
  the same two blockers clearing first. See `NEXT_MISSIONS.md` for the
  full list and what runs automatically the moment either clears.
- **Overall completion:** ~99.5% of everything engineering-closeable
  without a business/vendor decision. The remaining fraction is
  exclusively: (a) writing a concrete collector once a source resolves
  live (`IndexConstituentCollector`/`FinancialStatementCollector` are
  already built and waiting), (b) a source-verified PDF extraction stage
  once a real filing layout exists (deliberately not attempted
  speculatively — TD-32), and (c) System 18's deployment/secrets/
  scheduling wiring, blocked on a hosting/vendor decision.
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
