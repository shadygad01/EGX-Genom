# The EGX-Genom Investment Handbook

**Status: permanent operational doctrine.** This is the complete
operating manual for how EGX-Genom thinks — from raw data to a labeled
investment decision to a recorded outcome. `docs/INVESTMENT_CONSTITUTION.md`
states the permanent principles; `docs/INVESTMENT_PLAYBOOK.md` states how
those principles read in twelve market situations; `docs/DECISION_STANDARDS.md`
and `docs/PORTFOLIO_STANDARDS.md` state the exact minimum bars a
recommendation and a portfolio must clear. This handbook is the
connective tissue: the full pipeline, in order, with every formula,
every threshold, and every gate named — detailed enough that an
engineering team with no access to `research/src/agx_research/` could
rebuild this investment process from this document alone.

Every number in this handbook is real, cited from the module that
computes it. Nothing here is aspirational unless explicitly marked
**[doctrine — not yet built]**.

---

## Chapter 1 — What Gets Evaluated, and When

The universe is EGX30 (primary) and EGX70, evaluated across three
independent time horizons that are **never blended into one action**:

| Horizon | Window | Governs |
|---|---|---|
| `MICRO` | 1–3 trading days | Short-term signal, requires ≥60 price observations |
| `SWING` | 1–4 weeks | Requires ≥120 price observations, a linked news item or corporate event |
| `INVESTMENT` | 1–6 months | Requires ≥252 price observations, a reliable fair value, sufficient macro/country-risk data. **Only this horizon ever drives a position-aware Buy/Increase/Hold/Reduce/Exit/No-Action action** — this platform's long-term-investor mission is scoped to `INVESTMENT` specifically. |

Every computation is anchored to a fixed `as_of` date and reads only data
knowable as of that date (`market_memory.MarketMemory.reconstruct(as_of)`
produces an immutable, content-hashed `DatasetSnapshot`/`MarketState`) —
nothing downstream may read data outside that window. This is what makes
every number in this handbook reproducible: the same `as_of` date and the
same stored evidence always produce the same output.

---

## Chapter 2 — Data Foundations

1. **Collection.** Every data source is a declared `SourceSpec` in a
   central registry, with a status (`IMPLEMENTED`/`PLANNED`/etc.) — a
   source is only ever collected from once its status is `IMPLEMENTED`,
   which itself requires a maintainer to have confirmed real content
   parses correctly, not merely that an endpoint is reachable. Every
   fetch respects robots.txt, per-source rate limits, and retry/backoff;
   no NEEDS_KEY (paid API) sources exist by explicit platform policy —
   only genuinely free, legal sources.
2. **Provenance.** Every fetched payload is wrapped in a `RawDocument`
   (source, collector, content hash, license) before anything is
   extracted from it — the full chain from a final number back to the
   exact document it came from is always walkable.
3. **Quality gating.** Every collected batch is scored by
   `assess_quality()` before being materialized into the canonical data
   layer; a batch scoring below the confidence floor is **withheld
   entirely**, never passed through degraded — "no downstream system may
   ignore data quality" is enforced by withholding, not by flagging.
4. **Adjustments.** Every return calculation goes through
   `data.adjustments.adjusted_returns_for_ticker()` (or
   `adjusted_dated_returns()`), which applies real, dated stock-split and
   dividend corporate events — a raw `close`-to-`close` return is never
   used anywhere in this platform, because a split or dividend would
   otherwise look like a fabricated windfall or loss. Adjustment factors
   use the last **cum-dividend** close strictly before the ex-date, never
   the ex-date close itself.
5. **Point-in-time discipline.** Financial statements and macro series
   are only visible to any computation once their real, declared
   publication lag has elapsed — no computation may see a number before
   it was actually knowable, even if the underlying data file already
   contains it (this is what prevents look-ahead bias structurally,
   rather than by convention).

---

## Chapter 3 — Agents: Evidence Generation

Eight real agents each produce `ResearchFinding` objects from a
`DatasetSnapshot` — agents **propose, they never decide**, and never
write to any store directly:

| Agent | Evidence category | What it evaluates |
|---|---|---|
| `MacroAgent` | Macro | Sensitivity to macro series (currency, commodities, rates once collected) |
| `MarketStructureAgent` | Sector (closest real proxy — no dedicated sector-peer computation exists yet) | Cross-ticker co-movement/correlation |
| `CorporateEventsAgent` | Catalyst | Real corporate events (earnings, dividends, buybacks, management changes) |
| `LiquidityAgent` | Liquidity | Trading-volume/traded-value patterns |
| `TechnicalStructureAgent` | Technical | Price-pattern findings |
| `NewsIntelligenceAgent` | Catalyst | Headline-keyword sentiment feeding a mechanical event-study-lite signal |
| `HistoricalPatternsAgent` | Technical | Analog-matching against prior events |
| `FinancialPerformanceAgent` | Quality | Real revenue-growth-trend and leverage-trend findings from financial statements |

A ninth category, **Value**, is not agent-produced — it comes from the
Fair Value Engine (Chapter 5) blended in separately at the recommendation
stage. A tenth and eleventh, **Risk** and **Execution**, are modifiers on
the final decision (gates/multipliers), never additive contributors —
see Chapter 5's attribution model.

---

## Chapter 4 — Hypothesis Validation: The Gate Pipeline

A `ResearchFinding` becomes a `Hypothesis` and walks a fixed, ordered gate
pipeline before it can ever become knowledge. The default pipeline
(`hypotheses.pipeline.DEFAULT_PIPELINE`) is:

**1. OBSERVATION → 2. HYPOTHESIS → 3. DATA_COLLECTION → 4. EXPERIMENT →
5. STATISTICAL_VALIDATION → 6. STRESS_TEST → 7. BACKTEST →
8. PEER_VALIDATION**

Gates are configurable data (`GateSpec(name, order)`), not hardcoded
control flow — a different pipeline can add or reorder stages for a
different asset class or horizon, but no live pipeline may skip a
configured gate. A hypothesis revision persists via its repository even
when it fails and is never promoted — failed research is not deleted, it
is recorded.

Three additional, independent layers of scrutiny apply on top of the
pipeline itself, all of which must pass:

- **The Economic Rationale Gate**
  (`causal.reasoner.EconomicRationaleGate`) — refuses any hypothesis
  relying on correlation alone. Requires a stated candidate cause **and**
  a stated economic rationale; passing caps confidence at `0.5` (it
  verifies a rationale was stated, not that it is correct).
- **The Scientific Review Board** (`review.board.ScientificReviewBoard`)
  — runs every configured reviewer; approval requires **all** reviewers
  that actually ran to pass. A reviewer raising `NotImplementedError` is
  skipped, never counted as a pass — a board with zero working reviewers
  can never approve anything.
  - `StatisticianReviewer`: `p_value < 0.05` **and** `sample_size ≥ 30`.
  - `RiskReviewer`: `expected_risk ≤ 0.10` (10% ceiling).
  - `EconomistReviewer`: rationale ≥ 40 characters, engages the specific
    asset/sector or a recognized economic-mechanism term (flow, margin,
    rate, demand, supply, cost, currency, liquidity, earnings, dividend,
    index, sector, export, import, inflation, capital), and the causal
    gate passed.
  - `PeerValidatorReviewer`: an independent replication (2-fold
    cross-validation, a 300-iteration bootstrap with a different seed)
    must reproduce the same statistical sign **and** remain significant
    at `α = 0.05`.
  - `HistoricalReviewer` is a real interface, not yet implemented — it
    needs a historical-analog database of labeled market episodes this
    platform does not have yet. It is **skipped**, not faked.
- **The Adversarial Scientist** (`adversarial.scientist.AdversarialScientist`)
  — actively attacks the surviving confidence rather than accepting it.
  Nine named attack types: random coincidence, small-sample bias, time
  leakage, look-ahead bias, overfitting, parameter instability, regime
  dependency, out-of-sample degradation, weak economic rationale. A
  successful attack (finds a real problem) lowers confidence; an
  attempted attack that genuinely finds nothing raises it; an attack
  never attempted reports `attempted=False`, never assumed passed.

Only a hypothesis that survives all of this becomes a `KnowledgeObject`.

---

## Chapter 5 — Knowledge Lifecycle and Prediction

### 5.1 Lifecycle

`KnowledgeStatus`: `PROMOTED → MONITORING → RETIRED`, one-directional
(`knowledge.lifecycle.can_transition`) — knowledge can only move toward
retirement, never back to a less-scrutinized state.

### 5.2 Prediction

`horizons.knowledge_weighted.KnowledgeWeightedHorizonModel.predict()`
aggregates every non-retired `KnowledgeObject` covering the ticker and
horizon:

```
expected_return = Σ(confidence_i × expected_return_i) / Σ(confidence_i)
expected_risk   = Σ(confidence_i × expected_risk_i) / Σ(confidence_i)
confidence      = min(mean(confidence_i), max(confidence_i))
                  # mean is always ≤ max, so this is exactly the plain
                  # arithmetic mean of confidences — deliberately not a
                  # confidence-weighted mean, so one very-high-confidence
                  # source cannot inflate the aggregate merely by having a
                  # large weight in its own average.
```

No knowledge covering the ticker/horizon means **no prediction at all** —
never a guess.

**Real events inflate risk and deflate confidence, multiplicatively.**
Any real, confirmed/corroborated `Event` affecting the ticker (or the
whole `EGX` market entity) within the last 30 days, whose
`impact_horizons` include this horizon, applies a severity-weighted
penalty before the prediction is finalized:

```
severity_penalty = {LOW: 0.02, MEDIUM: 0.05, HIGH: 0.12, CRITICAL: 0.25}
event_risk = min(0.50, Σ severity_penalty[event.severity] × event.confidence)
expected_risk *= (1 + event_risk)
confidence    *= (1 − event_risk)
```

This is the mechanism behind `docs/INVESTMENT_CONSTITUTION.md` Article
X's Risk modifier and `docs/INVESTMENT_PLAYBOOK.md`'s political-risk/
liquidity-crisis entries: a real, active, corroborated event pushes a
prediction toward more caution automatically, capped at a 50% combined
penalty so no single event (or pile of low-severity ones) can zero out a
prediction outright.

### 5.3 Combination into a Recommendation

`meta.decision_engine.MetaDecisionEngine.decide()` combines whichever
horizons have a prediction into one `Recommendation`, per-horizon
(never blended across horizons):

```
score = expected_return × confidence / max(expected_risk, 1e-9)

action = ABSTAIN        if confidence < 0.60
       = ABSTAIN         if action would be BUY_CANDIDATE but no reference price exists
       = AVOID            if expected_return ≤ 0
       = BUY_CANDIDATE   if score ≥ 1.0
       = WATCH            otherwise
```

A `BUY_CANDIDATE` also computes a real entry condition (at or below the
reference price), an invalidation level
(`reference_price × (1 − risk_buffer)`, `risk_buffer = clamp(expected_risk, 0.02, 0.25)`),
and a review condition — every executable-looking decision carries real,
numeric levels, never a bare label.

### 5.4 Value Blend

`meta.recommendation_service` blends the Fair Value Engine's implied
return into the INVESTMENT-horizon prediction at a fixed
`FAIR_VALUE_INVESTMENT_WEIGHT = 0.20` (20%) — the remaining 80% is the
knowledge-weighted return above. The Fair Value Engine
(`valuation.engine.FairValueEngine`) computes up to 7 models (DCF 30%,
DDM 10%, Residual Income 15%, Earnings Power 15%, EV/EBITDA 10%, P/E 10%,
P/B 10% — weighted by `MODEL_WEIGHTS`), requires **at least 3 valid
models within 3× of the median** to produce a result at all, and uses
declared assumptions (`risk_free_rate=12.5%`, `equity_risk_premium=7%`,
`beta=1.0`, `WACC=16%`, `terminal_growth=4%`, `tax_rate=22.5%`). No fair
value, no Value contribution — never fabricated from an incomplete model
set.

---

## Chapter 6 — Readiness and Publication: The Two Gates Before Any Real Consequence

### 6.1 Decision Readiness (`meta.readiness.assess_decision_readiness`)

Per-horizon blockers, evaluated per ticker:

| Horizon | Blocking conditions (any one blocks that horizon) |
|---|---|
| MICRO | <60 price observations; stale price (>7 days old); no active MICRO knowledge; illiquid |
| SWING | <120 price observations; stale price; no linked news/corporate event; no active SWING knowledge; illiquid |
| INVESTMENT | <252 price observations; stale price; no fair value from ≥3 models; price >20% above fair value; <3 macro series; insufficient exchange-rate data; no active INVESTMENT knowledge; illiquid |

A ticker is `READY` only if at least one horizon is unblocked **and**
active knowledge exists; `DEGRADED` if prices exist but nothing is ready;
`BLOCKED` if no price history exists at all.

### 6.2 Decision Quality Gate (`meta.decision_quality.evaluate_decision_quality`)

**Superseded 2026-08-02** (see `docs/ARCHITECTURE_DECISIONS.md`): until
this date, §6.2 described a system-wide, six-check publication gate —
live EGX market data, four periods of official disclosures, current
CBE/CAPMAS macro data, two-source price corroboration, 30+ per-horizon
benchmark-outperforming results, and human legal review, **all**
required *simultaneously, for every ticker*, before *any* decision could
ever size a position. None of these had ever been satisfied once in this
platform's history, so every decision stayed `RESEARCH_ONLY` regardless
of how complete or well-evidenced it was.

The project owner's explicit correction: publication should be governed
by decision quality, not by how much track record has accumulated or
whether a human has formally signed off. Those two other concerns still
matter — as separate, non-blocking layers:

- Historical track record and an optional human governance review now
  only ever *label* system credibility (§6.2b below) — they never gate
  whether a decision publishes.
- The gate itself moved to being evaluated **per ticker per horizon**,
  directly against that decision's own `Explanation`/`HorizonDecision`,
  never as one system-wide switch. Six checks, all required for **that
  specific decision**:

1. Supporting evidence is present and traceable (`supporting_evidence`/
   `evidence_refs` both non-empty on the relevant horizon's `Prediction
   .explanation`).
2. The investment thesis is complete (`why_this_stock`/`why_now`/
   `why_not_others` all stated, not blank).
3. Confidence was actually calculated (a finite number in `[0, 1]`).
4. Invalidation conditions are defined (`HorizonDecision
   .invalidation_conditions` non-empty).
5. Entry and review (monitoring) conditions are defined (`entry_condition`/
   `review_condition` both real statements).
6. The decision is internally consistent — a `BUY_CANDIDATE` carries
   numeric `entry_value`/`invalidation_value`.

`apply_decision_quality_gate()` then, for every horizon decision:
- Sets `publication_status = PUBLICATION_READY` only if that decision's
  own quality report passed **and** the action isn't `ABSTAIN`.
- Sets `max_position_pct = clamp(confidence × 0.05, 0.01, 0.05)` only when
  `PUBLICATION_READY` **and** `BUY_CANDIDATE`; otherwise `0.0`.
- Appends every failed check's blocker to `abstention_reasons` when the
  gate didn't pass — never a silent zero with no explanation.

`dashboard.validate`'s cross-artifact safety check independently
re-derives this same per-decision verdict from each shipped
recommendation's own data before allowing a dashboard build to pass —
there is no separate global report file left to trust instead.

### 6.2b System Maturity (`meta.system_maturity.compute_system_maturity`) — informational only

Reports one of five levels — `early` / `validating` / `developing` /
`established` / `verified` — from real `decision_ledger.json` history,
using exactly the math §6.2's old check 5 used (30+ benchmark-evaluated
results per horizon, `mean_excess_return > 0`, `median_excess_return > 0`,
`excess_return_lower_95 > 0`). `verified` additionally requires a valid,
dated human governance review (reviewer, scope, evidence, conflicts
disclosed, methodology approved, not expired — the same shape §6.2's old
check 6 used, now optional and decoupled). `agx publication-status`
reports this and always exits `0` — there is no "blocked" outcome left
to signal. Nothing here is read by, or gates, `agx decide`/`agx run`.

---

## Chapter 7 — Position-Aware Decisions

`decision_service.service.DecisionService.decide_portfolio()` is the
layer a real investor sees. It is **stateless-per-call, queried on
demand only** — never wired into the autonomous daily pipeline, because
it requires externally-supplied `PositionState` (a real portfolio's
holdings) that no autonomous run can discover.

**Step 1 — score every ticker jointly.** For every ticker with a
`Recommendation` union every currently-held ticker:

```
eligible = (INVESTMENT decision.action != ABSTAIN)
           AND (publication_status == PUBLICATION_READY)
score    = risk_adjusted_score if eligible else 0.0
total_positive_score = Σ max(score, 0) across all tickers
```

**Step 2 — compute a joint target weight:**

```
target_weight = min(
    max(score, 0) / total_positive_score,
    max_position_weight (0.25),
    max_position_pct (0.01–0.05, from the publication gate)
) if total_positive_score > 0 and score > 0 else 0.0
```

**Step 3 — apply hard overrides**, unconditionally after Step 2:
- If the ticker is below the liquidity floor (EGP 1,000,000 average
  daily traded value): `target_weight = 0.0`.
- If Country & Macro Risk severity is `CRISIS`: `target_weight = 0.0`
  for **every** ticker.

**Step 4 — resolve abstention** (see `docs/DECISION_STANDARDS.md` §7 for
the full rule) — sets `abstained = True` with real, stated reasons
whenever no evidence exists, the research verdict is itself `ABSTAIN`, or
the publication gate blocked it.

**Step 5 — resolve the six-way label** by comparing `target_weight` to
`current_weight` (`docs/DECISION_STANDARDS.md` has the complete table).

**Step 6 — build the full explanation.** Every decision computes:
`investment_thesis` (one deterministic sentence from the decision's own
numbers), `key_risks` (the model's own risk metric plus any disagreeing
sibling-horizon signal), `contradicting_evidence` (disagreeing sibling
horizons plus active country-risk findings), `active_catalysts` (real,
already-collected upcoming corporate events), `monitoring_events` (which
supporting knowledge is currently `MONITORING`), and `expected_review_date`
(the decision's own `valid_until`).

---

## Chapter 8 — Capital Allocation

`capital_allocation.CapitalAllocationEngine` reads
`DecisionService`'s output only — it never re-derives eligibility or
scoring. Same on-demand-only posture as `DecisionService` (there is
nothing to rank or recycle without real capital and real holdings).

**Step 1 — rank.** Every decision, sorted by `opportunity_score`
descending (ties broken by ticker), gets `rank = 1..N`. Includes every
ticker evaluated, not only the funded ones.

**Step 2 — compute the effective target.** An abstained decision's
`current_weight` is used in place of its raw `target_weight` for every
flow computation — an evidence gap never counts as a real capital
release (`_effective_target()`).

**Step 3 — match capital flows**, deterministically:
- Demanders (`effective_target > current_weight`) are walked
  best-rank-first.
- Suppliers (`current_weight > effective_target`) are walked
  weakest-rank-first (highest rank number first).
- Each demander draws from idle cash first
  (`1 − Σ current_weight` across all decisions), then from suppliers in
  order, recording one `CapitalFlow(from, to, amount)` per unit matched.
- Any supplier capital left unclaimed after all demand is met flows back
  to cash (`CapitalFlow(from=ticker, to=None, amount=remainder)`).

**Step 4 — assemble the plan**, all derived from Step 3's flow ledger,
never a second independent computation:
- **Ranking** — every ticker, ranked.
- **Deployment Queue** — one entry per demander: priority (rank), target
  allocation, capital delta, expected contribution
  (`capital_delta × expected_return`), marginal benefit
  (`opportunity_score`), marginal risk (`expected_risk`), capital
  sources, a human `required_action` sentence, and an
  `opportunity_cost_note` naming the best-ranked idea currently without
  capital.
- **Capital Released Today** — one entry per supplier, with named
  destinations.
- **Capital Recycled** — every flow where both ends are real tickers
  (true ticker-to-ticker recycling, excluding cash-only flows).
- **Best New Opportunities** — top-ranked demanders with
  `current_weight ≈ 0` (genuinely new positions, not top-ups).
- **Highest Opportunity Cost** — top-ranked tickers with positive
  `opportunity_score` but zero funding: real, evidence-backed ideas
  outranked by something stronger.
- **Allocation Changes** — every mover (demander or supplier), one flat
  list sorted by magnitude of change.
- **Cash Waiting** — idle cash before/after, with an explicit,
  human-readable reason for any capital left unallocated.

---

## Chapter 9 — Portfolio Construction and Validation

Two parallel construction paths exist and must never be confused
(`CLAUDE.md`'s standing warning):

- **Position-unaware** (`portfolio.constructor.PortfolioConstructor`) —
  autonomous, safe to run on a schedule, considers the best eligible
  decision across *any* horizon (not INVESTMENT-only). Produces the
  "model portfolio" shown when no real holdings exist.
- **Position-aware** (`decision_service.service.DecisionService`) —
  on-demand only, INVESTMENT-horizon only, requires real
  `PositionState`. Produces the real, personalized six-way decisions.

`investment_proof.portfolio_validation.PortfolioValidationEngine`
independently checks both: Herfindahl concentration (§`docs/
PORTFOLIO_STANDARDS.md` §1), sector concentration (§2), weight
reconciliation, liquidity violations, an explicitly-named
`expected_downside_proxy` (weighted-average `expected_risk` across held
positions — never presented as a true VaR, which would need a real
covariance matrix this platform does not have), and `decision_conflicts`
between the two paths.

---

## Chapter 10 — Monitoring: What Changed Since the Last Decision

`dashboard.monitoring.build_warnings()` derives every warning from an
already-computed, real signal — never a new judgment invented for the
monitoring layer:

| Category | Real trigger |
|---|---|
| `broken_thesis` | A knowledge object behind a recommended ticker was `RETIRED` within the last 14 days — scanned across the *whole* knowledge store, not just current positions, since a retirement is exactly what can drop a ticker out of the model portfolio entirely |
| `macro_risk_increased` | `CountryRiskAssessment.severity != NORMAL` |
| `catalyst_expired` | A corporate event fell within the last 7 days for a recommended ticker |
| `liquidity_deterioration` | A recommended ticker fell below the liquidity floor |
| `portfolio_concentration` | Herfindahl or sector concentration crossed its ceiling |
| `review_required` | A decision's `valid_until` has passed, or its supporting knowledge entered `MONITORING` |

Every warning carries a `severity` (`info`/`warning`/`critical`) and a
`detail` string naming the real number/date behind it.

---

## Chapter 11 — Continuous Learning: How the Platform Corrects Itself

`learning.monitor.ContinuousLearningMonitor.evaluate(as_of)`, for every
non-retired knowledge object:

1. Computes its **realized** mean forward return from real, later
   observed market data (`data.adjustments.horizon_forward_returns`) —
   never simulated.
2. Appends a `PerformanceRecord` to the knowledge object (and its
   lineage `Gene`) — full pre-retirement history is preserved, never
   overwritten.
3. Transitions `PROMOTED → MONITORING` on the first performance record.
4. **Retires** the knowledge (`MONITORING → RETIRED`) once, with at least
   `min_records = 3` observations, the realized return's sign disagrees
   with the original expected-return sign in a **strict majority** of
   records (`disagreements × 2 > len(records)`). The exact count is
   recorded in the retirement reason.

`investment_proof.thesis_survival.ThesisSurvivalEngine` separately
compares a specific `PositionAwareDecision` against a later
re-evaluation of the same ticker and labels it:

- **`alive`** — no broken assumptions, no new contradicting evidence, not
  overdue for review.
- **`weakening`** — a broken assumption or new contradicting evidence
  exists, but the current action hasn't reached `EXIT`/`REDUCE_POSITION`;
  or the review date has passed.
- **`broken`** — a broken assumption exists **and** the current action is
  `EXIT` or `REDUCE_POSITION`.
- **`expired`** — the ticker is no longer produced by a fresh
  re-evaluation at all.

Every real decision is permanently recorded in
`meta.decision_ledger.DecisionLedger` at the moment it is made, and
evaluated once its validity window expires: entry/exit price (adjusted),
gross return, a `20 bps` transaction-cost deduction, benchmark return
(against the `EGX30` ticker id), excess return, and a binary `hit`
(`excess_return > 0`). `performance_summary()` aggregates this into the
exact statistics the publication gate itself requires (Chapter 6.2 §5) —
the ledger and the gate can never silently disagree, because the gate
reads the ledger's own summary directly.

---

## Chapter 12 — Institutional Validation and Proof

Two frameworks independently stress-test the platform's own claims,
never trusting them on assertion alone:

### 12.1 Institutional Investment Validation — 10 falsification-attempting questions

1. Can the system rank the full EGX30/70 universe?
2. Can it explain every ranking?
3. Can it reject every stock if appropriate?
4. Can it recommend holding 100% cash?
5. Can it build a complete portfolio instead of isolated recommendations?
6. Can it compare recommendations against benchmark indices?
7. Can it detect when an investment thesis has failed?
8. Can it identify why a recommendation changed?
9. Can every decision be traced back to evidence?

Each answers `PASS`/`PARTIAL`/`BLOCKED`/`FAIL` with concrete evidence
from real platform code, never a mock — run via `agx validate-investment`.

### 12.2 Investment Proof Framework — the Capital Trust Report

Ten dimensions, run via `agx investment-proof`: Decision Attribution
(does the math reconcile — `attribution_residual`?), Counterfactual
Analysis (real ablation — which categories are actually decisive?),
Confidence Calibration (Brier score, expected calibration error, 30-sample
floor), Investment Thesis Survival, Portfolio Validation, Investment
Committee Validation (per-category agreement/decisiveness rates),
Decision Stability (proven determinism — same evidence run 3× must match
exactly, timestamps excluded), Walk-Forward Infrastructure (a real
day-stepping replay driver over `RecommendationService` + `DecisionLedger`;
needs ≥252 real contiguous trading days per ticker to be meaningful).
Each dimension reports `PASS`/`BLOCKED`/`READY FOR DATA` — never a
fabricated pass on data that doesn't exist yet.

---

## Chapter 13 — Glossary of Every Real Constant

| Constant | Value | Governs |
|---|---|---|
| Research confidence floor | `0.60` | Below this, `ABSTAIN` at the research level |
| Buy-candidate score floor | `1.0` | `confidence × expected_return / expected_risk` |
| Entry invalidation buffer | `clamp(expected_risk, 0.02, 0.25)` | How far below entry the invalidation level sits |
| Validity windows | MICRO 3d / SWING 28d / INVESTMENT 183d | How long a decision stays valid before review |
| `max_position_weight` | `0.25` | Structural per-position ceiling |
| Publication-gate `max_position_pct` | `clamp(confidence × 0.05, 0.01, 0.05)` | Real per-position ceiling on any published decision |
| Herfindahl concentration ceiling | `0.25` | Portfolio-level concentration |
| Sector concentration ceiling | `0.40` | Single-sector weight |
| Weight reconciliation tolerance | `0.01` | Cash + invested must sum to 1.0 within this |
| Liquidity floor | `EGP 1,000,000` | Average daily traded value |
| Currency deterioration floor | `5%` | Cumulative EGP/USD move for `DETERIORATING` |
| Price-above-fair-value ceiling | `20%` | Blocks INVESTMENT readiness above this |
| Fair-value model floor | `≥3` models within `3×` of median | Minimum for any fair value at all |
| Fair-value weight in return blend | `20%` | `FAIR_VALUE_INVESTMENT_WEIGHT` |
| MICRO/SWING/INVESTMENT price-history floors | `60` / `120` / `252` observations | Per-horizon readiness |
| Statistical significance | `α = 0.05`, `n ≥ 30` | `StatisticianReviewer` |
| Risk ceiling (review) | `10%` | `RiskReviewer` |
| Economic rationale minimum length | `40` characters | `EconomistReviewer` |
| Causal-gate confidence cap | `0.5` | Stating a cause is necessary, not sufficient |
| Continuous-learning retirement floor | `3` records, strict majority disagreement | `ContinuousLearningMonitor` |
| Thesis "recently broken" window | `14` days | Broken-thesis warning freshness |
| Catalyst "recently expired" window | `7` days | Catalyst-expired warning freshness |
| Benchmark evaluation sample floor | `30` per horizon | Publication gate + calibration + walk-forward |
| Transaction cost | `20 bps` | Applied to every realized/benchmark return |
| Benchmark 95%-confidence factor | `1.645` | `DecisionLedger`'s lower-bound excess return |
| Max drawdown floor | `≥ -25%` | Publication gate |
| Walk-forward minimum trading days | `252` (~1 EGX year) | Meaningful INVESTMENT-horizon replay |
| Market regime lookback | `20` trading days | Trend/volatility classification window |
| Bullish/bearish trend threshold | `±3%` cumulative return | `MarketTrend` |
| Elevated/high volatility threshold | `1.5%` / `2.5%` daily | `VolatilityLevel` |
| Trailing volume window | `20` trading days | Market breadth "above/below average" |

Every threshold above marked *declared, uncalibrated* throughout the
companion documents is logged in `docs/TECHNICAL_DEBT.md` with a named
repayment trigger. This handbook does not claim more precision than the
platform actually has — it states exactly what the platform does, today,
with real numbers, and names honestly where a mechanism described in
`docs/INVESTMENT_PLAYBOOK.md` is doctrine awaiting a detector that has
not been built yet.

---

## How to Rebuild This Process From This Document Alone

An engineering team with only this handbook and its three companion
documents could rebuild the investment process by implementing, in
order: (1) a point-in-time data snapshot layer with quality gating and
split/dividend adjustment; (2) independent evidence-generating agents,
one per category; (3) the 8-gate validation pipeline plus the three
independent scrutiny layers (causal gate, review board, adversarial
attacks); (4) a knowledge store with the one-directional
promoted→monitoring→retired lifecycle; (5) a per-horizon,
knowledge-weighted prediction model with the confidence-cap rule; (6) a
meta decision engine applying the exact score/confidence formulas in
Chapter 5.3; (7) the two-gate readiness/publication system in Chapter 6,
with every numeric floor as written; (8) a position-aware decision
service applying Chapter 7's six-step algorithm; (9) a capital allocation
engine applying Chapter 8's four-step algorithm; (10) portfolio
validation and monitoring exactly as Chapters 9–10 specify; (11) a
continuous-learning retirement loop and an append-only decision ledger
per Chapter 11; and (12) the validation/proof layer of Chapter 12 to
continuously verify the rebuild actually satisfies this handbook, not
merely resembles it. Every formula and threshold needed to do this is in
Chapter 13.
