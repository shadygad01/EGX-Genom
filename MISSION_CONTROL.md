# Mission Control

The top-level index into AGX's living status documents. This file itself
stays short and stable — it points, it doesn't duplicate. Update the file
it points to, not this one, except to add a new pointer.

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
