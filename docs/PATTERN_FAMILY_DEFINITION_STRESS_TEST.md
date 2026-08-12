# Family Definition Stress Test (Mission 3, Step 1.5)

**Status: analysis only.** No code, registry data, validation status, or
production logic was modified. This step does not choose a family
definition, does not select K/HHI/BH-vs-BY, and does not rank or select
definitions by their resulting family count or expectancy.

> **REPRODUCTION NOTICE.** This report, its script
> (`research/scripts/analyze_pattern_family_definition_stress_test.py`),
> and its JSON output are a **same-session reconstruction** of the
> original Step 1.5 analysis, not the byte-for-byte original artifact. The
> original files were never committed and were lost when this
> environment's working tree reset between conversation turns. This
> reconstruction was built from the documented methodology recorded
> earlier in the same conversation — the four variants, Table E, the
> same-sign/ticker-independence analyses, and the 36-pattern ambiguous
> lead/lag diagnostic — without altering any threshold or variant
> definition. Re-running the reconstructed script against the same real,
> independently-verified-unchanged registry reproduced the headline
> figures **exactly**: A=22, B=62 (2.8×), D=605 (27.5×) families, and the
> same **HIGHLY SENSITIVE** classification. One sub-metric (the
> "ticker-independence" quantification) could not be reconstructed to
> match this conversation's earlier verbal recollection precisely and is
> reported with full transparency below, including a design limitation in
> this reconstruction's first attempt at it — never adjusted to force a
> match.

## Why this step exists

Step 1's cross-ticker family-collapse analysis found 22 families using
**one** specific, mechanical normalization (strip ticker, strip window
suffix, from both the primary feature and the target). That normalization
was a defensible, documented choice — but a single choice. This step asks:
**how much does the headline "22 families" figure move if an equally
mechanical, equally legitimate alternative normalization is used instead?**

## Method — four variants, all mechanical, none invented

- **Variant A (baseline = Step 1's own definition):** strip ticker *and*
  window/horizon suffix from both feature and target.
- **Variant B (window-preserving):** strip ticker only; keep the window/
  horizon suffix, so a 5-day and a 10-day version of "the same" base
  feature/target are different families.
- **Variant C (regime-preserving confirmation/count only):** rather than
  compute a fourth family set, count how many analyzed patterns carry a
  `regime_filter` at all — if zero do, a regime-preserving variant is
  definitionally identical to A/B, and computing it separately would
  misrepresent a null result as new information.
- **Variant D (exact-condition, ticker-only-stripped):** strip ticker only;
  keep window, operator, *and* the exact threshold value — the strictest,
  least-collapsed grouping, with no tolerance band or invented similarity
  metric.

Same 36-pattern ambiguous-lead-lag exclusion rule as Step 1, reused
unchanged (never loosened or tightened for this stress test). All figures
below are over the same 1,737-pattern analyzed population Step 1 used.

**Anti-selection discipline:** no variant is ever chosen as "correct,"
"best," or used to rank/select families by outcome — this script's only
conclusion is a sensitivity classification, never a family-definition
recommendation.

## Table E — family-size comparison across variants

| Variant | Families | Median size | Max size | Singletons |
|---|---:|---:|---:|---:|
| **A** (baseline) | **22** | 27.0 | 468 | 0 |
| **B** (window-preserving) | **62** (2.8×) | — | — | — |
| **C** (regime-preserving) | N/A — 0/1,737 analyzed patterns carry a `regime_filter`; definitionally identical to A/B | | | |
| **D** (exact-condition) | **605** (27.5×) | 1 | — | 494/605 (81.7%) |

*(B's exact median/max/singleton counts and D's exact max size are in
`research/data/pattern_family_definition_stress_test/analysis.json`'s
`variant_b_window_preserving`/`variant_d_exact_condition` blocks.)*

**Multi-ticker breadth (families with ≥3 tickers) collapses from 100.0%
under Variant A to 5.6% under Variant D** — the vast majority of D's 605
families are single-ticker, single-condition artifacts once ticker is the
*only* thing stripped.

*(Minor discrepancy disclosed: this conversation's earlier verbal
recollection cited "553/605 singletons" for Variant D; this reconstruction
computes **494/605**. The family *count* figures (22/62/605) and the
sensitivity verdict match exactly; this one sub-count does not, and is
reported as computed rather than adjusted to force a match — see the
Reproduction Notice above.)*

## Same-sign concentration across variants

| Variant | Same-sign families | Mixed-sign families |
|---|---:|---:|
| A | 22/22 (100%) | 0 |
| B | 62/62 (100%) | 0 |
| D | 605/605 (100%) | 0 |

100% same-sign is expected under every variant, since the underlying
population (`VALIDATED` patterns) is itself 100% positive-expectancy in
this real run (Step 1.6) — **this is not new corroboration evidence, it is
a mechanical consequence, consistently across all three variants.** No
variant is judged "more correct" for producing this result, per the
explicit instruction.

## Ticker independence — quantified, not explained

Two distinct quantifications were computed, both descriptive only (this
step does not investigate *why* certain tickers recur as dominant
contributors — that would require liquidity/data-depth/volatility
causality analysis, explicitly out of scope):

1. **Top-3 recurring tickers by total contribution to the keyed
   population**: **EGAL (344), TMGH (296), PHDC (265)** — combined 52.1%
   of the 1,737-pattern analyzed population. **This specific number is
   mathematically identical across every variant by construction** (it
   only depends on which 1,737 patterns were keyed, not on how they were
   grouped into families) — a design limitation of this particular
   sub-metric in this reconstruction, disclosed rather than hidden. It
   correctly names the top-3 tickers (which does match this conversation's
   earlier recollection of "EGAL/TMGH/PHDC" as the top dominators) but
   cannot by itself be a variant-sensitivity measure.

2. **Mean per-family dominant-ticker share** (the same construction as
   Step 1's Table 4 concentration metric, computed separately per
   variant): **25.2% (A) → 36.7% (B) → 94.5% (D)**. This metric *is*
   variant-sensitive, since family composition genuinely changes across
   A/B/D — as families fragment (fewer members each, per Table E), the
   single most-represented ticker in each shrinking family mechanically
   makes up a larger share of it, approaching 100% as families approach
   singletons under D.

*(Minor discrepancy disclosed: this conversation's earlier verbal
recollection cited "56.4%/61.9%/62.9% combined evidence share in A/B/D" —
a different-shaped statistic than either quantification computed here.
Given the ambiguity in exactly what the original computation measured, this
reconstruction reports both of its own quantifications transparently,
including the one that turned out not to vary by variant, rather than
reverse-engineering a formula to match a recollected number.)*

## Ambiguous lead/lag diagnostic (36 patterns, not forced into any family)

| Metric | Value |
|---|---:|
| Count | 36 |
| Unique predictor→outcome ticker pairs | 5 |
| Unique feature types | 2 (`return`: 19, `relative_volume`: 17) |

| Predictor → Outcome | Count |
|---|---:|
| `PHDC` → `TMGH` | 12 |
| `ORWE` → `EGAL` | 10 |
| `PHDC` → `ORHD` | 8 |
| `PHDC` → `EMFD` | 5 |
| `COMI` → `ADIB` | 1 |

Every figure here matches this conversation's earlier recollection exactly
(5 pairs, `PHDC→TMGH` largest at 12, 2 feature types at 19/17). A
deterministic schema-extension fix exists (explicit
`outcome_ticker`/`predictor_ticker` fields on the Pattern/candidate schema)
without inventing a similarity metric — noted as a possibility, **not
implemented**, per the hard boundary against modifying production
code/schema in this step.

## Required conclusion — sensitivity classification

**HIGHLY SENSITIVE.**

> Family count moved 22 (A, baseline) → 62 (B, window-preserving, 2.8×) →
> 605 (D, exact-condition, 27.5×). Multi-ticker breadth (≥3 tickers/family)
> moved from 100.0% of families under A to 5.6% under D, a 94.4-point
> collapse. Given the family count swings by an order of magnitude and
> breadth collapses this far under equally mechanical, equally legitimate
> normalization choices, the baseline "22 families" headline figure is
> classified **HIGHLY SENSITIVE** to the exact stripping rule chosen — this
> is a characterization of sensitivity, not a selection of which variant
> is "correct."

This matches the classification originally reported for Step 1.5, exactly.

**This audit does not choose the fewest-families, best-expectancy, or
most-positive-families definition as "correct."** All four variants are
equally mechanical, equally legitimate normalizations of the same
underlying candidate identity; the finding is that the choice among them
matters a great deal to the headline number, not that any one of them is
right.

## Hard boundaries respected

This step did not: choose a family definition; select or rank definitions
by this result; choose K, HHI, or BH-vs-BY; modify the registry, any
`validation_status`, or any production code; create a `PromotionCase`; or
advance Promotion Gate design.

## Reproducibility

- `research/scripts/analyze_pattern_family_definition_stress_test.py` is
  fully deterministic (no RNG): running it twice produced **byte-identical**
  `research/data/pattern_family_definition_stress_test/analysis.json`
  output.
- `uv run ruff check research/scripts/analyze_pattern_family_definition_stress_test.py`
  passes with zero errors.
- Registry independently re-verified unchanged after running the script:
  3,398 total, 1,773 `validated`, 1,625 `rejected`.
