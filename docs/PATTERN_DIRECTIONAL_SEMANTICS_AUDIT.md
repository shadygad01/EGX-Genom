# Pattern Directional Semantics & Economic Validity Audit (Mission 3, Step 1.7)

**Status: analysis only.** No code, registry data, validation status, or
`PromotionCase` record was modified. This step does not design or implement
the Pattern Promotion Gate.

## Critical provenance notice (read first)

Before starting this step's investigation, this session checked whether
Step 1 and Step 1.5 artifacts still exist on disk, per the explicit
provenance requirement.

**They do not — and neither do Step 1.6's.** This session's working tree
does not persist uncommitted files across turns: even Step 1.6's own
report, script, and JSON output — produced and delivered to the user
earlier in this *same* conversation — were absent from disk at the start of
this step. `git status` was clean before this step began.

Per the provenance requirement, this is reported honestly rather than
silently regenerated:

- **Step 1 and Step 1.5 artifacts are missing and were NOT reproduced.**
  Step 1.7 does not need their family-collapse output — directional
  semantics is analyzed at the individual-pattern/code level, the same
  scope discipline Step 1.6 already established (family grouping cannot
  create or remove directional meaning). No reproduction was attempted.
- **Step 1.6's specific reconciliation *figures*** (not the missing file
  itself) **were independently recomputed this session**, directly from
  the registry, by `research/scripts/audit_pattern_directional_semantics.py`.
  This is labeled explicitly as `"source": "recomputed_this_session"` in
  the JSON output, not claimed as a byte-identical retrieval of the
  original file. The recomputation is trustworthy because the registry
  itself was independently re-verified unchanged (3,398 total / 1,773
  `validated` / 1,625 `rejected` — identical to every count Step 1.6, Step
  1, and Step 1.5 all reported), and the recomputation reproduced the same
  figures reported to the user in this conversation (94.3% positive at
  `DISCOVERED`, GT 2,590/LT 808 discovered, 400/511 robustness-ambiguous
  rejections deterministically explained by the transaction-cost floor).

## Executive conclusion

**Classification: C — Direction semantics are missing/ambiguous.**

A negative-expectancy pattern in the current architecture is **not**
provably a failed long signal (A), **not** demonstrably a valid short/
inverse signal (B or D) — and **not** excluded by any explicit long-only
mandate (which would be D under the objective's own framing). It falls into
**C: interpreting it economically requires directional metadata that does
not currently exist anywhere in this system.**

The system's actual behavior is an **undocumented, emergent long-only
assumption**, baked into two specific gates
(`robustness.py:126`, `baselines.py:161-162`), that stands in direct
tension with `live.py`'s own explicit framing of pattern output as
direction-agnostic ("deliberately never a BUY/SELL recommendation"). No
authoritative document — `docs/VISION.md`, `MASTER_PROMPT.md`, the
investment doctrine set, or `patterns/`'s own mission-derived docstrings —
states a long-only mandate, checked directly (grep-verified, zero
matches for "long-only," "short-sell," "short signal," or "direction-
agnostic" in any of the six authoritative documents searched). This is an
unresolved internal inconsistency, not a deliberate design choice.

**A negative-expectancy pattern should currently be read as: "a
statistically real effect on `forward_return` whose economic meaning is
undetermined without further architectural work" — not as "noise," and
not as "a validated short opportunity."**

## 1. Authoritative design-intent evidence

Searched `docs/VISION.md`, `MASTER_PROMPT.md`,
`docs/PATTERN_DISCOVERY_DATA_AUDIT.md`, `docs/INVESTMENT_CONSTITUTION.md`,
`docs/DECISION_STANDARDS.md`, and `docs/PORTFOLIO_STANDARDS.md` for any
explicit statement of long-only, direction-agnostic, or long+short intent.

| Document | "long-only" | "short-sell(ing)" / "short signal" | "direction-agnostic" |
|---|---|---|---|
| `docs/VISION.md` | not found | not found | not found |
| `MASTER_PROMPT.md` | not found | not found | not found |
| `docs/PATTERN_DISCOVERY_DATA_AUDIT.md` | not found | not found | not found |
| `docs/INVESTMENT_CONSTITUTION.md` | not found | not found | not found |
| `docs/DECISION_STANDARDS.md` | not found | not found | not found |
| `docs/PORTFOLIO_STANDARDS.md` | not found | not found | not found |

**Conclusion: undocumented/ambiguous.** None of the platform's authoritative
design documents make any explicit statement about trade direction for
pattern discovery specifically.

The clearest *indirect* signal comes from `decision_service/`'s
`PositionAction` enum (`service.py`) — the only place in this entire
codebase where an actual trade action is emitted:

```
BUY = "buy"
INCREASE_POSITION = "increase_position"
HOLD = "hold"
REDUCE_POSITION = "reduce_position"
EXIT = "exit"
NO_ACTION = "no_action"
```

No `SHORT`, `SELL_SHORT`, `OPEN_SHORT`, or `COVER` variant exists (grep-
verified: `position_action_has_short_variant=False`). Every downstream
decision surface this platform actually has is long-position lifecycle
management only. This is consistent with an *implicit* long-only posture
for the platform as a whole — but implicit is not the same as explicit, and
critically, `decision_service/` does not consume `patterns/` output at all
today (§8), so this cannot be read as a deliberate statement about pattern
discovery's own directional scope.

## 2. Direction-semantics trace

Traced fresh against `candidates.py`, `evaluation.py`, `targets.py`,
`registry.py`, `live.py`, `validation.py`, `robustness.py`, `baselines.py`.

| Concept | Meaning, as coded | Direction-relevant? |
|---|---|---|
| `ConditionOperator.GT`/`LT` | Which side of a feature threshold a candidate tests (e.g. `RSI > 70` vs. `RSI < 30`). `FeatureCondition.evaluate()` only returns whether the comparison holds. | **No** — a feature-threshold direction, never a trade direction. |
| `expectancy` | `mean(matched forward_return)` (`evaluation.py:113`) | Economically long-only by construction (see next row) but the field itself carries no explicit direction tag. |
| `forward_return` target | `(closes[i+h] - closes[i]) / closes[i]` (`targets.py:76-85`) — the return of buying at `close[i]` and holding `h` days. Computed identically for every condition, operator, and sign. | **Implicitly long-entry**, universally, with no parallel short-return target anywhere in `TargetKind`'s 9 members. |
| `Pattern.conditions[0].operator` (GT/LT) | Feature-threshold direction only | **No relationship to trade direction** — confirmed by the fact GT and LT survivors have near-identical positive-expectancy rates (92.9% vs. 98.6%, from Step 1.6) — if operator implied trade direction, this symmetry would be a coincidence; it is not, because operator was never meant to encode direction. |
| `PatternActivation` / live output | `label: str = "ACTIVE_PATTERN"`, always (`live.py`, grep-verified) | **Explicitly direction-agnostic** by the package's own docstring: "deliberately never a BUY/SELL recommendation." |
| Walk-forward sign agreement (`validation.py:170-174`) | OOS-vs-discovery expectancy sign must agree | Tests *consistency* of the long-return statistic across time, not trade direction. |
| Final-holdout sign agreement (`engine.py:673`) | Holdout-vs-validation expectancy sign must agree | Same as above. |
| Robustness `transaction_cost_survival` (`robustness.py:124-126`) | `net_expectancy = expectancy - 0.002 > 0` | **Implicitly assumes a long position** — this is a viability test that only makes sense if the trade being evaluated is "buy on the signal." |
| `beats_baseline()` (`baselines.py:156-162`) | `net_expectancy > baseline.mean_outcome`, where `baseline` = `buy_and_hold_baseline()` | **Implicitly long-vs-long** — no short-baseline comparison exists anywhere. |

**The core finding of this section:** the codebase's *output vocabulary*
(`PatternActivation`, its docstring, `CLAUDE.md`'s own description of the
package) is deliberately direction-agnostic, but the *underlying economic
computation* two gates depend on (`robustness.py:126`, `baselines.py:161-
162`) is silently long-only. These two facts are in tension, and nothing in
the codebase reconciles them.

## 3. GT/LT meaning (detail)

`_single_conditions()` generates both GT and LT at every quantile threshold
(`candidates.py:178-187`); `_median_condition()` — used for every two/
three-feature interaction, regime filter, and lead/lag candidate — is
GT-only (`candidates.py:189-194`). This asymmetry governs *which feature-
threshold shape gets tested*, not the sign of the resulting `forward_return`
statistic. Step 1.6 already confirmed empirically that LT-conditioned
survivors are *more* likely to be positive-expectancy than GT-conditioned
ones (98.6% vs. 92.9%) — direct evidence that GT/LT is orthogonal to
outcome sign, consistent with the code trace above.

## 4. Negative-expectancy interpretation

A pattern with negative `expectancy` means, precisely and only: **"the mean
forward_return following this feature-condition's trigger, computed as a
long-entry return, was negative over the sample measured."** Nothing more.
It does **not** by itself mean:

- the effect is not real (discovery's own significance test is two-sided
  and would treat a strong negative effect as equally significant to an
  equally strong positive one — Step 1.6, §3);
- the effect is noise (the same walk-forward/robustness perturbation
  machinery that validates positive patterns is, by construction,
  direction-neutral except for the two long-only-coded gates identified
  above);
- the effect is a valid short signal (§6 below).

**Per the instruction not to assume the explanation:** this audit does not
conclude any of the above. It concludes only that the *sign* of expectancy
under the current schema conflates two genuinely different claims — "is
there a real, repeatable statistical effect here" and "which direction (if
any) is this effect tradeable" — into one field, with no mechanism to
separate them.

## 5. Pattern schema: explicit direction semantics

**Confirmed absent.** `Pattern` (`registry.py`, full model re-read for this
audit) has no `side`, `direction`, `position_type`, `is_short`, or
equivalent field (grep-verified:
`pattern_schema_has_explicit_direction_field=False`).

**What semantic information is missing, precisely:**

1. A **direction/side field** (e.g. `intended_position: LONG | SHORT |
   UNDETERMINED`) — currently absent entirely; the sign of `expectancy` is
   the only proxy, and conflates statistical sign with trade direction as
   described in §4.
2. **Short-side economic viability fields** — a `net_of_cost_expectancy`
   computed against a short-specific cost model, an `availability`/
   `shortable` flag, and a `borrow_cost_bps` or equivalent — none exist
   anywhere in `Pattern`, `RobustnessResult`, or `TransactionCostSensitivity`.
3. **A short-side baseline** — `baselines.py` has no `short_baseline()`
   analogous to `buy_and_hold_baseline()`.

## 6. Short/inverse validity test

**Question:** can `short_return = -forward_return` legitimately reinterpret
a negative-expectancy pattern as a valid short signal, or would that be
invalid retrospective relabeling?

**Arithmetic validity:** mechanically well-defined. Negating a realized
long return equals the frictionless, unconstrained P&L of an
equal-and-opposite short position, ignoring financing, borrow cost, and
availability.

**Economic validity: invalid as a promotion basis**, for four independent,
non-overlapping reasons:

1. **No independent re-validation.** The entire `discover()` →
   `validate()` → `final_holdout()` pipeline — bootstrap significance,
   walk-forward sign agreement, robustness perturbation-agreement,
   transaction-cost floor, baseline-beat — was computed and gated using
   `forward_return` (long economics) throughout. Retroactively negating
   already-computed statistics is not equivalent to independently running
   `-forward_return` through the same discovery/validation/holdout
   machinery: a candidate whose sign flips under negation might fail
   perturbation-sign-agreement or baseline-beat under the negated series
   even though it passed under the original one. This was never tested,
   by this audit or by anything upstream.
2. **No short-specific cost model exists anywhere.** The only cost model
   in this codebase — `robustness.py`'s flat 20bps and
   `transaction_costs.py`'s 0–100bps sensitivity grid — is a single,
   symmetric, direction-blind round-trip figure. Real short economics
   require a borrow fee, a hard-to-borrow premium/availability constraint,
   a financing rate, and often asymmetric execution cost, none of which
   exist in this codebase (grep-verified:
   `transaction_costs_py_models_borrow_or_short_cost=False`).
3. **No EGX-specific short-selling/securities-lending data source
   exists.** This audit found zero references to short-selling, margin
   trading, or securities-lending availability anywhere in `sources/`,
   `data/`, or the documented Data Acquisition Program. Even if a cost
   figure were assumed, no data exists to determine *whether a given
   EGX30 ticker is shortable at all* — this audit makes no claim about
   EGX's actual real-world short-selling regime, only that this codebase
   does not model it.
4. **Direct internal precedent already rejects this move.**
   `docs/ARCHITECTURE_DECISIONS.md`'s **AD-42** — in a different subsystem
   (trade-performance evidence for the Publication Gate) — already states:
   *"Only an actually issued BUY candidate enters trade-performance
   evidence; WATCH/AVOID/ABSTAIN remain research outcomes, not synthetic
   long/short positions... Counterfactual avoidance and observation are
   not executed portfolio returns."* A negative-expectancy pattern's
   `forward_return` series was never executed as a short trade by
   anything in this system. Applying `short_return = -forward_return` and
   calling the result "a valid short signal" is the same category of
   retrospective fabrication AD-42 already rules out elsewhere in this
   codebase.

**Conclusion:** the transform is mechanically well-defined but
economically unvalidated. Using it to promote a negative-expectancy
pattern would assert an executed short-trade edge that was never modeled,
priced, or independently tested by any part of this system. **This audit
does not choose classification D merely because negative expectancy
exists**, per the explicit instruction.

## 7. Transaction-cost / borrow-model audit

| Requirement | Status | Evidence |
|---|---|---|
| Transaction costs (generic) | **Modeled** — flat 20bps default, 0–100bps sensitivity grid | `robustness.py: DEFAULT_TRANSACTION_COST_BPS = 20.0`; `transaction_costs.py: DEFAULT_COST_GRID_BPS = (0.0, 5.0, 10.0, 20.0, 50.0, 100.0)` |
| Borrow/short availability | **Not modeled** | No field, constant, or data source found anywhere |
| Borrow fees | **Not modeled** | Same |
| Asymmetric execution costs (buy vs. sell/short spread) | **Not modeled** | The single cost figure is applied identically to every `outcome`, direction-blind |
| Financing (margin/carry cost) | **Not modeled** | Same |
| Liquidity constraints specific to short availability | **Not modeled**, though `data.quality`'s general liquidity floor exists for long-side data quality — unrelated to short-specific constraints |
| Price-limit / market-structure constraints (e.g. EGX circuit breakers, uptick-style rules) | **Not modeled** | No reference found in `patterns/`, `sources/`, or `data/` |
| Does current data contain enough information to model these? | **No** | No collected data source (checked against `sources/` registry conceptually — no borrow-rate, securities-lending, or short-availability `SourceSpec` exists) provides any of the above; adding short-side economics would require both new schema fields *and* a new data source, not just a code change |

## 8. Downstream directional assumptions

Grep-confirmed (`grep -rl "from agx_research.patterns" src tests`, run from
`research/`): the **only** non-test, non-self file anywhere in the
repository that imports `agx_research.patterns` is `cli.py`. Every other
file importing the package is either inside `patterns/` itself or a test.

| Downstream system | Imports `patterns/`? | Executes trades? | Emits BUY/SELL? | Ranks patterns? | Constructs portfolios from patterns? |
|---|---|---|---|---|---|
| `decision_service/` | No | N/A | N/A | N/A | N/A |
| `portfolio/` | No | N/A | N/A | N/A | N/A |
| `capital_allocation/` | No | N/A | N/A | N/A | N/A |
| `shadow_fund/` | No | N/A | N/A | N/A | N/A |
| `api/` | No | N/A | N/A | N/A | N/A |
| `web/` | No | N/A | N/A | N/A | N/A |
| `cli.py` | **Yes** | No — only invokes `PatternDiscoveryEngine` methods and prints/persists reports | No | No | No |

**Nothing today assumes positive expectancy means long exposure, because
nothing today acts on `Pattern`/`PatternActivation` data for any real
decision, ranking, or execution.** The directional-semantics ambiguity
identified in this audit currently has **zero live consequence**. It
becomes load-bearing the moment a Promotion Gate — Mission 3's actual
objective — creates the first real bridge from `patterns/` into
decision-relevant use, which is exactly why this question needed answering
*before* that bridge is designed, not after.

## 9. What is proven

1. GT/LT operators define feature-threshold direction only, never trade
   direction (`candidates.py`, direct code read).
2. `expectancy`/`forward_return` are always computed as a long-entry
   return, identically regardless of operator or sign (`targets.py`,
   `evaluation.py`).
3. The `Pattern` schema has no direction/side field (`registry.py`,
   grep-verified).
4. `PatternActivation` never emits BUY/SELL (`live.py`, grep-verified,
   matches its own docstring).
5. `robustness.py`'s `transaction_cost_survival` and `baselines.py`'s
   `beats_baseline()` both implicitly assume long-only economics via their
   exact code construction (`robustness.py:126`, `baselines.py:161-162`).
6. No short-cost, borrow-fee, financing, or short-availability model
   exists anywhere in `patterns/` (grep-verified against
   `transaction_costs.py`, the only cost-modeling module).
7. Nothing outside `patterns/` (and its own tests/`cli.py`) currently
   imports or consumes `Pattern` data — zero live downstream directional
   consequence today (grep-verified).
8. No authoritative doc states an explicit long-only or short-capable
   mandate for pattern discovery specifically (§1).
9. This codebase has an internal precedent (AD-42) against fabricating
   synthetic long/short positions from non-executed outcomes, directly
   analogous to the `short_return = -forward_return` transform tested in
   §6.

## 10. What is not proven

1. Whether EGX30 tickers are, in reality, shortable at all, and at what
   cost — this audit found no data source addressing this, but does not
   claim to have exhaustively searched every possible external source.
2. Whether a negative-expectancy pattern, if independently re-validated
   end-to-end against a properly-modeled short-return series (with real
   borrow/financing costs), would or would not survive — this was never
   tested, and this audit deliberately does not test it (out of scope, and
   no short-cost data exists to test it with).
3. Whether the long-only behavior in `robustness.py`/`baselines.py` was a
   deliberate simplification the original implementer intended to revisit
   later, or a genuine oversight — no comment, commit message, or doc
   found by this audit states either way.
4. Whether any future consumer of `Pattern` data would in practice need
   short-signal support at all — that is a product/scope decision, not
   something this audit can determine from the code alone.

## 11. Architectural decision — RESOLVED

**Decision (2026-08-13, user/product owner): AGX/the Promotion Gate is
long-only, permanently, by explicit product decision.** Short-selling is
cancelled as a topic for this project in its entirety — not deferred, not
left open pending a future data/infrastructure investment.

Consequently:

- Negative-expectancy patterns are explicitly and permanently out of scope
  for promotion (`OUT_OF_SCOPE_FOR_PROMOTION`), documented as such, rather
  than silently rejected by an incidental cost gate the way they were
  before this decision.
- The short/inverse option that was previously listed as a live
  alternative — adding a direction/side field to the `Pattern` schema,
  building a real short-side cost/availability/financing model, and
  independently re-running `discover()` → `validate()` → `final_holdout()`
  against a properly-defined short target — is **not going to happen**. It
  is recorded here only as historical context for why this audit initially
  framed the question as open; it is not a live option and must not be
  re-opened without a new, equally explicit product decision reversing this
  one.
- No re-entry path, extension point, or "if short is decided later" design
  hook should be built anywhere in the Promotion Gate for this. Any such
  hook that predates this decision should be treated as dead scope, not as
  a pending TODO.

This decision was made by the user/product owner, as this audit and the
Promotion Gate design always required.

## 12. Impact on Step 1.6 interpretation

Step 1.6 correctly identified the code-level mechanism
(`robustness.py:126`'s `net_expectancy > 0` gate) and the data-level
mechanism (positive market drift) that together explain why the
`VALIDATED` population is 100% positive. **Step 1.6 did not claim
negative-expectancy patterns are short signals, and explicitly did not
need to** — that question is precisely what Step 1.7 was scoped to answer.

Step 1.7 does not overturn any Step 1.6 finding. It adds one clarification:
Step 1.6's "accidental implementation bias" component (Component B) can
now be stated more precisely as **"the codebase assumes long-only
economics without ever declaring that assumption explicitly, and provides
no mechanism to evaluate a negative-expectancy candidate under any
alternative economic interpretation"** — i.e. the bias is not merely an
arbitrary implementation accident, it is a specific, identifiable *gap*
(missing direction semantics), consistent with this audit's own
classification (C).

Reconciliation figures (recomputed this session, independent of the
missing Step 1.6 file — see provenance notice above — and matched against
the same registry state Step 1.6 reported):

| Step 1.6 figure | Recomputed this session | Match |
|---|---:|---|
| Total `DISCOVERED` | 3,398 | 3,398 | ✓ |
| v1 positive-expectancy count | 3,202 (94.3%) | 3,202 (94.3%) | ✓ |
| v1 negative-expectancy count | 4 | 4 | ✓ |
| GT discovered / validated | 2,590 / 1,513 | 2,590 / 1,513 | ✓ |
| LT discovered / validated | 808 / 260 | 808 / 260 | ✓ |
| Robustness-ambiguous rejections explained by transaction-cost floor alone | 400/511 | 400/511 | ✓ |

## 13. Recommendation: may Promotion Gate work proceed?

**YES, WITH AN EXPLICIT SCOPING CONSTRAINT.**

Promotion Gate design/implementation **may proceed for positive-expectancy
patterns** — their economic interpretation (a long signal) is unambiguous
under every gate traced in this audit, with no open architectural question
blocking it.

Promotion Gate design/implementation **must not**:
- create any pathway that promotes, scores, or otherwise treats a
  negative-expectancy pattern as a tradeable (short/inverse) signal;
- apply `short_return = -forward_return` or any equivalent relabeling
  anywhere;

**until** the architectural decision in §11 is made explicitly by the
user/product owner.

Given only 4 of 3,398 `DISCOVERED` patterns are even negative (Step 1.6),
this constraint is narrow in practical scope today — but it must be stated
**explicitly** in the Gate's design, not left implicit the way it currently
is in `discover()`/`validate()`.

## Reproducibility

- `research/scripts/audit_pattern_directional_semantics.py` is fully
  deterministic (no RNG, no wall-clock-dependent fields): running it twice
  produced **byte-identical**
  `research/data/pattern_directional_semantics_audit/analysis.json`
  output (verified via direct `diff`).
- `uv run ruff check research/scripts/audit_pattern_directional_semantics.py`
  passes with zero errors.
- `uv run python research/scripts/check_truth_preservation.py` reports
  clean (no fabrication patterns detected).
- `git status --short` / `git diff --stat` (repo root) confirm zero
  changes to any tracked file — only this step's two new files
  (`research/scripts/audit_pattern_directional_semantics.py`,
  `research/data/pattern_directional_semantics_audit/analysis.json`) are
  untracked additions.
- `PatternRegistry` counts independently re-verified unchanged after
  running the audit script: **3,398 total, 1,773 `validated`, 1,625
  `rejected`** — exactly matching Step 1.6's own reported counts.
- No `validation_status` was changed by this audit (registry access is
  read-only throughout the script — no `PatternRegistry.add()`/
  `.transition()` call exists anywhere in
  `audit_pattern_directional_semantics.py`).
- No `PromotionCase` entity exists in this codebase yet (confirmed — this
  step did not create one, and none existed before it, per the
  established Mission 3 constraint).

## Compliance with hard boundaries

This step did not: modify code, registry data, validation statuses,
`PromotionCase` records, Promotion Gate logic, or any existing research
artifact; fix anything; commit or push anything (all Step 1.7 files remain
uncommitted, matching the posture established for every prior Mission 3
step); or begin Promotion Gate design or implementation. Negative
expectancy was not assumed to imply short alpha, and classification **D**
was not chosen merely because negative-expectancy patterns exist.

---

## Reproduction notice (added when committed to `mission-3-audit-evidence`)

This report and its accompanying script/JSON are a **same-session
reproduction**, not the byte-for-byte original artifact from the turn that
first produced Step 1.7. This repository's working tree does not persist
uncommitted files across turns in this environment, so the original,
uncommitted Step 1.7 files were lost before this preservation step began
(confirmed: they were gone from disk at the start of the very next turn,
before the stop-hook-driven preservation request was even made).

This reproduction was made by re-writing
`research/scripts/audit_pattern_directional_semantics.py` from the exact
source text captured earlier in the same conversation (not from memory of
its behavior), and re-running it against the same real,
independently-verified-unchanged registry
(`/tmp/agx_real_run/patterns/registry.json`: 3,398 total / 1,773
`validated` / 1,625 `rejected`, identical before and after). Re-running the
recreated script reproduced the exact same classification (`C`) and
registry-verification output already reported in this document. No
threshold, methodology, or historical finding was altered, improved, or
reinterpreted in producing this reproduction. Step 1 and Step 1.5's
artifacts remain genuinely unavailable and are reported as such in the
top-level preservation report, not silently recreated as this report's
provenance notice above already documents.
