# EGX30 Pattern Discovery — Validated Patterns (Mission 2, Phase 18)

**This is not a list of trustworthy trading signals.** Read
`docs/PATTERN_DISCOVERY_FINAL_HOLDOUT.md` in full before drawing any
conclusion from the numbers below — it explains, with a concrete real
example, why 1,773 simultaneously `VALIDATED` patterns from a 14-ticker,
~4.6-year real dataset is itself strong evidence of an unresolved
multiple-testing gap (TD-72), not evidence of 1,773 real market
inefficiencies. This document exists because the mission requires an
honest accounting of whatever the pipeline actually produced — not
because any specific pattern below should be acted on.

Full data: `research/data/pattern_discovery_real_run/run_summary.json`
(complete run manifest) and `validated_patterns_condensed.csv` (all 1,773
patterns, one row each).

## Headline numbers

- **1,773 patterns reached `VALIDATED`** out of 3,398 `DISCOVERED` (43.0%
  of 7,899 generated candidates) and 1,880 promoted to `VALIDATING`.
- Every one used `horizon_days=5` and the `forward_return` target family;
  none of `10/20/60`-day horizons or the barrier/MFE-MAE/probability/
  relative-return target families produced a `VALIDATED` pattern.
- 207 of 1,773 (11.7%) are lead/lag (cross-ticker) patterns; 0 are
  regime-conditioned.
- Median expectancy **+1.74%** per matched 5-day forward return; median
  hit rate **56.2%**; median holdout sample size **59** (min 5, max 162).
- By ticker: EGAL 354, TMGH 308, PHDC 265, GBCO 160, COMI 136, ORHD 132,
  EMFD 115, FWRY 94, ORWE 73, ADIB 59, ETEL 46, EFIH 18, HELI 13.

## Why this is not 1,773 discoveries

`docs/PATTERN_DISCOVERY_FINAL_HOLDOUT.md`'s illustrative-evidence section
walks through EGAL's 354 `VALIDATED` patterns collapsing to 19 distinct
base-feature groups (stripping window-length suffixes), with the single
largest group — 131 patterns all keyed on some window/threshold variant of
`return:EGAL` predicting `forward_return_5d:EGAL` — being one underlying
tendency counted 131 times, not 131 independent facts about EGAL. The same
structure is visible across every heavily-represented ticker in this set.

## Illustrative sample: the 20 patterns with the largest holdout sample

Selected by holdout sample size (the most statistically grounded
selection criterion available — not by expectancy or hit rate, which
would read as cherry-picking the best-looking outcomes). Individually,
none of these look obviously wrong; that is exactly the point made above
— no single pattern's own statistics reveal the multiple-testing problem,
only the aggregate volume does.

| Ticker | Definition | Sample | OOS sample | Holdout sample | Expectancy | Holdout expectancy | Hit rate | Lead/lag |
|---|---|---:|---:|---:|---:|---:|---:|---|
| COMI | `distance_from_low_3d:COMI > -0.0564 -> forward_return_5d:COMI` | 388 | 388 | 162 | +0.0109 | +0.0095 | 0.570 | No |
| COMI | `distance_from_low_10d:COMI > -0.0526 -> forward_return_5d:COMI` | 605 | 605 | 162 | +0.0113 | +0.0095 | 0.560 | No |
| EGAL | `distance_from_high_1d:EGAL > -0.1307 -> forward_return_5d:EGAL` | 389 | 389 | 162 | +0.0190 | +0.0137 | 0.550 | No |
| EGAL | `distance_from_low_10d:EGAL > -0.1227 -> forward_return_5d:EGAL` | 606 | 606 | 162 | +0.0204 | +0.0137 | 0.564 | No |
| GBCO | `distance_from_low_3d:GBCO > -0.0235 -> forward_return_5d:GBCO` | 610 | 609 | 162 | +0.0140 | +0.0077 | 0.540 | No |
| GBCO | `volatility_60d:GBCO < 0.0291 -> forward_return_5d:GBCO` | 359 | 359 | 162 | +0.0134 | +0.0077 | 0.549 | No |
| ORHD | `volatility_60d:ORHD < 0.0304 -> forward_return_5d:ORHD` | 570 | 570 | 162 | +0.0154 | +0.0164 | 0.554 | No |
| ORWE | `distance_from_high_60d:ORWE > -0.3124 -> forward_return_5d:ORWE` | 571 | 571 | 162 | +0.0104 | +0.0044 | 0.483 | No |
| ORWE | `volatility_60d:ORWE < 0.0315 -> forward_return_5d:ORWE` | 570 | 570 | 162 | +0.0133 | +0.0044 | 0.505 | No |
| TMGH | `distance_from_low_1d:TMGH > -0.0046 -> forward_return_5d:TMGH` | 612 | 610 | 162 | +0.0164 | +0.0095 | 0.531 | No |
| TMGH | `return_60d:TMGH > -0.0154 -> forward_return_5d:TMGH` | 572 | 572 | 160 | +0.0210 | +0.0090 | 0.535 | No |
| ADIB | `volatility_20d:ADIB > 0.0178 -> forward_return_5d:ADIB` | 604 | 592 | 158 | +0.0137 | +0.0217 | 0.549 | No |
| GBCO | `distance_from_low_60d:GBCO < 0.3313 -> forward_return_5d:GBCO` | 575 | 575 | 158 | +0.0195 | +0.0077 | 0.593 | No |
| ETEL | `distance_from_high_1d:ETEL > -0.0602 -> forward_return_5d:ETEL` | 173 | 173 | 157 | +0.0197 | +0.0212 | 0.653 | No |
| ORHD | `distance_from_low_3d:ORHD > 0.0010 -> forward_return_5d:ORHD` | 616 | 605 | 156 | +0.0130 | +0.0148 | 0.559 | No |
| ORWE | `return_60d:ORWE < 0.1189 -> forward_return_5d:ORWE` | 579 | 579 | 155 | +0.0144 | +0.0055 | 0.532 | No |
| COMI | `volatility_10d:COMI > 0.0119 -> forward_return_5d:COMI` | 619 | 619 | 153 | +0.0112 | +0.0091 | 0.572 | No |
| FWRY | `acceleration_60d:FWRY < 0.1499 -> forward_return_5d:FWRY` | 538 | 538 | 152 | +0.0112 | +0.0112 | 0.556 | No |
| FWRY | `distance_from_low_60d:FWRY < 0.3157 -> forward_return_5d:FWRY` | 582 | 582 | 152 | +0.0134 | +0.0103 | 0.572 | No |
| ORHD | `distance_from_high_3d:ORHD > -0.0618 -> forward_return_5d:ORHD` | 620 | 599 | 152 | +0.0141 | +0.0175 | 0.561 | No |

## What to do with this

Nothing, yet. Per `docs/PATTERN_DISCOVERY_FINAL_HOLDOUT.md` and TD-72:
this `VALIDATED` set should not feed `live.LiveActivationEngine`,
`decision_service`, or any capital-facing decision until the
multiple-testing hardening TD-72 describes lands and this run (or an
equivalent one) is repeated. The honest, mission-faithful conclusion of
this Phase 18 deliverable is: **the current pipeline cannot yet
distinguish real EGX30 patterns from an at-scale false-discovery flood,
and that gap — not a specific list of tradeable signals — is Mission 2's
real, actionable finding.**
