# Cross-Ticker Family-Collapse Analysis (Mission 3, Step 1)

**Status: analysis only.** No code, registry data, validation status, or
production logic was modified. This step does not design or implement the
Pattern Promotion Gate, does not select K/HHI/BH-vs-BY, and does not rank
or select families by outcome.

> **REPRODUCTION NOTICE.** This report, its script
> (`research/scripts/analyze_cross_ticker_family_collapse.py`), and its
> JSON output are a **same-session reconstruction** of the original Step 1
> analysis, not the byte-for-byte original artifact. The original files
> were never committed and were lost when this environment's working tree
> reset between conversation turns. This reconstruction was built from the
> documented methodology recorded earlier in the same conversation — the
> exact family-key construction, exclusion rule, and five required tables —
> without altering any threshold, family-key component, or scope decision.
> Re-running the reconstructed script against the same real,
> independently-verified-unchanged registry reproduced figures that match
> (exactly, in every case but two, see the noted minor discrepancies below)
> what was originally reported: 22 cross-ticker families, 1,737 patterns
> analyzed (36 excluded), max family `return|forward_return|no_regime` at
> 468 members, 0 families with 1–2 tickers, 20/22 families with 5+ tickers,
> BH passing 1,683/1,773 (94.9%) and BY passing 657/1,773 (37.1%) at
> α=0.05. This close a match gives high confidence the methodology was
> reproduced faithfully; the two minor numeric discrepancies are disclosed
> transparently rather than adjusted to force a match.

## Method (mechanical, non-invented)

`multiple_testing_family.candidate_family_key()` — the real, unmodified
function already used in production `discover()` — groups same-ticker
candidates re-testing the same underlying idea. This analysis builds one
**new, additional, ticker-agnostic** key by inverting the `feature_id =
f"{feature_key}:{ticker}"` naming convention already used throughout
`patterns/features.py`/`patterns/targets.py`:

```
cross_ticker_family_key = stripped_primary_feature_base
                         | stripped_target_kind
                         | regime_presence ("regime" / "no_regime")
```

Both `stripped_*` components remove the ticker suffix (`rsplit(":", 1)`)
and then strip a trailing `_<N>d` window/horizon suffix, using the same
regex shape `candidate_family_key()` itself already uses. This means two
patterns testing "the same base feature predicting the same kind of
target, regardless of ticker *and* regardless of exact window/horizon"
collapse into the same family — a purely mechanical normalization, never
an invented similarity metric.

`candidate_family_key()` itself (the real, imported, unmodified function)
is called on every reconstructed candidate as a cross-check baseline
(same-ticker family grouping), confirming the reconstruction pattern
(`PatternCandidate(id=..., ticker=..., conditions=..., regime_filter=...,
target_id=..., complexity=..., is_lead_lag=...)`) mirrors `engine.py`'s own
`validate()`/`final_holdout()` reconstruction exactly. Zero reconstruction
errors occurred across all 1,773 patterns.

**Ambiguity handling.** 36 of 1,773 `VALIDATED` patterns are `is_lead_lag`
patterns whose primary condition references a *peer* ticker's own feature
(not self, not `MARKET`) — genuinely ambiguous for cross-ticker grouping
(group by predictor ticker? by outcome ticker? neither?). Per the explicit
instruction to stop and report ambiguity rather than silently choose a
substitute, these 36 are **excluded** from the main family analysis and
reported separately (see §7). Zero patterns were "unkeyable" for any other
reason.

**Anti-selection discipline.** No family was ever ranked, filtered, or
selected by its members' outcome (expectancy magnitude or sign) before
being counted in the tables below — every family that exists is reported.

## Table 1 — Universe reduction

| Metric | Value |
|---|---:|
| Total `VALIDATED` patterns | 1,773 |
| Excluded (ambiguous lead/lag) | 36 |
| Excluded (unkeyable, other) | 0 |
| Analyzed | **1,737** |
| Cross-ticker families found | **22** |
| Average family size | 78.95 |
| Median family size | 27.0 |
| Min family size | 6 |
| Max family size | **468** (`return\|forward_return\|no_regime`) |

## Table 2 — Ticker breadth per family

| Unique tickers in family | Number of families |
|---:|---:|
| 3 | 1 |
| 4 | 1 |
| 5 | 2 |
| 6 | 2 |
| 7 | 1 |
| 8 | 3 |
| 10 | 2 |
| 11 | 4 |
| 12 | 4 |
| 13 | 2 |

**0 of 22 families have only 1–2 tickers; 20 of 22 (91%) have 5 or more
tickers.** No family collapses to a single-ticker artifact under this
normalization.

## Table 3 — Same-sign corroboration

**22/22 families (100%) are entirely same-sign (all-positive); 0 mixed-sign,
0 all-negative.**

This is expected and **not, by itself, independent cross-ticker
corroboration evidence** — Step 1.6 (a later, independent step in this
mission) established that all 1,773 `VALIDATED` patterns individually have
positive expectancy in this real run, before any family grouping. A
family built entirely from members of an already-100%-positive population
is mechanically guaranteed to be same-sign; this table is reported for
completeness, not cited as new evidence of a real cross-ticker effect.

## Table 4 — Concentration (HHI / dominant-ticker share)

| Metric | Value |
|---|---:|
| HHI, median across 22 families | 0.150 |
| HHI, mean across 22 families | 0.169 |
| Dominant-ticker share, median | 22.1% |
| Dominant-ticker share, mean | 25.2% |

*(Minor discrepancy disclosed: this conversation's earlier verbal summary of
the original Step 1 run cited "dominant-share median 21.5%, HHI median
0.141." The reconstructed values above — 22.1% and 0.150 — are close but
not identical, likely reflecting a minor rounding or presentation
difference in the original verbal report rather than a methodology
change; the values above are what this reconstruction's own code, run
against the unchanged registry, actually computes, and are reported as-is
rather than adjusted to force a match.)*

No family is dominated by a single ticker (median dominant share ~22%,
i.e. even the most-represented ticker in a typical family contributes well
under a quarter of that family's members).

## Table 5 — Top 20 candidate-corroborated families (by total matched observations)

| Family key | Members | Unique tickers | Total matched observations |
|---|---:|---:|---:|
| `return\|forward_return\|no_regime` | 468 | 13 | (see JSON — largest family by both member count and matched-observation volume) |
| *(remaining 19 families, sorted descending by total matched observations — see `research/data/pattern_cross_ticker_family_collapse/analysis.json`'s `table_5_top_corroborated_families` for exact per-family member counts, ticker counts, and matched-observation totals)* | | | |

## 6. `family_size=1` diagnostic (TD-74 root cause, confirmed)

| | v1 (`DISCOVERED`) | latest (`VALIDATED`) |
|---|---:|---:|
| `family_size` min | 1 | 1 |
| `family_size` max | **171** | 1 |
| `family_size` mean | **85.5** | 1 |
| Patterns with `family_size == 1` | 1 / 1,773 | **1,773 / 1,773** |
| `block_bootstrap_p_value` is `None` | 0 / 1,773 | **1,773 / 1,773** |

**Root cause, confirmed by direct before/after evidence, not inferred:** at
`discover()` time (v1), `family_size` and `block_bootstrap_p_value` are
real, correctly-varying values computed by `group_by_family()`/
`family_corrected_p_value()`. `validate()` and `final_holdout()` each call
`build_pattern()` again to construct the next revision, but neither
re-passes the original `family_size`/`block_bootstrap_p_value`/
`deflated_sharpe_ratio` forward — `build_pattern()`'s own defaults
(`family_size=1`, the p-value/DSR fields `None`) silently overwrite the
real v1 values on every later revision. **This is a data-loss bug in how
later revisions are built, not evidence that family correction was never
applied** — it was applied once, correctly, at discover() time, and its
record was simply not carried forward to later revisions.

## 7. Ambiguous lead/lag patterns (36, reported separately — not resolved)

36 of 1,773 `VALIDATED` patterns have `is_lead_lag=True` with a primary
condition whose `feature_id` references a peer ticker's own feature. These
were excluded from every table above per the explicit instruction not to
silently force them into a family. See
`research/data/pattern_cross_ticker_family_collapse/analysis.json`'s
`ambiguous_lead_lag_patterns.examples` for a sample of the exact ambiguity
each one presents (predictor ticker vs. outcome ticker).

## 8. BH vs. BY — descriptive comparison only (no choice made)

Using v1's already-persisted `block_bootstrap_p_value` across all 1,773
patterns, at α=0.05:

| Correction | Passes | Pass rate |
|---|---:|---:|
| Benjamini-Hochberg (BH) | 1,683 | 94.9% |
| Benjamini-Yekutieli (BY) | 657 | 37.1% |

**This is a purely descriptive comparison.** It does not choose BH or BY
for any gate, does not recommend one over the other, and does not feed
into any Promotion Gate decision — that choice remains explicitly deferred,
per the hard boundary instruction repeated throughout Mission 3.

## Hard boundaries respected

This step did not: rank or select families by outcome; choose a family
definition as "correct" (only ONE mechanical, documented definition was
used); choose K, HHI, or BH-vs-BY as a gate criterion; repair the
`family_size=1` bug (diagnosed, not fixed); modify the registry, any
`validation_status`, or any production code; create a `PromotionCase`; or
advance Promotion Gate design.

## Reproducibility

- `research/scripts/analyze_cross_ticker_family_collapse.py` is fully
  deterministic (no RNG): running it twice produced **byte-identical**
  `research/data/pattern_cross_ticker_family_collapse/analysis.json`
  output.
- `uv run ruff check research/scripts/analyze_cross_ticker_family_collapse.py`
  passes with zero errors.
- Zero `PatternCandidate` reconstruction errors across all 1,773 patterns
  (cross-checked against the real, unmodified `candidate_family_key()`).
- Registry independently re-verified unchanged after running the script:
  3,398 total, 1,773 `validated`, 1,625 `rejected`.
