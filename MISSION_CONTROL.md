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
  research engine, production pipeline, and frontend complete. Three real
  live sources are connected and collecting (World Bank, Enterprise, FRA
  — see below); every *research conclusion* the platform produces is
  still scoped to mock data pending the promotion pipeline's first real
  trading-day run, and no output is claimed as real research until a
  licensed EGX price vendor exists (`docs/ROADMAP.md`).
- **Current mission: acquisition freeze partially lifted — EGX30+EGX70
  Financial Source Registry (TD-38, TD-39).** The project owner asked for
  large-scale EGX30/EGX70 company source discovery, exactly what the
  standing freeze (below) deferred pending a new named business input —
  scoped narrowly to extending the existing `acquisition_intelligence`/
  `discovery` architecture, not a parallel system. TD-38 added a third
  `domain_hints` source (real web-search evidence, 26/31 EGX30 tickers).
  TD-39 built the per-company **Financial Source Registry** itself —
  `discovery.company_financial_registry`/`company_financial_discovery`
  (IR/annual/quarterly/statements classification, source type, collector
  recommendation, all in a resumable `JsonFileRepository`) plus
  `scripts/build_financial_source_registry.py`, wired into
  `.github/workflows/discovery.yml` alongside the existing weekly job.
  **Actually run against all 101 EGX30+EGX70 companies this session**:
  0 `DISCOVERED`/`VALIDATED`, 26 `BLOCKED` (real fetch attempts, real
  proxy-403 evidence — same egress block TD-38 found), 75
  `HOMEPAGE_UNRESOLVED` (no evidenced homepage yet). This is the honest
  result, not a shortfall to paper over: this sandbox has never had
  network egress to any external host tested, confirmed repeatedly, not
  assumed. The mechanism, classifier, and CI wiring are complete and
  tested; the actual registry data needs a real `discovery.yml` run (next
  scheduled Monday, or `workflow_dispatch` now). The freeze on *unscoped*
  further acquisition engineering (new source families beyond this) still
  stands. Full detail: `CURRENT_MISSION.md`, `docs/ACQUISITION_STRATEGY.md`'s
  "Final Data Acquisition Sprint" section, and `NEXT_MISSIONS.md` for
  what's next.
- **Prior missions (same overall phase): price-data feasibility (proven
  impossible autonomously, with live evidence — Stooq's robots.txt is a
  confirmed blanket block, Yahoo Finance's real ToS explicitly prohibits
  automation, Investing.com/TradingView are blocked, Mubasher/Zawya have
  no structured price page) and coverage expansion (`fra_egypt` — Egypt's
  own Financial Regulatory Authority, the first official government
  source this platform has connected, 10 real disclosure items/events;
  plus two real bugs found and fixed: nine catalogued outlets had no
  discovery target at all, and the production pipeline had its own
  separate hardcoded 5-source allowlist excluding everything else from
  ever being auto-attempted). Full detail:
  `docs/ACQUISITION_STRATEGY.md`'s "Price Data Feasibility Mission" and
  "Coverage-Expansion Mission" sections.
- **Live-run evidence:** World Bank (66 real Egypt CPI observations,
  macro), `enterprise_press` (6 real news items/events), and `fra_egypt`
  (10 real disclosure items/events) are `IMPLEMENTED` and collecting.
  Stooq is blocked by a confirmed blanket robots.txt rule; IMF is blocked
  by a confirmed WAF rule; FRED's live behavior varies (sometimes
  succeeds, sometimes times out); EGX/CBE/Mubasher/Zawya each fail with a
  distinct, evidenced, source-side reason (network-level reset, WAF
  rejection, robots.txt disallow, or — Zawya/Mubasher — real, parseable
  content with zero legally-clearable structured candidates). Full
  detail: `docs/ACQUISITION_STRATEGY.md`.
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
- **Connected live sources: 3 collecting (World Bank, Enterprise, FRA),
  6+ more evidenced-blocked with named reasons, not unbuilt.** Every mechanism
  needed (discovery, verification, ranking, registration, qualification,
  collection, archival, validation, universe membership, corporate-event
  classification, financial-statement collection) is built and tested and
  has now genuinely run live (GitHub Actions has real outbound egress;
  this coding sandbox does not — the two are not the same environment,
  see `CURRENT_MISSION.md`). See `docs/ACQUISITION_STRATEGY.md` for the
  per-capability breakdown of what's blocked and why.
- **Historical coverage:** 66 real Egypt CPI observations (World Bank,
  live), 6 real Enterprise news items/events, and 10 real FRA disclosure
  items/events (live, EGX-specific) as of the most recent run. Every
  collector (including
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
  refuse to defeat — not an engineering gap; Zawya's/Mubasher's sitemaps
  are real and parseable but every entry is an HTML article page, not a
  legally-clearable feed — see `docs/ACQUISITION_STRATEGY.md`. (1b) No
  free, legally-obtainable, autonomously-implementable EGX equity price
  source exists — proven with live evidence this phase (Stooq: blanket
  robots.txt block; Yahoo/TradingView: real ToS text explicitly
  prohibits automation; Investing.com: 403 Forbidden; Mubasher/Zawya:
  no structured price page exists) — same root cause as blocker (3)
  below, now demonstrated rather than assumed. (2) No verified,
  complete EGX30/EGX70 constituent list exists in this codebase (only a
  10-company EGX30 placeholder, no EGX70 list at all) — a business
  decision reserved for the project owner, since fabricating ~90
  ticker/company-name pairs from training-data recall would itself
  violate the platform's anti-fabrication principle. (3) A licensed EGX
  market data vendor has not been selected — the standing gate on
  treating any output as real research (`docs/ROADMAP.md`).
- **Estimated remaining acquisition work: none, by design — frozen.**
  `agx discover-sources`, `generate_company_ir_targets()`,
  `IndexConstituentCollector`, and `FinancialStatementCollector` are all
  already built to scale automatically the moment blocker (2) clears, so
  no further acquisition engineering is needed in the meantime either.
  Blocker (1) needs a business/legal resolution per source (a WAF or
  robots.txt disallow is not something this program will bypass) — not
  an engineering fix, and not this program's decision to make. System
  18's remaining deployment/secrets/scheduling work is separately blocked
  on a hosting/vendor decision. **All engineering effort now goes toward
  `NEXT_MISSIONS.md`'s explainable-investment-intelligence work instead.**

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
