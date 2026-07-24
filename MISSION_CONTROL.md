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
- **Current mission: first real Egyptian market data flowing live —
  succeeded.** `enterprise_press` is now `IMPLEMENTED`/`TRUSTED`, collecting
  real news from `https://enterpriseam.com/egypt/feed/` (found via standard
  RSS autodiscovery on its own homepage, never guessed). A live GitHub
  Actions run confirmed: 6 real news items parsed, 6 real events registered
  in the Event Platform, `data_quality_score=0.97`. `corporate_disclosures`,
  `corporate_actions`, and `news` capabilities all report `succeeded=True`
  in `acquisition_decisions.json`. Getting here surfaced and fixed three
  real bugs — an unhandled crash on non-ASCII URLs, an unbounded robots.txt
  fetch that hung a run for 90+ minutes, and an unbounded sitemap-candidate
  count that caused a second ~70-minute hang — plus a fourth correctness
  bug where discovery silently regressed an `IMPLEMENTED` source back to
  `PLANNED` on every subsequent run. Full detail: `CURRENT_MISSION.md` and
  `docs/ACQUISITION_STRATEGY.md`'s "First Live Egyptian Source" section.
  This followed the capability-driven runtime engine mission (every data
  requirement is an independent `Capability` with a ranked strategy pool,
  `acquisition_intelligence.capability`/`capability_engine`), which itself
  followed the acquisition-strategy analysis and Egyptian Live Data Sprint
  missions — the platform has run live via GitHub Actions (which has real
  outbound egress, unlike this coding sandbox) many times since.
- **Live-run evidence:** World Bank is `IMPLEMENTED` and has collected 66
  real Egypt CPI inflation observations (macro, not EGX-specific).
  `enterprise_press` is `IMPLEMENTED` and collecting real EGX news/events
  (see above — the first genuinely EGX-specific live source). Stooq is
  reachable but blocked by a Cloudflare-style JS challenge (confirmed at
  its real CSV endpoint, not just its homepage); FRED's live behavior
  varies (sometimes succeeds, sometimes times out); the four remaining
  named Egyptian sources (EGX, CBE, Mubasher, Zawya) each fail with a
  distinct, evidenced, source-side reason (network-level reset, WAF
  rejection, robots.txt disallow, or — Zawya — a real, parseable sitemap
  whose entries are all HTML article pages, not a legally-clearable feed).
  Full detail: `docs/ACQUISITION_STRATEGY.md`.
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
- **Connected live sources: 2 (World Bank, Enterprise), 4 more
  evidenced-blocked with named reasons, not unbuilt.** Every mechanism
  needed (discovery, verification, ranking, registration, qualification,
  collection, archival, validation, universe membership, corporate-event
  classification, financial-statement collection) is built and tested and
  has now genuinely run live (GitHub Actions has real outbound egress;
  this coding sandbox does not — the two are not the same environment,
  see `CURRENT_MISSION.md`). See `docs/ACQUISITION_STRATEGY.md` for the
  per-capability breakdown of what's blocked and why.
- **Historical coverage:** 66 real Egypt CPI observations (World Bank,
  live) plus 6 real Enterprise news items/events (live, EGX-specific) as
  of the most recent run. Every collector (including
  `IndexConstituentCollector`/`FinancialStatementCollector`) already
  fetches a source's full available series by construction, so a source's
  first live run *is* its backfill.
- **Knowledge growth:** 0 real `KnowledgeObject`s promoted from live data
  yet — the run that first collected Enterprise's real events landed on a
  non-trading day, so the research pipeline correctly produced zero
  hypotheses that run (an honest calendar gap, not a strategy failure);
  the registered events persist and feed the next trading-day run. The
  full validation → promotion pipeline is proven correct against mock
  data (the production pipeline's daily research cycle produces real
  hypotheses, gates, and — when evidence clears the bar — promotions).
- **Genome growth:** 0 real `Gene`s from live EGX-specific evidence yet,
  for the same non-trading-day reason above — `AlphaGenome` correctly
  creates genes from mock-data knowledge promotions today; the first real
  EGX-specific evidence (Enterprise's events) is now registered and
  waiting on the next trading-day run to potentially produce one.
- **Known blockers:** (1) EGX official, CBE, and Mubasher are each blocked
  by a genuine source-side defensive measure (network-level reset, WAF
  rejection, robots.txt disallow) this program's own rules correctly
  refuse to defeat — not an engineering gap; Zawya's sitemap is real and
  parseable but every entry is an HTML article page, not a legally-
  clearable feed — see `docs/ACQUISITION_STRATEGY.md`. (2) No verified,
  complete EGX30/EGX70 constituent list exists in this codebase (only a
  10-company EGX30 placeholder, no EGX70 list at all) — a business
  decision reserved for the project owner, since fabricating ~90
  ticker/company-name pairs from training-data recall would itself
  violate the platform's anti-fabrication principle. (3) A licensed EGX
  market data vendor has not been selected — the standing gate on
  treating any output as real research (`docs/ROADMAP.md`).
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
