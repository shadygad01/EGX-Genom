# EGX30 Pattern Discovery — Real-Data Final Holdout Run

Mission 2 (Data Unlock + Scientific Hardening) Phase 16 deliverable: the
one, un-repeated, full `discover -> validate -> final_holdout` run against
real EGX price data, with the engine's unmodified production defaults
(`PatternDiscoveryEngineConfig()` — no threshold loosened or tightened for
this run). Raw/condensed artifacts: `research/data/pattern_discovery_real_run/`
(`run_summary.json`, `validated_patterns_condensed.csv`).

**Bottom line, stated first:** the pipeline found a real, planted-momentum-
grade positive control recoverable (`docs/PATTERN_DISCOVERY_CONTROL_SUITE.md`)
and, run against real EGX data, promoted 1,773 patterns all the way to
`VALIDATED` — including through a genuinely held-out final slice never
touched by discovery or validation. **That volume is not evidence of 1,773
real market inefficiencies.** It is strong, concrete, real-data evidence of
the multiple-testing/correlated-candidate-pool gap this codebase's own
`fdr_alpha` docstring, `docs/PATTERN_DISCOVERY_REPORT.md`, and TD-70/TD-72
already flagged from synthetic testing — now confirmed at real-data scale,
in the most direct way an empirical run can show it: far more "validated"
patterns than any credible EGX momentum/reversion literature would support
from 14 tickers. **No individual pattern in this run's `VALIDATED` set
should be treated as trustworthy or actionable until the TD-72 remediation
lands and this run (or an equivalent one) is repeated.** This is the
mission's own explicitly legitimate kind of outcome — a real, non-zero,
non-fabricated result that nonetheless does not answer "yes, EGX contains
real, tradeable patterns" in the affirmative, because the result cannot yet
be trusted at face value.

## Universe and data

14 tickers: the intersection of (a) `research/data/universe/EGX30.csv`'s
real, current EGX30 constituent list (31 members, as-of 2026-07-26) and
(b) the real, third-party, MIT-licensed community price seed
(`research/data/community_prices_seed/`, 75 tickers, ~4.6 years,
`docs/EGX30_DATA_SOURCE_QUALIFICATION.md`): **ADIB, COMI, EFIH, EGAL, EMFD,
ETEL, FWRY, GBCO, HELI, ORAS, ORHD, ORWE, PHDC, TMGH**. The other 17 real
EGX30 constituents have no price history in this free dataset; the other
61 seed tickers are not current EGX30 members — a real, disclosed coverage
gap, not a silent omission (see TD-71's update).

`--as-of 2026-08-06` (the seed's last trading day). `--source collected`
materializes the real seed into the run's `--data-dir` per the existing
`materialize_community_price_seed()` contract.

## Why only 14 tickers, not the full 75

A timing probe (5 real tickers, full production defaults) took 7m28s for
`discover()` alone. Full production defaults on the broader 75-ticker seed
would have taken multiple hours just for `discover()`, before `validate()`
(which turned out to be the dominant cost — see below). Restricting to the
real EGX30-covered subset is the scientifically cleanest bound available
(this mission is titled "EGX30 Pattern Discovery," and the resulting
universe is real EGX30 membership, not an arbitrary shrink) — not a
threshold loosened to manufacture a result, and not chosen after seeing any
intermediate output.

## Reproducibility

| Stage | git commit | experiment id | dataset version (community seed source commit) |
|---|---|---|---|
| discover | `3f34f28c978f2c2e15cc180f73b1a4b4706d9fd7` | `experiment_0e0ca6fdb941` | `555fb77e290738f3ff97dd4db65791457ec1e90c` |
| validate | `da84d705303d23be8e0872d5b9cbe84bf197a3a6` | `experiment_4edb4c2fe846` | `555fb77e290738f3ff97dd4db65791457ec1e90c` |
| final-holdout | (same session, `research/data/pattern_discovery_real_run/run_summary.json` has the full manifest) | — | `555fb77e290738f3ff97dd4db65791457ec1e90c` |

The `discover` and `validate` stages of this one logical run were stamped
with two different git commits because the run spans several hours during
which unrelated test files (not `patterns/`, not touching engine
behavior) were committed on this same branch — disclosed here rather than
silently glossed over, per the mission's zero-fabrication posture. The
engine/feature-factory/target-factory versions and every declared config
constant are identical and unchanged across all three stages (full
manifest in `run_summary.json`).

Engine config used (unmodified production defaults):
`min_sample_size=30`, `correlation_prune_threshold=0.8`,
`match_overlap_prune_threshold=0.85`, `max_candidates_per_ticker=500`,
`enable_two_feature=True`, `enable_three_feature=True`,
`enable_regime_conditioning=True`, `fdr_alpha=0.05`, `run_robustness=True`,
`require_beats_baseline=True`, `horizons=(5,10,20,60)`,
`holdout_fraction=0.15`, `enable_barrier_targets=True`,
`enable_lead_lag=True`, `n_folds=4`, `min_train_size=30`,
`min_oos_sample_size=10`, `embargo_days=2`.

## Exact commands run

```bash
cd research
DATA_DIR=/tmp/agx_real_run
TICKERS="ADIB,COMI,EFIH,EGAL,EMFD,ETEL,FWRY,GBCO,HELI,ORAS,ORHD,ORWE,PHDC,TMGH"
AS_OF=2026-08-06

uv run python -m agx_research.cli --data-dir "$DATA_DIR" \
  research discover --as-of "$AS_OF" --source collected --tickers "$TICKERS"
uv run python -m agx_research.cli --data-dir "$DATA_DIR" \
  research validate --as-of "$AS_OF" --source collected --tickers "$TICKERS"
uv run python -m agx_research.cli --data-dir "$DATA_DIR" \
  research final-holdout --as-of "$AS_OF" --source collected --tickers "$TICKERS"
```

## The funnel — real numbers, every stage

| Stage | Count | Notes |
|---|---:|---|
| Features generated | 811 | price/volume/cross-sectional/macro, across 14 tickers |
| Candidates generated | 7,899 | single/two/three-feature, regime-conditioned, lead/lag |
| Hypothesis families (`candidate_family_key`) | 315 | ~25 candidates/family on average |
| Candidates surviving family correction alone | 3,550 | before the joint BH-FDR pass |
| Candidates surviving BH-FDR (`fdr_alpha=0.05`) → `DISCOVERED` | 3,398 | **43.0%** of all candidates |
| `DISCOVERED` → `validate()` → `VALIDATING` | 1,880 | 1,518 rejected (purged walk-forward / robustness / baseline-beating) |
| `VALIDATING` → `final_holdout()` → `VALIDATED` | 1,773 | 107 rejected — **94.3%** of `VALIDATING` patterns passed the untouched holdout slice |

Every gate real, every number real, no threshold adjusted between stages
or after seeing an intermediate result. And that is exactly the problem:
**43% discovery-sample survival and 94.3% final-holdout survival are both
far too permissive for a candidate pool this large and this correlated
to be credible.** A textbook-honest search over 7,899 largely-derived,
largely-correlated candidates on 14 tickers' price history should not
produce over a thousand independently real, economically distinct,
tradeable relationships — and it did not; it reproduced a small number of
real underlying statistical tendencies (see below) many times over.

## Illustrative evidence: this is redundancy, not 1,773 discoveries

`EGAL` alone contributed 354 of the 1,773 `VALIDATED` patterns. Grouping
its patterns by base feature (stripping the window-length suffix, e.g.
`return_1d`/`return_3d`/`return_5d`/... → `return`) collapses those 354
down to **19 distinct base-feature groups** — the single largest group,
`return:EGAL`, alone accounts for 131 of them:

```
return_1d:EGAL  > -0.0100 -> forward_return_5d:EGAL
return_1d:EGAL  >  0.0000 -> forward_return_5d:EGAL
return_1d:EGAL  >  0.0104 -> forward_return_5d:EGAL
return_3d:EGAL  > -0.0163 -> forward_return_5d:EGAL
return_3d:EGAL  >  0.0021 -> forward_return_5d:EGAL
return_3d:EGAL  >  0.0228 -> forward_return_5d:EGAL
return_5d:EGAL  > -0.0188 -> forward_return_5d:EGAL
return_5d:EGAL  >  0.0057 -> forward_return_5d:EGAL
return_5d:EGAL  >  0.0353 -> forward_return_5d:EGAL
return_10d:EGAL > -0.0229 -> forward_return_5d:EGAL
...
```

These are not 131 independent facts about EGAL's price behavior — they are
one underlying (real-or-spurious) directional tendency, sliced by every
combination of lookback window (1/3/5/10/20/60 days) and quantile threshold
(30th/50th/70th percentile), each counted as its own "discovery." This is
the concrete, real-data face of the risk `docs/PATTERN_DISCOVERY_REPORT.md`
and TD-70 already named from synthetic pure-noise testing.

**A pointed, unexplained diagnostic**: every one of the 1,773 `VALIDATED`
patterns carries `family_size=1` in the persisted registry — meaning
`family_corrected_p_value()` applied *zero* penalty to every single
survivor (the correction only discounts candidates sharing a family with
others; solo-family candidates pass through unpenalized). Family
correction is therefore not what is filtering false discoveries here at
all — every filtering gate that mattered (BH-FDR itself, purged
walk-forward, robustness, baseline-beating, final holdout) let this
through regardless. This is left as an open, disclosed diagnostic rather
than a fully root-caused fix (see TD-72's repayment trigger) — it narrows
where future remediation work should look first.

## Other real, notable shape of the result

- **Every single `VALIDATED` pattern uses `horizon_days=5` and the
  `forward_return` target family** — none of the `10/20/60`-day horizons,
  and none of the barrier/MFE-MAE/probability/relative-return target
  families this engine also searches, produced a single `VALIDATED`
  pattern. Reported as observed; the likely mechanical reason (fewer
  effective non-overlapping observations at longer horizons reduces
  significance/robustness margins) is a plausible hypothesis, not verified
  here — flagged for whoever picks up TD-72's remediation.
- **Zero regime-conditioned patterns validated** — consistent with TD-73's
  separate finding that regime-conditioned candidates struggle to survive
  discovery-stage BH-FDR at all at the sample sizes this run affords.
- **207 of 1,773 (11.7%) are lead/lag patterns** — the cross-ticker
  `feature_lookup` regression this mission's own `test_pattern_lead_lag.py`
  guards against evidently works correctly at real-data scale (lead/lag
  patterns reach `VALIDATED`, not silently zero) — but they inherit the
  exact same over-permissiveness concern as everything else in this run.
- Median `expectancy` across `VALIDATED` patterns: **+1.74%** per matched
  5-day forward return; median `hit_rate`: **56.2%**; median
  `holdout_sample_size`: **59** (min 5, max 162) — individually
  plausible-looking numbers, which is exactly why the *volume* (not any
  one pattern's own statistics) is the tell here.

## What would make this run's `VALIDATED` set trustworthy

Per TD-72: a per-ticker cap on how many patterns may reach `VALIDATED`
simultaneously, a dependence-robust multiple-testing correction (e.g.
Benjamini-Yekutieli) in place of/alongside the current family correction,
and/or a requirement that a lead/lag or cross-sectional pattern be
corroborated by more than one instrument before promotion. None of these
exist yet. Until one does, this run's honest conclusion stands:

**This run does not establish that EGX30's real, free price data contains
repeatable, economically meaningful patterns.** It establishes that this
engine, run against real data at production defaults, needs its
multiple-testing control hardened before its `VALIDATED` label can be
trusted — a real, disclosed, actionable finding, and a legitimate outcome
under this mission's own explicit acceptance criteria ("the correct result
may still be zero validated patterns" generalizes here to "the correct
result may be too many nominally-validated patterns to trust any single
one without further work").

See also: `docs/VALIDATED_PATTERNS.md` (the required Phase 18 output),
`docs/PATTERN_DISCOVERY_CONTROL_SUITE.md` (the positive/negative control
suite that first surfaced this class of risk empirically), `docs/
TECHNICAL_DEBT.md`'s TD-70/TD-72/TD-73.
