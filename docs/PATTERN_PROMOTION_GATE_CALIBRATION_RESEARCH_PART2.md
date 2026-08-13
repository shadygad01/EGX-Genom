# Pattern Promotion Gate — Calibration Research Part 2 (Manus) & Reconciliation

## Provenance

- **Part 1** below is Manus AI's second calibration-research memo,
  commissioned as a follow-up to
  `docs/PATTERN_PROMOTION_GATE_CALIBRATION_RESEARCH.md` to cover the 7
  provisional gates its first memo did not address. It is saved here
  **verbatim**, exactly as delivered (`Reference date: 13 August 2026` per
  the memo's own header) — no wording, numbers, or citations have been
  edited. Its repository-specific factual claims were checked against the
  actual repository documents and code it cites
  (`PATTERN_CROSS_TICKER_FAMILY_COLLAPSE.md`,
  `PATTERN_FAMILY_DEFINITION_STRESS_TEST.md`,
  `PATTERN_DISCOVERY_FINAL_HOLDOUT.md`, `PATTERN_PROMOTION_GATE_DESIGN.md`,
  `research/src/agx_research/patterns/candidates.py`) before this file was
  created, and all of them matched exactly (1,737 analyzed patterns,
  median/mean HHI 0.150/0.169, dominant-ticker share progression
  25.2%→36.7%→94.5%, `match_overlap_prune_threshold=0.85`, the existing
  OOS floor of 10 via `WalkForwardValidatorConfig.min_oos_sample_size`, and
  the existing 95%/α=0.05 bootstrap default).
- **Part 2** is a reconciliation note, written by Claude Code (not Manus),
  mapping this memo's findings onto the remaining provisional-threshold
  rows in `PATTERN_PROMOTION_GATE_DESIGN.md`'s v2.2 §14 that
  `PATTERN_PROMOTION_GATE_CALIBRATION_RESEARCH.md` (Part 1 of this
  research effort) did not cover. It is analysis only — it does not
  select, adopt, or hardcode any threshold value anywhere in this
  repository, and it does not modify `PATTERN_PROMOTION_GATE_DESIGN.md`
  itself.
- **This document is external research input, not a decision.** Every
  threshold discussed remains PROVISIONAL exactly as v2.2 §14 already
  states; nothing here changes that status.

---

# Part 1 — Manus AI calibration-research memo, Part 2 (verbatim)

# Pattern-Promotion Gate Calibration Research — Part 2

**Repository:** `shadygad01/EGX-Genom`
**Scope:** Remaining provisional thresholds and methodology questions in the pattern-promotion gate
**Purpose:** Evidence-backed ranges and trade-offs for product-owner calibration; **not final decisions**
**Prepared by:** Manus AI
**Reference date:** 13 August 2026

## Executive summary

The current EGX-Genom design is correct to avoid treating a single family definition, a single ticker-breadth number, or a single similarity threshold as ground truth. The repository's own stress test produces 22, 62, or 605 families from the same validated population depending on whether windows and exact thresholds are stripped. That result is evidence of **granularity instability**, not evidence that one of those three answers is correct.

For same-feature/window and same-feature/threshold variants, the literature does not provide a defensible universal discount such as "count each variant as 0.5 independent tests." The more principled approaches are to estimate an **effective number of tests** from the dependence structure, use hierarchical or grouped testing, or calibrate the entire candidate-generation and promotion process with dependence-preserving resampling. Effective-test methods based on eigenvalues can summarize redundancy, but published work warns that they may be imperfect substitutes for permutation or resampling [1].

For cross-ticker grouping, **side-by-side reporting across multiple granularities is more defensible than collapsing immediately to one granularity** when the result is demonstrably unstable. Cluster-stability research supports bootstrap or subsampling stability profiles and consensus representations rather than reliance on one arbitrary partition [2]. The gate should therefore preserve exact, window-preserving, and base-feature views, while also reporting name-independent trigger-date overlap, cross-ticker return correlation, temporal clustering, and regime span.

HHI provides a useful concentration diagnostic, but HHI thresholds from antitrust or portfolio diversification cannot be transplanted directly into "evidence breadth." The DOJ describes 0.10–0.18 as moderately concentrated and above 0.18 as highly concentrated in a market-concentration context [3]. For evidence, those values are best treated as **reference bands**, not pass/fail rules. A pattern supported 80% by one ticker has HHI at least 0.64 before the remaining shares are considered; that is concentration so high that the claim should normally be described as ticker-specific evidence rather than broad cross-sectional replication, unless the product owner explicitly accepts that interpretation.

For a block-bootstrap expectancy interval, 95% is a reasonable central calibration point, but it is not automatically reliable in small, dependent, heavy-tailed samples. Higher coverage increases width and reduces promotion power; lower coverage improves usability but increases the chance that the lower bound is positive by sampling luck. Block-bootstrap theory also shows that coverage error depends on block length and sample size [4]. The appropriate final level should be chosen through EGX-specific coverage simulations and sensitivity at 90%, 95%, and 99%, with a minimum effective-event floor.

For the economic-rationale substance bar, use a structured rubric, independent double-coding, adjudication, and a pre-registered agreement analysis. Cohen's kappa is appropriate for two raters, Fleiss' kappa for three or more, and Krippendorff's alpha for multiple raters or missing/varied coding structures [5]. Agreement should be accompanied by raw agreement, category prevalence, confidence intervals, and examples of disagreements because kappa is sensitive to marginal distributions. The qualitative-methodology literature also emphasizes a shared codebook, trained coders, dialogue, expert adjudication, and applying the agreed rubric to the remaining cases [6].

For `INSUFFICIENT_EVIDENCE`, the strongest governance pattern is a **bounded pending state** rather than indefinite persistence: maintain the case while evidence can plausibly arrive, require a scheduled review, and automatically expire or re-review it after a declared calendar or inactivity limit. Neither the reviewed research-pipeline nor model-monitoring literature provides a universal TTL. Model-risk guidance instead emphasizes risk-based, non-prescriptive monitoring and validation appropriate to the model's materiality and use [7] [8]. Candidate ranges should therefore be expressed as governance bands, such as 3, 6, and 12 months, with event-triggered review and a restart rule if the frozen definition or evidence universe changes.

> **Working calibration envelope, not a final selection:** test effective-test ratios rather than fixed per-variant discounts; report three family granularities side by side; use HHI 0.15 / 0.25 / 0.40 as diagnostic bands rather than imported truth thresholds; compare 90% / 95% / 99% bootstrap lower bounds; run a two-stage reviewer study with at least two independent coders and a power-based sample-size calculation; and test `INSUFFICIENT_EVIDENCE` TTLs of 3 / 6 / 12 months with event-triggered escalation.

## 1. Repository verification and current design position

The current raw `main` documents were read from GitHub before preparing this memo. The authoritative Part 2 section of `docs/PATTERN_PROMOTION_GATE_DESIGN.md` explicitly marks the gate as **design only** and identifies the following values as provisional: the existing OOS floor of 10 as an absolute starting floor; a 95% bootstrap confidence level inherited from existing code; an uncalibrated paper-validation window; no BH-versus-BY choice; a structural but untested economic-rationale heuristic; and a Jaccard redundancy starting point of 0.85 inherited from `match_overlap_prune_threshold` [9]. The same section explicitly declines to set an HHI ceiling or a single family-definition K.

The current v2 design replaces a single family-key gate with a `RedundancyReport`. It separates exact duplicates, same-feature/different-window variants, same-feature/different-threshold variants, same-target variants, cross-ticker variants at multiple granularities, and name-independent trigger-date overlap. It also proposes reporting cross-sectional correlation, temporal clustering, and regime span without yet converting those diagnostics into hard thresholds [9]. This structure is consistent with the evidence and should be preserved.

The repository-specific evidence remains material. The cross-ticker analysis reports 1,737 analyzed patterns, 22 families under one normalization, a median HHI of 0.150, a mean HHI of 0.169, and a descriptive BH/BY pass-rate contrast of 94.9% versus 37.1% [10]. The family-definition stress test reports 22, 62, and 605 families under equally mechanical normalizations and classifies the result as **HIGHLY SENSITIVE** [11]. The real-data final-holdout report describes 7,899 candidates, 3,398 discovered, 1,880 validating, and 1,773 validated, with a median holdout sample of 59, a minimum of 5, and a maximum of 162; it also documents 354 EGAL variants collapsing to 19 base-feature groups [12]. These facts were verified against the current raw repository documents and are not inferred from the user's prompt.

## 2. Same-feature/window redundancy discount

### 2.1 Why a fixed fractional discount is not established

Suppose a base feature is tested at windows of 5, 10, 20, and 60 days. Those variants share the same underlying price series, often share observations, and may be mechanically selected because their trigger sets overlap. Treating them as four independent hypotheses exaggerates the effective search size. Treating them as one hypothesis discards information about whether the effect is stable across horizons. A fixed discount such as 0.5 independent tests per variant does not solve this generally because the dependence can vary with window distance, horizon overlap, trigger frequency, and market regime.

The effective-number-of-tests literature offers a more defensible abstraction. Li et al. describe estimating an effective number of independent tests, `M_eff`, from the correlation structure, often using eigenvalues, and using it to replace the raw number of tests in a multiple-testing threshold [1]. The same paper notes that available `M_eff` formulas have limitations and that permutation methods can better account for dependency. The implication for EGX-Genom is that `M_eff` may be useful as a reporting diagnostic or sensitivity input, but should not be presented as an exact count of independent economic mechanisms.

### 2.2 Candidate approaches

| Approach | How it handles window variants | Strength | Main caveat |
|---|---|---|---|
| Full collapse | All windows of the same base feature become one family/evidence unit | Conservative and simple | Can hide genuine horizon-specific effects and prevents stability reporting. |
| Full independence | Every window is a separate hypothesis | Maximizes nominal discovery power | Overstates evidence when windows share dates and outcomes. |
| Effective-test adjustment | Estimate `M_eff` from return/trigger/test-statistic dependence | Quantifies partial redundancy | Estimator is method-dependent; eigenvalue-based `M_eff` is not exact. |
| Hierarchical testing | Test the base-feature family first, then windows conditionally | Separates "is there a base effect?" from "which horizon?" | Requires a predeclared hierarchy and careful error-control proof. |
| Grouped or cluster-level FDR | Cluster variants by dependence and test clusters plus representatives | Avoids counting every parameter variant equally | Cluster definition and representative selection can introduce bias. |
| Resampling calibration | Preserve window overlap and re-run the full search under nulls | Directly measures realized false promotions | Computationally expensive and requires a credible null generator. |

For the promotion gate, the most defensible evidence representation is a **two-level report**. First, report the base-feature family as the broad claim. Second, report window-specific variants with their own effect estimates, trigger counts, and stability. For multiple-testing purposes, the base family can receive one family-level error budget, while horizon variants are treated as conditional or secondary claims. The final implementation should not silently convert a family of 10 highly correlated windows into 10 independent pieces of corroboration.

### 2.3 Calibration grid

The owner could test the following non-final bands:

| Window relationship | Candidate evidence treatment | What to measure |
|---|---|---|
| Nearly identical trigger sets and overlapping outcome horizons | Treat as one primary evidence unit; retain variants as sensitivity details | Jaccard, directional containment, outcome-window overlap, and test-statistic correlation. |
| Moderate overlap | Estimate partial redundancy through `M_eff` or cluster-level resampling | Effective-test ratio, null false-promotion rate, and stability of representative selection. |
| Distinct trigger dates or non-overlapping horizons | Allow more than one evidence unit, subject to cross-regime and cross-ticker checks | Date overlap, regime span, and incremental OOS information. |

A practical sensitivity study could vary a correlation or similarity linkage rule at 0.70, 0.85, and 0.95, but these values should be applied to the **measured dependence matrix**, not treated as universal semantic thresholds. The important output is how many effective units remain and how often a supposedly independent second window adds incremental OOS information after the first is known.

## 3. Same-feature/threshold redundancy discount

### 3.1 Threshold variants are usually nested, not independent

Top-10% and top-20% triggers based on the same feature and lookback are typically nested or partially nested sets. The top-10% observations are often a subset of the top-20% observations, so their outcomes share observations and their estimated expectancies are correlated. They should not be counted as independent corroboration merely because the thresholds differ.

Unlike window variants, threshold variants can reveal a meaningful dose-response or monotonicity pattern. A consistent effect across several predeclared quantile bins is more informative than a single optimized cutoff, but only if the bins are evaluated as a structured family rather than as isolated discoveries. The same family-level and hierarchical logic therefore applies.

### 3.2 Defensible treatment options

| Treatment | Interpretation | Trade-off |
|---|---|---|
| Primary threshold plus neighboring sensitivity band | Select one threshold without post-hoc optimization and use nearby thresholds as robustness checks | Reduces multiplicity, but depends on the pre-registration rule. |
| Ordered or hierarchical threshold testing | Test whether an effect exists across the feature, then test monotonicity or selected quantile contrasts | Economically interpretable, but requires a defined order and error-control method. |
| Nested-set resampling | Preserve the nesting structure in bootstrap/permutation calibration | Directly handles threshold dependence, but computationally heavier. |
| Effective-test calculation | Estimate the number of independent threshold contrasts from their correlation matrix | Useful diagnostic, but may be unstable with sparse triggers. |
| Treat all quantiles as one family | Simple and conservative | May reduce power when the threshold-response shape is real. |

A reasonable non-final range is to regard a narrow neighborhood of thresholds around a predeclared value as one primary family, while reporting the full threshold-response curve. For example, 10%, 15%, and 20% could be treated as one ordered threshold family, not three independent discoveries. Wider gaps may be reported separately only when trigger dates and outcome windows demonstrate meaningful incremental information.

The key calibration statistic is **incremental information**: after conditioning on the best predeclared threshold or family-level effect, does another threshold produce materially new trigger dates, a new regime, or independent OOS performance? If not, the additional threshold should be treated as a robustness observation, not another unit of evidence.

## 4. Cross-ticker redundancy and granularity stability

### 4.1 The repository's instability finding

The repository's family-definition stress test is directly relevant. Stripping ticker and window suffixes yields 22 families; preserving windows yields 62; preserving exact thresholds yields 605. The mean dominant-ticker share changes from 25.2% to 36.7% to 94.5% [11]. Therefore, choosing one grouping rule and reporting one family count would make a major scientific conclusion depend on an arbitrary representation choice.

### 4.2 What clustering-stability research suggests

Cluster-stability research treats resampling stability as a surrogate for robustness when no gold-standard labels exist. Yu et al. propose nonparametric bootstrap approaches that compare clusterings across resamples, assess individual-cluster stability, and visualize stability profiles [2]. Their review of prior work also notes that Jaccard-based matching can overestimate stability when unmatched or absent clusters are ignored and when maximum matching is asymmetric. This is a useful warning for a trigger-date graph: connected components can look stable merely because a few bridge edges join otherwise different structures.

The defensible practice is therefore not to force one granularity, but to report **multiple linked views** and assess their stability under resampling, time splits, and threshold perturbations.

| View | Purpose | Recommended status |
|---|---|---|
| Exact-condition view | High precision, little collapse | Diagnostic lower-bound on aggregation. |
| Window-preserving view | Separates horizon variants | Secondary family view. |
| Base-feature view | Broad economic tendency | High-level family view, not sole truth. |
| Trigger-date-overlap graph | Name-independent co-occurrence | Primary redundancy diagnostic, subject to sparse-set safeguards. |
| Cross-ticker correlation/regime view | Tests whether ticker breadth is actually independent | Required companion evidence, not an automatic family collapse. |

The report should display family counts, component-size distributions, ticker breadth, dominant-ticker shares, and representative membership across all views. A pattern should be called **granularity-robust** only if its status and representative family persist across reasonable perturbations. If the status changes materially across views, the correct output is "granularity-sensitive," not a forced pass or fail.

### 4.3 Recommended stability experiment

For each candidate grouping rule, use date-block bootstrap or rolling historical subsamples and recompute the family graph. Compare partitions with adjusted Rand index or variation of information, and compare individual family membership using Jaccard overlap. Track the probability that a family survives as a recognizable component, splits, merges, or disappears. Do not use realized expectancy to choose the grouping rule. If no view is stable, preserve the case as a redundancy-sensitive case and avoid treating cross-ticker count as independent evidence.

## 5. HHI ceiling for evidence concentration

### 5.1 What HHI does and does not mean here

HHI is the sum of squared shares. The U.S. Department of Justice describes it as a measure of market concentration, with 1,000–1,800 points considered moderately concentrated and above 1,800 highly concentrated under its cited framework [3]. On a 0–1 scale, these correspond approximately to 0.10–0.18 and >0.18. These are **market-structure thresholds**, not evidence-quality thresholds.

For evidence concentration, HHI answers: "How much of the apparent support comes from a small number of tickers?" It does not answer whether the pattern is causal, whether the tickers are independent, or whether one ticker is more informative because it has more valid observations. The denominator must therefore be declared: matched observations, non-overlapping effective events, or equal ticker weights. These produce different HHIs.

### 5.2 Diagnostic bands rather than a final ceiling

| HHI on ticker evidence shares | Evidence-breadth interpretation | Suggested action for calibration |
|---:|---|---|
| <0.15 | Relatively diffuse evidence under the chosen denominator | Broad-evidence candidate, subject to cross-ticker correlation and regime checks. |
| 0.15–0.25 | Moderate concentration | Report prominently; require sensitivity to equal-ticker weighting and dominant-ticker removal. |
| 0.25–0.40 | High concentration | Treat as fragile cross-sectional evidence; likely require a stronger independent-ticker or leave-one-ticker-out test. |
| >0.40 | Very concentrated | Candidate should generally be labeled ticker-dominated rather than broadly corroborated unless additional evidence offsets the concentration. |

These bands are a calibration envelope, not a recommendation to adopt 0.40. The existing design mentions 0.40 because it mirrors a portfolio-sector concentration posture, but the authoritative v2 document correctly declines to reuse that value as a decided evidence ceiling [9]. A single ticker contributing 80% of matched observations creates an HHI of at least 0.64, even before the remaining shares are added. That should not be described as broad cross-sectional evidence under any ordinary interpretation.

The strongest test is leave-one-ticker-out robustness. Recompute the effect after removing the dominant ticker and separately weight each ticker equally. A pattern that survives both tests is more credible than one that merely has a low raw HHI because many highly correlated tickers contributed the same market episode.

## 6. Bootstrap confidence-level calibration

### 6.1 Coverage is not a free safety margin

A two-sided 90% interval is narrower and more usable than a 95% interval, while a 99% interval is wider and more conservative. If the gate requires the lower confidence bound to be positive, increasing coverage makes promotion harder and reduces false positives at the cost of more false negatives. This is a decision-theoretic trade-off, not a purely statistical ranking.

For dependent returns, block bootstrap is preferable to IID resampling when the block scheme captures serial dependence and overlapping holding periods. Zvingelis shows that block-bootstrap coverage error depends on sample size and block length and that block resampling does not perfectly reproduce the original dependence structure [4]. In small samples, heavy tails, sparse activations, and poorly chosen blocks can make a nominal 95% interval materially miscalibrated.

### 6.2 Candidate levels and uses

| Nominal coverage | Width/power trade-off | Plausible use |
|---:|---|---|
| 90% | Narrower interval; easier promotion; greater false-positive risk | Exploratory or early OOS monitoring, not necessarily final capital promotion. |
| 95% | Central compromise; conventional default | Primary calibration benchmark for a robust promotion gate, conditional on sufficient effective events. |
| 99% | Widest interval; strongest conservatism; substantial power loss | High-materiality or low-frequency promotion, or a sensitivity/safety benchmark. |

A defensible calibration study should evaluate all three levels, at least 1,000 bootstrap replications per case where computationally feasible, and estimate empirical coverage in EGX-preserving simulations. The simulation must preserve blocks, trigger clustering, cross-ticker dependence, and the actual selection/promotion process. The final gate should also record whether the interval is percentile, studentized, or BCa; coverage level alone is not enough.

A useful compromise is to use a 95% lower-bound-positive requirement only after an effective-event floor is met, while displaying 90% and 99% intervals as sensitivity bands. A case with a positive 90% lower bound but a negative 95% lower bound should be labeled borderline, not passed silently. A case whose lower bound remains positive at both 95% and 99% is stronger, but the owner should understand that this may materially reduce discovery power.

## 7. Human-reviewer agreement study for economic rationale

### 7.1 Design objective

The goal is not to prove that a proposed mechanism is true. The goal is to measure whether independent reviewers can apply a predeclared distinction between a **substantive, potentially falsifiable rationale** and a **plausible-sounding but unfalsifiable narrative**. The rubric should therefore evaluate observable textual properties, not reviewer intuition about whether the trading effect "sounds right."

### 7.2 Recommended study design

Create a codebook with binary primary labels and ordinal secondary scores. A suitable primary label is `substantive`, `borderline`, or `insufficient`. Secondary dimensions can score whether the rationale states a mechanism, identifies a measurable implication, specifies conditions under which it should fail, distinguishes correlation from causation, and identifies disconfirming evidence. Reviewers should not see realized OOS performance, ticker identity where unnecessary, or the proposed promotion outcome.

Use a calibration set containing real rationales, deliberately weak examples, and adversarially plausible examples. The examples should be sampled across pattern families and should include borderline cases; otherwise agreement will be inflated by easy items. At least two independent reviewers should code every calibration item. If three or more reviewers participate, use Fleiss' kappa or Krippendorff's alpha rather than averaging pairwise Cohen kappas [5].

After independent coding, conduct an adjudication meeting, revise the codebook only through a versioned change log, and then re-code a fresh holdout sample using the final rubric. The holdout must not be used to tune the rubric. Cofie et al. recommend a shared framework, at least two coders, trained or experienced coders, dialogue and consensus, expert conflict resolution, and applying the resulting codebook to the remaining material [6].

### 7.3 Agreement metrics and sample-size calibration

| Element | Recommended analysis |
|---|---|
| Two reviewers, nominal labels | Cohen's kappa plus raw agreement and category counts. |
| Three or more reviewers | Fleiss' kappa or Krippendorff's alpha; report pairwise agreement as a diagnostic. |
| Ordered labels (`substantive` / `borderline` / `insufficient`) | Weighted kappa or ordinal Krippendorff alpha as a secondary analysis. |
| Multiple labels per rationale | Krippendorff's alpha or per-dimension kappa, with missing-code handling. |
| Rare categories | Report prevalence and confidence intervals; do not rely on kappa alone. |
| Sample size | Power analysis based on expected kappa, baseline agreement, category prevalence, α, and desired power. |

Bujang and Baharum show that kappa sample-size requirements can vary widely with expected effect size and marginal rating frequencies, and unequal marginals can more than double the required sample [13]. Consequently, there is no defensible universal "50 rationales is enough" rule. As a study-planning range, the owner could test 50, 100, and 200 calibration items, but the final number should come from a power calculation and a minimum count in each label category.

The gate should not use reviewer agreement as a truth claim. If agreement is low, the appropriate response is to improve the rubric, split ambiguous dimensions, or route the case to expert adjudication. It is not appropriate to lower the standard until agreement becomes convenient.

## 8. `INSUFFICIENT_EVIDENCE` staleness and abandonment

### 8.1 Current repository position

The authoritative v2 design treats `INSUFFICIENT_EVIDENCE` as non-terminal and allows the same case to re-enter the same stage once more evidence exists. It explicitly identifies newly required post-run OOS evidence as rate-limited by real calendar time and says this cannot be rushed [9]. The repository also has a `DecayMonitor` pattern in which weakening is recorded rather than silently deleting evidence [9].

This is a sound distinction: insufficient evidence is not the same as failed evidence. However, a non-terminal state without a time or activity boundary can become an indefinite backlog and can make the registry appear healthier than it is.

### 8.2 Candidate TTL and review bands

The reviewed model-risk guidance emphasizes that monitoring and validation should be risk-based and tailored to model materiality; it does not impose one universal periodicity or annual validation rule [7] [8]. That supports a governance range rather than a universal TTL.

| Pending duration or condition | Candidate governance action |
|---|---|
| 0–3 months | Keep pending if the required evidence window is actively accumulating; require next-review date and evidence plan. |
| 3–6 months without meaningful new evidence | Mandatory re-review of data availability, frozen definition, and whether the case remains worth carrying. |
| 6–12 months without meeting the evidence plan | Auto-expire to `ABANDONED_PENDING` or require explicit owner renewal with a new deadline. |
| 12+ months or two missed review cycles | Require a new intake/review rather than indefinite resurrection of the old case. |
| Material data, universe, feature, threshold, or target change | Close the old case and open a new versioned case; do not refresh the old case in place. |
| Evidence becomes available but fails a hard criterion | Move to `REJECTED`, not stale pending. |

These are candidate bands for testing, not final settings. The exact TTL should reflect the pattern's horizon and expected activation rate. A 60-day signal may reasonably need a longer calendar allowance than a daily signal, but both should have a maximum review interval. The pending record should store `last_evidence_at`, `next_review_at`, `evidence_plan`, `missed_review_count`, and `expiry_reason`.

A robust policy is **calendar TTL plus event-triggered review**. Re-review immediately if the data source changes, the covered ticker universe changes materially, the pattern definition is altered, the expected activation rate collapses, or the market regime changes enough to invalidate the evidence plan. If the case expires, preserve its complete lineage and permit reopening only through an explicit new review, not silent continuation.

## 9. Consolidated calibration matrix

| Open item | Evidence-backed range or method for owner testing | Important caveat |
|---|---|---|
| Same-feature/window redundancy | Effective-test or hierarchical/grouped treatment; sensitivity across dependence cutoffs such as 0.70 / 0.85 / 0.95; do not use a universal fractional discount | `M_eff` is a summary, not a count of true mechanisms; resampling is the benchmark. |
| Same-feature/threshold redundancy | Treat nested thresholds as one ordered family; use primary-plus-neighbor sensitivity or nested-set resampling | Threshold response can contain real information, but optimized cutoffs are selection-biased. |
| Cross-ticker granularity | Report exact, window-preserving, and base-feature views side by side; assess bootstrap/rolling stability | The repository has already shown 22/62/605 family instability. |
| HHI evidence concentration | Diagnostic bands <0.15, 0.15–0.25, 0.25–0.40, >0.40; test leave-one-ticker-out and equal-ticker weighting | DOJ HHI thresholds are market-concentration references, not evidence-quality laws. |
| Bootstrap CI coverage | Compare 90%, 95%, 99%; central benchmark 95% only after effective-event and block-length calibration | Nominal coverage may fail in small, dependent, heavy-tailed data. |
| Economic rationale review | Two-stage independent coding with 2+ reviewers; Cohen/Fleiss/Krippendorff as appropriate; power-based sample size | Agreement measures rubric reproducibility, not economic truth. |
| `INSUFFICIENT_EVIDENCE` TTL | Test 3-, 6-, and 12-month pending/review bands plus event-triggered escalation | No universal TTL exists; align to horizon, activation rate, and materiality. |

## 10. Recommended calibration experiments before final decisions

The first experiment should build a dependence-preserving candidate simulator. It should regenerate window and threshold variants from the same EGX time series, preserve nested trigger sets and overlapping outcome windows, and run the full promotion procedure under null and planted-effect conditions. Compare raw test counts, effective-test estimates, cluster-level procedures, and resampling-calibrated procedures by realized false-promotion rate and power.

The second experiment should produce a multi-granularity stability report. Recompute exact, window-preserving, and base-feature groupings on date-block bootstrap samples and rolling time slices. Measure partition stability, family survival, splits, merges, dominant-ticker share, and leave-one-ticker-out expectancy. The goal is not to select the most flattering view; it is to identify which conclusions are invariant and to label the rest as granularity-sensitive.

The third experiment should calibrate HHI and confidence intervals jointly. For each evidence denominator, compare raw matched-observation HHI, equal-ticker HHI, and effective-event HHI. Cross these with 90%, 95%, and 99% block-bootstrap lower bounds, varying block length and effective-event floors. Report how often a pattern passes only because one ticker dominates or because a nominal interval is under-covered.

The fourth experiment should run the reviewer study as a blinded reliability exercise. Pre-register the rubric, draw a stratified calibration sample, independently code, calculate agreement with confidence intervals, adjudicate, freeze the codebook, and then test on a holdout sample. Store rubric version and reviewer decisions in the audit trail.

The fifth experiment should replay pending-case governance on historical data. Compare 3-, 6-, and 12-month TTLs, missed-review limits, and event-triggered escalation. Measure backlog size, time-to-evidence, stale-case rate, false abandonment, and the proportion of expired cases that would have later satisfied the evidence plan. Preserve cases rather than deleting them so the TTL policy can be audited.

## 11. References

[1]: https://pmc.ncbi.nlm.nih.gov/articles/PMC3325408/ "Li et al. (2011), Evaluating the Effective Numbers of Independent Tests and Significant p-Value Thresholds in Commercial Genotyping Arrays and Public Imputation Reference Datasets"

[2]: https://par.nsf.gov/servlets/purl/10148630 "Yu et al. (2018), Bootstrapping Estimates of Stability for Clusters, Observations and Model Selection"

[3]: https://www.justice.gov/atr/herfindahl-hirschman-index "U.S. Department of Justice, Herfindahl-Hirschman Index"

[4]: https://www.ssc.wisc.edu/~bhansen/718/zvingelis.pdf "Zvingelis, On Bootstrap Coverage Probability with Dependent Data"

[5]: https://pmc.ncbi.nlm.nih.gov/articles/PMC3900052/ "McHugh (2012), Interrater Reliability: The Kappa Statistic"

[6]: https://pmc.ncbi.nlm.nih.gov/articles/PMC9099179/ "Cofie, Braund, and Dalgarno (2022), Eight Ways to Get a Grip on Intercoder Reliability Using Qualitative-Based Measures"

[7]: https://www.federalreserve.gov/frrs/guidance/supervisory-guidance-on-model-risk-management.htm "Federal Reserve, Supervisory Guidance on Model Risk Management"

[8]: https://www.occ.gov/news-issuances/bulletins/2026/bulletin-2026-13.html "OCC Bulletin 2026-13, Model Risk Management: Revised Guidance"

[9]: https://raw.githubusercontent.com/shadygad01/EGX-Genom/main/docs/PATTERN_PROMOTION_GATE_DESIGN.md "EGX-Genom, Pattern Promotion Gate Design and Audit Report — Mission 3 v2"

[10]: https://raw.githubusercontent.com/shadygad01/EGX-Genom/main/docs/PATTERN_CROSS_TICKER_FAMILY_COLLAPSE.md "EGX-Genom, Cross-Ticker Family-Collapse Analysis"

[11]: https://raw.githubusercontent.com/shadygad01/EGX-Genom/main/docs/PATTERN_FAMILY_DEFINITION_STRESS_TEST.md "EGX-Genom, Family Definition Stress Test"

[12]: https://raw.githubusercontent.com/shadygad01/EGX-Genom/main/docs/PATTERN_DISCOVERY_FINAL_HOLDOUT.md "EGX-Genom, Pattern Discovery — Real-Data Final Holdout Run"

[13]: https://riviste.unimi.it/index.php/ebph/article/view/17614 "Bujang and Baharum (2017), Guidelines of the Minimum Sample Size Requirements for Kappa Agreement Test"

## Non-decisions

This memo does not select a same-window discount, same-threshold discount, family granularity, HHI ceiling, bootstrap coverage level, reviewer-agreement cutoff, or `INSUFFICIENT_EVIDENCE` TTL. It provides calibration ranges, study designs, and decision trade-offs for the product owner. The repository remains design-only for this gate; no production code, registry, validation status, or `PromotionCase` record was changed.

---

# Part 2 — Reconciliation with `PATTERN_PROMOTION_GATE_DESIGN.md` v2.2 §14

This memo completes coverage of the 12 provisional gates in v2.2 §14. Its
first memo (`PATTERN_PROMOTION_GATE_CALIBRATION_RESEARCH.md`) covered 5;
this memo covers the remaining 7.

| v2.2 §14 provisional gate | This memo's section | What the memo adds | Still open? |
|---|---|---|---|
| Same-feature/window redundancy dimension | Part 1 §2 | Explains why a fixed fractional discount (e.g. "count each variant as 0.5 tests") has no literature basis; proposes effective-number-of-tests (`M_eff`, eigenvalue-based) or hierarchical/grouped testing as principled alternatives, with an explicit caveat that `M_eff` is a diagnostic, not an exact count; proposes a two-level report (base-feature family + window-specific variants) rather than either full collapse or full independence | **Yes.** No discount rule adopted. v2.2 §14's named dependency ("a defined collapse/discount rule") is not resolved — the memo supplies candidate *methods* to build that rule from, not the rule itself. |
| Same-feature/threshold redundancy dimension | Part 1 §3 | Explains threshold variants are typically nested/partially-nested sets, not independent; proposes treating a narrow neighborhood of thresholds as one ordered family while reporting the full threshold-response curve; introduces "incremental information after conditioning on the primary threshold" as the calibration statistic | **Yes.** No discount rule adopted; same open dependency as above. |
| Cross-ticker Variant A/B redundancy dimensions | Part 1 §4 | Directly engages the repository's own 22/62/605 instability finding; recommends reporting exact/window-preserving/base-feature views side by side rather than collapsing to one, backed by cluster-stability literature (bootstrap/subsampling stability profiles); proposes a concrete stability experiment (adjusted Rand index / variation of information across date-block bootstrap resamples) | **Partially resolved as a *methodological* recommendation** ("report multiple granularities side by side" — one of v2.2 §14's own two named acceptable resolutions), but the granularity-stability *calibration* itself (the stability experiment in Part 1 §4.3) has not been run. Still PROVISIONAL per v2.2 §14 until that experiment exists. |
| Ticker concentration (HHI) ceiling | Part 1 §5 | Distinguishes DOJ market-concentration HHI bands (0.10–0.18 moderate, >0.18 high) from evidence-concentration use; proposes diagnostic bands (<0.15 / 0.15–0.25 / 0.25–0.40 / >0.40) explicitly as a calibration envelope, not an adopted ceiling; explicitly flags that the existing 0.40 sector-concentration constant should not be reused for evidence without justification (consistent with v2.2 §14's own "none proposed" status); recommends leave-one-ticker-out and equal-ticker-weight robustness checks | **Yes.** No ceiling adopted — the memo explicitly declines to recommend 0.40 or any other single value. v2.2 §14's "a calibrated ceiling number — none proposed" dependency is unresolved. |
| Bootstrap CI coverage level | Part 1 §6 | Frames coverage as a decision-theoretic trade-off (width/power vs. false-positive risk), not a pure statistics question; cites block-bootstrap coverage-error dependence on block length and sample size; proposes comparing 90%/95%/99% with a "borderline" label for cases where the sign flips between coverage levels, rather than silently passing at one nominal level | **Yes.** No coverage level adopted (95% remains a declared default per the existing design, not a calibrated choice). v2.2 §14's "real paper-validation history correlating coverage choice with promotion accuracy (does not exist yet)" dependency is unresolved. |
| Economic-rationale substance bar | Part 1 §7 | Supplies a full study design (not a result): codebook with primary/secondary labels, blinded reviewers, calibration set with adversarial examples, Cohen's/Fleiss'/Krippendorff's agreement statistics depending on reviewer count, adjudication-then-holdout protocol, power-based sample-size guidance (citing evidence that unequal marginals can more than double required sample size) | **Yes.** No study has been run — this is a design for one. v2.2 §14's "human-reviewer agreement study (zero contamination risk, achievable independently)" dependency now has a concrete design to execute, but execution itself is new work not started here. |
| `INSUFFICIENT_EVIDENCE` staleness/abandonment limit | Part 1 §8 | Proposes a governance band (0–3mo keep-pending / 3–6mo mandatory re-review / 6–12mo auto-expire / 12+mo require new intake), explicitly non-universal and horizon-dependent; introduces a concrete stale-case data model (`last_evidence_at`, `next_review_at`, `evidence_plan`, `missed_review_count`, `expiry_reason`); proposes calendar-TTL-plus-event-trigger as the robust pattern, with lineage preserved on expiry (never deleted) | **Yes.** No TTL adopted. v2.2 §14's "a declared maximum dwell-time or retry count — none proposed yet" dependency is unresolved — the memo supplies candidate bands to declare from, not a declaration. |

## What this reconciliation does NOT do

- Does not select a final value for any threshold in either memo's table.
- Does not modify `PATTERN_PROMOTION_GATE_DESIGN.md` itself — v2.2 §14's
  status table remains unedited; this is a separate, additive research
  artifact, same posture as Part 1 of this research effort.
- Does not change v2.2's `Implementation Readiness` classification
  (`READY_WITH_BLOCKING_DEPENDENCIES`) — every dependency this memo
  touches remains named-but-unresolved, exactly as before.
- Does not commit to running any of the five calibration experiments this
  memo's §10 proposes (dependence-preserving candidate simulator;
  multi-granularity stability report; joint HHI/CI calibration; blinded
  reviewer-agreement study; pending-case governance replay). Running any
  of them is new work requiring separate, explicit instruction.

## Coverage summary — both memos combined

All **12** provisional gates in v2.2 §14 now have evidence-backed
candidate ranges or concrete study designs to calibrate from (5 from the
first memo, 7 from this one). **Zero** thresholds have been selected,
adopted, or hardcoded anywhere in the repository. v2.2's own
`READY_WITH_BLOCKING_DEPENDENCIES` classification and its explicit BH-vs-BY
policy-decision blocker are unchanged by either memo.
