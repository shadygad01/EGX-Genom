# Pattern Promotion Gate — HHI Evidence-Concentration Audit

**Status: descriptive audit only. No HHI ceiling is adopted. No pattern or
family is promoted, rejected, or otherwise verdicted. The registry is not
modified.**

## Purpose

`docs/PATTERN_PROMOTION_GATE_DESIGN.md`'s v2.2 §14 lists "Ticker
concentration (HHI) ceiling" as PROVISIONAL, with "a calibrated ceiling
number — none proposed" as the named dependency. Manus AI's second
calibration-research memo
(`docs/PATTERN_PROMOTION_GATE_CALIBRATION_RESEARCH_PART2.md` Part 1 §5)
proposed diagnostic bands (`<0.15` / `0.15–0.25` / `0.25–0.40` / `>0.40`)
as a **calibration envelope, not a recommendation to adopt any one value**.

This audit applies those bands to the real Mission 2 registry's
cross-ticker families, to answer a concrete question the design doc could
not answer without doing so: **how much of a problem, in practice, is
ticker concentration in the current real 1,773-pattern population?**

This is the same posture as Step 1's (`analyze_cross_ticker_family_collapse.py`)
own Table 4, which already reported an aggregate mean/median HHI (0.169 /
0.150) but not a per-family distribution across bands — this audit adds
that missing distribution, using the identical, unmodified family-
construction methodology (script:
`research/scripts/audit_pattern_hhi_evidence_concentration.py`, output:
`research/data/pattern_hhi_evidence_concentration_audit/analysis.json`).

## Methodology notes

- **Population**: the same 1,773 real `PatternStatus.VALIDATED` patterns
  Step 1 analyzed, read from `/tmp/agx_real_run/patterns/registry.json`
  (read-only; the registry's MD5 hash was verified unchanged before and
  after every run).
- **Family construction**: identical to Step 1's
  `cross_ticker_family_key` (strip ticker + window suffix from the primary
  feature and target, keep regime-filter presence). 22 families analyzed,
  1,737 patterns keyed, 36 excluded as ambiguous lead/lag or unkeyable —
  **identical counts to Step 1**, confirming the reused methodology is
  faithful.
- **Two declared HHI denominators**, per Manus's own point that "the
  denominator must be declared... [it] produce[s] different HHIs":
  1. **`member_count`** — one vote per pattern-family-member, identical to
     Step 1's Table 4 methodology. This audit's median (0.15049898...) and
     mean (0.16941421...) reproduce Step 1's Table 4 values **exactly**,
     confirming methodological consistency.
  2. **`matched_observations`** — weighted by each pattern's own
     `sample_size` instead of member count. This is a **new** metric; Step
     1 did not compute it.
- Reproducibility: the script was run twice; output was byte-identical
  both times (pure computation over already-persisted data, no
  randomness).

## Findings — band distribution

### Under `member_count` (Step 1's own denominator)

| Band | Families | % of families | Patterns | % of patterns |
|---|---:|---:|---:|---:|
| Diffuse (<0.15) | 11 | 50.0% | 712 | 41.0% |
| Moderate (0.15–0.25) | 8 | 36.4% | 1,001 | 57.6% |
| High (0.25–0.40) | 3 | 13.6% | 24 | 1.4% |
| Very concentrated (>0.40) | 0 | 0.0% | 0 | 0.0% |

### Under `matched_observations` (new, sample_size-weighted)

| Band | Families | % of families | Patterns | % of patterns |
|---|---:|---:|---:|---:|
| Diffuse (<0.15) | 11 | 50.0% | 967 | 55.7% |
| Moderate (0.15–0.25) | 7 | 31.8% | 737 | 42.4% |
| High (0.25–0.40) | 4 | 18.2% | 33 | 1.9% |
| Very concentrated (>0.40) | 0 | 0.0% | 0 | 0.0% |

## Interpretation

**Under either denominator, no family in the real registry falls in
Manus's "very concentrated" (>0.40) band**, and roughly half of all
families (50%) are "diffuse" (<0.15) — the more favorable end of the
scale. This is a materially better picture than the hypothetical worst
case Manus's memo used to illustrate concentration risk ("a single ticker
contributing 80% of matched observations creates an HHI of at least
0.64").

However, this should not be read as "concentration is not a problem
here":

- **~82–86% of families (18–19 of 22) are moderate-or-worse** under both
  denominators — only the diffuse band is unambiguously comfortable by
  Manus's own bands.
- The five most-concentrated families by matched observations (see
  `most_concentrated_families_by_matched_observations` in the JSON) are
  all in the "high" band (0.267–0.395), with a single dominant ticker
  responsible for 34–51% of that family's matched observations — e.g. the
  `EGP_USD_acceleration|forward_return|no_regime` family (6 patterns, 3
  tickers) has COMI alone responsible for 51.1% of its 188 matched
  observations.
- The two denominators **do not always agree** on a family's band (e.g.
  the `turnover_anomaly` family is "high" under member-count but
  "moderate" under matched-observations, and vice versa for
  `BRENT_USD_change`) — directly illustrating Manus's point that the
  choice of denominator changes the concentration verdict, not just its
  magnitude.
- This audit does **not** run the leave-one-ticker-out or
  equal-ticker-weight robustness checks Manus's memo also recommended
  (§5.2's "strongest test") — those are a heavier, separate calibration
  experiment, not part of this descriptive pass.

## Non-decisions

- **No HHI ceiling is adopted.** The bands used are Manus's proposed
  diagnostic envelope, reported as-is, not calibrated or endorsed as
  final.
- **No pattern or family is promoted, rejected, or labeled
  `OUT_OF_SCOPE_FOR_PROMOTION`** as a result of this audit. v2.2 §14's HHI
  ceiling row remains PROVISIONAL — this audit supplies real distributional
  evidence for that future decision, not the decision itself.
- **No registry data was modified.** This audit is read-only; the
  registry's MD5 hash was verified identical before and after every run.
- **No `PromotionCase` was created**, and no production code
  (`robustness.py`, `registry.py`, `multiple_testing_family.py`, etc.) was
  touched.

## Files

- Script: `research/scripts/audit_pattern_hhi_evidence_concentration.py`
- Data: `research/data/pattern_hhi_evidence_concentration_audit/analysis.json`
- This report: `docs/PATTERN_HHI_EVIDENCE_CONCENTRATION_AUDIT.md`
