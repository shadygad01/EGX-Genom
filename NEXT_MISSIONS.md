# Next Missions

**Acquisition architecture is frozen as of this commit** (see
`CURRENT_MISSION.md` and `docs/ACQUISITION_STRATEGY.md`'s "Final Data
Acquisition Sprint" section). Every mission from here forward must
increase AGX's ability to **generate, validate, rank, and explain**
investment decisions from the evidence already connected (World Bank,
Enterprise, FRA) — not collect additional data. Grounded in
`docs/PHASE_STATUS.md`'s per-system audit (all 18 charter systems
architecturally DONE), here is what that actually means, in priority
order:

## 1. Monte Carlo stress simulator (System 10, Experiment Factory)

`docs/PHASE_STATUS.md` names this the one Experiment Factory gap that is
**not data-blocked** — an explicit placeholder "needs a simulator, a
research decision," unlike every other named gap in the validation stack
(which genuinely need more real trading history first). This is the
highest-leverage closeable item: a real Monte Carlo stress test would
strengthen every hypothesis that reaches Stress Testing, using data the
platform already has (real and mock alike) — no new source required.
Scope it as a design decision first (which simulation methodology —
block bootstrap, parametric, historical-resampling — matches the
existing `HistoricalWorstWindowStressTester`'s "locate a real scenario in
real data, never a simulated one" philosophy) before writing code.

## 2. NewsIntelligenceAgent (System 08, Scientist Framework)

`agents/news_intelligence.py` is an honest `NotImplementedError` stub —
previously correctly deferred because there was no real Egyptian news
flow to research. That's no longer true: `enterprise_press` and
`fra_egypt` are now producing real, dated `NewsItem`/`CorporateEvent`
records every live run. This is the most directly-unblocked stub in the
codebase — a genuine research/engineering task now, not a data-blocked
one. Design a real signal methodology (headline-keyword sentiment is the
honest starting tier, matching `corporate_event_classifier`'s own
precedent — never a fabricated NLP score) before implementing; the
`ResearchAgent` interface and `DatasetSnapshot` plumbing are already
built and tested.

## 3. Verify the pipeline against the next real trading day

Not new engineering — an operational checkpoint. Every real event
registered so far (`fra_egypt`'s 10 disclosures, `enterprise_press`'s 6
news items) landed on non-trading days, so the research pipeline
correctly produced zero hypotheses from them (an honest calendar gap,
not a strategy failure — see `MISSION_CONTROL.md`). The next scheduled
live run that lands on a real trading day is the first real test of
whether the full Observation → Hypothesis → ... → Promotion lifecycle
produces anything from genuinely live evidence. Watch it; don't force it.

## 4. Still correctly data-blocked — do not force these

Per `docs/PHASE_STATUS.md`, these remain honest gaps until enough real
history exists, not because the engineering is missing:

- **`HistoricalReviewer`** (System 12) — needs a historical-analog
  database; there isn't enough real trading history yet to build one
  without fabricating analogs.
- **`FinancialPerformanceAgent`** (System 08) — needs a real fundamentals
  feed, which is itself gated on the same business decisions
  `MISSION_CONTROL.md`'s "Known blockers" names (verified constituent
  list, licensed vendor) — not a new acquisition target to chase.
- **`HistoricalPatternsAgent`** (System 08) — needs years of real price
  history; genuinely blocked on the same Price Data wall
  `docs/ACQUISITION_STRATEGY.md`'s "Price Data Feasibility Mission"
  documents in full.
- **Trained prediction models** (System 14) — explicitly deferred until
  years of real data exist, "otherwise fabricated science" per the
  system's own DONE-with-caveat status.

Do not chase a new data source to unblock these — that would violate this
sprint's freeze. They unblock themselves once real history accumulates
from the sources already connected, or once the project owner clears a
named business blocker.

## 5. Known frontend gaps waiting on new backend artifacts

Still open, still honest "not yet available" states rather than
fabricated content (per `CLAUDE.md`'s anti-fabrication principle) — worth
closing once the artifact they depend on exists, but none of them require
new data collection:

- **Market Regime classification** (Market Intelligence, Company Research
  Workspace) — no artifact exists upstream yet.
- **Market Breadth & Liquidity** (Market Intelligence) — needs a
  backend-computed artifact (advancers/decliners, adjusted volume); the
  frontend must not compute returns from raw price bars itself.
- **Review Board decision history** (Research Center) — no repository
  persists past `BoardDecision`s yet.
- **Discovery Engine detail** (Mission Control) — `acquisition_intelligence`
  has no dashboard export yet; low priority now that acquisition is
  frozen, but the artifact would still be useful for showing *why* each
  connected source is trusted.
- **Raw log lines** (System Administration) — no artifact carries them
  yet.

## Beyond this

Every other named technical debt item in `docs/TECHNICAL_DEBT.md` that
touches acquisition/discovery/collectors is now dormant by design (frozen
architecture) unless a named business input clears its trigger. Debt
items touching validation/genome/explainability/review calibration (TD-6,
TD-17) remain open the same way items 4 above are — waiting on real run
history, not new engineering. Future missions should come from this list,
a genuine gap the project owner surfaces, or what item 3's real-trading-
day checkpoint reveals — never from re-opening acquisition work.
