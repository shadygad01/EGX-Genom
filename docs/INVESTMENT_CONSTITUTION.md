# The EGX-Genom Investment Constitution

**Status: permanent doctrine.** This document is not a description of the
codebase — it is the governing law the codebase implements. Where this
constitution and a future feature disagree, the constitution wins unless
it is amended first, in the open, the same way `docs/ARCHITECTURE_DECISIONS.md`
already records every irreversible design choice this platform has made.
`docs/VISION.md` states the eight immutable principles of *why AGX exists*;
`MASTER_PROMPT.md` states the operating charter — role, non-negotiable
build order. This constitution sits between them and the code: it is the
permanent answer to *how AGX decides*, at the level a Chief Investment
Officer would write it down for every analyst, every committee, and every
future engineer to follow without deviation.

Every article below is grounded in a real, already-implemented mechanism —
cited by module and, where relevant, by exact threshold — not an aspiration
floating free of the platform. Where a mechanism does not exist yet, this
constitution says so honestly rather than describing code that isn't
there. This is the same anti-fabrication discipline that governs every
number AGX produces, applied to governance itself.

---

## Preamble: What This Platform Is For

AGX exists to answer one question with evidence instead of opinion: *is
this a good use of capital, right now, relative to every other use of
that same capital?* It is not a stock-picking tool and not a signal
generator. It is a research organization compressed into software, with
the same discipline a real institutional investment committee would
demand: nothing is believed until it has survived scrutiny, nothing is
acted on until it has cleared every applicable gate, and nothing is ever
acted on by an unaccountable machine — every number traces back to real
evidence, and every recommendation stays advisory research until a human
publication process, not a model, decides it may influence real capital.

Three structural facts follow from this and recur throughout every
article below:

1. **Agents propose, gates decide.** No finding ever reaches "promoted
   knowledge" without passing every stage of a fixed validation pipeline.
   No promoted knowledge ever becomes a public recommendation without
   separately clearing a fail-closed publication gate that requires real,
   dated, source-verified evidence — not merely internal statistical
   passage.
2. **Nothing is scored in isolation.** A ticker's action is never a
   verdict about that ticker alone; it is that ticker's standing relative
   to every other ticker with evidence, every currently held position,
   and idle cash, evaluated jointly.
3. **Silence is a valid, and often correct, answer.** `ABSTAIN`,
   `HOLD`, and `NO_ACTION` are first-class outcomes, not failure modes.
   A platform that always has an opinion is a platform that eventually
   fabricates one.

---

## Article I — Why Invest

AGX allocates capital to a ticker only when a real, surviving,
risk-adjusted expectancy exists — never because a ticker is popular,
newsworthy, or "due." Concretely, capital is proposed only when:

- At least one `KnowledgeObject` — a hypothesis that has already survived
  the full 8-gate validation pipeline (Article IX) — covers the ticker at
  the relevant horizon, is not `RETIRED`, and carries positive confidence
  (`horizons.knowledge_weighted.KnowledgeWeightedHorizonModel.predict()`:
  no knowledge, no prediction, ever — never a guess in evidence's
  absence).
- The resulting prediction's risk-adjusted score
  (`confidence × expected_return / expected_risk`) clears the research
  action threshold (`score ≥ 1.0` for `BUY_CANDIDATE`,
  `meta.decision_engine.MetaDecisionEngine._decision_for_prediction()`)
  — a merely positive expectancy is not enough; it must be positive
  *after* being discounted for how uncertain and how risky it is.
- The ticker outranks the available alternatives for the same capital
  (Article VII) — a positive-but-weak case competing against idle cash
  and stronger ideas correctly loses, not because it is bad, but because
  it is not the best available use of that unit of capital today.

An investment is never made because the platform "likes" a company. It is
made because a chain of evidence — statistical, economic, and structural —
survived every attempt to falsify it, and the resulting number beat every
other claim on the same capital.

---

## Article II — Why Reject Investments

Rejection is not a single event; it is any of several distinct,
honestly-labeled outcomes, each with its own real trigger:

- **`AVOID`** — the model's own expected return is non-positive
  (`expected_return ≤ 0`). The evidence itself argues against the
  position; there is nothing to select for.
- **`WATCH`** — the expectancy is positive but does not clear the
  `score ≥ 1.0` action threshold. Real, but not strong enough to act on;
  a candidate for renewed attention if the evidence strengthens, not a
  rejection of the underlying thesis.
- **`ABSTAIN`** — the platform declines to state an opinion at all,
  because at least one of these is true:
  - Confidence is below the 60% research floor
    (`meta.decision_engine._decision_for_prediction`).
  - A `BUY_CANDIDATE` verdict has no real, current reference price to
    attach an executable entry level to — an opinion with no way to act
    on it is withheld rather than published as a bare label.
  - The ticker fails `meta.readiness.assess_decision_readiness()`'s
    horizon-specific data-sufficiency gate (Article IX) — insufficient
    price history, stale prices, no linked news/corporate event, no fair
    value from at least three valid models, insufficient macro/country-
    risk data, or no active knowledge at all for that horizon.
  - The ticker sits below the liquidity floor (Article III) or the
    country-risk severity is `CRISIS` (Article III) — both are hard
    overrides, not weighted evidence a strong thesis can outweigh.
  - The publication gate itself is not cleared (Article IX) — even a
    statistically excellent internal case is withheld from any real
    capital consequence until live market data, four periods of official
    disclosures, current macro data, two-source price corroboration,
    30+ benchmark-outperforming results per horizon, and a valid human
    legal review all exist simultaneously
    (`meta.publication_gate.evaluate_publication_gate`).

`ABSTAIN` is deliberately the platform's most common honest answer today:
until a licensed EGX market-data vendor exists, the publication gate can
never fully clear, so every real recommendation currently and correctly
abstains from public consequence (`docs/DECISION_SYSTEM_ACCEPTANCE.md`).
This is not a defect to work around — it is the constitution working
exactly as designed. A system that quietly loosened this gate to "have
more opinions" would be committing the platform's one unforgivable sin:
manufacturing confidence that hasn't been earned.

---

## Article III — When to Hold Cash

Cash is never an oversight — it is the default state of every unit of
capital until a specific, evidence-backed ticker earns it away. Concretely,
capital stays in cash when:

- No ticker's risk-adjusted score is positive and large enough to clear
  the funding threshold under the current shared budget
  (`decision_service.service.DecisionService.decide_portfolio()`'s joint
  normalization; `capital_allocation.CashWaiting` reports this
  explicitly as "no additional ticker currently clears a positive,
  publication-ready risk-adjusted score large enough to absorb this
  capital").
- A ticker that would otherwise be funded falls below the liquidity floor
  — EGP 1,000,000 average daily traded value
  (`decision_service.liquidity_floor.DEFAULT_MIN_AVERAGE_TRADED_VALUE`).
  Illiquidity caps target weight to zero *regardless of thesis strength*,
  because you cannot execute meaningful size in a thin name without
  moving the price against yourself — this is a constraint on
  executability, not a data point to weigh against the rest of the case.
- Country & Macro Risk severity is `CRISIS`
  (`decision_service.country_risk.CountryRiskSeverity`) — every target
  weight is forced to zero across the board. `CRISIS` requires a real,
  discrete sovereign rating downgrade, never an inferred currency move
  alone (Article X's evidentiary discipline applied to macro risk).
- Idle cash genuinely has nothing better to fund. The Capital Allocation
  Engine draws idle cash *before* ever displacing an existing holding
  (`capital_allocation.engine._match_capital_flows`) — cash is never
  forced into a weaker idea merely to look "fully invested."

Holding cash is a decision, not an absence of one, and it is reported as
such: `cash_waiting.reason` always states explicitly why the capital is
idle, never leaving it as an unexplained gap in the portfolio.

---

## Article IV — When to Increase

An existing position's target weight rises above its current weight,
producing `INCREASE_POSITION`, only when the ticker's current,
re-evaluated evidence — not the original thesis, a *fresh* recomputation
of it — still clears every gate in Article II and its resulting
risk-adjusted share of the shared capital budget is larger than what is
currently held
(`decision_service.service.DecisionService._resolve_action`:
`target_weight > current_weight + ε` while held). An increase is never
based on price momentum alone, "already being right so far," or a sunk
cost that would look better with more capital behind it — the same
evidence discipline that justified the original position must still
justify a larger one, re-evaluated as of today.

---

## Article V — When to Reduce

`REDUCE_POSITION` fires when a held ticker's re-evaluated target weight
is positive but lower than what is currently held. This is distinct from
an exit: the thesis is not dead, but it now deserves less of the
portfolio's capital than before, because:

- Its risk-adjusted score weakened relative to its own prior standing, or
- It has been outranked by stronger competing ideas under the same
  shared capital budget (Article VII) — the Opportunity Cost Engine
  names exactly which higher-ranked idea now deserves the capital being
  released.

A reduction is not a verdict on the company; it is the platform stating,
explicitly, that a specific portion of this position's capital has a
better home right now. `capital_allocation.CapitalRelease.destinations`
records precisely where that capital goes — a genuine reduce is always
traceable to a genuine gain elsewhere, never an unexplained trim.

---

## Article VI — When to Exit

`EXIT` fires when a held ticker's re-evaluated target weight reaches
zero while a position is still held. This happens for one of two
structurally different reasons, and the platform is required to say
which:

1. **The thesis failed on the evidence.** The supporting knowledge was
   retired (Article XI's continuous-learning mechanism), a hard override
   applies (illiquidity or country-risk crisis), or the risk-adjusted
   case genuinely turned non-positive. This is a decisive call, and
   `_resolve_action` labels it `EXIT`.
2. **The evidence simply went quiet.** No fresh INVESTMENT-horizon
   evidence currently exists for a held ticker — an *absence* of
   evidence, not an *argument against* the position. The platform
   deliberately does **not** label this `EXIT`; it labels it `HOLD` and
   states the abstention reason plainly ("no current INVESTMENT-horizon
   evidence for this held ticker"). Treating a data gap as a sell signal
   would fabricate a decision the evidence never made — the same
   discipline the Capital Allocation Engine enforces mechanically via
   `_effective_target()` (Article VII), which refuses to treat this kind
   of zeroed, abstained `target_weight` as a real capital release at all.

The distinction between "the evidence says leave" and "the evidence went
silent" is not cosmetic — it is one of this constitution's central
commitments: an evidence gap is never allowed to masquerade as a
decision.

---

## Article VII — How Capital Is Allocated

Capital allocation is never local. No ticker's action is decided by
looking at that ticker alone; every ticker with a live `Recommendation`
or an existing position is evaluated **in the same pass**, against the
same shared budget (`DecisionService.decide_portfolio()`'s joint
`total_positive_score` normalization), and then made explicit as a
competition rather than left implicit:

- **Global ranking.** Every evaluated ticker — funded, rejected, held, or
  abstained — receives one rank, 1..N, by its risk-adjusted opportunity
  score (`capital_allocation.CapitalAllocationEngine._rank()`). Nothing
  is displayed or reasoned about in isolation.
- **Capital as the primary input.** A recommendation is a *proposal
  requesting capital*, not a verdict about a stock. It is granted capital
  only if it outranks every lower-scoring alternative and idle cash
  under today's budget.
- **Idle cash funds before any holding is displaced.** The matching
  algorithm always draws unallocated cash first; a currently-held
  position is only ever named as a capital source when idle cash
  genuinely was not enough. This platform never fabricates a "replace
  this holding" conflict that a little idle cash would have resolved.
- **The weakest idea is displaced first.** When a holding must fund a
  stronger new proposal, the lowest-ranked funded holding is reduced or
  exited before a stronger one ever would be
  (`_match_capital_flows`'s weakest-supplier-first ordering).
- **Every capital movement names its source and destination.** A `BUY`
  or `INCREASE` states exactly which idle cash and/or which displaced
  ticker funded it (`CapitalQueueEntry.capital_sources`); a `REDUCE` or
  `EXIT` states exactly where the released capital went
  (`CapitalRelease.destinations`) — to a specific higher-ranked demander,
  or explicitly back to cash if nothing currently needs it.
- **Every proposal states its opportunity cost.** Every funded entry's
  `opportunity_cost_note` names the best-ranked idea that currently
  receives *no* capital, or explicitly states none exists. This is the
  platform's structural answer to "if I invest here, what am I
  rejecting?" — never left as an unstated tradeoff.
- **No capital movement is fabricated from an evidence gap.** An
  abstained decision — no fresh evidence, not a decisive sell — never
  participates in capital-flow matching even though its raw target
  weight computes to zero (Article VI, `_effective_target()`).

Capital allocation is, structurally, the platform's answer to "is this
the best use of capital available today?" rather than "is this stock
good?" — the reframe every later mission in this platform's history
(Capital Allocation Intelligence) exists to make explicit.

---

## Article VIII — How Confidence Is Interpreted

Confidence is a number on `[0, 1]`, never a vague adjective, and it is
never invented beyond what its inputs support:

- **Confidence is bounded by its weakest link, not inflated by
  aggregation.** `KnowledgeWeightedHorizonModel.predict()` computes a
  confidence-weighted mean across supporting evidence, then caps it at
  the single strongest piece of evidence's own confidence
  (`min(weighted_mean, max(individual confidences))`) — combining several
  moderate-confidence findings must never manufacture certainty none of
  them individually earned.
- **A stated cause caps confidence, it does not guarantee it.**
  `causal.reasoner.EconomicRationaleGate` refuses to grant *any*
  meaningful confidence to a hypothesis relying on correlation alone; even
  when it passes (a real candidate cause and economic rationale were
  stated), confidence caps at 0.5, because the gate verifies a rationale
  was *stated*, not that it is *correct* — judging correctness is
  `review.reviewers.EconomistReviewer`'s job, not this gate's.
  `AdversarialScientist` attacks then push confidence further down for
  every real weakness a successful attack finds (Article IX), and up only
  for attacks that were attempted and genuinely failed to find a problem.
- **60% is the floor for having an opinion at all**, not a target to
  clear cosmetically — below it, the platform abstains rather than
  publishing a low-conviction guess (Article II).
- **Confidence is measured against reality, continuously, and reported
  honestly when there isn't yet enough history to measure it.**
  `investment_proof.calibration.ConfidenceCalibrationFramework` computes
  a real Brier score and expected calibration error from
  `DecisionLedger`'s recorded confidence-vs-outcome pairs — but only once
  30 benchmark-evaluated decisions per horizon exist
  (`DEFAULT_MIN_SAMPLE = 30`, the same floor `DecisionLedger.
  performance_summary()` and the publication gate itself require). Below
  that floor, every calibration statistic is honestly `None` and
  `sample_status="insufficient"` — never a fabricated number standing in
  for real measurement.
- **Confidence is not a portfolio-weight substitute.** A high-confidence
  idea still competes for capital against every other opportunity
  (Article VII) — confidence discounts the score that ranking is built
  from, it is not itself the allocation.

---

## Article IX — How Evidence Is Evaluated

No finding reaches "promoted knowledge" — the only tier from which a
recommendation may ever be built — without surviving, in order, the full
validation pipeline (`hypotheses.pipeline.DEFAULT_PIPELINE`):

**OBSERVATION → HYPOTHESIS → DATA_COLLECTION → EXPERIMENT →
STATISTICAL_VALIDATION → STRESS_TEST → BACKTEST → PEER_VALIDATION**

Gates are configurable data (`GateSpec`), never hardcoded control flow —
a lighter track for Micro-horizon screening or an extra regime-robustness
gate for Investment-horizon claims can be added without touching the
platform's core, but no gate may ever be skipped or reordered for a live
run. Alongside the pipeline itself, three independent layers of scrutiny
apply before promotion, and every one of them can say no:

1. **The Economic Rationale Gate** (Article VIII) — correlation alone is
   never enough; a stated candidate cause and rationale are structurally
   required.
2. **The Scientific Review Board** — every configured reviewer runs, and
   *all* must pass. A reviewer still `NotImplementedError` (not yet
   built — e.g. the historical-analog reviewer, which needs years of
   labeled market episodes this platform does not have) is skipped, never
   silently counted as passed; a board with zero working reviewers can
   never approve anything, by construction. The reviewers that do run
   today are real and mechanical: `StatisticianReviewer` (significance +
   sample size), `RiskReviewer` (expected-risk ceiling), `EconomistReviewer`
   (rationale has real substance, engages the specific claim, and the
   causal gate passed — structural coherence, never a judgment of
   economic *truth*), and `PeerValidatorReviewer` (an independent
   replication with a perturbed methodology — different fold count,
   different bootstrap seed — must reproduce the same sign and
   significance; this is "can an independent run reproduce your result,"
   not simulated human agreement).
3. **The Adversarial Scientist** — actively attacks the surviving
   confidence rather than accepting it: random coincidence, small-sample
   bias, time leakage, look-ahead bias, overfitting, parameter
   instability, regime dependency, out-of-sample degradation, and weak
   economic rationale are each a real, distinct attack type. A successful
   attack (one that finds a real problem) reduces confidence; an attempted
   attack that genuinely fails to find a problem reinforces it. An attack
   never attempted is reported `attempted=False`, never assumed passed.

Only once a hypothesis clears all of this does it become a
`KnowledgeObject` and enter the post-promotion lifecycle:
`PROMOTED → MONITORING → RETIRED` (`knowledge.lifecycle`), a one-way
transition graph — knowledge can move forward toward retirement but never
backward toward a less-scrutinized state.

Beyond the knowledge layer, two further gates apply before any evidence
can influence a real decision:

- **Ticker-level readiness** (`meta.readiness.assess_decision_readiness`):
  MICRO requires ≥60 price observations, fresh prices, active MICRO-horizon
  knowledge, and liquidity above the floor; SWING additionally requires
  ≥120 observations and a linked news item or corporate event; INVESTMENT
  additionally requires ≥252 observations, a reliable fair value from at
  least three valid models (Article X), the price not sitting more than
  20% above that fair value, ≥3 macro series, and sufficient exchange-rate
  data to assess country risk. A ticker missing any of these for a given
  horizon is not "researchable" at that horizon — full stop, regardless of
  how strong the rest of its case looks.
- **The publication gate** (Article II) — the final, hardest gate,
  because it is the only one requiring evidence about the real world
  rather than about the platform's own internal statistics: live,
  legally usable EGX market data; four periods of official disclosures;
  current CBE/CAPMAS macro data; two independently-sourced price
  corroborations; 30+ per-horizon benchmark-outperforming results at
  95% confidence, after transaction costs; and a valid, dated human legal
  review. All of it, simultaneously, or nothing is `PUBLICATION_READY`.

---

## Article X — How Conflicting Evidence Is Handled

Conflicting evidence is never averaged away into a smoothed number that
hides the disagreement — it is surfaced, explicitly, at every layer:

- **Sibling-horizon disagreement is reported as contradicting evidence,
  not blended.** MICRO/SWING/INVESTMENT decisions are never combined
  into one action (`AD-35`'s standing rule); when a non-primary horizon's
  model disagrees with the acting horizon's own conclusion — a negative
  expected return, or an `AVOID` — that disagreement is attached verbatim
  to the decision's `contradicting_evidence`, visible to whoever reads it,
  never silently netted out.
- **Committee-level disagreement is measured, not assumed.**
  `investment_proof.committee_validation.CommitteeValidationEngine`
  treats each evidence category (Macro/Sector/Quality/Value/Catalyst/
  Technical) as an independent "committee" and computes, across a real
  batch of tickers, whether that committee's own directional signal
  agreed or disagreed with the platform's final blended answer — a real
  measured agreement rate, not a narrative claim of consensus.
- **Decisiveness is proven by real ablation, not assumed by intuition.**
  `investment_proof.counterfactual.CounterfactualEngine` removes each
  evidence category in turn and *literally recomputes* the decision with
  the same real model and decision engine a live decision would use.
  Whichever category's removal actually flips the action is the evidence
  that genuinely drove the decision — never a coefficient, never a
  guessed importance ranking.
- **Contributions must reconcile, or the discrepancy is surfaced, not
  hidden.** `investment_proof.attribution.DecisionAttributionEngine`
  decomposes the final expected return into named category contributions
  and checks that they actually sum back to the total
  (`attribution_residual`) — a nonzero residual is a real finding to
  investigate (an unmapped evidence source, an arithmetic drift), never
  silently absorbed into rounding.
- **Country/macro risk is a graduated axis, not a binary override
  invented from a single number.** A currency move alone can only ever
  reach `DETERIORATING`; `CRISIS` requires a real, discrete sovereign
  rating downgrade. A large currency move is real evidence of
  deterioration, but this platform will not assert "crisis" from an
  inferred number when a real, dated, corroborating event is the honest
  bar for that word.
- **A macro/rate/political disagreement never gets silently split the
  difference.** If macro evidence argues one way and company-specific
  evidence argues the other, both remain visible in the decision's
  `explanation`/`contradicting_evidence` fields; the final action is
  whatever the risk-adjusted score says, but the disagreement itself is
  never erased from the record.

The governing principle: disagreement is data. A platform that resolves
conflicting evidence by quietly averaging it away has thrown away the
single most useful signal that evidence can produce — the fact that it
disagrees.

---

## Article XI — How Mistakes Are Reviewed

Every decision this platform ever makes is recorded, and every recorded
decision is eventually checked against what actually happened. Nothing is
allowed to be "probably right" forever without being tested:

- **Every horizon decision is appended to a permanent, append-only
  ledger** (`meta.decision_ledger.DecisionLedger`) at the moment it is
  made, and evaluated once its validity window expires: entry price, exit
  price, gross return, a 20-bps transaction-cost deduction, benchmark
  return (against `EGX30`), excess return, and a binary `hit` (excess
  return positive). This is not optional bookkeeping — the publication
  gate itself cannot clear without 30+ of these per horizon showing real,
  positive, statistically defensible outperformance.
- **A thesis's survival is checked directly against the assumptions it
  was built on**, never merely against price
  (`investment_proof.thesis_survival.ThesisSurvivalEngine`): were any of
  the original supporting knowledge objects since retired? Did new
  contradicting evidence appear that wasn't present originally? Did an
  active catalyst lapse? Did the review date pass without a
  re-evaluation? The resulting label —`alive`, `weakening`, `broken`, or
  `expired`— is a plain, mechanical fact derived from real lookups, never
  a learned or historically-calibrated score.
- **Knowledge is retired for a stated, quantitative reason, never
  quietly.** `learning.monitor.ContinuousLearningMonitor` re-evaluates
  every promoted knowledge object's *realized* return against real,
  observed market data (never simulated) and retires it once, with at
  least 3 monitored records, the realized return's sign disagrees with
  the original expected-return sign in a majority of them. The exact
  count that triggered retirement is recorded in the reason string, and
  the pre-retirement history is preserved, never overwritten.
- **The same evidence, evaluated twice, must produce the same answer.**
  `investment_proof.stability.DecisionStabilityEngine` proves this by
  literally calling the real recommendation and decision services
  multiple times against identical inputs and diffing the results —
  determinism is a measured property, not a claimed one, and any
  divergence is a real bug to fix, not a rounding footnote.
- **A gap in the evidence chain is recorded as a debt, not hidden.**
  Every declared-but-uncalibrated threshold in this constitution (the
  60% confidence floor, the 0.25 concentration ceiling, the 5% currency-
  deterioration floor, the liquidity floor, the 20%
  price-above-fair-value ceiling, and every other number cited above) is
  logged in `docs/TECHNICAL_DEBT.md` with an explicit repayment trigger —
  real multi-year EGX history accumulating enough to test it against.
  This constitution does not pretend any of these numbers are more
  scientifically settled than they are; it commits to revisiting them
  once real evidence exists to do so, and names exactly what that
  evidence is.
- **Every irreversible design choice is recorded, permanently, in
  `docs/ARCHITECTURE_DECISIONS.md`** — including the choices this very
  constitution encodes (e.g. AD-45: `decision_service` never runs
  autonomously; AD-35: horizons are never blended into one action). A
  future engineer disagreeing with a past decision does not get to
  silently reverse it; they write a new, numbered decision explaining
  why, the same discipline this constitution itself is bound by.

A mistake, in this platform's vocabulary, is not "a stock that went
down" — a real, well-evidenced, risk-adjusted case can lose and still
have been the right call given what was knowable at the time. A mistake
is a *process failure*: evidence that should have been caught by a gate
and wasn't, a calibration that turns out systematically overconfident, a
thesis that broke and wasn't flagged. Every mechanism in this article
exists to catch exactly that category of failure, continuously, and to
leave a permanent, honest record when it happens.

---

## Amendment

This constitution may be extended by a future mission — new market
regimes understood, new evidence categories discovered, new gates added —
but never silently contradicted. Any change to a principle stated here
requires the same discipline `docs/ARCHITECTURE_DECISIONS.md` already
demands of every irreversible choice: a numbered decision, a stated
reason, and a permanent record. Nothing in `docs/INVESTMENT_PLAYBOOK.md`,
`docs/DECISION_STANDARDS.md`, or `docs/PORTFOLIO_STANDARDS.md` may
override an article of this constitution — those documents operationalize
this one; they do not supersede it.
