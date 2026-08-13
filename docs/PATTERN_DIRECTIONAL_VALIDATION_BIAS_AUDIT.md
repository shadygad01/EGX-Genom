# Pattern Directional Validation-Bias Audit (Mission 3, Step 1.6)

**Status: analysis only. No code, registry, or prior Mission 2/Step 1/Step 1.5
artifact was modified to produce this report.** This step does not design,
implement, or advance the Pattern Promotion Gate in any way; it answers one
narrow, precise question raised by Step 1.5's report and stops.

## Executive finding

**The question:** among the 1,773 real `PatternStatus.VALIDATED` patterns
from the Mission 2 real-data run (`/tmp/agx_real_run/patterns/registry.json`,
3,398 total `DISCOVERED`-or-later patterns, 14-ticker EGX30 universe), all
1,773 have strictly positive expectancy — zero negative, zero exactly-zero.
Why?

**The answer is a mixed explanation with two independently-evidenced,
additive components** — not a single root cause:

1. **A real, positive market drift in the underlying price data
   (Component C).** The 14-ticker universe this run actually used had a
   strongly positive unconditional forward-return drift over the sample
   window — independently computed directly from the raw EGX price data
   (not from the registry) at **+0.83% mean over 5 trading days / +1.68%
   over 10 trading days**, despite an almost-coin-flip 49.2% unconditional
   up-day rate. This alone explains why **94.3% of patterns were already
   positive at the `DISCOVERED` stage** (3,202/3,398), before any
   directional gate ever runs — `discover()`'s own significance test is
   genuinely two-sided and provably sign-neutral (traced and cited below).

2. **A real, code-level "long-only" assumption baked into the robustness
   gate (Component B).** `RobustnessTester.run()` (`patterns/robustness.py`
   line 126) computes `transaction_cost_survival = net_expectancy > 0` —
   an absolute, non-sign-relative test that can never be satisfied by a
   negative-expectancy pattern regardless of market regime, and never
   evaluates the candidate as a short/inverse signal. `engine.validate()`
   (`patterns/engine.py` lines 512–533) turns `robustness_result.passed ==
   False` directly into `PatternStatus.REJECTED`. This same
   `net_expectancy > 0` construction recurs verbatim in a second, unrelated
   module (`transaction_costs.py` line 83), indicating a consistent,
   undocumented design assumption rather than a one-off accident. Of the
   511 rejections whose reason text is genuinely ambiguous between
   "perturbation sign-flip" and "fails transaction costs," **400 are
   deterministically explained by the transaction-cost floor alone**
   (`v1.expectancy − 20bps ≤ 0`), independent of any perturbation evidence.

Neither component alone is sufficient (see "Why not pure C" / "Why not pure
B" below); together they are. Full evidence, code citations, and the
classification rationale follow.

## Scope discipline

Per the Step 1.6 instructions, this audit:

- Never reads or cites Step 1's (`docs/PATTERN_CROSS_TICKER_FAMILY_COLLAPSE.md`)
  or Step 1.5's (`docs/PATTERN_FAMILY_DEFINITION_STRESS_TEST.md`) family-collapse
  results to explain the zero-negative phenomenon. Everything below is derived
  at the individual-pattern / pipeline-gate level.
- Never mutates `PatternRegistry`, never changes a `validation_status`, never
  creates a `PromotionCase`, never chooses K/HHI/BH-vs-BY, never repairs
  `family_size`, never touches Mission 2/Step 1/Step 1.5 artifacts. Verified
  by `git status --short` / `git diff --stat` showing zero changes to any
  tracked file, and by re-reading the registry's own status counts
  (unchanged: 1,773 `validated` / 1,625 `rejected` / 3,398 total) after
  running the audit script.
- Reports every finding with an exact file/function/line citation where the
  finding is code-derived, and flags explicitly what could and could not be
  reconstructed from persisted data.

## 1. Complete lifecycle trace

| Stage | n | Notes |
|---|---:|---|
| Candidates generated (`discover()`) | 7,899 | Per `TestingLedger` (`testing_ledger_b498fe448de3`, `hypotheses_tested`) |
| Candidates with an evaluable discovery-sample distribution | **unrecoverable** | `discover()`'s own `discovery_ok` count was never persisted anywhere — see §7 |
| Surviving family-corrected p-value alone (pre-BH-FDR) | 3,550 | `TestingLedger.surviving_after_family_correction` |
| Surviving family+BH-FDR → persisted `DISCOVERED` (v1) | 3,398 | = total registry pattern count; matches `TestingLedger.surviving_after_fdr` exactly |
| — of which v1 expectancy **positive** | 3,202 (94.3%) | |
| — of which v1 expectancy **exactly zero** | 192 (5.6%) | See §6, degenerate-match artifact |
| — of which v1 expectancy **negative** | 4 (0.1%) | |
| Reaching `VALIDATING` (survives `validate()`: walk-forward + robustness + baseline) | 1,880 | Per Mission 2's own report; all with positive expectancy by construction (see §3–§4) |
| Reaching `VALIDATED` (survives `final_holdout()`) | **1,773** | 100% positive expectancy |
| `REJECTED` (any stage) | 1,625 | 100% of the negative (4/4) and zero (192/192) v1 groups; 1,429/3,202 (44.6%) of the positive v1 group |

**Where negative/zero-expectancy candidates disappear, precisely:**

- Of the 7,899 generated candidates, an unknown split never even produced an
  evaluable discovery-sample distribution or failed family+BH-FDR control —
  this ~4,501-candidate gap is **irrecoverable** for this run (§7). Whatever
  their sign distribution was, it left no trace.
- Of the 3,398 that *were* persisted as `DISCOVERED`, only 4 negative and 192
  zero-expectancy candidates survived even the sign-neutral, two-sided
  discovery-stage significance test — already a striking imbalance, fully
  explained by the market-drift finding (§8/Component C), not by any
  sign-aware code at this stage (verified sign-neutral, §3).
- Every one of those 196 (4 negative + 192 zero) was rejected at the
  `validate()` stage specifically by `RobustnessTester`'s
  `transaction_cost_survival = net_expectancy > 0` gate (§4/Component B) —
  mechanically guaranteed, since `net_expectancy = expectancy − 0.002` can
  never exceed zero when `expectancy ≤ 0`.
- Of the 3,202 *positive*-v1 candidates, 1,429 (44.6%) were *also* rejected
  later — mostly (1,007, i.e. 62% of all rejections) for failing to beat
  their own ticker's positive buy-and-hold baseline (§4/§9) — showing the
  filtering pressure continues well past the sign boundary, not stopping at
  "positive vs. negative."

## 2. Candidate-level directional audit (what is and is not recoverable)

**Recoverable** (from the persisted registry, at the `DISCOVERED`/v1 stage
onward): expectancy sign/value, operator (GT/LT) of the primary condition,
ticker, target id, `is_lead_lag`, and full lifecycle status/rejection-reason
history, for exactly the 3,398 patterns that survived discovery-stage
FDR control.

**Not recoverable**: any of the above for the 4,501 candidates that were
generated but never persisted (§7). No sign, operator, ticker, or
significance-test outcome exists anywhere for that pool.

| v1 (DISCOVERED) expectancy sign | count | % of 3,398 |
|---|---:|---:|
| Positive | 3,202 | 94.3% |
| Zero (exactly 0.0) | 192 | 5.6% |
| Negative | 4 | 0.1% |

| Primary-condition operator (v1) | discovered | validated | validation rate |
|---|---:|---:|---:|
| GT (`>`) | 2,590 | 1,513 | 58.4% |
| LT (`<`) | 808 | 260 | 32.2% |

Operator × v1-expectancy-sign:

| Operator | positive | negative | zero |
|---|---:|---:|---:|
| GT | 2,405 (92.9%) | 3 | 182 |
| LT | 797 (98.6%) | 1 | 10 |

**Both operators generate candidates and both operators produce validated
patterns.** LT-conditioned survivors are, if anything, *more* likely to be
positive-expectancy than GT-conditioned ones (98.6% vs. 92.9%) — the exact
opposite of what "LT is being structurally suppressed" would predict. This
rules out a per-operator code bug as the explanation (see §5, §6).

`is_lead_lag` breakdown: all 415 lead/lag patterns use GT exclusively (0 use
LT) — because `generate_lead_lag()` (`candidates.py` lines 385–414) always
derives its condition's operator from `_median_condition()`, which is
GT-only (see §6/§8's candidate-generation note). This is a real asymmetry in
*which feature-threshold direction gets tested* for lead/lag candidates
specifically, not in the sign of the resulting outcome — lead/lag GT
survivors (49.9% validation rate) are not meaningfully different from
same-ticker GT survivors (60.0%).

## 3. Discovery-gate trace (candidate generation → `DISCOVERED`)

Traced fresh against `patterns/candidates.py`, `patterns/evaluation.py`,
`patterns/multiple_testing.py`, `patterns/multiple_testing_family.py`, and
`patterns/engine.py::discover()`.

| Gate | A. Can negative pass? | B. Under what conditions? | C/D. If no, why / intentional? |
|---|---|---|---|
| `evaluate_outcomes()`'s bootstrap p-value (`evaluation.py:43-63,85-125`) | **Yes** | Two-sided by construction: `opposite_side = sum(1 for m in means if (m <= 0) != (observed_mean <= 0))`; a strongly negative mean is exactly as "significant" as an equally strong positive one. | N/A — sign-neutral by design; this is standard two-sided significance testing, not a bug. |
| `family_corrected_p_value()` (`multiple_testing_family.py:76-77`) | **Yes** | Pure scalar penalty on the p-value by family size; never reads expectancy or sign. | N/A — sign-neutral. |
| `benjamini_hochberg()` (`multiple_testing.py:21-37`) | **Yes** | Pure rank-order FDR control on p-value magnitude. | N/A — sign-neutral. |
| **Net effect of `discover()`** | **Yes, in principle** | A negative-expectancy candidate that clears the discovery sample floor and is statistically significant (two-sided) is added to the registry as `DISCOVERED` exactly like a positive one. | **Confirmed empirically**: 4 negative and 192 zero-expectancy patterns *did* reach `DISCOVERED` (§2). The near-absence of negative survivors at this stage is a data property (§8/§9), not a `discover()`-stage code restriction. |

**Conclusion for §3: `discover()` itself is not the source of directional
selection.** It is provably sign-neutral by code, and empirically admitted
both negative and zero-expectancy candidates to `DISCOVERED` (just very few
of them, for data reasons — §9).

## 4. Validation-gate audit (`DISCOVERED` → `VALIDATING` → `VALIDATED`)

Traced fresh against `patterns/validation.py`, `patterns/robustness.py`,
`patterns/baselines.py`, and `patterns/engine.py::validate()`/`final_holdout()`.

| Gate | Sign-relative or positive-only? | Citation | Can a negative pattern pass? |
|---|---|---|---|
| `WalkForwardValidator.validate()` — OOS-vs-discovery sign agreement | **Sign-relative** (agreement, not positivity) | `validation.py:170-174`: `(oos_distribution.expectancy > 0) != (discovery_distribution.expectancy > 0)` rejects on *disagreement* | **Yes** — a consistently negative pattern (negative discovery AND negative OOS) passes this gate. |
| `RobustnessTester.run()` — `transaction_cost_survival` | **Positive-only** (hard, absolute) | `robustness.py:124-126,142-143`: `net_expectancy = base_dist.expectancy - 0.002`; `transaction_cost_survival = net_expectancy > 0`; `result.passed = agreeing_all AND transaction_cost_survival` | **No** — mathematically impossible for `expectancy ≤ 0.002` regardless of perturbation stability. |
| `engine.validate()`'s use of `robustness_result.passed` | Inherits robustness's positive-only behavior | `engine.py:512-533`: `elif robustness_result is not None and not robustness_result.passed: reason = ...` → `status` stays `REJECTED` | **No**, once robustness fails. |
| `beats_baseline()` | **Sign-relative in code** (vs. `baseline.mean_outcome`, not vs. zero) | `baselines.py:156-162`: `net_expectancy > baseline.mean_outcome` | **Sign-relative in principle**, but *empirically* anti-negative here because every one of the 14 tickers' real buy-and-hold baselines was positive (§9) — so in practice, on this real dataset, this gate also filters out negative-expectancy candidates, just not by hard-coded construction. |
| `engine.final_holdout()` — holdout-vs-validation sign agreement | **Sign-relative** (agreement) | `engine.py:673`: `(holdout_distribution.expectancy > 0) != (pattern.expectancy > 0)` | **Would** pass a consistently negative pattern, but by this point the `VALIDATING` population is already 100% positive (enforced upstream), so this gate never actually gets the chance to test a negative one on this run — see §4's holdout note below. |

**Important nuance, per the Step 1.6 instruction not to assume "negative
expectancy" means "bad pattern":** the walk-forward and final-holdout gates
are genuinely agreement-based, not positivity-based — the architecture *did*
leave room for a validated short/negative-expectancy signal. **The one gate
that forecloses that possibility unconditionally is the robustness gate's
`transaction_cost_survival` check**, which was written purely in terms of
realistic cost modeling (per its own docstring) but, as coded, only ever
tests the raw (not absolute, not direction-adjusted) expectancy against a
positive floor.

**Rejection-reason breakdown, all 1,625 `REJECTED` patterns:**

| Category | n | % of rejected | v1 expectancy (mean / range) |
|---|---:|---:|---|
| `BASELINE_failure` (failed `beats_baseline()`) | 1,007 | 62.0% | +1.11% (range +0.46% to +1.83%) — **100% were already positive** |
| `ROBUSTNESS_ambiguous` (failed `RobustnessTester.run()`) | 511 | 31.4% | +0.29% mean, range −3.96% to +2.64% — mixed sign (196 ≤ 0, 315 > 0) |
| `HOLDOUT_sign_disagreement` (failed `final_holdout()`) | 91 | 5.6% | +1.62% mean — **100% were already positive** going into holdout |
| `HOLDOUT_sample_floor` | 16 | 1.0% | +1.45% mean — **100% were already positive** |

`ROBUSTNESS_ambiguous`'s rejection text ("N/M perturbation(s) flipped sign,
*or* the pattern does not survive transaction costs") does not by itself
distinguish which of the two caused a given rejection. Recomputing
`net_of_cost = v1.expectancy − 0.002` independently for each of the 511:

- **400/511 (78.3%)** have `net_of_cost ≤ 0` — the transaction-cost floor
  *alone*, deterministically, is sufficient to explain the rejection,
  regardless of perturbation outcomes.
- **111/511 (21.7%)** have `net_of_cost > 0` — for these, a perturbation
  sign-flip must have been at least a contributing cause.

**Conclusion for §4:** the transaction-cost floor (`robustness.py:126`) is a
directly-confirmed, code-level, unconditionally positive-only gate,
responsible for at least 400 rejections outright and for excluding all 196
non-positive `DISCOVERED` survivors. The baseline-beating gate
(`baselines.py:161-162`) is sign-relative in code but, on this real dataset,
behaves identically to a positive-only filter because the real baselines it
compares against are themselves positive (§9) — it is the single largest
rejection category (62%) and its victims were *already* solidly positive,
just not positive enough to beat the market's own drift.

## 5. Operator parity — is one direction structurally prevented from surviving?

No. See the table in §2: **both GT and LT generate candidates, both reach
`DISCOVERED`, and both reach `VALIDATED`.** GT has a higher raw validation
rate (58.4% vs. 32.2%), but this tracks candidate volume and composition
(`_median_condition()`, used for every two/three-feature interaction, regime
filter, and lead/lag candidate, is GT-only — `candidates.py:189-194,388-397`
— so GT's pool includes candidate types LT never gets to compete in), not a
directional block on LT's *outcome sign*. LT-conditioned survivors are
*more* likely to be individually positive-expectancy than GT-conditioned
ones (98.6% vs. 92.9%). **The key question the Step 1.6 brief poses — "is
one direction systematically prevented from surviving" — is answered no**:
the near-absence of negative-expectancy survivors is symmetric across both
operators, consistent with a shared underlying cause (market drift, §9)
rather than an operator-specific code path.

## 6. Positive-only-selection code search

Searched `patterns/` for `abs(`, `expectancy > 0`, `mean_outcome`,
`net_expectancy`, `> 0`, one-sided constructs, sign-stripping, and
operator-inversion logic. Every match, with file/line and disposition:

| Location | Pattern | Sign-relative or positive-only? |
|---|---|---|
| `robustness.py:126` | `transaction_cost_survival = net_expectancy > 0` | **Positive-only** (the primary finding — §4) |
| `robustness.py:142-143` | `result.passed = agreeing_all AND transaction_cost_survival` | Inherits positive-only from above |
| `robustness.py:102,189,225,251` | `(dist.expectancy > 0) == base_sign` | Sign-relative (agreement) |
| `baselines.py:161-162` | `net_expectancy > baseline.mean_outcome` | Sign-relative in code, empirically anti-negative on this dataset (§4/§9) |
| `validation.py:170-174` | `(oos.expectancy > 0) != (discovery.expectancy > 0)` | Sign-relative (agreement) |
| `engine.py:673` | `(holdout.expectancy > 0) != (pattern.expectancy > 0)` | Sign-relative (agreement) |
| `decay.py:88-92` | `(live_expectancy > 0) != (pattern.expectancy > 0)` | Sign-relative (agreement); out of scope (live-monitoring, post-`VALIDATED` only) |
| `transaction_costs.py:83` | `survives_default_cost = (gross_expectancy - 0.002) > 0` | **Positive-only**, same construction as `robustness.py:126`, but **not imported by `engine.py`** — confirmed by inspecting `engine.py`'s import block — so it never itself gates a pattern's registry status. Included because it shows the same long-only assumption recurring in a second, independent module. |
| `evaluation.py:104,110,118` | `positive_sum`, `hit_rate = ... o > 0 ...`, `profit_factor` | Descriptive statistics only, not a pass/fail gate |
| `candidates.py:171,145(baselines.py)` | `abs(correlation)`, `abs(prior)` | Unrelated to outcome sign (feature-correlation pruning, growth-rate denominator) |

No `abs()` is ever applied to an *outcome*/expectancy value anywhere in
`patterns/`. No one-sided statistical test beyond the two positive-only
constructs above exists. No operator-inversion or "treat LT as a short
signal" logic exists anywhere — `live.py`'s `PatternActivation` (confirmed
by direct re-read) never emits a directional label at all
(`label: str = "ACTIVE_PATTERN"`, always), consistent with the package's own
stated intent to be direction-agnostic in its *output* vocabulary — which
makes the *hard-coded long-only economics* inside `robustness.py:126` and
`transaction_costs.py:83` an inconsistency with the package's own framing,
not a deliberate, documented design choice.

## 7. Discovery-pool loss (candidates never persisted)

- **7,899** candidates were generated by `discover()` (per `TestingLedger`).
- **3,398** survived family+BH-FDR control and were persisted as
  `DISCOVERED`.
- **4,501 (57.0%)** were generated but never appear in any artifact.

**What is and is not recoverable for that 4,501:**

- **Not recoverable, for any of the 4,501**: expectancy sign/value,
  operator, ticker, feature/target identity, raw or family-corrected
  p-value, or even whether a given one ever produced an evaluable
  discovery-sample distribution at all.
- **The specific intermediate count that would at least partly close this
  gap — `discover()`'s own `len(discovery_ok)`, i.e. how many of the 7,899
  had *any* evaluable distribution before family-correction/BH-FDR — was
  never persisted.** `DiscoveryRunReport.candidates_meeting_discovery_floor`
  exists as a field in the pydantic model (`engine.py:92`) and would have
  answered part of this question, but the report object itself is only ever
  returned to the CLI caller for one run, never written to a repository —
  confirmed by checking `research/src/agx_research/storage/` usage: no
  `DiscoveryRunReport` repository exists, and no copy of it survived from
  this specific run in `/tmp/agx_real_run` or anywhere else in this
  environment. `docs/PATTERN_DISCOVERY_FINAL_HOLDOUT.md`,
  `docs/PHASE_STATUS.md`, and `docs/TECHNICAL_DEBT.md` (checked directly)
  quote only `candidates_generated=7,899` and `patterns_discovered=3,398` —
  never the intermediate count.
- This is a genuine, structural epistemic gap, not an oversight of this
  audit. Closing it for a *future* run is possible (persist
  `DiscoveryRunReport`, or add candidate-level logging), but nothing closes
  it for *this* run — re-running `discover()` now would produce new
  candidates on a re-materialized panel, not a reconstruction of the
  original 7,899.

**Why this does not block a classification (§9):** the decisive evidence for
both components of this audit's conclusion — the 94.3%-positive-at-
`DISCOVERED` finding and the exact code citations for the robustness/
baseline gates — comes from data and code that *were* fully recoverable.
The unpersisted 4,501 could, in principle, contain information that shifts
the *exact* magnitude of the market-drift effect at the true candidate-
generation level, but cannot overturn either of the two directly-cited
code-level gates, which apply regardless of what the unpersisted pool
contained.

## 8. Family analysis — explicitly out of scope, confirmed unused

Per the Step 1.6 instruction, this audit never reads or reasons from Step
1's 22-family result or Step 1.5's 22/62/605-family stress test. Every count
above is derived directly from individual `Pattern` records and the
`TestingLedger`, never from any family grouping. Family analysis cannot
create sign variance where the underlying pattern population has none, and
this audit does not rely on it to explain anything.

## 9. Supporting evidence: independent market-drift check

Computed directly from the raw EGX price data
(`research/data/community_prices_seed/normalized/prices/*.csv`), for
exactly the 14 tickers this real run used, **independent of the pattern
registry**:

| Horizon | n (pooled across 14 tickers) | mean forward return | median | % positive days |
|---|---:|---:|---:|---:|
| 5 trading days | 15,522 | **+0.83%** | 0.0% | 49.2% |
| 10 trading days | 15,452 | **+1.68%** | +0.39% | 51.8% |

Per-ticker mean 5-day forward return ranged from +0.00% (ORAS) to +1.44%
(EGAL) — **every one of the 14 tickers had a non-negative mean**, several
above +1%.

**Caveat, stated explicitly:** this is computed from raw, unadjusted close
prices, not the platform's own corporate-action-adjusted return pipeline
(`data.adjustments.adjusted_returns_for_ticker()`). It is reported as
corroborating, order-of-magnitude evidence for a real positive nominal
price drift over the sample window — plausible given EGX's known nominal
volatility/devaluation-driven equity inflation over 2022–2025 — not as a
recomputation of any registry field, and not as a claim about real
(inflation-adjusted) returns.

The near-50% up-day rate alongside a clearly positive mean return is the
important structural detail: **it is not that prices went up more often —
it is that up moves were larger than down moves**, consistent with a
market experiencing periodic large nominal repricings. This is exactly the
kind of regime that would make almost *any* conditioned subsample of
forward returns skew positive in expectation, regardless of which feature
or threshold direction (GT/LT) defined the condition — matching the
observed near-symmetric-across-operators positive skew in §2/§5.

## 10. Required classification

**Category E — Mixed explanation**, with two independently-evidenced,
non-overlapping components:

**Component C (statistical/data-generating asymmetry):**
- 94.3% of `DISCOVERED` patterns were already positive before any
  directional gate runs (§1), and `discover()`'s significance test is
  provably sign-neutral (§3).
- Independently-computed real price data shows a genuine positive drift
  (+0.83%/5d, +1.68%/10d) across every ticker in the actual universe used
  (§9).
- Both GT- and LT-conditioned survivors are overwhelmingly positive (§2,
  §5), ruling out an operator-specific code cause for the pre-gate skew.
- 1,007 rejections (62% of all rejections) were of *already-positive*
  candidates failing to beat a real, positive market baseline (§4) — only
  possible because the baseline itself is driven by real positive drift.

**Component B (accidental implementation bias):**
- `robustness.py:126`'s `transaction_cost_survival = net_expectancy > 0` is
  a hard, absolute, non-sign-relative floor that mechanically forecloses
  any negative-expectancy pattern in any market regime (§4, §6) — verified
  to be the deterministic sole cause of at least 400 of the 1,625
  rejections (§4).
- The identical construction recurs in an unrelated module
  (`transaction_costs.py:83`), indicating a consistent, undocumented
  long-only assumption across the package, not a single accidental line
  (§6).
- No docstring or design document anywhere in `patterns/` (all read fresh
  for this audit) frames this as deliberate directional selection —
  `robustness.py`'s own docstring frames the check purely as cost realism,
  and `live.py`'s docstring frames the package's *output* as deliberately
  direction-agnostic, in tension with this hard-coded long-only gate.

**Why not pure C:** the market-drift explanation alone does not predict the
400 deterministic transaction-cost rejections, nor the recurrence of the
identical `net_expectancy > 0` code pattern in a second module — a
mechanism exists that would reproduce part of this bias even in a flat or
negative-drift market.

**Why not pure B:** the code-level gate alone does not explain why 94.3% of
candidates were *already* positive at `DISCOVERED`, before that gate (or any
gate) ever runs — `discover()`'s significance test is directly verified
sign-neutral, so the pre-gate skew must trace to the data, not to engine
code.

**Why not A (intentional directional selection):** no code, comment,
docstring, or design document anywhere in `patterns/` states or implies
"reject negative-expectancy patterns because only long positions are
tradeable," or any equivalent. The absence of any such statement across
every file read for this audit (`candidates.py`, `engine.py`,
`evaluation.py`, `validation.py`, `robustness.py`, `baselines.py`,
`multiple_testing.py`, `multiple_testing_family.py`, `decay.py`, `live.py`,
`transaction_costs.py`, `registry.py`) is the basis for ruling this out.

**Why not D (undetermined/unrecoverable):** sufficient evidence was
*directly* recoverable — from the persisted registry, the testing ledger,
and an independent recomputation from raw real price data — to support both
components above with specific counts and exact code citations. The
genuinely unrecoverable piece (the ~4,501-candidate discovery-pool loss,
§7) does not block this classification, since it cannot overturn either the
94.3%-positive-at-`DISCOVERED` finding or the direct code citations, both of
which stand independently of what that unpersisted pool contained.

## 11. Limitations (stated explicitly, not implied)

1. The exact `discover()`-stage `len(discovery_ok)` intermediate count (how
   many of the 7,899 candidates had *any* evaluable distribution before
   family-correction/BH-FDR) was never persisted and cannot be
   reconstructed for this run (§7).
2. The per-candidate operator/sign/ticker identity of the 4,501 candidates
   that never reached `DISCOVERED` is permanently unrecoverable for this
   specific run (§7).
3. The market-drift corroborating check (§9) uses raw, unadjusted close
   prices, not the platform's own corporate-action-adjusted return
   pipeline — reported as directional/order-of-magnitude corroborating
   evidence only, not a recomputation of any registry field.
4. `beats_baseline()`'s exact `baseline.mean_outcome` value used for each
   individual `BASELINE_failure` rejection was never persisted on the
   `Pattern` record (computed ephemerally inside `validate()`, never
   stored) — this audit infers the mechanism from the code
   (`baselines.py:156-162`) plus the independently-computed per-ticker
   drift (§9), not from a stored per-pattern baseline value.
5. This audit covers exactly one real run (the same one Step 1/Step 1.5
   analyzed). It says nothing about whether a different sample window, a
   different universe, or a future bear-market run would reproduce the same
   94.3%-positive-at-`DISCOVERED` skew — Component C's magnitude is
   necessarily specific to this window's real market drift.

## Reproducibility

- `research/scripts/audit_pattern_directional_validation_bias.py` is fully
  deterministic (no RNG, no wall-clock-dependent fields): running it twice
  produced **byte-identical** `research/data/pattern_directional_validation_bias_audit/analysis.json`
  output (verified via direct `diff`, not just a timestamp-excluded
  comparison).
- `uv run ruff check research/scripts/audit_pattern_directional_validation_bias.py`
  passes with zero errors.
- `uv run python research/scripts/check_truth_preservation.py` reports
  clean (no fabrication patterns detected).
- `git status --short` / `git diff --stat` confirm zero changes to any
  tracked file — only the two new Step 1.6 files
  (`research/scripts/audit_pattern_directional_validation_bias.py`,
  `research/data/pattern_directional_validation_bias_audit/analysis.json`)
  are untracked additions.
- The registry's own status counts were re-verified unchanged after running
  the audit script: 3,398 total patterns, 1,773 `validated`, 1,625
  `rejected` — identical to the counts Step 1 and Step 1.5 both recorded.

## Compliance with hard boundaries

This step did not: design or implement the Promotion Gate; choose a family
definition, K, HHI, or BH-vs-BY; repair `family_size`; modify any production
code, the registry, or any pattern's status; create a `PromotionCase`
entity; or commit/push anything (per instruction — all Step 1.6 files
remain uncommitted, exactly like the Step 1/Step 1.5 files before them).

---

## Reproduction notice (added when committed to `mission-3-audit-evidence`)

This report and its accompanying script/JSON are a **same-session
reproduction**, not the byte-for-byte original artifact from the turn that
first produced Step 1.6. This repository's working tree does not persist
uncommitted files across turns in this environment, so the original,
uncommitted Step 1.6 files were lost before this preservation step began.

This reproduction was made by re-writing
`research/scripts/audit_pattern_directional_validation_bias.py` from the
exact source text captured earlier in the same conversation (not from
memory of its behavior), and re-running it against the same real,
independently-verified-unchanged registry
(`/tmp/agx_real_run/patterns/registry.json`: 3,398 total / 1,773
`validated` / 1,625 `rejected`, identical before and after). Re-running the
recreated script reproduced the exact same figures already reported in this
document (v1 sign counts `{'positive': 3202, 'negative': 4, 'zero': 192}`;
rejection categories `{'BASELINE_failure': 1007, 'ROBUSTNESS_ambiguous':
511, 'HOLDOUT_sample_floor': 16, 'HOLDOUT_sign_disagreement': 91}`), and the
script's own two-run output was byte-identical. No threshold, family
definition, or historical finding was altered, improved, or reinterpreted
in producing this reproduction.
