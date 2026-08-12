# Pattern Promotion Gate — Design & Audit Report

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

*Stopping here per instruction. No code, tests, or Mission 2 artifacts
were modified to produce this report.*
