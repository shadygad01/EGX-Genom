# Pattern Promotion Gate — Design & Audit Report

**Document structure.** This file now contains two parts:

- **Part 1 (below, unchanged)** — the original Design & Audit Report,
  produced before Mission 3's evidence-gathering steps (Steps 1, 1.5, 1.6,
  1.7) existed. Preserved verbatim for historical provenance. Several of
  its recommendations (K ≥ 3 as a hard gate, `candidate_family_key()`'s
  ticker-excluding extension as *the* family definition, BY as the
  presumptive multiple-testing winner) are **superseded** by Part 2 below,
  which incorporates evidence Part 1 did not have access to. Where Part 2
  supersedes Part 1, this is stated explicitly in Part 2 — Part 1 is not
  edited to hide what changed.
- **Part 2 (`## Mission 3 Final Promotion Gate Specification — v2`)** —
  the current, evidence-informed specification. **This is the authoritative
  version for any future implementation work.** Read Part 2 first; consult
  Part 1 only for historical context on what the pre-evidence proposal
  looked like and why specific pieces of it changed.

---

# Part 1 — Original Design & Audit Report (pre-evidence, historical)

**Status: DESIGN ONLY. No code, tests, thresholds, Mission 2 artifacts, or
production decision logic changed by this document.** Produced per an
explicit instruction to audit the repository, design a promotion
lifecycle, and stop for review before any implementation. This is that
audit and design — not a patch.

**Mission boundary respected**: `docs/PATTERN_DISCOVERY_FINAL_HOLDOUT.md`,
`docs/VALIDATED_PATTERNS.md`, TD-70/TD-72/TD-73/TD-74, every `Pattern`'s
current `validation_status` in the real registry, the bounded Top-20
`failure-profile` supplementary analysis, and `decision_service`/
`meta.decision_engine`/every other production consumer are all read-only
inputs to this design, untouched by it. No new pattern-discovery run, no
full 1,773-pattern `failure-profile`, was executed to produce this report.

---

## 0. The one-sentence problem this gate exists to solve

Mission 2 proved, empirically, on real data, that **passing this
codebase's current discover → validate → final_holdout pipeline is not
sufficient evidence for production trust** — 1,773 patterns reached
`VALIDATED` from 14 tickers, a volume TD-72/TD-74 attribute to a
correlated-candidate-pool multiple-testing gap, illustrated concretely by
EGAL's 354 "validated" patterns collapsing to 19 distinct underlying
signals (131 of them window/threshold variants of *one* tendency). The
Pattern Promotion Gate is the structural answer: a second, independent,
harder gate that a pattern must clear — on evidence a strong historical
backtest alone cannot manufacture — before it is even eligible for paper
validation, let alone production.

---

## 1. Existing mechanisms found in the repository

An asset this codebase already has, discovered by reading source, not
inferred: **every ingredient this gate needs already exists somewhere in
this repository, just never assembled for this purpose, and (critically)
several of the most relevant statistics are already *computed* on every
real pattern but never *gated on*.**

| Area | What exists | File |
|---|---|---|
| Pattern lifecycle / state machine | `PatternStatus` enum + `_ALLOWED_TRANSITIONS` graph, enforced in `PatternRegistry.transition()`; real, versioned, append-only history via `storage.JsonFileRepository` | `patterns/registry.py` |
| Purged/embargoed temporal OOS validation | `WalkForwardValidator`, `purge_and_embargo()`, chronological-only splits, OOS-sign-agreement gate | `patterns/validation.py` |
| Three-way discovery/validation/holdout split | `engine.discover()` → `validate()` → `final_holdout()`, `holdout_fraction`, "run once" holdout discipline | `patterns/engine.py` |
| Robustness / parameter-stability testing | `RobustnessTester`: threshold/lookback/horizon perturbation, regime breakdown, transaction-cost survival, "all perturbations must agree in sign" | `patterns/robustness.py` |
| Multiple-testing correction | `benjamini_hochberg()` (BH-FDR); `candidate_family_key()`, `group_by_family()`, `family_corrected_p_value()`, `block_bootstrap_p_value()`, `deflated_sharpe_ratio()` — **the last two are computed for every real pattern and never gated on today** | `patterns/multiple_testing.py`, `patterns/multiple_testing_family.py` |
| Regime / stability characterization | Six real dimensions (volatility/breadth/dispersion/trend/correlation/turnover), bucket-count sensitivity (k=2/3/4), `overall_tag` classification (`unconditional`/`sensitive`/`regime_specific`/`unstable`/`insufficient_data`) | `patterns/regimes.py` |
| Transaction-cost sensitivity | Gross vs net expectancy across a declared cost grid, breakeven cost | `patterns/transaction_costs.py` |
| Reproducibility | `ReproducibilityManifest`: experiment id, git commit, dataset version, full config, stamped on every run | `patterns/reproducibility.py` |
| Live matching / outcome tracking | `LiveActivationEngine.evaluate()` (never a BUY/SELL label), `OutcomeTracker`/`OutcomeRepository`/`ActivationOutcome` | `patterns/live.py`, `patterns/outcomes.py` |
| Decay → revalidation (never silent removal) | `DecayMonitor`: live sample floor, hit-rate-drop threshold, sign-flip → `WEAKENING`, never deletion | `patterns/decay.py` |
| **Analogous promotion gate #1 (unrelated pipeline)** | `sources.qualification.evaluate_promotion()`: `CANDIDATE → QUARANTINE → EVALUATION → TRUSTED → CORE`, one stage at a time, `min_runs`/`min_composite` reputation thresholds per stage, pure-function evaluation separate from persistence (`apply_promotion`), automatic one-stage demotion on a bad health signal | `sources/qualification.py` |
| **Analogous promotion gate #2 (unrelated pipeline)** | `hypotheses.pipeline.GateSpec`/`StageName`: a *configurable, data-driven* gate pipeline (`Observation → Hypothesis → ... → Peer Validation`), not hardcoded stage logic | `hypotheses/pipeline.py` |
| **Analogous promotion gate #3 (unrelated pipeline)** | `knowledge.store.KnowledgeStore.promote()`: refuses unless `evidence.is_ready_for_promotion`, depends on a structural `PromotableEvidence` Protocol, not a concrete class | `knowledge/store.py` |
| **Analogous promotion gate #4 (unrelated pipeline)** | `review.board.ScientificReviewBoard` + `review.reviewers.{Statistician,Risk,Economist,Historical,PeerValidator}Reviewer`: approves only if every reviewer that *actually ran* passed; unimplemented reviewers are skipped, never faked as passing | `review/board.py`, `review/reviewers.py` |
| **Analogous promotion gate #5 (unrelated pipeline)** | `adversarial.scientist.AdversarialScientist`: real attacks — `SmallSampleBias`, `TimeLeakage`, `LookAheadBias`, `WeakEconomicRationale`, `RandomCoincidence` (seeded permutation test), `ParameterInstability` (sign-stability across trailing windows) — three more (`Overfitting`, `RegimeDependency`, `OutOfSampleDegradation`) honestly marked `attempted=False`, not faked | `adversarial/scientist.py` |
| Economic plausibility gate | `causal.reasoner.EconomicRationaleGate`: "correlation alone is not enough" — requires a stated candidate cause *and* rationale, caps confidence at 0.5 even on pass, never claims causal truth | `causal/reasoner.py`, `causal/assessment.py` |
| Portfolio-level concentration caps | `decision_service.concentration.compute_concentration_caps()`: sector + correlation-cluster hard caps, walked best-ranked-first, excess weight returns to cash (never redistributed) | `decision_service/concentration.py` |
| Evidence-readiness gate (per ticker) | `meta.readiness`: `READY`/`DEGRADED`/`BLOCKED` with explicit `blockers`/`next_actions` — extended, not duplicated, when new mandatory checks appear (liquidity floor, country risk) | `meta/readiness.py` |
| Abstention vocabulary (never fabricate a decision) | `decision_service.service.PositionAwareDecision.abstained: bool` + `reasons: list[str]` — a real, distinct outcome, never conflated with rejection | `decision_service/service.py` |
| Lineage / mutation discipline | `genome.gene.Gene`/`AlphaGenome.mutate()`: a changed understanding is always a *new* child, parent marked `REPLACED`, never edited in place | `genome/gene.py`, `genome/service.py` |
| Continuous re-evaluation → retirement | `learning.monitor.ContinuousLearningMonitor`: realized-return sign-disagreement-in-majority-of-records retirement rule, `min_records` floor | `learning/monitor.py` |
| Forward walk-forward *decision* replay (not pattern-level, but structurally the closest existing thing to "paper validation") | `investment_proof.walk_forward.WalkForwardInfrastructure`: day-by-day replay of `RecommendationService` against a real trading calendar, records into `DecisionLedger`, `required_datasets()` reports honest availability | `investment_proof/walk_forward.py` |
| Positive/negative control suite precedent | `patterns.control_suite`: proves a pipeline recovers real planted relationships and does not consistently manufacture false ones from noise — a *methodology*, directly reusable for testing the gate itself | `patterns/control_suite.py` |

**The single most important audit finding**: `patterns/` today is
imported by nothing except `cli.py` — no `decision_service`, `meta`,
`capital_allocation`, `shadow_fund`, or `investment_proof` module
references it at all (`grep -rl "from agx_research.patterns" src/
agx_research --include=*.py` returns only `cli.py`). **This gate is being
designed pre-emptively, into a genuine architectural gap, not to patch an
active leak into production.** That is good news (nothing downstream is
currently at risk) and a real constraint (there is no existing consumer
contract to preserve — the gate's *output* destination is itself an open
question, see §13).

---

## 2. Existing mechanisms that can be reused (vs. genuinely new work)

**Reuse verbatim, no modification:**
- `patterns.validation.{WalkForwardValidator, purge_and_embargo, chronological_split}`
- `patterns.robustness.RobustnessTester` (all four perturbation families + transaction-cost survival)
- `patterns.multiple_testing.benjamini_hochberg`
- `patterns.multiple_testing_family.{candidate_family_key, group_by_family, family_corrected_p_value, block_bootstrap_p_value, deflated_sharpe_ratio}`
- `patterns.regimes.analyze_pattern_failure_conditions` (all six dimensions, bucket-count sensitivity)
- `patterns.transaction_costs.analyze_transaction_cost_sensitivity`
- `patterns.reproducibility.build_reproducibility_manifest`
- `patterns.live.LiveActivationEngine` (as the paper-validation "does it currently match" signal)
- `patterns.outcomes.{OutcomeTracker, OutcomeRepository, ActivationOutcome}` (as the paper-validation realized-outcome recorder)
- `storage.JsonFileRepository` (every new versioned entity, per this codebase's own hard rule)
- `decision_service.concentration`'s *structure* (best-ranked-first walk, hard cap, excess returns to cash/is dropped rather than redistributed) as the template for the new ticker-concentration cap — the specific numbers are new (see §8)
- `causal.reasoner.EconomicRationaleGate` / `review.reviewers.EconomistReviewer`'s *structure* (mechanical "rationale stated + engages the claim" check, confidence capped, never a truth judgment) as the template for §5 — extended to a new field patterns don't have yet

**Reuse the pattern, not the code (different domain object):**
- `sources.qualification.evaluate_promotion()`'s exact shape (pure-function `evaluate_X(state, evidence) -> Decision`, separate `apply_X(registry, decision)` for persistence, one-stage-at-a-time movement, automatic demotion on a bad signal) is the direct template for this gate's own transition functions.
- `genome.AlphaGenome.mutate()`'s "changed understanding is always a new child, parent marked terminal" discipline is the direct template for "a pattern changed after paper validation begins must restart, never be edited in place" (§6, §7).

**Genuinely new, no existing equivalent:**
- Cross-ticker robustness / family-level ticker-concentration measurement (§2 of the required dimensions) — nothing in this codebase currently asks "does the same signal appear on more than one ticker."
- A promotion-specific temporal OOS check against data that **postdates** the original Mission 2 run (as opposed to `final_holdout()`'s single, already-spent holdout slice).
- `economic_rationale`/`candidate_cause` fields on a pattern-adjacent object — `Pattern`/`PatternCandidate` carry no such field today.
- Frozen-snapshot paper-validation infrastructure at the *pattern* level (`investment_proof.walk_forward` replays *decisions*, not individual patterns).
- The `PromotionCase` entity and its state machine itself.

---

## 3. Gaps that prevent rigorous promotion today

1. **`block_bootstrap_p_value` and `deflated_sharpe_ratio` are computed for every discovered pattern and never gated on.** (`engine.py`'s own comment: *"Both are additional, informational diagnostics attached to every DISCOVERED pattern — neither gates promotion here."*) This is arguably the single cheapest, most direct fix available and the clearest evidence that today's volume problem is a *gating* gap, not only a *methodology* gap.
2. **No cross-ticker requirement anywhere.** A pattern conditioned on one ticker's own price history can reach `VALIDATED` (and, per the real run, frequently does) with zero corroboration from any other instrument.
3. **No concentration limit on how many patterns one ticker (or one underlying signal family) may contribute.** EGAL alone is 20% of the real `VALIDATED` set.
4. **`family_size=1` for every one of the 1,773 real `VALIDATED` patterns (TD-74, unexplained).** Whatever mechanism is supposed to be penalizing large families is not visibly binding on the patterns that actually survive — a real, open diagnostic question this gate's design must not paper over (see §13).
5. **No economic-rationale or candidate-cause requirement** — a pattern is pure statistics, no structural story, unlike the parallel `hypotheses`/`knowledge` pipeline which already requires one.
6. **No temporal OOS check against data that postdates the original run.** `final_holdout()`'s slice is spent the moment it's checked; nothing re-tests a pattern against genuinely new calendar time.
7. **No paper-validation stage of any kind at the pattern level.** `investment_proof.walk_forward` exists but operates on `RecommendationService`/`DecisionLedger`, not `Pattern`/`LiveActivationEngine`.
8. **No frozen-definition discipline.** Nothing today prevents re-deriving a pattern's threshold from a wider or different date range after the fact — the underlying `PatternCandidateGenerator` machinery is available to call again at any time, and nothing stops it being pointed at "the version of the data that makes this pattern look best."
9. **No bridge — and, deliberately, no *decision yet* about a bridge — from a maximally-promoted pattern to any actual consumer** (§1's "imported by nothing but `cli.py`" finding). Designing the gate does not answer what a `PROMOTED` pattern is *for*.

---

## 4. Proposed promotion-state machine

```
                    ┌─────────────┐
   Pattern.status   │             │
   == VALIDATED  ───▶  DISCOVERED │ (gate-local: "opened as a promotion
   (Mission 2's own  │             │  candidate" — see naming-collision
   endpoint)         └──────┬──────┘  warning below)
                             │ cross-ticker + multiple-testing +
                             │ effect-size hard gates (§8)
                             ▼
                     ┌───────────────┐
                     │ OOS_VALIDATED │ (fresh, post-original-run temporal
                     │               │  slice — NOT final_holdout()'s spent one)
                     └───────┬───────┘
                             │ perturbation/regime/cost stability (§3, reused
                             │ RobustnessTester + regimes.py as-is)
                             ▼
                       ┌───────────┐
                       │  ROBUST   │
                       └─────┬─────┘
                             │ economic rationale stated + structurally
                             │ coherent (§5) — gates entry, not a stage itself
                             │ (see note below the table)
                             ▼
                   ┌──────────────────┐
                   │  PAPER_VALIDATED │ frozen definition, pre-registered
                   │                  │ window + criteria, zero capital
                   └────────┬─────────┘
                             │ paper window's pre-registered criteria met
                             ▼
                        ┌───────────┐
                        │ PROMOTED  │  (terminal for this gate; what
                        │           │   consumes it is OUT OF SCOPE, §13)
                        └───────────┘

  From any non-terminal stage, at any time evidence fails a hard gate:
        ──▶ REJECTED (terminal within this PromotionCase; a materially
             changed pattern requires a brand-new PromotionCase, mirroring
             genome.mutate()'s "new child, old REPLACED" rule — never a
             resurrection of the same case)

  From any non-terminal stage, when evidence is too thin to judge (not
  wrong, just insufficient):
        ──▶ INSUFFICIENT_EVIDENCE (mirrors decision_service's `abstained`
             — a real, distinct, non-pejorative outcome; a case here may
             re-enter the SAME stage once more evidence exists — this is
             the one legitimate "wait and retry" path, distinct from
             REJECTED's finality, and it is not "repeated testing" because
             no evaluation actually ran the first time)
```

**Naming-collision warning (needs a decision before implementation)**:
the mission's requested vocabulary reuses the string `"DISCOVERED"`,
which `patterns.registry.PatternStatus` already uses for something
different (the *start* of Mission 2's own pipeline, before even
`validate()`). Technically harmless (a new `PromotionStage` enum is a
distinct Python type, no runtime collision), but a real risk for human
readers and log messages. **Recommendation**: keep the requested
vocabulary in the design/spec, but consider renaming the gate's own enum
values in code to something unambiguous — e.g. `PromotionStage.INTAKE`
instead of `DISCOVERED` — flagged here for review, not decided
unilaterally.

**Why `OOS_VALIDATED` and `ROBUST` are ordered before the economic
rationale check, and why the rationale check is drawn as gating entry to
`PAPER_VALIDATED` rather than being its own numbered stage**: the mission
lists economic plausibility as dimension 5, between stability (3) and
paper validation (6). Structurally it behaves like `EconomicRationaleGate`
already does for hypotheses — a *necessary, cheap, always-computable*
check (it needs no new data, just a written rationale) — so gating it
immediately before the *expensive, calendar-time-bound* paper-validation
stage avoids ever opening a real forward-observation window for a pattern
that has stated no plausible mechanism at all. This is a design choice,
not a requirement; an alternative that makes it stage 3.5 as its own
named status is equally defensible and noted as an open question (§13).

---

## 5. Exact gate criteria for every transition

| Transition | Hard requirements (any failure → `REJECTED`) | Soft/insufficient-data outcome |
|---|---|---|
| `VALIDATED` → `DISCOVERED` (intake) | Pattern's `validation_status == PatternStatus.VALIDATED` in the source-of-record registry. Frozen snapshot captured (`conditions`, `regime_filter`, `target_id`, `ticker`, `family_key`). | Never — intake is definitional, always succeeds or the case is never opened. |
| `DISCOVERED` → `ROBUST` (cross-ticker + statistics, §8/§4-stat) | (a) `family_key`-mates (§2 methodology) show the same-signed effect on ≥ K independent tickers (K declared, not calibrated — recommend starting at 3, see §13). (b) Promoting this pattern would not push the `PROMOTED`-eligible set's per-ticker HHI (§8) above a declared ceiling. (c) `block_bootstrap_p_value` (already computed) ≤ a declared alpha, corrected via Benjamini–Yekutieli across the pattern's full originating family (§4-stat). (d) `deflated_sharpe_ratio` (already computed) > 0. (e) Net-of-transaction-cost expectancy (`RobustnessResult.net_of_cost_expectancy`, reused) > 0. (f) All `RobustnessTester` perturbations agree in sign (already the existing `RobustnessResult.passed` rule, reused verbatim). (g) `regimes.overall_tag` is not `unstable`. | Fewer than K tickers exist *at all* for this family (e.g. an EGX-unique signal with no peer to corroborate) → `INSUFFICIENT_EVIDENCE`, not `REJECTED` — a real absence-of-corroborating-data case, not a failed test. |
| `ROBUST` → `OOS_VALIDATED` (temporal, fresh data) | A declared minimum number of genuinely new (post-original-`final_holdout`) matched observations exist, AND their expectancy sign agrees with the original discovery/validation-period sign — same sign-agreement rule `WalkForwardValidator`/`final_holdout()` already use, applied to a window that starts strictly after the original run's `as_of`. | Not enough calendar time has passed yet for enough new matched observations → `INSUFFICIENT_EVIDENCE` (this is the *expected*, common outcome immediately after any real run — see §13, this cannot be rushed). |
| `OOS_VALIDATED` → economic-rationale check (gates entry to `PAPER_VALIDATED`) | A stated `economic_rationale` (new field) is non-empty, of minimum substance (reuse `EconomistReviewer`'s length/engagement checks structurally), and a `CausalAssessment` via `EconomicRationaleGate` passes (candidate cause + rationale both present). Confidence from this step is capped at 0.5, per the existing gate's own posture — it never claims proof. | A rationale that is empty or a placeholder → `REJECTED` (this is cheap to provide; absence is a real failure, not a data gap). |
| → `PAPER_VALIDATED` (paper validation itself) | A `PaperValidationRun` opened against the frozen snapshot, pre-registered window (N trading days or M matched observations, whichever is later — declared, not calibrated) and pre-registered success criterion (sign-agreement + a minimum matched sample, mirroring `final_holdout()`'s own criterion) is met when the window closes. Zero capital deployed throughout (enforced by construction — the paper run never touches `decision_service`/`shadow_fund`). | Window still open → the case stays at `OOS_VALIDATED` with an active `PaperValidationRun` reference; this is not a distinct enum value, just an in-progress sub-state (see §11's `PaperValidationRun.status`). |
| `PAPER_VALIDATED` → `PROMOTED` | Paper window's pre-registered criterion met at close. | — |
| Any stage → `REJECTED` | Any hard requirement above fails outright (not merely "not yet enough data"). | Terminal for this `PromotionCase`. A materially changed pattern (different threshold, different feature) requires a **new** `PromotionCase` against a **new** `Pattern` id — never resurrecting a rejected case, mirroring `genome.mutate()`. |
| Any stage → `INSUFFICIENT_EVIDENCE` | Explicitly marked above per stage. | Non-terminal: the *same* case may re-enter the *same* stage once more real evidence exists (real calendar time passing, more tickers becoming available) — this is the one legitimate retry path, and it is not "repeated testing" because the original attempt never actually produced a verdict. |

---

## 6. Anti-leakage controls

| Forbidden practice (from the mission spec) | Concrete mechanism that prevents it |
|---|---|
| Threshold fishing | `PromotionCase` stores an immutable `frozen_conditions`/`frozen_regime_filter`/`frozen_target_id` snapshot captured once at intake. Every downstream stage evaluates against *that* frozen copy — the gate never calls `PatternCandidateGenerator`, `_median_condition()`, or any other candidate-generation code again. |
| Repeated holdout testing | Every stage's evaluation window is declared and recorded *before* its outcome is computed (pre-registration in the `PromotionCase`'s own append-only transition log, mirroring `PatternRegistry`'s versioned history) — an auditor can always check the recorded window predates the recorded verdict. Each stage transition is monotonic; there is no path back to a *lower* gate stage except the explicit `INSUFFICIENT_EVIDENCE` retry (which re-attempts the *same*, not a *cherry-picked new*, evaluation). |
| Cherry-picking tickers | The `family_key`-based cross-ticker membership set is frozen at intake from the *original* Mission 2 registry snapshot — a ticker cannot be silently dropped from the family's evidence set to improve the aggregate statistic after the fact. |
| Cherry-picking time windows | `OOS_VALIDATED`'s window start is fixed mechanically (original run's `as_of` + 1 trading day) before any result exists; it is never chosen after seeing which window looks favorable. |
| Selecting the best regime after observing results | All six `regimes.py` dimensions are always computed and reported together (already true of `analyze_pattern_failure_conditions()` today — directly observed producing all 6 uniformly in this session's supplementary run); the gate uses the single composite `overall_tag`, never a caller's choice of "which dimension to cite." |
| Changing the pattern after paper validation begins | `PaperValidationRun` stores its **own independent copy** of the frozen definition, structurally decoupled from the live `Pattern`/`PromotionCase`. A mismatch between the running paper validation's stored definition and the source `Pattern` at evaluation time is a hard integrity error, not a silent adoption of the new definition. Any actual change requires closing the current run as failed and opening a **new** `PaperValidationRun` against a **new** `PromotionCase`. |

---

## 7. Multiple-testing strategy (recommended, with justification)

**Recommendation: stack four already-partially-built mechanisms as hard
gates, replacing "informational only" with "load-bearing," and upgrade
the correction itself from Benjamini–Hochberg to Benjamini–Yekutieli.**

1. **Family-corrected block-bootstrap p-values as the primary
   significance test**, not a plain parametric test. `block_bootstrap_p_value()`
   already exists, already respects the outcomes' own chronological/serial
   dependence (unlike an i.i.d. t-test), and is already computed for every
   real pattern — it is simply never checked against anything today. This
   directly addresses the "raw statistical significance alone" prohibition
   in the mission spec, since it is not raw: it is a bootstrap p-value
   under a null that preserves the time-series structure this data
   actually has.
2. **Benjamini–Yekutieli in place of (or alongside) the current
   Benjamini–Hochberg + linear family correction.** BH's guarantee formally
   requires independence or positive regression dependence (PRDS) among
   the tested hypotheses. TD-70/TD-72/TD-74 all converge on the same
   diagnosis — this candidate pool's dependence structure is neither
   independent nor demonstrably PRDS (features/targets/lags derived from a
   handful of underlying price series), and the `family_size=1`-for-every-
   survivor anomaly (TD-74) is itself evidence the existing family-grouping
   heuristic is not fully capturing the real correlation structure. BY's
   correction factor (`Σ 1/i` for `i=1..n` instead of `n`) is valid under
   *arbitrary* dependence — strictly more conservative, and appropriate
   precisely because the true dependency structure here is unknown. This
   is a formalization of the mitigation TD-70/TD-72 already named as a
   repayment trigger, not a new idea introduced here.
3. **`deflated_sharpe_ratio()` as a hard floor (> 0, or a declared higher
   floor), not an attached field.** This is Bailey & López de Prado's own
   answer to "how many trials were effectively run," already implemented
   in this codebase and already computed per pattern — again, simply never
   gated.
4. **Net-of-transaction-cost expectancy as an effect-size floor**, reusing
   `RobustnessResult.net_of_cost_expectancy > 0` (already computed, already
   attached, never currently required). A pattern can be "significant" in
   a bootstrap sense and still economically worthless after realistic
   costs — this is the mission's own explicit "do not use raw significance
   alone" instruction, operationalized with a number this codebase already
   produces.

**Why not just tighten `fdr_alpha` further (e.g. 0.05 → 0.01)?** Because
TD-70/TD-72's own diagnosis is that the *guarantee itself* weakens under
this candidate pool's dependence, not merely that the threshold was too
loose — a tighter threshold under the same broken guarantee is not a
principled fix, only a smaller number. BY changes what the guarantee
actually promises; that is the recommended direction, not further
tightening of an assumption that doesn't hold.

**Confidence intervals / bootstrap**: recommend reporting a bootstrap
confidence interval on expectancy (the same bootstrap machinery
`block_bootstrap_p_value` already runs can produce one) and requiring the
CI's lower bound to remain positive at `OOS_VALIDATED`/`ROBUST` — stricter
than a point-estimate-only sign check, and directly reusable
infrastructure.

---

## 8. Cross-ticker robustness methodology

This is the dimension that most directly targets TD-72/TD-74's finding,
and the one with the least existing machinery — it is designed, not just
assembled, here.

1. **Family definition**: reuse `candidate_family_key()` unmodified
   (`ticker|base_feature|target_id|regime` with window-length suffixes
   stripped) as the unit of "the same underlying signal." **Extension
   needed**: `candidate_family_key()` currently *includes* the ticker in
   the key, so it groups near-duplicate *thresholds on one ticker*
   together, not the *same signal across tickers*. Cross-ticker grouping
   needs a second key that **excludes** ticker (`base_feature|target_kind|
   regime`) — a small, additive extension, not a change to the existing
   function's behavior or callers.
2. **Minimum independent tickers (K)**: a family reaches `ROBUST` only if
   the same-signed effect (same direction of the base condition, same sign
   of expectancy) appears on at least K distinct tickers' own
   `PatternStatus.VALIDATED` instances of that cross-ticker family.
   Recommend **K ≥ 3**, declared and explicitly uncalibrated (same posture
   as every other declared constant in this codebase, TD-6-class) —
   real calibration requires real decision-ledger outcome history that
   doesn't exist yet.
3. **Ticker concentration measurement**: reuse the exact Herfindahl-Hirschman
   formula `market_memory.breadth`/`features.py` already compute for
   volume concentration, applied instead to "share of `PROMOTED`-eligible
   patterns attributable to each ticker." A declared HHI ceiling (start
   from the same conservative posture as `MAX_SECTOR_CONCENTRATION=0.40`,
   translated to pattern-count share, not portfolio weight — a distinct
   number requiring its own TD entry once implemented, not a silent reuse
   of the portfolio constant) caps how much of the `PROMOTED` set any one
   ticker may represent at a given time.
4. **Minimum non-dominant contribution**: once a family clears K, require
   that no single ticker contributes more than a declared fraction (e.g.
   50%) of that family's *own* matched sample — preventing "3 tickers
   corroborate, but 2 of them contributed 5 matches each while 1
   contributed 3,000," which would be corroboration in name only.
5. **Rejection conditions**: fewer than K tickers ever existing for a
   family → `INSUFFICIENT_EVIDENCE` (an absence of data, not a failure).
   K tickers exist but the effect's sign is genuinely mixed across them
   (e.g. positive on COMI, negative on ADIB) → `REJECTED` — a mixed-sign
   family is not "partially corroborated," it is evidence *against* one
   underlying mechanism (flagged as an open methodological question in
   §13: should mixed-sign directions be split into two *separate*
   families instead of rejected outright? Both are defensible; a decision
   is needed before implementation).

---

## 9. Temporal OOS methodology

- **Train/discovery period**: unchanged from Mission 2 — whatever
  `discover()`/`validate()` already used (documented per-pattern in the
  existing `discovery_period`/`validation_period` fields).
- **Mission 2's final holdout period**: unchanged, already spent, never
  re-read by this gate (the gate does not re-litigate `final_holdout()`'s
  own verdict — a pattern that failed `final_holdout()` never reaches this
  gate at all, since intake requires `PatternStatus.VALIDATED`).
- **This gate's own OOS period**: **strictly after** the original run's
  `as_of` date (2026-08-06 for the real Mission 2 run) — data that did not
  exist, in any form, at any point during discovery, feature selection,
  threshold selection, or pattern selection. This is the only window in
  the entire pipeline that is guaranteed leak-free by construction, since
  it postdates the run that produced the pattern.
- **Leakage controls**: the window boundary is fixed and recorded before
  any result is computed (§6). The frozen `conditions`/`target_id`
  snapshot from intake is what's evaluated — never a re-derived version
  tuned to the new window.
- **Minimum sample requirements**: declared, not calibrated — recommend
  reusing `WalkForwardValidatorConfig.min_oos_sample_size` (currently 10)
  as an absolute floor, but this stage's true requirement should scale
  with how rarely the pattern's conditions trigger (a pattern matching
  every few days needs far fewer *calendar* days than one matching every
  few months to reach the same *matched-observation* floor) — gate on
  matched observations, not elapsed calendar days.
- **The hard, unavoidable cost**: this stage cannot be rushed or
  substituted. Immediately after any real discovery run (including
  Mission 2's), essentially every case will sit at `INSUFFICIENT_EVIDENCE`
  here until real trading days actually accumulate. See §13 — this is
  presented as a feature of the design, not a defect to work around.

---

## 10. Paper-validation methodology

- **Frozen pattern definition**: `PaperValidationRun` stores its own
  immutable copy of `conditions`/`regime_filter`/`target_id`/`ticker`,
  independent of the live `Pattern` record (§6).
- **Frozen parameters**: no re-fitting of thresholds, no re-selection of
  lag/window, for the run's entire duration — enforced by the same
  frozen-copy mechanism, not by policy alone.
- **No post-hoc tuning**: a change of any kind requires closing the
  current run (as `REJECTED` or as an expired/failed observation) and
  opening a brand-new `PaperValidationRun` under a brand-new
  `PromotionCase` — never an in-place edit, mirroring `genome.mutate()`.
- **Predefined observation window**: N trading days *or* M matched
  observations (whichever is later), both declared *before* the window
  opens and recorded in the `PaperValidationRun` itself.
- **Predefined success/failure criteria**: sign-agreement between the
  paper window's realized expectancy and the pattern's original
  discovery/validation-period expectancy, plus the matched-observation
  floor — the same criterion shape `final_holdout()` already uses,
  applied to genuinely live-forward data this time. Declared before the
  window opens, immutable for its duration.
- **No capital deployment**: enforced by construction — the paper-
  validation machinery only ever calls `LiveActivationEngine.evaluate()`
  (read-only feature matching) and `OutcomeTracker` (read-only realized-
  outcome recording); it has no code path into `decision_service`,
  `capital_allocation`, or `shadow_fund`, and should be built in a way
  that makes that structurally true (no import of those packages), not
  merely a policy.
- **Mechanism reuse**: this is the closest analog to `investment_proof.
  walk_forward.WalkForwardInfrastructure`'s day-by-day replay discipline,
  but at the pattern level instead of the decision level — a new,
  narrower driver following that module's own precedent (a day-stepping
  loop over `LiveActivationEngine`, not a new replay concept).

---

## 11. Required data fields / artifacts

New, `storage.JsonFileRepository`-backed, versioned entities (per this
codebase's own hard rule — no bespoke persistence):

- **`PromotionCase`**: `id`, `pattern_id`, `version`, `promotion_stage`
  (the new enum), `frozen_conditions`, `frozen_regime_filter`,
  `frozen_target_id`, `frozen_ticker`, `family_key` (ticker-scoped),
  `cross_ticker_family_key` (ticker-excluded, new — §8), `oos_window`,
  `oos_result_ref`, `robustness_result_ref` (reuses `RobustnessResult`
  as-is), `regime_profile_ref` (reuses `PatternFailureProfile` as-is),
  `cost_sensitivity_ref` (reuses `TransactionCostSensitivity` as-is),
  `economic_rationale`, `causal_assessment_ref` (reuses `CausalAssessment`
  as-is), `paper_validation_run_id`, `rejection_reason`,
  `insufficient_evidence_reason`, `provenance`, `reproducibility_manifest`
  (reuses `ReproducibilityManifest` as-is).
- **`CrossTickerRobustnessReport`**: `cross_ticker_family_key`,
  `tickers_in_family`, `tickers_with_matching_effect`, `dominant_ticker`,
  `dominant_ticker_share_of_matched_sample`, `ticker_concentration_hhi`,
  `verdict`.
- **`PaperValidationRun`**: `id`, `promotion_case_id`, frozen definition
  copy, `window_start`, `window_end_or_target_matched_count`,
  `pre_registered_success_criteria` (text + structured threshold),
  `matched_observations` (append-only, mirrors `PatternRegistry`'s own
  append-only posture), `realized_outcomes` (reuses `ActivationOutcome`
  shape), `verdict`, `provenance`.

All reused as-is, unmodified: `WalkForwardResult`, `RobustnessResult`,
`PatternFailureProfile`, `TransactionCostSensitivity`,
`ReproducibilityManifest`, `CausalAssessment`, `ActivationOutcome`.

---

## 12. Required tests

- **State-machine legality**: illegal `PromotionStage` transitions raise,
  mirroring `test_pattern_registry.py`'s existing style for
  `PatternStatus`.
- **Anti-leakage proofs**: mutate the live `Pattern` after a
  `PromotionCase`/`PaperValidationRun` has frozen its snapshot; assert the
  frozen copy is unaffected and a definition mismatch at evaluation time
  raises rather than silently adopting the change.
- **Positive control**: a synthetic, genuinely cross-ticker, genuinely
  robust planted relationship (extending `control_suite.py`'s own
  momentum/mean-reversion constructions across ≥ K tickers) must be able
  to reach `PROMOTED` — proving the gate is not *impossible* to pass, only
  hard.
- **Negative control**: an EGAL-354-style single-ticker family (many
  near-duplicate thresholds, one real underlying tendency, no cross-ticker
  corroboration) must be structurally capped at `DISCOVERED`/`ROBUST` at
  most, never reaching `PAPER_VALIDATED` — the single most important proof
  this gate actually closes TD-72/TD-74's gap.
- **Real-data regression**: replay the *existing* real Mission 2 registry
  (1,773 `VALIDATED` patterns, already persisted, no new discovery run
  needed) through the gate's family-collapse + cross-ticker + statistical
  hard gates only (§4's `DISCOVERED → ROBUST` transition, which requires
  no new calendar time), and assert the surviving count is small — a
  specific, falsifiable number, not "fewer than 1,773." This is the
  regression test that proves the gate does its job without re-running
  the expensive full pipeline.
- **`INSUFFICIENT_EVIDENCE` correctness**: a family with fewer than K
  tickers, and a case immediately after intake (no new calendar time
  elapsed) at `OOS_VALIDATED`, must both land at `INSUFFICIENT_EVIDENCE`,
  never silently pass or silently fail.

---

## 13. Risks and unresolved methodological questions

1. **Naming collision** between the mission's requested `DISCOVERED` and
   `PatternStatus.DISCOVERED` (§4) — needs an explicit decision.
2. **`OOS_VALIDATED` is structurally rate-limited by real calendar time.**
   Immediately after Mission 2's real run, every one of the 1,773 cases
   will sit at `INSUFFICIENT_EVIDENCE` here for however long it takes new
   trading days to accumulate. This is presented as correct and
   unavoidable, not a flaw to route around — flagged explicitly so it is
   not later mistaken for a bug or "fixed" by weakening the requirement.
3. **K (minimum corroborating tickers) is proposed (≥3), not calibrated.**
   Same "declared, not measured" posture as every other threshold in this
   codebase (TD-6-class) — needs the same eventual calibration trigger.
4. **Mixed-sign families**: does a family with corroborating tickers that
   disagree in sign get `REJECTED` outright, or split into two separate
   sign-specific families? Both are defensible (§8); not resolved here.
5. **Where the economic-rationale check sits in the sequence** (gating
   entry to `PAPER_VALIDATED` vs. its own numbered stage) is a real design
   choice, not a requirement (§4) — flagged for review.
6. **The output destination question**: a `PROMOTED` pattern currently has
   nowhere to go — `patterns/` connects to nothing downstream (§1). This
   gate deliberately does not answer "does `PROMOTED` become a
   `KnowledgeObject` via `KnowledgeStore.promote()`, feed `decision_service`
   directly, or stay pattern-only," per the explicit "do not modify
   production decision logic" boundary — but implementation cannot begin
   in earnest without eventually answering it, since it shapes what
   `PROMOTED` actually needs to carry.
7. **Opening cost at scale**: naively opening one `PromotionCase` per
   existing `VALIDATED` pattern (1,773) re-creates the same computational
   burden this session's `failure-profile` runs already demonstrated is
   impractical. §14's implementation order deliberately puts the
   cross-ticker *family*-collapse pass first, specifically so the gate
   operates on a few hundred families, not 1,773 individual patterns, from
   the start.
8. **`family_size=1`-for-every-survivor (TD-74) remains unexplained.**
   This design's statistical hardening (§7) does not require resolving
   that diagnostic first, but a full understanding of *why* it happened
   would materially improve confidence in the family-collapse step (§8)
   this gate depends on — recommended as parallel, not blocking, work.

---

## 14. Minimal implementation plan, ordered by dependency

1. **Family-collapse analysis pass** over the existing real registry
   (read-only script, no registry mutation, same posture as this
   session's supplementary `failure-profile` analysis) — extends
   `candidate_family_key()` with the ticker-excluding cross-ticker key
   (§8), producing the actual candidate count this gate will operate on.
   No new persisted entities yet.
2. **`PromotionCase` schema + registry + state machine** (`PromotionStage`
   enum, `_ALLOWED_TRANSITIONS`, `storage.JsonFileRepository`-backed),
   with legality tests only — no science wired in yet, mirroring how
   `patterns/registry.py` itself preceded `patterns/engine.py` in Mission 1.
3. **Frozen-snapshot intake** (`VALIDATED → DISCOVERED`) — the anti-
   leakage foundation every later stage depends on.
4. **Cross-ticker + statistical hard gates** (`DISCOVERED → ROBUST`,
   §5/§7/§8) — wires `block_bootstrap_p_value`, `deflated_sharpe_ratio`,
   net-of-cost expectancy, and the new ticker-concentration/HHI check as
   *hard* gates. This is where TD-72/TD-74 actually gets addressed, and it
   requires no new calendar time — it can run against the existing real
   registry immediately, which is also where §12's real-data regression
   test lives.
5. **Temporal OOS mechanism** (`ROBUST → OOS_VALIDATED`, §9) — build now;
   its first real exercise necessarily waits for new trading days (§13.2).
6. **Economic-rationale gate** (§5) — extends `PromotionCase` with the new
   field, reuses `EconomicRationaleGate`/`EconomistReviewer` structurally.
7. **Paper-validation infrastructure** (`PaperValidationRun`, §10, §6) —
   reuses `LiveActivationEngine`/`OutcomeTracker`, new day-stepping driver
   following `WalkForwardInfrastructure`'s precedent.
8. **Positive/negative control suite for the gate itself** (§12) —
   mirrors `control_suite.py`'s own methodology, proves the gate is
   passable by a real relationship and blocks an EGAL-354-style overfit
   family.
9. **Documentation** (`CLAUDE.md`/`PHASE_STATUS.md`/`TECHNICAL_DEBT.md`) —
   last, once implemented and tested, matching every other mission's own
   closing convention in this codebase.

Steps 1–4 require no new calendar time and can be fully built and tested
against the *existing* real Mission 2 registry data without waiting on
anything external. Steps 5 and 7 are inherently time-gated (§13.2) —
buildable now, but their first real verdicts cannot be rushed.

---

*End of Part 1. No code, tests, or Mission 2 artifacts were modified to
produce this report. Superseded in the specific ways stated in Part 2
below — read Part 2 for the current design.*

---

# Mission 3 Final Promotion Gate Specification — v2

**Status: DESIGN ONLY.** No code, tests, thresholds, Mission 2 artifacts,
production decision logic, the registry, any `validation_status`, or any
`PromotionCase` record is changed by this document. No new discovery run
and no full failure-profile run was executed to produce it. This section
revises Part 1 using the complete findings of Mission 3 Steps 1, 1.5, 1.6,
and 1.7 — all four now committed, reproducible, and read as primary
evidence for every decision below.

## 0. What changed from Part 1, and why (read this first)

| Part 1 said | Evidence that changed it | Part 2 says instead |
|---|---|---|
| "Recommend K ≥ 3" as the cross-ticker hard gate (§8.2) | Step 1.5: the baseline family definition (Variant A) already gives 20/22 families ≥5 tickers and 0/22 families with 1–2 tickers — K≥3 passes almost everything under A. Under Variant D (ticker-only-stripped, exact condition), 494/605 families are singletons — K≥3 would reject almost everything. The *same* real data produces wildly different K-vs-threshold outcomes purely as a function of an arbitrary normalization choice. | K is **not adopted as a hard gate at all**. Cross-ticker evidence becomes one input to a multi-dimensional Redundancy Report (§5), reported at multiple stripping granularities simultaneously, never collapsed into one pass/fail number. |
| "Reuse `candidate_family_key()`'s ticker-excluding extension" as *the* family definition (§8.1) | Step 1.5 classified the family definition **HIGHLY SENSITIVE** (22 → 62 → 605 families, 2.8×–27.5× swings, multi-ticker breadth collapsing from 100% to 5.6%) across equally mechanical, equally legitimate normalizations. | No single family definition is chosen as canonical. §5 below specifies a redundancy framework that reports several distinct redundancy dimensions without conflating them. |
| "22/22 families same-sign" implied as cross-ticker corroboration evidence (§8, implicit) | Step 1.6: all 1,773 `VALIDATED` patterns are individually positive-expectancy *before* any family grouping (94.3% already positive at `DISCOVERED`, driven by real positive EGX market drift + a code-level long-only gate). Step 1.5 confirmed 100% same-sign holds identically across every family-definition variant (A/B/D) — a mechanical consequence of the upstream population, not new evidence. | Same-sign family results are **never cited as corroboration** anywhere in this spec. §3/§5 state this explicitly as a standing rule. |
| BY "recommended... in place of (or alongside) BH" (§7.2), phrased as a near-decision | Step 1 ran the descriptive comparison: BH passes 1,683/1,773 (94.9%), BY passes 657/1,773 (37.1%) at α=0.05. A 2.6× difference in surviving count from the correction choice alone, with no calibration evidence for either. | BH vs BY is **explicitly reopened as unresolved** (§6). Both are reported; neither is chosen. |
| No explicit statement about negative-expectancy patterns (Part 1 predates the discovery that this was even a live question) | Step 1.6 discovered 100% of `VALIDATED` patterns are positive; Step 1.7 determined this is an **undocumented, unresolved architectural gap** (classification C — direction semantics missing/ambiguous), not a deliberate long-only design, and found `short_return = -forward_return` economically invalid as a promotion basis (4 independent reasons, including a direct internal precedent, AD-42, against retrospective synthetic-position fabrication). | §7 adds an explicit, mandatory **Direction Scope Gate** at intake: only positive-expectancy patterns are in scope; everything else is `OUT_OF_SCOPE_FOR_PROMOTION`, never `REJECTED`, never reinterpreted as a short signal. |
| Implicit assumption that `family_size`/`block_bootstrap_p_value`/`deflated_sharpe_ratio` are trustworthy on any `Pattern` revision (§7.1, §7.3) | Step 1's `family_size=1` diagnostic (TD-74) is now **root-caused**: `validate()`/`final_holdout()` each call `build_pattern()` without forwarding these fields, so `build_pattern()`'s own defaults silently overwrite the real v1 values on every later revision. Confirmed by direct before/after evidence (v1: real range 1–171, mean 85.5, 0/1,773 null p-values; latest: 1,773/1,773 reset to `family_size=1`, 1,773/1,773 null p-values). | §12 adds this as an **explicit blocking implementation dependency**: these fields are only trustworthy at `Pattern` version 1 today; the gate must either read v1 directly or the upstream bug must be fixed first — this design does not fix it (out of scope, production code). |

Every other structural piece of Part 1 — the state-machine precedent
survey (§1), the reuse-vs-new inventory (§2), the anti-leakage controls
(§6), the temporal-OOS methodology (§9), and the paper-validation
methodology (§10) — is **carried forward largely intact** into this
section, since none of Steps 1/1.5/1.6/1.7 produced evidence that
contradicts them. Where carried forward, this is stated rather than
silently repeated.

---

## 1. Evidence from Steps 1–1.7 (what this specification is built on)

**Step 1 — Cross-Ticker Family-Collapse Analysis**
(`docs/PATTERN_CROSS_TICKER_FAMILY_COLLAPSE.md`): using one specific,
mechanical, ticker-and-window-stripped family key, the 1,773 `VALIDATED`
patterns (1,737 analyzed, 36 excluded as genuinely ambiguous lead/lag
patterns) collapse to **22 cross-ticker families** (median size 27, max
468 members in one family). 20/22 families span ≥5 tickers; 0/22 span only
1–2. All 22 are same-sign. `family_size=1` for every `VALIDATED` pattern's
*latest* revision is a confirmed data-loss bug in `build_pattern()`
call-sites, not evidence family correction never ran (it ran correctly
once, at `discover()` time). BH passes 1,683/1,773 (94.9%) vs. BY passes
657/1,773 (37.1%) at α=0.05 — descriptive only.

**Step 1.5 — Family Definition Stress Test**
(`docs/PATTERN_FAMILY_DEFINITION_STRESS_TEST.md`): the same population,
under three alternative, equally mechanical normalizations, gives **22
(A) → 62 (B, window-preserving, 2.8×) → 605 (D, exact-condition,
27.5×)** families. Multi-ticker breadth (≥3 tickers/family) collapses from
100% (A) to 5.6% (D). Classified **HIGHLY SENSITIVE**. 100% same-sign
holds under every variant (mechanical, not new evidence). The
36 ambiguous lead/lag patterns reduce to 5 unique predictor→outcome ticker
pairs and 2 feature types — a real, small, structurally distinct group,
never forced into any family.

**Step 1.6 — Directional Validation-Bias Audit**
(`docs/PATTERN_DIRECTIONAL_VALIDATION_BIAS_AUDIT.md`): all 1,773
`VALIDATED` patterns are individually positive-expectancy. Root cause is
**mixed**: (a) real positive EGX market drift over the sample window
(+0.83%/5 trading days, +1.68%/10 days, independently computed from raw
price data, every one of the 14 tickers non-negative) makes 94.3% of
patterns positive already at `DISCOVERED`, before any gate runs — proven,
since `discover()`'s significance test is genuinely two-sided/sign-neutral;
(b) `robustness.py:126`'s `transaction_cost_survival = net_expectancy > 0`
is a hard, absolute, non-sign-relative gate that forecloses any
negative-expectancy pattern regardless of market regime — deterministically
responsible for at least 400 of 1,625 rejections. GT/LT operator parity
rules out a per-operator code bug (LT survivors are *more* often positive
than GT, 98.6% vs. 92.9%). The original 7,899-candidate discovery pool has
a permanent, ~4,501-candidate (57%) unrecoverable gap — no per-candidate
sign/operator/ticker data exists for what didn't survive discovery-stage
FDR control.

**Step 1.7 — Directional Semantics & Economic Validity Audit**
(`docs/PATTERN_DIRECTIONAL_SEMANTICS_AUDIT.md`): classification **C —
direction semantics are missing/ambiguous**. No authoritative document
(`docs/VISION.md`, `MASTER_PROMPT.md`, the investment doctrine set, or
`patterns/`'s own docstrings) states an explicit long-only mandate — the
long-only behavior is an undocumented, emergent property of
`robustness.py:126` and `baselines.py:161-162`, in direct tension with
`live.py`'s own explicit "never a BUY/SELL label" framing. `Pattern` has
no direction/side field. `short_return = -forward_return` is mechanically
valid but economically invalid as a promotion basis: no independent
re-validation of the negated series through the pipeline, no short-cost/
borrow/availability model anywhere in this codebase, no EGX
short-selling data source, and a direct internal precedent (**AD-42**)
already rejects fabricating synthetic long/short positions from
non-executed outcomes elsewhere in this platform. Nothing downstream
(`decision_service`, `portfolio`, `capital_allocation`, `shadow_fund`,
`api`, `web`) imports `patterns/` today — the directional ambiguity has
zero live consequence *yet*, which is exactly why it must be resolved
*before* this Gate creates the first real bridge into decision-relevant
use, not after. Recommendation: Gate design may proceed, scoped to
positive-expectancy patterns only.

---

## 2. Revised state machine

```
   Pattern.status                        DIRECTION SCOPE CHECK (immediate,
   == VALIDATED    ┌─────────────┐       no new data required — see §7)
   ─────────────▶  │ DISCOVERED  │───────────┬─────────────────────────┐
   (Mission 2's     │ (gate-local │           │                         │
   endpoint; same   │  intake)    │   expectancy > 0            expectancy <= 0
   naming-collision └──────┬──────┘   (long, in scope)          (out of scope --
   caveat as Part 1        │                  │                  NOT a short
   applies -- see §13)     │                  ▼                  candidate)
                            │         ┌────────────────┐                │
                            │         │  proceeds to   │                ▼
                            │         │  OOS_VALIDATED │      ┌──────────────────────┐
                            │         └───────┬────────┘      │ OUT_OF_SCOPE_FOR_    │
                            │                 │ fresh, post-original-run│ PROMOTION (terminal, │
                            │                 │ temporal slice; sign-   │ NOT rejected, NOT a  │
                            │                 │ agreement (§8.A)        │ short signal -- §7)  │
                            │                 ▼                └──────────────────────┘
                            │         ┌────────────────┐
                            │         │ OOS_VALIDATED  │
                            │         └───────┬────────┘
                            │                 │ redundancy/independence report +
                            │                 │ perturbation/regime/cost stability +
                            │                 │ effect-size/CI floor (§8.B/C/E/F/G/H)
                            │                 ▼
                            │           ┌───────────┐
                            │           │  ROBUST   │
                            │           └─────┬─────┘
                            │                 │ economic rationale + cohort-level
                            │                 │ multiple-testing correction +
                            │                 │ data-provenance integrity check (§6, §8.D/I)
                            │                 ▼
                            │      ┌─────────────────────┐
                            │      │ PROMOTION_ELIGIBLE  │  (NEW in v2 -- the consolidated
                            │      │                     │   evidence checkpoint before any
                            │      └──────────┬──────────┘   forward window opens)
                            │                 │ frozen definition, pre-registered
                            │                 │ paper window + criteria (§8.J, §9)
                            │                 ▼
                            │      ┌──────────────────┐
                            │      │  PAPER_VALIDATED │  zero capital, frozen assumptions
                            │      └────────┬─────────┘
                            │                 │ paper window's pre-registered criteria met
                            │                 ▼
                            │            ┌───────────┐
                            │            │ PROMOTED  │  (terminal for this gate; consumer
                            │            │           │   destination remains out of scope, §13)
                            │            └───────────┘
                            │
        From any non-terminal stage, at any time evidence fails a hard gate:
              ──▶ REJECTED (terminal; a materially changed pattern requires a
                   brand-new PromotionCase against a new Pattern id, mirroring
                   genome.mutate() -- unchanged from Part 1 §4)

        From any non-terminal stage, when evidence is too thin to judge:
              ──▶ INSUFFICIENT_EVIDENCE (non-terminal; re-enters the SAME
                   stage once more evidence exists -- unchanged from Part 1 §4)
```

**Why `OOS_VALIDATED` now precedes `ROBUST`** (reversed from Part 1's
`ROBUST` → `OOS_VALIDATED` order): the redundancy/independence framework
(§5) that now backs the `ROBUST` transition is more expensive to compute
than it was in Part 1's single-family-key design (it evaluates several
redundancy dimensions at multiple granularities, plus cross-sectional
correlation and temporal-clustering checks, §5.4–5.5). Checking the
temporal-OOS gate first — cheap, mechanical, and the *only* evidence
source in the entire pipeline that is leak-free by construction because it
postdates the original run — filters the population before the more
expensive redundancy work runs. This is an efficiency ordering, not a
change in what evidence is ultimately required; a pattern must still clear
both.

**`PROMOTION_ELIGIBLE` is new in v2.** It is the single consolidated
checkpoint where: (a) the economic-rationale gate (Part 1 §5, carried
forward), (b) a promotion-cohort-level multiple-testing correction (§6.4 —
new, since promoting several patterns from the same registry "at once" is
itself a multiple-comparisons event this design must not ignore), and (c)
a full data-provenance integrity check (§8, extended) all run together,
*before* any real forward-observation window opens for paper validation.
Part 1 folded the economic-rationale check into "gates entry to
`PAPER_VALIDATED`" without its own named state; v2 promotes it to an
explicit, auditable stage because it now carries more than one
responsibility (rationale + cohort correction + provenance integrity), and
a name makes each of those three failure modes separately diagnosable in
the transition log.

**`OUT_OF_SCOPE_FOR_PROMOTION` is new in v2**, reachable only from intake
(`DISCOVERED`), immediately, from the pattern's own already-persisted
`expectancy` sign — no new data is required to reach this classification,
and no pattern is ever moved into it after entering `OOS_VALIDATED` or
later (a pattern's expectancy sign is fixed at intake by the frozen
snapshot, per the anti-leakage rules carried forward from Part 1 §6).

---

## 3. Exact gate criteria

Every transition, restated for v2 with its evidence source. "Hard" and
"Provisional" are used exactly as defined in §4 below.

| Transition | Criteria | Threshold status | Failure state |
|---|---|---|---|
| `VALIDATED` → `DISCOVERED` (intake) | `Pattern.validation_status == PatternStatus.VALIDATED`. Frozen snapshot captured (`conditions`, `regime_filter`, `target_id`, `ticker`, `expectancy`, `sample_size`, all at the pattern's **version 1** revision specifically — see §12's blocking dependency on the `family_size` data-loss bug). | Hard (definitional) | Never fails; always succeeds or the case is never opened |
| `DISCOVERED` → direction scope check | `expectancy > 0` at the frozen intake snapshot. | Hard (inherited scope boundary — see §7; not a statistical threshold, a scope decision) | `OUT_OF_SCOPE_FOR_PROMOTION` if `expectancy <= 0` — **never** `REJECTED`, **never** reinterpreted via `short_return = -forward_return` (§7) |
| `DISCOVERED` → `OOS_VALIDATED` | Matched observations exist on data strictly postdating the original run's `as_of`; sign agrees with the frozen discovery/validation-period sign; matched-observation count clears a declared floor. | Provisional floor (§4); Hard sign-agreement rule (inherited from `WalkForwardValidator`/`final_holdout()`'s own existing criterion, unchanged in this mission) | `INSUFFICIENT_EVIDENCE` if the floor isn't cleared yet (expected, common, not a bug — Part 1 §13.2, unchanged); `REJECTED` if sign disagrees |
| `OOS_VALIDATED` → `ROBUST` | Redundancy Report (§5) computed and attached (never gates on a single K threshold — §5.1); cross-sectional correlation and temporal-clustering checks computed and attached (§5.4–5.5, informational, not yet a hard pass/fail — see §13); all `RobustnessTester` perturbations agree in sign (`RobustnessResult.passed`, inherited, unchanged); `regimes.overall_tag != unstable`; net-of-cost expectancy `> 0` (inherited, already true of every `VALIDATED` pattern today — see §8.F); bootstrap CI lower bound on expectancy `> 0` (new, Provisional — §8.E). | Mixed — see §4 line items | `INSUFFICIENT_EVIDENCE` if the Redundancy Report cannot be computed for lack of comparison data (e.g. a genuinely EGX-unique signal with no peer at any granularity); `REJECTED` if any hard sub-criterion fails outright |
| `ROBUST` → `PROMOTION_ELIGIBLE` | Non-empty, minimum-substance `economic_rationale` + passing `CausalAssessment` (inherited structurally from `EconomicRationaleGate`/`EconomistReviewer`, unchanged from Part 1 §5); promotion-cohort-level multiple-testing correction passes for the currently-open cohort of `PromotionCase`s (§6.4, new); data-provenance integrity check confirms no evidence-window reuse across stages (§8, extended). | Mixed — see §4 | `REJECTED` if rationale is empty/placeholder, cohort correction fails, or provenance integrity check fails |
| `PROMOTION_ELIGIBLE` → `PAPER_VALIDATED` | `PaperValidationRun` opened against the frozen snapshot, pre-registered window (N trading days or M matched observations, whichever is later) and pre-registered success criterion, both declared before the window opens. Zero capital deployed (enforced structurally — no import path into `decision_service`/`capital_allocation`/`shadow_fund`). | Provisional window/criteria parameters (§4); Hard "frozen, pre-registered, zero-capital" structure (unchanged from Part 1 §10) | Window stays open (in-progress sub-state on `PaperValidationRun.status`, not a distinct enum value — unchanged from Part 1) |
| `PAPER_VALIDATED` → `PROMOTED` | Paper window's pre-registered criterion met at close. | Provisional criterion parameters, Hard criterion *shape* (sign-agreement + matched-obs floor, same as `final_holdout()`'s own — unchanged from Part 1) | `REJECTED` if criterion not met at close |
| Any stage → `REJECTED` | Any hard requirement fails outright (not "not yet enough data"). | — | Terminal; new `PromotionCase` required for a materially changed pattern (unchanged from Part 1 §4/§6) |
| Any stage → `INSUFFICIENT_EVIDENCE` | Explicitly marked per transition above. | — | Non-terminal; same case re-enters the same stage once more evidence exists (unchanged from Part 1 §4) |

---

## 4. Provisional vs. hard thresholds

Per the explicit methodological requirement: every threshold below states
its rationale, whether it is inherited from existing system policy, and
whether it requires calibration. Nothing is chosen "because it looks
reasonable."

### Hard (inherited from already-enforced system policy — not new, not calibrated by this design because they were already decided elsewhere)

| Threshold / rule | Inherited from | Why it's hard, not provisional |
|---|---|---|
| Sign-agreement between OOS/holdout and discovery-period expectancy | `validation.py:170-174`, `engine.py:673` (unchanged production code) | Already the exact rule `WalkForwardValidator`/`final_holdout()` use today; this gate reuses it verbatim rather than inventing a new criterion. |
| Net-of-cost expectancy `> 0` | `robustness.py:124-126` (unchanged production code) | Already a precondition for reaching `PatternStatus.VALIDATED` at all (Step 1.6 §4) — every pattern this gate ever sees already cleared this; the gate re-asserts it for defense-in-depth, it does not recompute a new number. |
| All `RobustnessTester` perturbations agree in sign | `robustness.py:142-143` (unchanged production code) | Same reasoning — already enforced upstream of `VALIDATED`. |
| `beats_baseline()` result | `baselines.py:156-162` (unchanged production code) | Same reasoning. |
| Direction scope: `expectancy > 0` required for promotion eligibility | Step 1.7's classification (C) plus the AD-42 precedent against synthetic-position fabrication | This is a **scope boundary**, not a statistical threshold subject to calibration — it does not become "more correct" with more data. It changes only if the architectural decision in Step 1.7 §11 (build real short-side infrastructure) is made explicitly by the user/product owner. |
| Frozen-snapshot / no-post-hoc-tuning discipline | `genome.AlphaGenome.mutate()`'s "new child, parent `REPLACED`" precedent, `sources.qualification`'s pure-function-then-persist pattern | Structural anti-leakage requirement, not a number — cannot be "miscalibrated," only present or absent. |
| Zero capital deployment during paper validation | Explicit mission boundary (`decision_service`/`shadow_fund` untouched) | A structural/architectural constraint, not a statistical threshold. |
| Same-sign family results are never cited as corroboration | Step 1.6 (94.3% pre-gate positive) + Step 1.5 (100% same-sign under every variant, mechanical) | A methodological rule directly required by evidence already gathered, not a number to tune. |

### Provisional (declared, requires calibration before being trusted as final; every one below is explicitly marked so no implementer treats it as decided)

| Threshold | Proposed starting value | Rationale for the starting value | What calibration requires |
|---|---:|---|---|
| Minimum OOS matched-observation floor | Reuse `WalkForwardValidatorConfig.min_oos_sample_size` (currently 10) as an absolute floor, scaled up for sparser-triggering patterns (Part 1 §9, unchanged) | Consistency with the one analogous floor that already exists in this codebase, not a fresh derivation | Real decision-ledger outcome history correlating floor size with paper-validation success rate — does not exist yet |
| Bootstrap CI lower-bound-positive requirement at `ROBUST` (new in v2) | Reuse the existing bootstrap machinery `block_bootstrap_p_value()` already runs, at the same default iteration count (1,000) and `alpha=0.05` | Reuses infrastructure and a confidence level already used elsewhere in this codebase (`evaluation.py`'s own bootstrap CI), not a new statistical framework | Whether 95% is the right coverage for a promotion decision (vs. e.g. 90% or 99%) is untested |
| Paper-validation window: N trading days / M matched observations (whichever is later) | Not proposed numerically here (Part 1 also declined to propose a number) | Depends on the pattern's own horizon (`horizon_days`) and trigger frequency — a fixed number would be wrong for a 5-day-horizon daily-triggering pattern and a 60-day-horizon monthly-triggering one alike | Needs at minimum one full real paper-validation cycle to observe before any number can be defended |
| Promotion-cohort-level multiple-testing correction: BH vs. BY | **Neither chosen** (§6.4) | Step 1's own descriptive comparison shows a 2.6× outcome swing (1,683 vs. 657 passes) between the two on the exact same data, with no calibration evidence for either at this stage | Real paper-validation false-promotion-rate history, which does not exist until this gate has run at least once |
| Economic-rationale "minimum substance" bar | Reuse `EconomistReviewer`'s existing length/engagement heuristic structurally (Part 1 §5, unchanged) | Consistency with the one existing analogous check in this codebase | Whether that heuristic (built for hypothesis rationale, not pattern rationale) transfers correctly to this new context is untested |
| Redundancy-report clustering/overlap threshold (§5.6) | Reuse `candidates.py`'s existing `match_overlap_prune_threshold` (0.85 Jaccard) as a starting point, since it is the one directly analogous, already-declared-and-used threshold in this codebase for "these two trigger-date sets are redundant" | Consistency with existing, already-shipped pruning logic | That threshold was calibrated (informally) for *within-run candidate generation* pruning, not *cross-pattern, cross-run* redundancy reporting at promotion time — an untested transfer |

**Explicitly not proposed as any kind of threshold in this document**: a
family-definition K (superseded, §0), an HHI ceiling on the `PROMOTED` set
(the concept from Part 1 §8.3 is retained conceptually in §5.3 below, but
no ceiling number is proposed — it depends on how many patterns ever reach
`PROMOTION_ELIGIBLE`, which is currently unknown), and a choice between BH
and BY (§6.4).

---

## 5. Redundancy / independence framework (replaces Part 1 §8's single family-key approach)

Per the explicit instruction, this section does **not** select Variant A,
B, or D as the final family definition, and does **not** hardcode K as a
gate. Instead, it specifies a **reporting layer** — a `RedundancyReport`
attached to every `PromotionCase` at `ROBUST` — that characterizes several
distinct kinds of redundancy without pretending they are the same signal,
plus three additional independence checks that go beyond naming-based
grouping entirely.

### 5.1 Why K-on-one-family-definition cannot be the gate

Step 1.5 proved the family *count* — and therefore any K-based pass/fail
computed from it — swings 22× to 27× across equally defensible, equally
mechanical normalizations. A gate that hardcodes K≥3 on Variant A rejects
almost nothing (20/22 families already clear it trivially); the identical
rule on Variant D rejects almost everything (494/605 families are
singletons). **Neither number is "the" answer** — the sensitivity itself
is the finding. Any gate that picks one definition and reports a single K
is reporting an artifact of that choice, not a property of the pattern.

### 5.2 The reporting layer: six named redundancy dimensions, reported separately

For every `PromotionCase` at `ROBUST`, compute and attach a
`RedundancyReport` with these named, distinct fields — each answers a
different question, and none is used alone as a pass/fail gate (only the
aggregate provisional scoring in §5.7 feeds a decision, and even that is
marked provisional):

| Dimension | Question it answers | Computed as |
|---|---|---|
| **Exact duplicates** | Does an identical `(ticker, conditions, target_id, regime_filter)` tuple exist elsewhere in the registry? | Direct equality check. Expected near-zero given `PatternCandidateGenerator`'s own generation-time overlap pruning (`match_overlap_prune_threshold`) — reported as a sanity check, not expected to be informative in practice. |
| **Same-feature, different-window variants** | How many other `VALIDATED` patterns share this pattern's ticker + stripped-of-window feature base + target kind, differing only in window/horizon? | `rsplit(":", 1)` + strip `_<N>d` suffix, same ticker only (no cross-ticker collapse) — the least controversial grouping, since these near-certainly share serial correlation from the same underlying series. |
| **Same-feature, different-threshold variants** | Among patterns with an identical feature+window+ticker, how many differ only in the quantile threshold tested? | Exact feature-id + ticker match, threshold varies. Also near-certainly correlated (same underlying series, same window, different cut point). |
| **Same-target variants** | How many other patterns predict the identical `target_id` (same ticker, same horizon) using a *different* feature? | Exact `target_id` match, differing `conditions[0].feature_id`. Independence here is more plausible than the two rows above (different economic signal), but still requires the match-set-overlap check (§5.6) before being treated as independent. |
| **Cross-ticker variants** | How many `VALIDATED` patterns test "the same idea" (base feature + target kind + regime status) on a *different* ticker? | Reported at **both** Step 1.5's Variant A (ticker+window stripped) and Variant B (ticker stripped, window preserved) granularities side by side — never collapsed into one number, exactly because §5.1 showed the choice matters. |
| **Highly overlapping patterns (any naming relationship)** | Regardless of feature/ticker naming, do this pattern's and another pattern's actual matched trigger-date sets overlap heavily? | Jaccard overlap of matched-anchor-date sets (§5.6) — the one redundancy signal that does **not** depend on any family-key string definition at all. |

No family-key-based dimension above is treated as sufficient by itself.
The Jaccard trigger-date-overlap dimension (last row) is the most
fundamental, because it is invariant to how features happen to be named —
two patterns with completely different feature/ticker labels that fire on
the same calendar dates are not independent evidence, no matter what their
`cross_ticker_family_key` says; two patterns in the "same" family under
some naming convention that fire on almost entirely disjoint dates
plausibly *are* more independent than their shared label suggests.

### 5.3 Ticker concentration (retained from Part 1 §8.3, ceiling not set)

The Herfindahl-Hirschman concentration measurement Part 1 proposed
(reusing the same formula `market_memory.breadth`/`features.py` already
compute) is retained conceptually — "what share of the currently
`PROMOTED`-eligible set does any one ticker represent" remains a real
question. No ceiling number is proposed here (Part 1 also declined to
propose one beyond "start from the same conservative posture as
`MAX_SECTOR_CONCENTRATION=0.40`, translated"), and this design does not
strengthen that into a number, since — per §5.1's lesson — any number
computed under one family definition is not obviously transferable to
another.

### 5.4 Cross-sectional independence (new in v2)

**Ticker breadth is not independence.** If a family's corroborating
tickers are themselves highly correlated with each other (same sector,
similar market-cap tier, similar beta to the EGX30 index), then multiple
tickers moving together on the same signal is largely one market-wide
effect observed on several correlated names, not several independent
replications. **Common EGX market factors can manufacture apparent
cross-ticker corroboration**: Step 1.6 independently confirmed a real,
strong, broad-based positive nominal drift across the entire 14-ticker
universe over the sample window (every ticker's own mean forward return
non-negative, ranging +0.00% to +1.44% per 5 days) — exactly the kind of
common factor that would make many tickers' price-derived features cross
their thresholds together during the same broad market episodes, without
that co-movement reflecting anything about the specific conditioning
feature at all.

**Proposed check**: for each `RedundancyReport`'s cross-ticker-variant
dimension, compute the pairwise Pearson correlation of adjusted daily
returns between the family's contributing tickers, reusing
`features.correlation.pearson_correlation()` — the same function
`decision_service.concentration`'s correlation-cluster cap already uses in
production. Report the family's mean/median pairwise correlation
alongside its ticker count. A family whose "5 corroborating tickers" have
a mean pairwise correlation of 0.85 is reporting far less independent
information than one whose 5 tickers average 0.15 — **this is reported as
a number, not yet converted into a pass/fail threshold** (§13, open
question).

### 5.5 Temporal and market-regime independence (new in v2)

**Observation count is not independence either.** If a family's aggregate
matched trigger dates (across all contributing tickers) cluster tightly
within one or two calendar episodes, that is closer to one event observed
many times than many independent events. Two checks, both reusing existing
machinery rather than inventing new statistics:

- **Temporal clustering**: compute the date-range dispersion of a family's
  pooled trigger-date set (e.g. what fraction of matches fall within any
  single 20-trading-day window) — reuses the same chronological ordering
  discipline `purge_and_embargo()` already applies, extended to a
  reporting statistic rather than a purge.
- **Regime-span**: reuse `regimes.py`'s existing six-dimension
  characterization (already computed per-pattern) at the family level —
  does the family's corroborating evidence span more than one regime
  bucket per dimension, or does it cluster entirely within a single
  regime? A family whose every member's evidence comes from the same
  volatility/breadth/trend regime bucket has not demonstrated the pattern
  survives *across* regimes, only *within* one.

Both are reported as descriptive statistics on the `RedundancyReport`, not
(yet) hard pass/fail gates — per the explicit instruction to quantify
without solving causality, this design does not claim to know how much
temporal clustering or regime concentration is "too much."

### 5.6 Jaccard trigger-date-overlap (the name-independent signal)

For any two `VALIDATED` patterns (regardless of ticker, feature name, or
family-key membership), compute the Jaccard similarity of their matched
anchor-date sets. Reuses the exact concept `candidates.py`'s own
`_is_redundant_match()`/`match_overlap_prune_threshold` already applies at
*generation* time within one `discover()` run — this design applies the
same computation as a *reporting* statistic across the full `VALIDATED`
population at promotion time, which no existing code currently does
(candidates from different tickers, different `discover()` runs, or
different feature families were never previously compared to each other
this way). **Proposed as the primary, family-definition-independent
redundancy signal** — see §5.7.

### 5.7 If a formal similarity/clustering methodology is required — specified, not implemented

Per the explicit instruction, a methodology is specified for future
implementation, **not built now**:

1. Compute the full pairwise Jaccard trigger-date-overlap matrix over all
   patterns under consideration for a promotion cohort (bounded — see
   Part 1 §13.7's "opening cost at scale" concern, which still applies and
   is why this runs on a *cohort*, not the full 1,773-pattern set, at any
   one time).
2. Build a graph with an edge between any two patterns whose Jaccard
   overlap exceeds a declared threshold (starting point: reuse
   `match_overlap_prune_threshold = 0.85`, §4's provisional table — marked
   PROVISIONAL, an untested transfer from a different use case).
3. Connected components of that graph are "genuinely overlapping clusters"
   — a structurally different, more conservative notion than any
   feature-name-based family, since it requires *actual observed
   co-occurrence*, not shared naming.
4. **Not implemented in this mission.** This is a specification for a
   future implementation step, explicitly deferred per the hard boundary.

---

## 6. Multiple-testing framework

Per the explicit requirement, four distinct correction *layers* are named
and kept separate — none is conflated with another, and BH-vs-BY is not
resolved.

### 6.1 Original candidate-universe correction (already applied, permanently limited)

`discover()`'s own family-corrected-p-value + BH-FDR pass over the
original 7,899-candidate pool, already applied and already reflected in
which 3,398 candidates reached `DISCOVERED` at all. **Permanently and
explicitly limited**: per Step 1.6 §7, ~4,501 of the original 7,899
candidates (57%) were never persisted anywhere — not the registry, not the
`TestingLedger`, not any recoverable artifact. The exact
`discover()`-stage `len(discovery_ok)` intermediate count (candidates with
*any* evaluable distribution before family-correction/BH-FDR) was never
persisted either. **This gate cannot audit or re-derive the original
correction's true denominator** — any claim about the original run's
false-discovery control is bounded by this gap and must be stated with
that caveat every time it is cited, never treated as a fully verified
number.

### 6.2 Post-selection correction (not currently applied anywhere — a real, unresolved gap)

Every pattern this gate ever evaluates already passed `discover()` →
`validate()` → `final_holdout()` — i.e., it was *already selected* for
looking good on the data available at selection time. Re-examining its
*already-computed* discovery/validation-period statistics (block-bootstrap
p-value, deflated Sharpe ratio) at promotion time is a second look at
data that was itself used to choose the pattern — the classic
post-selection-inference problem (a winner's-curse effect: patterns
selected partly by chance will regress toward the mean on genuinely new
data). **The temporal-OOS gate (`OOS_VALIDATED`, §8.A) is this design's
only real defense against this** — it is the one evidence source
guaranteed not to have been part of selection, because it postdates the
original run entirely. Statistics computed on discovery/validation-period
data (DSR, block-bootstrap p-value) are retained and reported, but this
design explicitly does **not** treat them as equivalent in strength to
`OOS_VALIDATED`'s fresh evidence — flagged as an open methodological
question in §13, not resolved with a discount factor here (no such factor
is proposed without calibration evidence).

### 6.3 Family-level correction (exists, currently broken beyond v1, must be fixed before use)

`family_corrected_p_value()`/`block_bootstrap_p_value()`/
`deflated_sharpe_ratio()` are real, correctly-computed fields — **but only
at a `Pattern`'s version-1 (`DISCOVERED`) revision**. Step 1's diagnostic
confirmed `validate()`/`final_holdout()` each silently reset these fields
to defaults on every later revision (a `build_pattern()` call-site bug,
not evidence the correction never worked). **This gate must read these
fields from a pattern's v1 revision specifically**, not its latest
revision, until that upstream bug is fixed (§12, blocking dependency —
this design does not fix production code).

### 6.4 Promotion-cohort-level correction (new in v2, unresolved)

Promoting several patterns "at once" from the same registry is itself a
multiple-comparisons event this design must not ignore — even a perfectly
individually-validated pattern's promotion decision is made in the context
of however many other `PromotionCase`s are simultaneously under
consideration. At `PROMOTION_ELIGIBLE`, a correction must be applied
across the currently-open cohort's evidence. **Which correction — BH or
BY — is explicitly left unresolved**, per the instruction not to declare
BY the final method. Step 1's own descriptive comparison (BH: 1,683/1,773
pass; BY: 657/1,773 pass, at α=0.05) is reported as context for whoever
makes this decision, not as a recommendation either way. **This is a
required open decision before `PROMOTION_ELIGIBLE` can be implemented**
(§13, §14).

---

## 7. Directional scope (explicit rule)

**Only positive-expectancy long candidates are currently in scope for this
Promotion Gate.**

- Enforced entirely at the new `PromotionCase` intake layer (§2, §3) — a
  simple `expectancy > 0` check against the frozen intake snapshot. **No
  production code is modified to formalize this** — `robustness.py`,
  `baselines.py`, and every other file Step 1.6/1.7 audited stay exactly
  as they are; this rule lives only in the new gate.
- A pattern with `expectancy <= 0` is classified `OUT_OF_SCOPE_FOR_PROMOTION`
  — **never** `REJECTED` (which would imply the pattern was evaluated and
  found wanting) and **never** silently converted into a short signal via
  `short_return = -forward_return` or any equivalent relabeling anywhere
  in this design.
- **Practical impact on the current real registry: none today.** Every one
  of the 1,773 currently `VALIDATED` patterns already has positive
  expectancy (Step 1.6) — this rule currently classifies zero patterns as
  out-of-scope. It is stated explicitly anyway, because a future run
  (different market regime, different universe, or a future code change to
  `robustness.py`/`baselines.py` outside this design's scope) could
  produce a `VALIDATED` pattern with non-positive expectancy, and this gate
  must not silently mishandle that case when it happens.
- **Re-entry path if the architecture changes later**: if the
  user/product owner makes the architectural decision Step 1.7 §11
  describes (building real short-side cost/availability/financing
  infrastructure and independently re-validating a short target through
  the full `discover()`→`validate()`→`final_holdout()` pipeline), an
  `OUT_OF_SCOPE_FOR_PROMOTION` case does **not** automatically become
  eligible — a **new** `PromotionCase` against a **new**, independently
  re-validated `Pattern` would be required, mirroring the "new child, old
  terminal" discipline already used for `REJECTED` (§2). This is noted as
  a future extension point, not decided or built now (§13).

---

## 8. Gate dimensions A–J: evidence requirements and where each lives

| Dimension | Evidence required | Lives at stage | Status |
|---|---|---|---|
| **A. Temporal OOS** | Matched observations on data strictly postdating the original run's `as_of`; sign-agreement with the frozen discovery/validation sign; matched-observation floor cleared. | `DISCOVERED` → `OOS_VALIDATED` | Sign-agreement rule Hard/inherited; floor Provisional (§4). Reuses `WalkForwardValidator`'s existing sign-agreement construction, applied to a genuinely fresh window (Part 1 §9, unchanged). |
| **B. Cross-ticker / cross-sample robustness** | `RedundancyReport`'s cross-ticker-variant dimension, reported at ≥2 granularities (§5.2) — never a single K. | `OOS_VALIDATED` → `ROBUST` | Provisional scoring methodology (§5.7); no hard K (superseded, §0). |
| **C. Redundancy / independence** | Full `RedundancyReport` (6 dimensions, §5.2) + cross-sectional correlation (§5.4) + temporal/regime independence (§5.5) + Jaccard overlap (§5.6). | `OOS_VALIDATED` → `ROBUST` | All Provisional/reported-only at this stage (§13); the reporting layer itself is the required deliverable, its conversion into a hard pass/fail is explicitly deferred. |
| **D. Multiple-testing control** | Original-run correction (with its permanent limitation stated, §6.1); family-level correction (read from v1 only, §6.3); promotion-cohort correction (§6.4, BH-vs-BY unresolved). | Spans intake (§6.1/6.3, read-only) and `ROBUST` → `PROMOTION_ELIGIBLE` (§6.4, gating) | Mixed — see §4 and §6. |
| **E. Effect size and confidence intervals** | Net-of-cost expectancy `> 0` (inherited) + bootstrap CI lower bound `> 0` (new). | `OOS_VALIDATED` → `ROBUST` | Net-of-cost Hard/inherited; CI Provisional (new) (§4). |
| **F. Transaction-cost-adjusted expectancy** | `RobustnessResult.net_of_cost_expectancy > 0` — already true of every pattern this gate ever sees, since it's a precondition of reaching `PatternStatus.VALIDATED` today (Step 1.6 §4). This gate re-asserts, does not recompute. | Re-asserted at `OOS_VALIDATED` → `ROBUST` | Hard/inherited (§4); should be unreachable-as-a-failure in practice given upstream enforcement. |
| **G. Baseline comparison** | `beats_baseline()` result — same "already true, re-asserted" status as F. | Re-asserted at `OOS_VALIDATED` → `ROBUST` | Hard/inherited (§4). |
| **H. Stability / perturbation robustness** | `RobustnessResult.passed` (all perturbations agree in sign) — same "already true, re-asserted" status. | Re-asserted at `OOS_VALIDATED` → `ROBUST` | Hard/inherited (§4). |
| **I. Economic plausibility** | Non-empty, minimum-substance `economic_rationale` + passing `CausalAssessment` (Part 1 §5, unchanged). | `ROBUST` → `PROMOTION_ELIGIBLE` | Providing a rationale is Hard; the substance bar is Provisional (§4). |
| **J. Forward paper validation** | `PaperValidationRun` against the frozen snapshot; pre-registered window and success criterion; zero capital (Part 1 §10, unchanged). | `PROMOTION_ELIGIBLE` → `PAPER_VALIDATED` → `PROMOTED` | Criterion shape Hard/inherited from `final_holdout()`; window/criteria parameters Provisional (§4). |

**Data-provenance integrity** (new, extends Part 1 §6's anti-leakage
controls): at `PROMOTION_ELIGIBLE`, before opening any paper-validation
window, verify the full evidence chain for a `PromotionCase` — discovery
data → validation data → final holdout → (this gate's) fresh OOS data —
uses **strictly non-overlapping, chronologically ordered** date ranges,
recorded in the case's own append-only transition log. No stage's window
may overlap any earlier stage's window for the same pattern. This is a
structural check (an assertion that raises on violation), not a
statistical threshold — Hard, not Provisional.

---

## 9. Paper-validation protocol

Unchanged from Part 1 §10, restated for completeness against the revised
state machine: frozen pattern definition and parameters (independent copy
on `PaperValidationRun`, decoupled from the live `Pattern`); no post-hoc
tuning (any change requires a brand-new `PaperValidationRun` under a
brand-new `PromotionCase`, never an in-place edit); predefined observation
window (N trading days or M matched observations, whichever is later,
both declared before the window opens); predefined success/failure
criteria (sign-agreement + matched-observation floor, the same criterion
shape `final_holdout()` already uses); zero capital deployment enforced
structurally (no import path into `decision_service`/`capital_allocation`/
`shadow_fund`); mechanism reuse follows `investment_proof.walk_forward
.WalkForwardInfrastructure`'s day-by-day replay precedent, at the pattern
level via `LiveActivationEngine`/`OutcomeTracker` rather than the decision
level.

---

## 10. Promotion / rejection logic

- **Promotion** (`PAPER_VALIDATED` → `PROMOTED`) requires every gate
  dimension A–J to have been cleared at its respective stage, with no
  stage skipped and no evidence window reused across stages (§8's
  provenance check). A pattern that has cleared every hard gate but still
  has open Provisional thresholds (§4) still promotes — Provisional means
  "not yet calibrated with confidence," not "blocking, unless and until
  the user explicitly tightens it."
- **Rejection** is always attributable to one specific, named hard-gate
  failure (§3's table), recorded in the `PromotionCase`'s
  `rejection_reason`, and is terminal for that case — a materially changed
  pattern requires a new `PromotionCase` against a new `Pattern` id
  (unchanged from Part 1 §4/§6, mirroring `genome.mutate()`).
- **`OUT_OF_SCOPE_FOR_PROMOTION`** is never conflated with rejection in
  logging, reporting, or any downstream consumer's read of a
  `PromotionCase` — a distinct terminal classification meaning "this
  system currently has no way to economically interpret this pattern," not
  "this pattern is bad" (§7).
- **`INSUFFICIENT_EVIDENCE`** is never conflated with rejection either —
  a real, non-pejorative, retry-eligible outcome (unchanged from Part 1
  §4).

---

## 11. Required schema / artifacts

Extends Part 1 §11's `PromotionCase`/`PaperValidationRun` design (all
prior fields retained) with the following new fields/entities:

**`PromotionCase`, new fields:**
- `direction_scope: Literal["IN_SCOPE_LONG", "OUT_OF_SCOPE"]` +
  `direction_scope_reason: str` (§7) — set once, at intake, immutable.
- `redundancy_report_ref` — reference to the new `RedundancyReport` entity
  (§5.2), replacing Part 1's single `cross_ticker_family_key` field (kept
  as one *component* of the report, not the report itself).
- `cross_sectional_correlation_ref` / `temporal_regime_independence_ref` —
  references to the §5.4/§5.5 descriptive statistics.
- `multiple_testing_evidence`: a structured object separating
  `original_run_correction_ref` (§6.1, with its stated permanent
  limitation), `family_level_correction_source_version: int` (must record
  that this was read from `Pattern` v1, per §6.3's blocking dependency),
  and `promotion_cohort_correction_ref` (§6.4, populated only once §6.4's
  open decision is made).
- `confidence_interval_ref` — the new bootstrap CI (§4, §8.E).
- `provenance_windows: list[DateRange]` — the append-only, non-overlapping
  evidence-window ledger (§8's provenance integrity check).

**New entity: `RedundancyReport`** — `pattern_id`, `exact_duplicates`,
`same_feature_different_window`, `same_feature_different_threshold`,
`same_target_variants`, `cross_ticker_variants_by_granularity: dict[str,
...]` (keyed by which stripping granularity, never collapsed to one),
`jaccard_overlap_cluster_members` (§5.6/§5.7, populated only once the
clustering methodology is actually implemented — a future step), `provenance`.

All Part 1 §11 entities (`CrossTickerRobustnessReport`,
`PaperValidationRun`, and the reused-as-is list — `WalkForwardResult`,
`RobustnessResult`, `PatternFailureProfile`, `TransactionCostSensitivity`,
`ReproducibilityManifest`, `CausalAssessment`, `ActivationOutcome`) are
retained; `CrossTickerRobustnessReport` is reinterpreted as one *input* to
`RedundancyReport.cross_ticker_variants_by_granularity`, not a
standalone verdict.

---

## 12. Required tests

Extends Part 1 §12 (all prior tests retained: state-machine legality,
anti-leakage proofs, positive/negative control, real-data regression,
`INSUFFICIENT_EVIDENCE` correctness) with:

- **`OUT_OF_SCOPE_FOR_PROMOTION` correctness**: a synthetic
  `PatternStatus.VALIDATED` pattern with `expectancy <= 0` must land at
  `OUT_OF_SCOPE_FOR_PROMOTION` at intake, never at `REJECTED`, and no code
  path anywhere in the gate may compute or reference a negated/short
  version of its expectancy.
- **No-hardcoded-K regression test**: assert no code path in the gate
  computes a single family count and compares it to a fixed K as a
  boolean pass/fail — the `RedundancyReport`'s cross-ticker dimension must
  always be reported at ≥2 granularities, never collapsed to one number
  before a decision is made.
- **Redundancy-report completeness**: all six named dimensions (§5.2) are
  populated (or explicitly marked not-computable, never silently omitted)
  for every `PromotionCase` reaching `ROBUST`.
- **`family_size` version-read correctness**: a test asserting the gate
  reads `family_size`/`block_bootstrap_p_value`/`deflated_sharpe_ratio`
  from a pattern's **version 1** revision, not its latest — with an
  explicit regression case using a pattern whose latest revision has the
  known-corrupted `family_size=1`/null-p-value values (§6.3), asserting
  the gate does not silently trust those.
- **Multiple-testing layer separation**: four separate tests asserting the
  original-run, post-selection, family-level, and cohort-level corrections
  are computed and stored independently, never merged into one number.
- **Cross-sectional correlation sanity**: a synthetic family of highly
  correlated tickers (reusing `control_suite.py`'s own synthetic-data
  conventions) produces a high mean pairwise correlation in the
  `RedundancyReport`, and a family of genuinely uncorrelated tickers
  produces a low one — proving the check is not a no-op.
- **Provenance-window overlap detection**: a `PromotionCase` whose
  `OOS_VALIDATED` window is manually constructed to overlap its
  `discovery_period` must fail the `PROMOTION_ELIGIBLE` provenance
  integrity check (§8) with a hard error, not a silent pass.

---

## 13. Open methodological questions

Carried forward from Part 1 §13 where still unresolved, with new items
appended:

1. Naming collision between the gate's `DISCOVERED` and
   `PatternStatus.DISCOVERED` (Part 1 §13.1) — still unresolved.
2. `OOS_VALIDATED` remains structurally rate-limited by real calendar time
   (Part 1 §13.2) — unchanged, still presented as correct, not a defect.
3. Mixed-sign families (Part 1 §13.4) — still open, and now sharpened by
   Step 1.6: since 100% of `VALIDATED` patterns are currently positive,
   this question is currently moot for the real registry, but remains
   unresolved for any future run where it might not be.
4. Where the economic-rationale check sits (Part 1 §13.5) — resolved
   differently in v2: it is now folded into the named `PROMOTION_ELIGIBLE`
   stage rather than being an unnamed gate-to-entry check, per §2's
   rationale.
5. The output-destination question (Part 1 §13.6) — still entirely
   unresolved and still deliberately out of scope.
6. Opening cost at scale (Part 1 §13.7) — still applies; sharpened by
   §5.7's clustering proposal explicitly operating on a bounded cohort,
   not the full 1,773-pattern set.
7. `family_size=1`-for-every-survivor (Part 1 §13.8) — **no longer
   unexplained** (Step 1 root-caused it as a `build_pattern()` data-loss
   bug), but **still unfixed** — §6.3/§12 make the workaround (read v1
   only) and the test that proves it explicit; fixing the underlying bug
   remains out of scope for this design (production code).
8. **(New)** Cross-sectional correlation and temporal/regime independence
   (§5.4/§5.5) are specified as *reported statistics*, not yet converted
   into hard pass/fail thresholds — how much correlation or temporal
   clustering is "too much" is genuinely unknown and requires real
   calibration evidence this mission does not yet have.
9. **(New)** BH vs. BY for the promotion-cohort-level correction (§6.4)
   remains explicitly unresolved — this is now a required decision before
   `PROMOTION_ELIGIBLE` can be implemented, not a preference stated in
   passing.
10. **(New)** The post-selection-inference discount question (§6.2): should
    discovery/validation-period statistics (DSR, block-bootstrap p-value)
    be down-weighted relative to fresh `OOS_VALIDATED` evidence in any
    future scoring formula, and if so by how much? No discount factor is
    proposed without calibration evidence.
11. **(New)** The Jaccard-overlap clustering threshold (§5.7) is proposed
    to start from `candidates.py`'s existing 0.85, but that value was
    calibrated for a different use case (within-run generation-time
    pruning) — whether it transfers to cross-pattern, cross-run redundancy
    reporting is untested.
12. **(New)** The `OUT_OF_SCOPE_FOR_PROMOTION` re-entry path (§7) if
    short-side infrastructure is ever built is noted as a future extension
    point but not designed in any detail here — deferred entirely.

---

## 14. Implementation dependencies

**Blocking, must resolve before implementation begins in earnest:**

1. **The `family_size`/`block_bootstrap_p_value`/`deflated_sharpe_ratio`
   data-loss bug** (§6.3) — `validate()`/`final_holdout()` silently reset
   these fields via `build_pattern()`'s own defaults. This design's
   workaround (always read from `Pattern` v1) is a valid stopgap, but the
   underlying production bug is a real, separate fix this mission does not
   make (out of scope: production code).
2. **BH-vs-BY for the promotion-cohort correction** (§6.4, §13.9) —
   required before `PROMOTION_ELIGIBLE` can be implemented, currently
   unresolved.
3. **The Redundancy Report's aggregate scoring methodology** (§5.7) —
   specified conceptually, not implemented; the six-dimension report can
   be built and populated before this is resolved, but converting it into
   any pass/fail decision cannot.

**Non-blocking but recommended, to close permanent evidence gaps for
future runs:**

4. Any future real `discover()` run should persist a `DiscoveryRunReport`
   (or at minimum the `len(discovery_ok)` intermediate count) to a
   repository, closing the ~4,501-candidate epistemic gap (§6.1, Step 1.6
   §7) that this specific Mission 2 run cannot retroactively close.

**Ordering, extending Part 1 §14** (steps 1–4 of Part 1's plan — family-
collapse pass, `PromotionCase` schema/state-machine, frozen-snapshot
intake, cross-ticker+statistical hard gates — are superseded by: build the
`RedundancyReport` schema and all six dimensions first, since no K/family
choice gates anything anymore; the direction-scope check (§7) is cheap and
should be built alongside intake, immediately, since it requires no new
data). Part 1's steps 5–9 (temporal OOS, economic-rationale gate,
paper-validation infrastructure, control suite, documentation) are
unchanged in relative order, with `PROMOTION_ELIGIBLE`'s cohort-correction
logic (§6.4) inserted between the economic-rationale gate and
paper-validation infrastructure, blocked on dependency #2 above.

---

## Final decision table

| Gate | Required Evidence | Hard / Provisional | Failure State | Data Source |
|---|---|---|---|---|
| Direction scope (intake) | `expectancy > 0` on frozen intake snapshot | **Hard** (scope boundary, not calibrated — §4, §7) | `OUT_OF_SCOPE_FOR_PROMOTION` | `Pattern.expectancy` (registry, v1 revision) |
| A. Temporal OOS | Matched observations strictly postdating original `as_of`; sign-agreement; matched-obs floor | Sign-agreement **Hard**/inherited; floor **Provisional** | `INSUFFICIENT_EVIDENCE` (floor not met) / `REJECTED` (sign disagrees) | Fresh post-run price/feature data (not yet collected) |
| B. Cross-ticker / cross-sample robustness | `RedundancyReport.cross_ticker_variants_by_granularity` (≥2 granularities, never one K) | **Provisional** (scoring methodology unresolved, §5.7) | `INSUFFICIENT_EVIDENCE` if too few comparators at every granularity | Registry + `RedundancyReport` |
| C. Redundancy / independence | Full `RedundancyReport` (6 dimensions) + cross-sectional correlation + temporal/regime independence + Jaccard overlap | **Provisional** (reported only; not yet a pass/fail — §13.8) | `INSUFFICIENT_EVIDENCE` if not computable | Registry, `features.correlation`, `regimes.py`, new Jaccard computation |
| D. Multiple-testing control | Original-run correction (limited, §6.1) + family-level correction (v1-only, §6.3) + cohort-level correction (§6.4) | Original/family **Hard-inherited-but-flagged-incomplete**; cohort-level **Provisional**, unresolved BH-vs-BY | `REJECTED` if cohort correction fails once resolved | `TestingLedger`, `Pattern` v1 fields, new cohort computation |
| E. Effect size and confidence intervals | Net-of-cost expectancy `> 0` (inherited) + bootstrap CI lower bound `> 0` (new) | Net-of-cost **Hard**/inherited; CI **Provisional** (new) | `REJECTED` | `RobustnessResult` (existing) + new CI computation |
| F. Transaction-cost-adjusted expectancy | `RobustnessResult.net_of_cost_expectancy > 0` | **Hard**/inherited (already enforced pre-`VALIDATED`) | `REJECTED` (should be unreachable in practice) | `RobustnessResult` (existing) |
| G. Baseline comparison | `beats_baseline()` result | **Hard**/inherited (already enforced pre-`VALIDATED`) | `REJECTED` (should be unreachable in practice) | `baselines.py` output (existing) |
| H. Stability / perturbation robustness | `RobustnessResult.passed` | **Hard**/inherited (already enforced pre-`VALIDATED`) | `REJECTED` (should be unreachable in practice) | `RobustnessResult` (existing) |
| I. Economic plausibility | Non-empty `economic_rationale` + passing `CausalAssessment` | Providing rationale **Hard**; substance bar **Provisional** | `REJECTED` (empty/placeholder) | New field + `causal/reasoner.py` |
| J. Forward paper validation | `PaperValidationRun` pre-registered criteria met, frozen definition, zero capital | Criterion shape **Hard**/inherited; window/criteria parameters **Provisional** | `REJECTED` (criteria not met at close) | `PaperValidationRun`, `LiveActivationEngine`, `OutcomeTracker` |

---

*End of Part 2 / v2. This is design only — no code, tests, registry data,
validation statuses, or `PromotionCase` records were created or modified
to produce this document. Nothing was merged to `main`. Implementation
does not begin until this specification is reviewed.*

---

# Mission 3 Design Readiness Review — v2

**Status: REVIEW ONLY.** No code, tests, thresholds, Mission 2 artifacts,
production logic, the registry, any `validation_status`, or any
`PromotionCase` record is changed by this section. This reviews Part 2
(the v2 specification above) against five remaining methodological
questions, produces a threshold inventory and a statistical-evidence
integrity matrix, and issues a single final readiness classification.
Part 1 and Part 2 are unmodified above this point.

## 1. Jaccard trigger-date overlap — findings

**What sets are being compared.** Per v2 §5.6, each `Pattern`'s **trigger
date set**: the subset of its own `anchor_dates` (the research-period
dates for its ticker, per `panel.tickers`/`_split_research_and_holdout()`)
on which `PatternCandidate.matches(feature_lookup, d)` evaluates `True`.
This mirrors `candidates.py`'s existing `_match_stats()`'s own
`trigger_dates` return value exactly (verified by direct code re-read):
"every anchor satisfying the conditions alone, independent of the
target" — i.e., **the set is defined purely by the feature-condition
comparison, not by whether the target/outcome was even observable that
day.** Two patterns being compared can be for different tickers, since
EGX trading-day calendars are shared across tickers even though the
underlying feature values differ per ticker.

**What constitutes a "trigger date."** A calendar date `d` such that,
for every one of the pattern's `conditions` (and its `regime_filter`, if
present), `condition.operator.evaluate(condition.read(series, d),
condition.threshold)` is `True`. No target/outcome value is consulted to
decide whether a date is a "trigger" — this is a pure input-side
(feature-threshold) definition.

**Before or after observing outcomes.** **Before.** The trigger-date set
is computed entirely from feature values against a fixed threshold; it
never reads `expectancy`, `forward_return`, or any realized outcome.
**However**, this must be qualified precisely: the *population of patterns
being compared* (only `PatternStatus.VALIDATED` patterns, or patterns with
an open `PromotionCase`) is itself the product of an outcome-based
selection process (`discover()`→`validate()`→`final_holdout()`, all of
which do read outcomes). So the pairwise Jaccard number for any two
already-selected patterns is locally outcome-blind (the number itself
never reads their returns), but it is computed over a population that was
globally shaped by outcomes — the same post-selection-inference concern
Part 2 §6.2 already names for a different metric. This is not a defect in
the Jaccard metric itself; it is a reason the metric's output should be
read as "overlap among survivors," not "overlap among all attempted
candidates."

**Whether a threshold is already defined.** **Yes, one is proposed, not
adopted.** v2 §5.7/§4 proposes reusing `candidates.py`'s existing
`match_overlap_prune_threshold = 0.85` as a *starting point* for a future
clustering step, explicitly marked **PROVISIONAL** and explicitly flagged
(§13.11) as "an untested transfer" from a different use case
(within-`discover()`-run, single-ticker candidate-generation pruning) to a
different one (cross-pattern, cross-run, cross-ticker redundancy reporting
at promotion time). **No threshold is adopted as final; this review does
not invent one either.**

**Where calibration data would come from, without contamination.** Two
non-contaminating paths, both already available in this codebase:

1. **`control_suite.py`'s synthetic data** (already built, per Part 1
   §2/§12) — construct synthetic pattern pairs with a *known, planted*
   ground-truth overlap/independence relationship, and observe what
   Jaccard values correspond to genuinely independent vs. genuinely
   redundant planted signals. **Zero risk of overlap with any real
   promotion candidate's evidence**, since the calibration data is
   entirely synthetic.
2. **Real paper-validation outcome history from an *earlier, disjoint*
   cohort** — once this gate has processed at least one real cohort
   through `PAPER_VALIDATED`, whether high-Jaccard-overlap pattern pairs
   *failed together* more often than the raw count would suggest becomes
   observable. This requires the same sequential bootstrapping v2 §6.4/§13.9
   already names for BH-vs-BY: the *first* cohort cannot be calibrated this
   way (no prior real outcome history exists yet); *later* cohorts could
   be, provided the calibrating cohort and the cohort under decision are
   always disjoint sets of patterns.

**How to prevent threshold selection from becoming post-hoc tuning.** The
same discipline v2 §8 already requires for pattern-level evidence windows
applies to the threshold itself: **calibration data must never include any
pattern currently under an open `PromotionCase`.** Concretely: (a) the
synthetic-data path (above) carries zero risk by construction; (b) the
real-data path may only use *closed* `PromotionCase`s from a *prior*
cohort, never the cohort whose promotion decision the threshold is about
to gate — the calibration/decision split must be as strict as any
train/test split, recorded in the same append-only provenance ledger v2
§8 already specifies for evidence windows.

**Classification.** As currently specified in v2, this metric is:

> **(A) descriptive redundancy evidence only, today** — v2 §8 itself
> already labels dimension C "Provisional (reported only; not yet a
> pass/fail)," and §5.7's clustering-into-a-gate proposal is explicitly
> "not implemented in this mission." **If and when the clustering step in
> §5.7 is built and a calibrated threshold is adopted, it becomes (C) a
> provisional gate requiring external calibration** — but that transition
> has not happened, and this review does not recommend rushing it. It is
> **not** (B) a hard-gate candidate today (no calibration evidence
> exists), and it is **not** (D) insufficiently specified — the set
> definitions, comparison timing, and starting-threshold provenance are
> all precisely traceable to existing code.

## 2. Cross-sectional correlation — findings

**What is correlated, precisely.** Per v2 §5.4 and direct verification
against `decision_service.concentration`'s existing production usage: the
correlated quantity is **each ticker's own adjusted daily return series**
(via `data.adjustments`-derived closes, the same series
`features.correlation.pearson_correlation()` already consumes in
production for the sector/correlation-cluster concentration cap). **Not**
raw feature values, **not** trigger indicators (0/1 per date), **not**
forward-return targets, **not** residual returns — v2 introduces no new
correlation target, exactly as instructed.

**Is `features.correlation` appropriate, or merely reusable
infrastructure with a different semantic meaning?** **The latter — reusable
infrastructure, not a semantically matched tool.** The existing production
use answers a *portfolio-construction* question: "if I hold both of these
tickers simultaneously, how much diversification do I actually get from
their general day-to-day co-movement?" v2 §5.4 asks a *different* question:
"are the specific trigger-date-conditioned observations corroborating this
pattern across tickers actually independent evidence, or does general
co-movement explain away the appearance of corroboration?" These are
related but not identical: two tickers with **low** general return
correlation (different sectors, different volatility regimes) could still
have their *specific, rare* trigger dates cluster on the same few calendar
episodes by coincidence — general correlation would not reveal this. Two
tickers with **high** general correlation could still have a specific
conditioning feature (e.g., an idiosyncratic fundamental signal) trigger on
genuinely disjoint dates. **General adjusted-return correlation is a cheap,
already-available, directionally-informative *proxy* for the independence
question, not a direct measurement of it.**

**"Correlated observations" vs. "statistically non-independent evidence"
— explicitly distinguished, not conflated.** "Correlated observations"
here means: two tickers' unconditional daily-return series move together
over time (a measured Pearson r on price data alone). "Statistically
non-independent evidence" means: the specific realized outcomes
(bootstrap p-value, expectancy sample) this gate treats as *K separate
corroborating trials* are not really K independent draws, because they
share a common underlying factor. **High return correlation is
suggestive, not proof, of the latter** — it raises the plausibility that
apparent cross-ticker corroboration is one common-factor event observed
on several correlated names (exactly the risk Step 1.6's confirmed
positive market drift illustrates concretely: a broad, EGX-wide nominal
drift that would make many tickers' price-derived features cross their
thresholds together, independent of whatever specific feature is being
tested). **Low return correlation does not prove independence either** —
per the coincidence scenario above. This review makes **no claim that
correlation alone proves independence or dependence**, per the explicit
instruction, in either direction.

**Market-factor residualization.** **Not proposed, and not added by this
review.** Direct verification against `decision_service.concentration`'s
existing usage of `features.correlation.pearson_correlation()` confirms it
operates on **raw, non-residualized** adjusted returns — no index-level or
market-factor residualization step exists anywhere in this codebase's
correlation machinery today. Per the explicit instruction not to add
residualization unless already supported by existing methodology, this
review does not propose it. **This is flagged as a genuine, unresolved
limitation**: the raw correlation measure conflates market-wide
co-movement (e.g., the shared positive-drift factor Step 1.6 identified)
with idiosyncratic, ticker-specific co-movement, and this codebase
currently has no infrastructure to separate them. Left as an open question
(§13.8 in Part 2, unchanged), not solved here.

## 3. Temporal / regime clustering — findings

**Do pre-defined, fixed-in-advance partitions currently exist?** **No —
verified by direct re-read of the regime-bucketing code
(`robustness.py`'s `_regime_breakdown()`, the same construction
`regimes.py` extends).** The partition boundary (e.g., "above-median" vs.
"below-median" for a regime feature) is computed as
`statistics.median(values)` **over the specific pattern's own analyzed
window, at analysis time** — not read from any externally declared,
version-controlled, date-stamped partition definition that would apply
identically regardless of which pattern or window is being evaluated.
**This does not meet "the partitions MUST be determined before observing
candidate performance" as that instruction is most naturally read** —
"before observing performance" implies a partition fixed once, in advance,
uniformly applicable — not one recomputed fresh from each case's own data
window. To be precise about what this *does* and *does not* risk: the
median split is computed from a **regime feature's own values** (e.g.
market breadth), never from the pattern's own **return/expectancy
outcomes** — so this is not literally "choosing regimes because they make
a pattern pass" in the crudest sense. But it is still a real, more subtle
risk: two evaluations of "the same" regime-independence question, run at
different times or over different windows, would use *different*
partition boundaries purely because the underlying sample changed — not a
genuinely pre-registered partition in the sense this review's instruction
requires.

**Classification: PROVISIONAL — infrastructure gap, not a calibration-value
gap.** This is not a case of "the right number hasn't been chosen yet"; it
is a case of "the infrastructure for a fixed, pre-registered partition
does not exist in this codebase today." `regimes.py` is a real, useful,
already-shipped *descriptive* tool for characterizing a *specific* pattern's
own sensitivity to regime, computed fresh each time — repurposing it as a
promotion-time *independence* signal without first building a frozen
partition registry would silently reintroduce the self-referential-boundary
risk this review is specifically checking for.

**What external calibration/pre-registration would be required (no new
thresholds invented here, per instruction).** A genuinely pre-registered
regime-partition capability would need: (a) fixed, date-stamped boundary
definitions for each of the six existing dimensions (volatility, breadth,
dispersion, trend, correlation, turnover), declared and version-controlled
**once**, independent of any specific pattern's own discovery/validation
window; (b) computed from a data source and time period that predates and
is independent of any pattern currently under promotion consideration
(e.g., the full historical EGX price record available at the time the
partition registry is frozen); (c) an explicit versioning/audit trail so a
later reviewer can confirm which partition definition was in force for any
given `PromotionCase`. **No specific numeric boundary is proposed here** —
per the explicit instruction not to invent new regime thresholds, this
review states the missing *capability*, not a number.

## 4. Provisional threshold inventory

| Threshold | Purpose | Current source | Hard / Provisional | Calibration required? | Calibration data | Can calibration data overlap promotion data? | Failure state if unresolved |
|---|---|---|---|---|---|---|---|
| Sign-agreement (OOS/holdout vs. discovery-period sign) | Confirms an effect's direction is stable across time | `validation.py:170-174`, `engine.py:673` (unchanged production code) | **Hard** | No — a rule shape, not a numeric value | N/A | N/A | N/A — already enforced today |
| Net-of-cost expectancy `> 0` | Baseline economic viability | `robustness.py:124-126` | **Hard** (value); **implementation gap** (re-read vs. recompute — see §5) | No (threshold itself); **yes** for how to re-derive the number at promotion time | N/A for the threshold; raw price/feature data for the recomputation | N/A | Currently mis-specified in v2 as "re-asserted" when it must be recomputed — see §5, §6 below |
| `RobustnessTester` perturbation sign-agreement | Overfitting/parameter-stability check | `robustness.py:142-143` | **Hard** (value); same recompute caveat as above | Same as above | Same as above | Same as above | Same as above |
| `beats_baseline()` result | Economic significance vs. passive benchmark | `baselines.py:156-162` | **Hard** (value); same recompute caveat | Same | Same | Same | Same |
| Direction scope: `expectancy > 0` | Scope boundary (§7) | Step 1.7 classification C + AD-42 precedent | **Hard** | No — a scope decision, not a statistic | N/A | N/A | Genuinely ready — `expectancy` verified safe at every revision (§5 below) |
| Minimum OOS matched-observation floor | Avoid judging on too little fresh data | `WalkForwardValidatorConfig.min_oos_sample_size` (currently 10), reused as a declared floor | **Provisional** | Yes, for the *final* number; usable now as a declared, uncalibrated default | Real paper-validation/decision-ledger outcome history correlating floor size with promotion success | **No** — does not yet exist; first use is necessarily an uncalibrated declared default, refined later from disjoint future cohorts | Stays at declared default (10, scaled) until real history accumulates — not blocking |
| Bootstrap CI lower-bound `> 0`, 95% coverage | New effect-size/CI floor (§8.E) | Reuses `block_bootstrap_p_value()`'s existing machinery/iteration count | **Provisional** | Yes, for coverage-level choice; the *computation itself* is fully implementable now (fresh, not read from a persisted field) | Comparison of different coverage levels' promotion outcomes against real forward performance | **No** — not yet available; usable now as a declared 95% default | Usable today as declared default; coverage-level choice remains uncalibrated |
| Paper-validation window: N trading days / M matched observations | Defines the forward-observation window | Not proposed numerically (Part 1, unchanged) | **Provisional** | Yes | At minimum one completed real paper-validation cycle | **No**, provided the *first* cohort's window is set by an explicit, disclosed, uncalibrated rule (e.g. horizon-scaled default), and later cohorts calibrate from the *first* cohort's already-closed outcomes only | First cohort must proceed on a declared, uncalibrated default — explicitly disclosed as such |
| Promotion-cohort multiple-testing correction: BH vs. BY | Controls false-promotion rate across a simultaneously-considered cohort | Step 1's descriptive BH/BY comparison (1,683 vs. 657 passes at α=0.05) | **Provisional / open policy decision** | Not a calibration problem — a **decision** problem. Real false-promotion-rate history would help pick between them, but does not exist yet either way | Real paper-validation false-promotion-rate history (future) | **No** — does not exist yet | **This component must remain disabled** (§6, §14 of Part 2, unchanged) until the user/product owner makes an explicit choice |
| Economic-rationale "minimum substance" bar | Filters empty/placeholder rationale | Reuses `EconomistReviewer`'s heuristic structurally | **Provisional** | Yes | **Human-reviewer agreement study** on whether the mechanical heuristic tracks domain-expert judgment | **No — and this is the one calibration path with no contamination risk at all**, since it is a text-quality/human-agreement study, entirely unrelated to price/return data | Usable now with the inherited heuristic as a declared default; substance bar itself unvalidated for this new context |
| Jaccard trigger-date-overlap clustering threshold | Redundancy clustering (§5.7) | `candidates.py`'s existing `match_overlap_prune_threshold = 0.85` | **Provisional** | Yes | Synthetic `control_suite.py` data (no contamination risk) **or** real disjoint-cohort history (sequential, no contamination if disjoint) | **No**, via either calibration path described in §1 above | **Must remain a descriptive/reported number only** — not a gate — until calibrated |
| Cross-sectional correlation "how much is too much" | Independence diagnostic (§5.4) | **No value currently proposed anywhere, including in v2 itself** | **Provisional — not even a starting value exists** | Yes, and the *semantic-mismatch* question (§2 above) must be resolved first, which is a methodology question, not only a data-availability one | Would require both a resolved semantic question and calibration data | N/A until the semantic question is resolved | **NOT IMPLEMENTABLE YET as a gate** — usable only as a descriptive, unthresholded statistic |
| Temporal / regime-partition independence check | Independence diagnostic (§5.5) | `regimes.py`'s existing (self-referential, per-analysis) bucket logic | **Provisional — required infrastructure does not exist** | Yes — requires building a pre-registered partition registry first (§3 above), which is a capability gap, not a value-calibration gap | A frozen, version-controlled historical partition registry (does not exist) | N/A until the registry exists | **NOT IMPLEMENTABLE YET as a gate**, and its current descriptive form must carry an explicit self-referential-boundary caveat whenever reported |

For every Provisional threshold above marked with a "No" in the
contamination column: **calibration is possible without touching the data
that will later determine any specific pattern's promotion**, via either
synthetic control-suite data (zero risk) or strictly disjoint,
already-closed prior-cohort history (risk-free provided disjointness is
enforced and recorded in the provenance ledger). The two rows marked **NOT
IMPLEMENTABLE YET** are blocked for a different reason than data
contamination — they are blocked because the *methodology itself*
(semantic appropriateness of the correlation target; existence of a
pre-registered partition registry) is not yet resolved, which this review
does not resolve on its own initiative, per instruction.

## 5. `family_size` / statistical-evidence integrity audit

**Root cause, reconfirmed by direct code re-read for this review** (not
re-asserted from memory): `discover()`'s `build_pattern()` call
(`engine.py:388-407`) passes `family_size=`, `family_corrected_p_value=`,
`block_bootstrap_p_value=`, and `deflated_sharpe_ratio=` explicitly.
**Neither** `validate()`'s call (`engine.py:553-567`) **nor**
`final_holdout()`'s call (`engine.py:692-707`) passes **any** of those
four keyword arguments — confirmed by direct inspection of both call
sites in this review, not inferred. Both therefore silently receive
`build_pattern()`'s own function-signature defaults
(`family_size: int = 1`, the other three `None`), overwriting the real
v1 values on every later revision. This matches Step 1's empirically
observed pattern (v1: `family_size` range 1–171, 0/1,773 null
`block_bootstrap_p_value`; latest: 1,773/1,773 reset to `family_size=1`,
1,773/1,773 null `block_bootstrap_p_value`) exactly.

**Per-metric classification:**

| Metric | At `Pattern` v1 | At any later revision | Why |
|---|---|---|---|
| `family_size` | **A** — safe to use as persisted | **C** — cannot be trusted as persisted | Real value computed once at `discover()`, never forwarded by `validate()`/`final_holdout()`'s `build_pattern()` calls (confirmed above) |
| `family_corrected_p_value` | **A** | **C** | Same mechanism |
| `block_bootstrap_p_value` (the **stored registry field**) | **A** | **C** | Same mechanism |
| `deflated_sharpe_ratio` | **A** | **C** | Same mechanism (this review directly re-verified `family_size`/`block_bootstrap_p_value` via Step 1's registry query; `deflated_sharpe_ratio`'s null count was not separately re-queried in this review, but follows identically from the same confirmed call-site omission — no separate reason exists for it to behave differently) |
| `expectancy`, `median_outcome`, `hit_rate`, `mfe`, `mae`, `max_drawdown`, `stability`, `sample_size`, `oos_sample_size`, `robustness_passed` | **A** | **A** | All derived fresh from that call's own `distribution`/`robustness` argument inside `build_pattern()`'s body at every revision — never defaulted, confirmed by direct code re-read. `final_holdout()` additionally re-asserts several of these explicitly via its own `model_copy(update={...})` (engine.py:711+), reinforcing (not weakening) their safety. |
| `Pattern.confidence` | **A** | **A** | Derived from `distribution.p_value_bootstrap` (`evaluation.py`'s **i.i.d.** bootstrap, a *different* field from `block_bootstrap_p_value`'s **moving-block** bootstrap) — recomputed fresh from the real `distribution` object at every call, not defaulted. **Do not confuse this with `block_bootstrap_p_value` — they are two distinct statistics, only one of which is affected by the reconstruction bug.** |

**Which v2 metrics depend on which — and one important scope
clarification.** The new `RedundancyReport` (Part 2 §5.2) does **not**
read the persisted `family_size` field at all — every one of its six
dimensions is computed fresh from `Pattern.conditions`/`ticker`/
`target_id`, independent of this bug entirely. **Only** the "Family-level
correction" layer (Part 2 §6.3, part of Multiple-Testing dimension D) and
the DSR-as-a-floor idea Part 1 §7.3 proposed depend on the four corrupted
fields — classified below.

| Dependent v2 metric/gate | Classification | Note |
|---|---|---|
| §6.3 Family-level correction (`family_corrected_p_value`) | **A, conditionally** — safe **only if** read from `Pattern` v1, which Part 2 §6.3/§11 already mandates explicitly | This review confirms the mandate is correctly specified; it does not, by itself, guarantee a future implementer follows it — hence Part 2 §12 already specifies a regression test for exactly this. |
| Deflated Sharpe Ratio as a hard floor | **A, conditionally (v1-only)** — **but internally inconsistent in v2's own text**, a new finding of this review | Part 1 §7.3 proposed DSR `> 0` as a hard floor. Part 2's rewritten §3/§8 gate-criteria tables **do not explicitly re-list DSR** among the `OOS_VALIDATED → ROBUST` requirements. This is an unresolved ambiguity in v2 as written — is DSR still required, silently dropped, or implicitly folded into "effect size" (dimension E)? **This review does not resolve it** (that would mean editing the design), but flags it as a required clarification before implementation. |

**A second, distinct integrity finding, newly surfaced by this review (not
previously flagged in Steps 1/1.5/1.6/1.7):** v2 §4/§8 describes
Dimensions F ("net-of-cost expectancy... already true... re-asserted, does
not recompute") and G/H (baseline-beat, perturbation-agreement, same
framing) as free re-assertions of already-persisted evidence. **Direct
re-verification of the `Pattern` schema for this review
(`registry.py`)** shows this is not accurate for the real registry: only
the aggregate boolean `robustness_passed: bool | None` is persisted on
`Pattern` — the full `RobustnessResult` object (which carries the actual
`net_of_cost_expectancy` number, per-perturbation breakdowns, and the
confidence interval) is **never persisted anywhere**, confirmed by
`registry.py`'s complete field list containing no such field. Similarly,
**direct re-verification of `cli.py`** confirms `PatternFailureProfile`
(`regimes.py`) and `TransactionCostSensitivity` (`transaction_costs.py`)
are computed **only on demand via CLI commands**, never inside
`engine.py`'s `discover()`/`validate()`/`final_holdout()` — i.e., **not**
"already computed per-pattern" for the real 1,773-pattern population, as
Part 2 §5.5/§8 currently implies. (Per this codebase's own documented
Mission 2 history, `PatternFailureProfile` was in fact computed for only
a bounded top-20 subset, not the full population.)

| Object | At `discover()`/`validate()` time | Persisted for later re-read? | Classification |
|---|---|---|---|
| `RobustnessResult` (full object, incl. `net_of_cost_expectancy`) | Computed once during `validate()` | **No** — only `robustness_passed: bool` survives | **B** — must be recomputed from preserved raw evidence (frozen conditions + underlying price/feature data, both still available) to re-derive the actual number; **not** "safe to use as currently persisted" the way v2 §8 currently implies |
| `PatternFailureProfile` (`regimes.py`) | Only via CLI, on demand, historically for a bounded top-20 subset | **No**, for the vast majority of the 1,773 population | **B** — same reasoning |
| `TransactionCostSensitivity` | Only via CLI, on demand | **No**, for the vast majority of the 1,773 population | **B** — same reasoning |

None of the above are **C** (cannot currently be trusted/reconstructed) —
the raw ingredients each recomputation needs (frozen pattern definition,
underlying price/feature CSVs, the panel-reconstruction machinery) remain
available in this environment. But they are **not A either** — v2's
current wording ("re-asserted, does not recompute") should be corrected
to "recomputed fresh from the frozen intake snapshot" before an
implementer follows it literally.

## 6. Final readiness classification

**READY_WITH_EXPLICIT_PROVISIONAL_COMPONENTS.**

**Why not NOT_READY**: no *hard* promotion criterion depends on
contaminated or unrecoverable evidence. The one hard criterion this review
scrutinized most closely for exactly that risk — direction scope,
`expectancy > 0` — is confirmed **A (safe)** at every `Pattern` revision
(§5 above), so the gate's single most consequential scope decision (§7 of
Part 2) rests on genuinely sound, uncorrupted data. The `family_size`
family of fields is corrupted beyond v1, but Part 2 already anticipated
this correctly (mandatory v1-only read, §6.3/§11/§12) before this review
began — this review confirms, rather than discovers, that safeguard is
correctly specified. The newly surfaced findings (§5's `RobustnessResult`/
`PatternFailureProfile`/`TransactionCostSensitivity` persistence gap; the
DSR internal-inconsistency) are real, but they are **B-class** (recomputable
from preserved raw evidence) or **specification-precision** issues, not
**C-class** (unrecoverable) ones — none of them require data that no
longer exists.

**Why not READY_FOR_IMPLEMENTATION outright**: several components remain
either explicitly undecided by policy (BH vs. BY), un-calibrated by
necessity (nothing in this codebase has real forward paper-validation
history yet — a strict chicken-and-egg constraint no amount of design work
resolves), or blocked on a missing capability this review will not build
unilaterally (a pre-registered regime-partition registry; a resolved
semantic question for cross-sectional correlation). Implementing the full
v2 specification literally as worded today — in particular, treating
Dimensions F/G/H as "free" re-assertions, or wiring the Jaccard/
correlation/regime checks in as active gates — would silently overstate
what is actually ready.

**Components approved for implementation now**, without further
methodological resolution:

- `PromotionCase` schema and the full state machine (`DISCOVERED` →
  `OOS_VALIDATED` → `ROBUST` → `PROMOTION_ELIGIBLE` → `PAPER_VALIDATED` →
  `PROMOTED`, plus `REJECTED`/`INSUFFICIENT_EVIDENCE`/
  `OUT_OF_SCOPE_FOR_PROMOTION`), with legality tests.
- Frozen-snapshot intake and the direction-scope gate (§7 of Part 2) —
  `expectancy` verified safe at every revision.
- The temporal-OOS mechanism (Part 2 §8.A) — buildable now; its first real
  exercise is rate-limited by calendar time, which is expected and
  correctly documented, not a blocker.
- The `family_size`/`family_corrected_p_value`/`block_bootstrap_p_value`/
  `deflated_sharpe_ratio` v1-only-read rule and its regression test
  (Part 2 §6.3/§12) — already correctly specified.
- The `RedundancyReport`'s six dimensions (Part 2 §5.2), **as a reporting
  layer only** — none of them depend on the corrupted fields, and their
  descriptive computation requires no unresolved calibration.
- Anti-leakage / data-provenance-window checks (Part 2 §8, §9).
- The economic-rationale field and its structural gate (Part 2 §7 of
  Part 2's evidence table, dimension I) — usable now with the inherited,
  uncalibrated substance-bar heuristic as a declared default.

**Components that must remain explicitly DISABLED (not silently active)
until specifically resolved:**

1. **Promotion-cohort-level multiple-testing correction (Part 2 §6.4)** —
   disabled until the user/product owner makes an explicit BH-vs-BY
   decision. This blocks `ROBUST → PROMOTION_ELIGIBLE` specifically, not
   the rest of the pipeline.
2. **Jaccard trigger-date-overlap clustering as a pass/fail gate (Part 2
   §5.7)** — the pairwise metric may be computed and reported now (§1
   above), but clustering it into a hard/provisional gate is disabled
   until calibrated via the synthetic-control-suite path identified in
   §1.
3. **Cross-sectional correlation as a pass/fail threshold (Part 2 §5.4)**
   — descriptive reporting only; disabled as a gate until the
   semantic-mismatch question (§2 above) is explicitly resolved and a
   threshold is derived, not assumed.
4. **Temporal/regime independence as a pass/fail threshold (Part 2 §5.5)**
   — descriptive reporting only, and even then must carry the
   self-referential-boundary caveat (§3 above); disabled as a gate until a
   genuinely pre-registered partition registry exists.
5. **Dimensions F/G/H's "re-assert, don't recompute" framing** — must be
   implemented as **fresh recomputation** from the frozen intake snapshot
   and preserved raw price/feature data, not as a read of a persisted
   field that does not exist for the real registry (§5 above). The
   underlying hard requirements themselves are not in doubt; only the
   implementation mechanism v2's current wording implies is inaccurate.
6. **Deflated Sharpe Ratio's status as a required gate** — must be
   explicitly clarified (kept as a stated v1-only-read hard/provisional
   gate, or explicitly and reasoned-ly dropped) before implementation, to
   resolve the internal inconsistency between Part 1 §7.3 and Part 2's
   rewritten §3/§8 (§5 above).

## Exact blockers, if any

**None of the above are hard-stop blockers that prevent starting
implementation of the approved components.** The six items above are
**scoped, named prerequisites for six specific sub-components**, not
blockers on the design as a whole. The one item closest to a true blocker
— BH vs. BY — blocks only one specific transition
(`ROBUST → PROMOTION_ELIGIBLE`'s cohort-correction sub-check) and Part 2
already correctly anticipated this (§14, dependency #2) before this review
began.

---

*End of Design Readiness Review. No code, tests, registry data, validation
statuses, or `PromotionCase` records were created or modified to produce
this section. No threshold was invented, chosen, or finalized — every
number cited above is either already declared in Part 1/Part 2 (and
explicitly marked provisional there) or explicitly withheld here per
instruction. Implementation of the approved components may begin only
once the six disabled-until-resolved items are tracked as explicit,
visible prerequisites — not implemented, not decided unilaterally by this
review.*
