# EGX-Genom Portfolio Standards

**Status: permanent doctrine, operationalizing `docs/INVESTMENT_CONSTITUTION.md`.**
This document specifies the platform's portfolio-construction rules —
concentration limits, diversification principles, liquidity rules, cash
rules, position sizing, and capital recycling — exactly as implemented in
`portfolio.constructor.PortfolioConstructor`,
`decision_service.service.DecisionService`,
`investment_proof.portfolio_validation.PortfolioValidationEngine`, and
`capital_allocation.CapitalAllocationEngine`. Every numeric threshold
below is cited from real code, and every threshold marked *declared,
uncalibrated* is logged in `docs/TECHNICAL_DEBT.md` with an explicit
repayment trigger — this document does not pretend any of them are more
scientifically settled than they are.

---

## 1. Maximum Concentration

Two independent ceilings apply, and both must hold simultaneously:

- **Per-position ceiling.** No single position's target weight may
  exceed `min(max_position_weight, max_position_pct)`:
  - `max_position_weight` defaults to `0.25` (25% of the portfolio) —
    the constructor-level cap shared by both `PortfolioConstructor` and
    `DecisionService`.
  - `max_position_pct` is set per-decision by the decision quality gate
    (`meta.decision_quality.apply_decision_quality_gate`, replacing the
    old system-wide `meta.publication_gate.apply_publication_gate` —
    2026-08-02, see `docs/ARCHITECTURE_DECISIONS.md`), and is *never*
    the full 25% for a real published decision: it is
    `min(0.05, max(0.01, confidence × 0.05))` — a confidence-scaled band
    between 1% and 5%.
    In practice, the binding per-position ceiling on any real,
    publication-ready decision is this 1–5% band, not the 25% structural
    maximum, until this platform's own conviction (via measured
    confidence) earns a larger allocation.
- **Portfolio-level concentration ceiling.** The Herfindahl-Hirschman
  Index of all position weights (`Σ weight²`) must stay at or below
  `0.25` (`investment_proof.portfolio_validation.
  HERFINDAHL_CONCENTRATED_THRESHOLD`) to be classified `diversified`; at
  or above it, the portfolio is flagged `concentrated` and a
  `portfolio_concentration` warning is raised
  (`dashboard.monitoring.build_warnings`). *Declared, uncalibrated* — no
  real multi-year EGX portfolio history yet exists to test whether 0.25
  is the threshold that actually separates healthy diversification from
  real concentration risk.

A portfolio may legitimately approach the Herfindahl ceiling purely from
price appreciation in winning positions, with no new buying at all
(`docs/INVESTMENT_PLAYBOOK.md` §1) — the ceiling is checked against the
portfolio's actual current state, not against trading intent.

## 2. Diversification Principles

- **Sector concentration is checked independently of position
  concentration.** `PortfolioValidationEngine` computes real sector
  exposures (from whatever sector mapping is available) and flags the
  portfolio `concentrated` if the single largest sector weight exceeds
  `MAX_SECTOR_CONCENTRATION = 0.40` (40%) — *declared, uncalibrated*, same
  posture as the Herfindahl ceiling. A portfolio can be
  position-diversified (no single ticker near 25%) while still being
  sector-concentrated, and both checks run independently; passing one
  never substitutes for the other.
- **Diversification is a consequence of the evidence chain, never a
  target achieved by forcing trades.** No mechanism in this platform buys
  a weak idea merely because a sector or position is under-represented —
  every position must still independently clear the full evidence chain
  (`docs/INVESTMENT_CONSTITUTION.md` Article IX) and win its share of
  capital in the Global Opportunity Ranking (Article VII). A
  concentration warning is a signal to review, not an instruction to
  force a trade that isn't otherwise evidenced.
- **`decision_conflicts` between the position-aware and position-unaware
  paths are surfaced, not hidden.** `PortfolioValidationEngine` compares
  `PortfolioConstructor`'s autonomous, position-unaware weight for a
  ticker against `DecisionService`'s position-aware target weight for the
  same ticker, and reports any disagreement beyond a `0.01` tolerance
  explicitly — the two paths are allowed to differ (Constitution's
  "agents propose, gates decide" discipline applies differently to each),
  but the disagreement itself must never be silently absorbed.

## 3. Liquidity Rules

- **A hard, binary floor, not weighted evidence.**
  `decision_service.liquidity_floor.compute_illiquid_tickers()` flags any
  ticker whose average `close × volume` over the available price history
  falls below `DEFAULT_MIN_AVERAGE_TRADED_VALUE = EGP 1,000,000`
  (*declared, uncalibrated*). A ticker below this floor is capped at
  target weight zero **regardless of how strong its thesis reads** — this
  is a constraint on real executability (you cannot transact meaningful
  size in a thin EGX name without moving the price against yourself), not
  a data point a strong thesis can outweigh.
- **A ticker with no price history at all is treated as illiquid**, never
  assumed tradable from an absence of data — the floor fails closed.
- **The same floor gates readiness, not just sizing.** `meta.readiness.
  assess_decision_readiness()` reuses the identical constant (imported,
  never re-declared) so a ticker below the floor is blocked from every
  horizon's readiness, not merely zeroed out downstream — the two
  mechanisms can never silently drift apart because they share one
  source of truth.
- **Liquidity deterioration is monitored continuously**, not only at
  decision time: `liquidity_deterioration` warnings fire the moment a
  currently-recommended ticker crosses below the floor, independent of
  whether a new decision is being computed that day.

## 4. Cash Rules

- **Cash is the default residual, always.** A ticker's target weight is
  only ever positive if it earns capital through the full evidence chain
  and wins its share of the shared budget; every unit of capital not so
  earned remains in cash. Total invested weight plus cash weight must
  reconcile to `1.0` within a `0.01` tolerance
  (`PortfolioValidationResult.weights_reconcile`) — an unreconciled
  portfolio is a real bug, not a rounding footnote.
- **Cash is drawn before any holding is ever displaced.** The Capital
  Allocation Engine's matching algorithm
  (`capital_allocation.engine._match_capital_flows`) always exhausts idle
  cash for a demanding proposal before it ever names an existing holding
  as a capital source — a holding is only ever displaced when idle cash
  genuinely was not enough.
- **Cash left idle is always explained, never an unexplained gap.**
  `CashWaiting.reason` states explicitly why capital stayed in cash: "all
  available capital is deployed" when nothing is idle, or "no additional
  ticker currently clears a positive, publication-ready risk-adjusted
  score" when it is — a reader must never have to guess why the portfolio
  isn't fully invested.
- **Cash is never forced to zero to "look invested."** Holding 100% cash
  is a fully legitimate, correctly-labeled outcome whenever no ticker
  clears the evidence chain — the Constitution (Article III) states this
  as a decision, not an absence of one.

## 5. Position Sizing Philosophy

- **Sizing is risk-adjusted and confidence-discounted, never
  conviction-only.** Every candidate's raw score is
  `confidence × expected_return / (expected_risk + ε)`
  (`portfolio.constructor.PortfolioConstructor`,
  `decision_service.service.DecisionService`) — a high-confidence,
  low-return, high-risk idea and a moderate-confidence, high-return,
  low-risk idea can legitimately size identically if their risk-adjusted
  scores agree; conviction alone never sets size.
- **Weights are proportional to score, not to an arbitrary tier.** Once
  every eligible ticker's score is known, weight is
  `score / total_positive_score`, capped by the per-position ceiling
  (§1) — a continuous proportional allocation, never a discrete
  small/medium/large bucket. This is a deliberate architectural choice
  (`docs/ARCHITECTURE_ADVERSARIAL_REVIEW.md` R5): a discrete lookup table
  over signal-strength buckets was proposed and rejected for
  combinatorial-growth risk.
- **Every position's size is jointly normalized, never sized in
  isolation.** A ticker's final weight is only ever computed after every
  other ticker with evidence or an existing position is considered
  together (`docs/INVESTMENT_CONSTITUTION.md` Article VII) — the same
  score evaluated alone versus evaluated against the full competing set
  can legitimately produce different weights, and the difference is
  exactly what `investment_proof.attribution`'s `Portfolio` modifier
  reports (`isolated_weight_share` vs. `final_target_weight`).
- **Ineligible evidence sizes to zero, not to a small non-zero
  position.** A ticker that fails §0 of `docs/DECISION_STANDARDS.md`
  contributes `0.0` to its own score, not a token minimum position —
  there is no minimum-position floor that overrides the evidence chain.

## 6. Capital Recycling Philosophy

- **Recycling is bookkeeping over already-computed weights, never a
  second optimization.** The Capital Allocation Engine's matching
  algorithm attributes each unit of already-computed capital movement to
  a real source and destination — it does not re-score or re-weigh
  anything `DecisionService`/`PortfolioConstructor` already computed
  (`docs/INVESTMENT_CONSTITUTION.md` Article VII).
- **The weakest idea is always displaced first.** When a stronger new
  proposal's capital need exceeds idle cash, the lowest-ranked currently
  funded holding is reduced or exited before a stronger one ever would
  be — ranked strictly by the same risk-adjusted `opportunity_score`
  every other standard in this platform uses, never by tenure, cost
  basis, or any factor outside the evidence chain.
- **Every recycled unit of capital is named on both ends.** A reduction's
  released capital states exactly which higher-ranked demander absorbed
  it, or that it returned to cash because nothing currently needed it
  (`CapitalRelease.destinations`); a funded proposal states exactly which
  cash and/or displaced holdings funded it (`CapitalQueueEntry.
  capital_sources`). A recycling event with an unstated source or
  destination does not meet this standard.
- **Recycling requires a real, existing holding to recycle from.**
  There is no capital to recycle in a purely autonomous, position-unaware
  view (no real holdings exist to displace) — capital recycling is,
  structurally, a position-aware-only concept, computed only on demand
  against real `PositionState`, never fabricated for a model portfolio
  that holds nothing real.

---

## Standards this document does not relax

Every threshold in this document that is marked *declared, uncalibrated*
is a real, working default, not a placeholder — it governs every real
decision this platform makes today. It may only be changed through the
same amendment discipline `docs/INVESTMENT_CONSTITUTION.md`'s closing
article requires: a numbered architecture decision, a stated reason
grounded in real accumulated evidence, and a permanent record in
`docs/ARCHITECTURE_DECISIONS.md`. No threshold in this document may ever
be silently loosened to make the portfolio "look" more invested,
diversified, or active than the evidence actually supports.
