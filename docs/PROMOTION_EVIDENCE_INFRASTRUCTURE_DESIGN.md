# Promotion Evidence Infrastructure — Design Note

**Mission 3, Blocking Dependency #1.** Resolves the persistence gap
`docs/PATTERN_PROMOTION_GATE_DESIGN.md`'s v2.2 specification (§5, "Persisted
Evidence") names as `BLOCKING DEPENDENCY` for four evidence types: net-of-cost
expectancy, baseline comparison, robustness detail, and regime profile.

**Scope discipline, stated up front and enforced throughout**: this is
evidence *infrastructure*, not the Promotion Gate. It computes and persists
observed/computed evidence about a pattern. It never creates a
`PromotionCase`, never introduces a `PROMOTED` state, never makes a
promotion/rejection decision, and is imported by nothing in the production
decision path. `robustness.py`, `baselines.py`, `regimes.py`,
`PatternRegistry`, `validation_status`, discovery, validation, and final
holdout are all read-only inputs — none of them is modified.

## Step 1 — Audit of existing evidence sources

Every function below was re-read directly from source for this design (not
recalled from memory) to confirm exact behavior.

| # | Evidence | Function | Inputs | Outputs | Persisted today? | Persistence location | Deterministic? | Random seed? | External/current data? | Future-information risk? |
|---|---|---|---|---|---|---|---|---|---|---|
| A | Net-of-cost expectancy | `RobustnessTester.run()` → `RobustnessResult.net_of_cost_expectancy` (`patterns/robustness.py:124-126`) | `candidate: PatternCandidate`, `anchor_dates: list[date]`, `feature_lookup: dict[str, FeatureSeries]`, `target: TargetSeries`, optional `nearby_feature_ids`/`nearby_targets`/`regime_feature`/`calendar_periods` | `RobustnessResult` (`net_of_cost_expectancy`, `base_expectancy`, threshold/lookback/horizon sensitivity, `transaction_cost_survival`, `passed`, `notes`) | **No** — only the boolean `robustness_passed: bool \| None` survives on `Pattern` (`registry.py`'s complete field list has no `net_of_cost_expectancy`, confirmed by direct re-read); `build_pattern()` (`registry.py:227`) only extracts `robustness.passed`, discarding the rest of the object | None — ephemeral, computed once inside `engine.validate()`, never written to disk | Yes, for identical inputs (no internal randomness of its own) | Indirectly — the `evaluate_outcomes()` calls it makes internally run a bootstrap with `seed=42` (evaluation.py's own default, never overridden here) | Whatever `ResearchPanel` the caller supplies | Only if `anchor_dates` is reconstructed incorrectly (see mitigation, §2 below) |
| B | Baseline comparison | `buy_and_hold_baseline()` (`patterns/baselines.py:58-63`) for the reference; `beats_baseline()` (`patterns/baselines.py:156-162`) for the pass/fail comparison | `buy_and_hold_baseline(panel, ticker, horizon_days)`; `beats_baseline(distribution: OutcomeDistribution, baseline: BaselineResult, transaction_cost_bps=20.0)` — `distribution` in the *original* `validate()` call is specifically `WalkForwardValidator`'s `wf_result.oos_distribution`, not `RobustnessResult`'s `base_dist` (confirmed by re-reading `engine.py:534-542`) | `BaselineResult` (`name`, `ticker`, `horizon_days`, `sample_size`, `mean_outcome`, `hit_rate`, `stdev`); `beats_baseline()` returns `bool` | **No** — neither `baseline.mean_outcome` nor the boolean is stored anywhere on `Pattern`; only indirectly reflected (if it caused rejection) in the free-text `rejection_reason` string | None | Yes — pure arithmetic over the panel's own adjusted-close series | No, for the specific fields this evidence reads (`mean_outcome`, `expectancy`) | Same as A | Same risk/mitigation as A, since the comparison distribution is itself `anchor_dates`-derived |
| C | Robustness detail | Same function as A (`RobustnessTester.run()`), consuming the **full** result object rather than one field | Same as A | Same as A | Same as A | Same as A | Same as A | Same as A | Same as A | Same as A |
| D | Regime profile | `analyze_pattern_failure_conditions()` (`patterns/regimes.py:394-412`) | `pattern: Pattern`, `panel: ResearchPanel` | `PatternFailureProfile` (`overall_tag`, `per_dimension`, `bucket_count_sensitivity`, `weakest_conditions`) | **No** — confirmed via direct re-read of `cli.py:386-400`: computed only on demand via the `failure-profile` CLI command, printed to stdout, never written to any repository. Per this codebase's own documented Mission 2 history, run for only a bounded top-20 sample of the 1,773 real patterns, never the full population | None | Yes, for the same pattern+panel inputs | Same `seed=42` caveat as A, inside each bucket's `OutcomeDistribution` | Same as A | **By design**, this function reads the pattern's **full** date range — research period *plus the already-spent final-holdout slice combined** (`regimes.py`'s own module docstring: legitimate for its original post-hoc purpose, since the pattern is already settled) — this must be labeled explicitly wherever persisted, never presented as fresh/future data |

**No existing calculation is duplicated without a concrete reason.** All
four evidence types are computed by calling the *existing, unmodified*
functions above — this module adds only the reconstruction of their
inputs (candidate, `anchor_dates`, `feature_lookup`, `target`), the
persistence wrapper, and the provenance/immutability layer. The one
non-obvious reconstruction detail, discovered during this audit and worth
recording: baseline comparison's original computation used the
walk-forward validator's *out-of-sample fold* distribution
(`wf_result.oos_distribution`), not the robustness tester's broader
*full-anchor-dates* distribution — reusing the wrong one would silently
change what "beats baseline" means relative to the original `validate()`
run. This infrastructure reconstructs `WalkForwardValidator.validate()`
internally, purely to obtain the correct `oos_distribution` for this one
purpose — never to re-decide `wf_result.survived` or any
`validation_status`.

## Step 2 — Frozen evaluation snapshot

`PromotionEvidenceProvenance` (full model in `promotion_evidence.py`)
captures every field the mission specified:

| Required field | Where it comes from |
|---|---|
| `pattern_id` | `Pattern.id`, unchanged |
| Pattern definition hash | SHA-256 over the canonical JSON of exactly the frozen fields Part 2's `PromotionCase` design already names — `ticker`, `conditions`, `regime_filter`, `target_id`, `complexity`, `is_lead_lag` |
| Registry revision/version | The specific `Pattern.version` the frozen fields were read from (the registry's *latest* revision — confirmed safe, see §5 below) |
| Source data snapshot/version | `dataset_source`/`dataset_version`, the same parameters `discover()`/`validate()`/`final_holdout()` already accept and pass to `build_reproducibility_manifest()` — for the real community-seed data, this is the seed's own `PROVENANCE.json` `source_commit`, exactly as `cli.py`'s existing `_dataset_version_for_source()` already resolves it |
| Evaluation code/version | `ReproducibilityManifest.git_commit` (reused as-is, same `_git_commit_sha()` resolution `reproducibility.py` already uses) |
| Evaluation timestamp | `ReproducibilityManifest.generated_at` (reused as-is) |
| Data start/end, evaluation window | `data_windows: list[DataWindowProvenance]` — see below |
| Target definition | `pattern.target_id` + the reconstructed `TargetSeries.spec` |
| Feature definition | `pattern.conditions` (already part of the definition hash) |
| Ticker universe | `panel.tickers` |
| Transaction-cost assumptions | `robustness.DEFAULT_TRANSACTION_COST_BPS`, imported, never hand-typed |
| Baseline definition | The literal string `"buy_and_hold_baseline"` — the one baseline function `validate()` actually used |
| Regime definition | `regimes.DEFAULT_BUCKET_COUNT`, `regimes.DEFAULT_REGIME_LOOKBACK_DAYS`, `regimes.CORRELATION_LOOKBACK_DAYS`, the six `RegimeDimension` members — all imported, never hand-typed |
| Random seed | `42` — `evaluation.py`'s own bootstrap default, stated explicitly since this module never overrides it |
| Methodology/version identifier | `PROMOTION_EVIDENCE_METHODOLOGY_VERSION` (module constant, same "explicit version, not implicit trust" posture as `reproducibility.FEATURE_FACTORY_VERSION`) |

**Reused, not reinvented**: `ReproducibilityManifest`/
`build_reproducibility_manifest()` are embedded as-is (Part 2 §11 already
named this as the intended reuse). No second, incompatible provenance
system is introduced.

**Multiple, explicitly labeled data windows** — the single largest
precision requirement this design adds, since different evidence types
legitimately use different windows of the same pattern's history:

| Label | Used by | What it is |
|---|---|---|
| `research_period_full` | net-of-cost expectancy, robustness detail | All of `anchor_dates` — the research-period dates `_split_research_and_holdout()` produces, identical to what `engine.validate()` used |
| `walk_forward_oos_folds` | baseline comparison | The out-of-sample fold dates inside `WalkForwardValidator`'s own internal reconstruction — a sub-portion of `research_period_full` |
| `full_history_incl_spent_final_holdout` | baseline comparison's reference series, regime profile | The pattern's complete date range, including the already-spent `final_holdout()` slice — **explicitly labeled as spent/historical, never as fresh evidence** |
| `future_paper_validation_data` | *none* | Always present with `start=None`, `end=None`, `trading_day_count=0`, and a note stating this evidence layer never reads or claims post-`as_of` data — the temporal-OOS/paper-validation mechanism remains a separate, not-yet-built component (Part 2 §8/§13) |

## Step 3 — No silent recomputation

Every `PromotionEvidenceSnapshot` records exactly what data, code, and
methodology produced it (§2). **A concrete, additional safeguard beyond
what was asked**: before computing anything, this module cross-checks the
reconstructed `research_period_full` window's start/end dates against the
pattern's own **already-persisted** `discovery_period` field. If they
disagree — signaling the supplied panel or engine config does not match
what the original `validate()` run actually used — net-of-cost expectancy
and robustness detail are both returned as `INSUFFICIENT_EVIDENCE` with an
explicit reason, **never** silently computed on a different window than
the original run used. Missing source data (ticker absent from the panel,
target unreconstructable, too few matched observations) produces
`INSUFFICIENT_EVIDENCE` at the affected evidence field, never an inferred
or reconstructed substitute value.

## Step 4 — Evidence schema (observed evidence, never a decision)

`PromotionEvidenceSnapshot` and its four evidence sub-objects
(`NetOfCostExpectancyEvidence`, `BaselineComparisonEvidence`,
`RobustnessDetailEvidence`, `RegimeProfileEvidence`) contain **only**
observed/computed values (`net_of_cost_expectancy`, `expectancy`,
`baseline_mean_outcome`, `beats_baseline: bool`, `robustness_result`,
`failure_profile`, each with an `EvidenceStatus` of `COMPUTED` or
`INSUFFICIENT_EVIDENCE`) and their per-field reasons. **No field named
`promote`, `eligible`, `production`, or any synonym exists anywhere in the
schema** — enforced by an explicit test (§8, test 7) that introspects the
model's field names.

## Step 5 — Immutability

`PromotionEvidenceSnapshot.id` is **content-derived**, not randomly
generated — a SHA-256 digest over `(pattern_definition_hash,
pattern_registry_version, dataset_source, dataset_version,
methodology_version)`. This is the same discipline
`events.service.build_candidate_event()` already uses elsewhere in this
codebase ("derives the id from a content fingerprint... never mint an
event id with `new_id()`" — reused conceptually here, not reinvented).
Consequences, matching every requirement in Step 5 exactly:

- Identical inputs → the identical id → re-running produces a byte-
  identical snapshot; persisting it again is a harmless no-op, never a
  silent overwrite of different content under the same id.
- A changed pattern definition (different `conditions`/`ticker`/
  `target_id`/etc.) changes the hash → a new id → a new snapshot.
- A changed source data version changes the id → a new snapshot.
- A changed methodology version changes the id → a new snapshot.
- Persistence goes through `storage.JsonFileRepository` (this codebase's
  own hard rule for every new versioned entity) — append-only by
  construction, so every prior snapshot remains available via
  `.history()`/`.all_latest()` for audit, exactly as `PatternRegistry`
  and every other store in this codebase already behaves.

## Step 6 — Directional scope

This module computes evidence for whatever pattern it is given — it does
**not** filter, gate, or interpret direction itself (that remains the
future Promotion Gate's job, per Part 2 §7/§12, unchanged). It never
converts a negative-expectancy pattern's outcomes into a short-return
series, and it never modifies `robustness.py`'s semantics. The evidence
objects report whatever sign the underlying computation produces, exactly
as the existing functions already do.

## Step 7 — Data leakage

Addressed throughout §2/§3 above: every evidence value carries an explicit
`data_windows` entry naming which of discovery/validation-research-period,
walk-forward-OOS-fold, full-history-including-spent-holdout, or
future/paper data produced it. **Mission 2's spent final holdout is never
labeled or treated as fresh OOS evidence** — anywhere it is used (the
baseline reference series, the regime profile), it is explicitly labeled
`full_history_incl_spent_final_holdout`, distinct from the
always-empty `future_paper_validation_data` entry.

## Step 8 — Testing (planned, implemented in `test_promotion_evidence.py`)

1. Deterministic evidence generation (same inputs, single run, sane output).
2. Identical input → identical evidence (two independent calls, byte-identical `model_dump_json()`).
3. Changed pattern hash → new snapshot id.
4. Changed methodology version → new snapshot id.
5. Changed data-snapshot version (`dataset_version` parameter) → new snapshot id.
6. Missing evidence source (ticker absent from panel) → `INSUFFICIENT_EVIDENCE` for all four fields, not a crash or a fabricated value.
7. Evidence schema contains no promotion-decision field names.
8. Snapshot is immutable after creation (pydantic frozen model / no setter path; a second `.add()` with a mutated copy produces a *new* id, never overwrites).
9. Provenance fields are complete (every required Step 2 field is populated on every successful snapshot).
10. No production decision path imports this module (`decision_service`, `meta.decision_engine`, `capital_allocation`, `shadow_fund`, `live.LiveActivationEngine` — grep-verified after implementation).

## Step 9 — Backward compatibility

Verified after implementation: the existing pattern-discovery test suite
passes unchanged, the real registry's counts remain 3,398/1,773/1,625,
zero `PromotionCase` entities exist anywhere, and this module is reachable
only via direct import/CLI invocation — never from any production decision
path.
