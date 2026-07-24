# Mission Control

The top-level index into AGX's living status documents, plus the
always-current answers to the questions that matter most. Update the
detail in the file it points to; update the answers below in the same
commit whenever the fact they state changes.

## Status at a glance

- **Merge readiness:** The prior branch (backend/data-acquisition mission)
  passed a full production-readiness audit and merged into `main`. The
  frontend mission that followed also completed and merged — see
  `CHANGELOG.md` for what's landed since.
- **Where the project is:** All 18 charter systems remain architecturally
  complete and tested (17 fully DONE, the 18th DONE for everything
  engineering can close without a cloud/vendor/secrets decision) — see
  `docs/PHASE_STATUS.md`. The project owner has declared the backend,
  research engine, production pipeline, and frontend complete; every
  research conclusion the platform can currently produce is still scoped
  to placeholder/mock data — no live source is connected yet.
- **Current mission:** Solve the Egyptian data **acquisition strategy**
  problem, not just connect one more homepage. See `CURRENT_MISSION.md`
  and `docs/ACQUISITION_STRATEGY.md` for the full capability-by-capability
  legal strategy matrix and what changed as a result. This mission
  followed the Egyptian Live Data Sprint, which replaced the mock-only
  production pipeline with a real `--mode live` default and fixed a
  genuine health-engine bug (see `CURRENT_MISSION.md`'s "Prior mission"
  section) — the platform has run live via GitHub Actions (which has real
  outbound egress, unlike this coding sandbox) multiple times since.
- **Live-run evidence (superseding the older "0 connected, fully blocked"
  framing below):** World Bank is `IMPLEMENTED` and has collected 66 real
  Egypt CPI inflation observations via a live GitHub Actions run. Stooq is
  reachable but blocked by a Cloudflare-style JS challenge; FRED's live
  behavior and the five named Egyptian sources (EGX, CBE, Enterprise,
  Mubasher, Zawya) each fail with a distinct, evidenced, source-side
  reason (network-level reset, WAF rejection, robots.txt disallow, or —
  Zawya — a reachable homepage with no discoverable feed, now addressed
  by this mission's sitemap-fallback fix). Full detail:
  `docs/ACQUISITION_STRATEGY.md`.
- **Progress this mission (frontend, prior phase):** all 9 sections built.
  Frontend audit complete. Six new backend dashboard artifacts (genes,
  papers, hypotheses, knowledge graph, financial statements, source
  reputation) exported to close gaps the 9-section spec needed. Design
  system, primitive component library, and routed application shell built.
  Every section is implemented against real dashboard artifacts, verified
  in a headless browser (dark theme, and light theme for the landing
  page). A handful of sub-sections are honest "not yet available" gaps
  where no backend artifact exists yet (market regime, breadth/liquidity,
  review board history, discovery engine detail, raw logs) — see
  `NEXT_MISSIONS.md` for the full list.
- **Overall completion (backend, unchanged from prior mission):** ~99.5%
  of everything engineering-closeable without a business/vendor decision.
  See `docs/PHASE_STATUS.md`/`docs/ROADMAP.md` for the backend detail.
- **Connected live sources: 1 (World Bank), 4 more evidenced-blocked with
  named reasons, not unbuilt.** Every mechanism needed (discovery,
  verification, ranking, registration, qualification, collection,
  archival, validation, universe membership, corporate-event
  classification, financial-statement collection) is built and tested and
  has now genuinely run live (GitHub Actions has real outbound egress;
  this coding sandbox does not — the two are not the same environment,
  see `CURRENT_MISSION.md`). See `docs/ACQUISITION_STRATEGY.md` for the
  per-capability breakdown of what's blocked and why.
- **Historical coverage:** 66 real Egypt CPI observations (World Bank,
  live). No other source has a real trading-day history yet — every
  collector (including `IndexConstituentCollector`/
  `FinancialStatementCollector`) already fetches a source's full available
  series by construction, so a source's first live run *is* its backfill.
- **Knowledge growth:** 0 real `KnowledgeObject`s promoted from live data
  yet. The full validation → promotion pipeline is proven correct against
  mock data (the production pipeline's daily research cycle produces real
  hypotheses, gates, and — when evidence clears the bar — promotions; it
  now also produces real, if headline-classified, corporate events), but
  every promoted object today traces back to placeholder CSVs or the one
  live macro source, not a licensed EGX price/disclosure feed.
- **Genome growth:** 0 real `Gene`s from live EGX-specific evidence, for
  the same reason — `AlphaGenome` correctly creates genes from mock-data
  knowledge promotions today; nothing yet exists to create one from real
  EGX-specific evidence (World Bank is macro, not EGX-specific).
- **Known blockers:** (1) EGX official, CBE, Enterprise, and Mubasher are
  each blocked by a genuine source-side defensive measure (network-level
  reset, WAF rejection, robots.txt disallow) this program's own rules
  correctly refuse to defeat — not an engineering gap, see
  `docs/ACQUISITION_STRATEGY.md`. (2) No verified, complete EGX30/EGX70
  constituent list exists in this codebase (only a 10-company EGX30
  placeholder, no EGX70 list at all) — a business decision reserved for
  the project owner, since fabricating ~90 ticker/company-name pairs from
  training-data recall would itself violate the platform's
  anti-fabrication principle. (3) A licensed EGX market data vendor has
  not been selected — the standing gate on treating any output as real
  research (`docs/ROADMAP.md`).
- **Estimated remaining work:** Near-zero engineering effort once blocker
  (2) above clears — `agx discover-sources`, `generate_company_ir_targets()`,
  `IndexConstituentCollector`, and `FinancialStatementCollector` are all
  already built to scale automatically. Blocker (1) needs either a
  business/legal resolution per source (not an engineering fix — a WAF or
  robots.txt disallow is not something this program will bypass) or
  reliance on the diversified strategies `docs/ACQUISITION_STRATEGY.md`
  names per capability. System 18's remaining deployment/secrets/
  scheduling work is separately blocked on a hosting/vendor decision.

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
