# Pattern Promotion Gate — Calibration Research (Manus) & Reconciliation

## Provenance

- **Part 1** below is Manus AI's calibration-research memo, commissioned by
  the user to research defensible ranges for the provisional thresholds
  `docs/PATTERN_PROMOTION_GATE_DESIGN.md`'s v2.2 specification declares but
  does not calibrate. It is saved here **verbatim**, exactly as delivered
  (received 2026-08-13, `Reference date: 13 August 2026` per the memo's own
  header) — no wording, numbers, or citations have been edited. Its
  repository-specific factual claims (candidate/pattern counts, BH/BY pass
  rates, family-collapse figures, holdout sample statistics) were checked
  against the actual repository documents it cites
  (`PATTERN_DISCOVERY_FINAL_HOLDOUT.md`, `PATTERN_CROSS_TICKER_FAMILY_COLLAPSE.md`,
  `PATTERN_FAMILY_DEFINITION_STRESS_TEST.md`) before this file was created,
  and all of them matched exactly.
- **Part 2** is a reconciliation note, written by Claude Code (not Manus),
  mapping the memo's findings onto the exact provisional-threshold rows in
  `PATTERN_PROMOTION_GATE_DESIGN.md`'s v2.2 §14. It is analysis only — it
  does not select, adopt, or hardcode any threshold value anywhere in this
  repository, and it does not modify `PATTERN_PROMOTION_GATE_DESIGN.md`
  itself.
- **This document is external research input, not a decision.** Every
  threshold discussed remains PROVISIONAL exactly as v2.2 §14 already
  states; nothing here changes that status.

---

# Part 1 — Manus AI calibration-research memo (verbatim)

# Pattern-Promotion Gate Calibration Research

**Repository:** `shadygad01/EGX-Genom`
**Scope:** Long-only EGX30 equity pattern discovery, promotion, paper validation, and live monitoring
**Purpose:** Evidence-backed ranges and trade-offs for product-owner calibration; **not a final threshold decision**
**Prepared by:** Manus AI
**Reference date:** 13 August 2026

## Executive summary

The literature does not support a single universal value for any of the requested thresholds. The strongest conclusion is methodological: the gate should calibrate its settings against the platform's own null simulations, effective-event counts, and observed dependence structure, while treating published rules of thumb as prior ranges rather than as validated constants.

For multiple testing, **BH is not automatically invalid under correlation**. Benjamini–Hochberg controls FDR under independence and under an important class of positive dependence, commonly expressed through positive regression dependence on the subset of true nulls (PRDS) [1] [2]. Overlapping engineered features and overlapping trigger dates are plausibly positive, but pairwise positive correlation alone does not establish PRDS. **BY provides FDR control under arbitrary dependence**, but its harmonic-number penalty can be severe when the family is large [2]. In this repository, the latest public evidence is unusually informative: a descriptive replay reports 1,683/1,773 passes for BH versus 657/1,773 for BY at α=0.05, and the real-data run reports 7,899 candidates with 3,398 surviving the existing BH discovery stage. Those figures show a material power/retention difference; they do **not** identify the realized Type-I error of BH.

For trigger-date overlap, duplicate-detection literature treats Jaccard as a useful set-similarity measure but does not establish a universal "duplicate" cutoff. Thresholds are application- and data-dependent, and the threshold can become unstable as the dataset grows or duplicate clusters become transitive [5]. A conservative near-duplicate application may use approximately 0.90 or higher, whereas 0.70–0.85 generally represents looser similarity screening rather than near-certain identity [6]. For trading patterns, raw trigger-date Jaccard should be treated as a **redundancy flag**, not as proof that two patterns are statistically non-independent. Sparse sets, common market regimes, and unequal set sizes can all distort its interpretation.

For OOS evidence, a minimum of 30–50 effective trades/events is best viewed as an **early-warning floor**, not a trust threshold. A more defensible research range is approximately 100–200 effective, non-overlapping event instances when the signal is intended to support capital allocation, subject to effect size, variance, costs, and cross-event dependence. The repository's own final-holdout report is a warning against relying on nominal observation counts: the median holdout sample was 59, with a minimum of 5 and a maximum of 162, while 1,773 patterns passed the final holdout. That is evidence that "passes a holdout" and "has enough independent evidence" are different gates.

For paper validation, the literature provides stronger evidence for the need for a genuinely forward period than for a universal desk rule. A large Quantopian cohort study used at least six months of OOS performance and found weak links between in-sample and OOS performance and a larger backtest/OOS gap for more heavily backtested strategies [7]. A practical calibration range for EGX daily signals is therefore **3–6 months and at least 30–50 live-forward signal instances**, with the longer calendar period or higher event count controlling. Sparse signals should remain in paper validation until they accumulate a predeclared effective-event count, even if the calendar minimum has elapsed.

For revalidation, no credible source supports one universal monthly, quarterly, or N-trade cadence. The defensible industry-practice pattern is **continuous monitoring plus periodic formal review**. A reasonable range for product-owner consideration is daily/weekly metric capture, monthly surveillance, and quarterly formal revalidation, with event-triggered review immediately after a sign flip, material drawdown, cost or liquidity breach, or deterioration over a rolling effective-event window. Cadence should be faster for high-turnover or rapidly changing signals and slower only where the economic mechanism and holding period justify it.

> **Bottom line:** use the following as candidate calibration bands for controlled sensitivity testing, not as adopted production values: BH with dependence diagnostics or a hybrid BH/BY sensitivity check; Jaccard 0.70/0.85/0.90 as a three-point redundancy grid; OOS floors of 30–50 effective events for initial evidence and 100–200 for stronger trust; paper-forward validation of 3–6 months plus 30–50 live events; and monthly monitoring with quarterly formal review, overridden by event-based alarms.

## 1. Repository context and why calibration matters here

The public `main` branch of EGX-Genom was reviewed before preparing this memo. The repository page reported a latest visible commit `a6c7b0c` and 286 commits at review time. The working tree could not be refreshed through a shell clone because the sandbox shell was unable to resolve `github.com`; therefore, repository-specific facts below are taken from the public repository page and current raw documents, and the memo is saved under the local working directory created for this task. No production code or validation result was changed.

The repository's own real-data final-holdout report is the most important local calibration evidence. It describes a single EGX30-covered run over approximately 4.6 years and 14 covered tickers: 7,899 candidates were generated, 3,398 reached `DISCOVERED`, 1,880 reached `VALIDATING`, and 1,773 reached `VALIDATED`. The report explicitly says that this volume should not be treated as evidence of 1,773 independent tradeable inefficiencies. It also reports that EGAL contributed 354 validated patterns which collapsed to 19 base-feature groups after window suffixes were removed, with one underlying tendency represented by 131 window/threshold variants [10].

The repository's family-collapse analysis reports that, on 1,773 patterns, BH passed 1,683 (94.9%) while BY passed 657 (37.1%) at α=0.05. It correctly labels this as descriptive rather than as a choice of correction [11]. Its family-definition stress test is also relevant to any Jaccard threshold: equally mechanical normalization choices produced 22, 62, or 605 families, and the report classifies the result as **highly sensitive** [12]. This is direct evidence that candidate identity and redundancy definitions are first-order calibration inputs, not cosmetic implementation details.

## 2. BH versus BY under correlated candidate families

### 2.1 What the statistical literature actually says

Benjamini and Hochberg introduced the step-up procedure for controlling the false discovery rate under independence and discussed its suitability for many applied multiple-testing problems [1]. Benjamini and Yekutieli extended the analysis to dependency. Their result is not simply "correlation breaks BH"; rather, they identify a positive-dependence condition under which BH remains valid and provide a procedure controlling FDR under arbitrary dependence [2]. The positive-dependence condition is commonly referred to as PRDS on the subset of true nulls.

> "Positive regression dependency on each one from a subset" is the relevant dependence framework in the Benjamini–Yekutieli analysis; arbitrary dependence requires the more conservative correction [2].

For EGX-Genom, overlapping features and overlapping trigger dates make dependence expected. However, the product owner should distinguish three statements:

| Statement | Defensible? | Reason |
|---|---:|---|
| The tests are independent | No | Overlapping features, dates, horizons, and ticker relationships contradict this assumption. |
| The tests are positively pairwise correlated | Plausible | Shared windows and market regimes likely induce positive association, but it must be measured. |
| The p-values satisfy PRDS | Not established by pairwise correlation alone | PRDS is a stronger structural condition than positive pairwise correlation. |
| BY controls FDR under arbitrary dependence | Yes, subject to the procedure's assumptions | This is the principal robustness advantage of BY [2]. |
| BH has a known Type-I-error inflation in this EGX family | No | The inflation depends on the joint null distribution, family construction, p-value validity, and selection pipeline. |

The finance literature reinforces the need to treat a large correlated strategy pool as a multiple-testing problem. Harvey and Liu explain that applying a single-test threshold to thousands of managers or strategies can create massive Type-I errors because some strategies will look good by luck; they propose bootstrap-based calibration of Type-I and Type-II errors specific to the data and testing procedure [3]. Bailey, Borwein, López de Prado, and Zhu likewise show that ordinary holdout methods can be unreliable in investment backtests and propose combinatorially symmetric cross-validation to estimate the probability of backtest overfitting [4].

### 2.2 Practical cost of switching from BH to BY

BY modifies the BH critical line by a harmonic-number factor:

\[
q_{BY} = \frac{q_{BH}}{H_m}, \qquad H_m=\sum_{i=1}^{m}\frac{1}{i}.
\]

For large families, `H_m` grows approximately as `ln(m)+γ`. The resulting penalty is not a small correction. Approximate values are shown below.

| Number of tests `m` | Harmonic factor `H_m` | BY critical level as fraction of BH | Interpretation |
|---:|---:|---:|---|
| 100 | 5.19 | 19.3% | BY is roughly 5.2× more stringent in the critical line. |
| 1,000 | 7.49 | 13.4% | BY is roughly 7.5× more stringent. |
| 7,899 | ~9.55 | 10.5% | The repository-scale family would face roughly a 9.6× critical-line penalty. |

The expected cost is primarily **power loss and missed discoveries**, not a directly knowable reduction in realized Type-I error. The repository's observed BH/BY pass counts illustrate the possible operational effect: 94.9% versus 37.1% in one descriptive family-collapse replay [11]. That contrast is much larger than the harmonic penalty alone would predict because the empirical p-value distribution, family sizes, and candidate structure interact with the step-up procedure.

The correct question for this platform is therefore not "Is BY safer?"—it is "How much power does BH retain under the EGX candidate-generating mechanism while keeping realized false discoveries within the product owner's tolerance?" A reproducible answer requires a null simulation that preserves the platform's dependence structure: block or stationary bootstrap over dates, feature-window overlap, ticker cross-correlation, horizon overlap, candidate-family construction, and every promotion-stage selection rule. The null should report realized FDR, false discovery proportion distribution, discovery count, and the fraction of null runs with at least one promoted pattern.

### 2.3 Defensible calibration ranges for the owner to test

| Candidate policy | Evidence basis | Main benefit | Main risk / condition | Suggested use in calibration study |
|---|---|---|---|---|
| BH at target FDR | Valid under independence and certain positive dependence such as PRDS [1] [2] | Much higher power than BY in large correlated pools | PRDS and valid p-values are not established automatically | Baseline if dependence diagnostics and EGX-preserving null simulations are favorable. |
| BY at target FDR | Controls FDR under arbitrary dependence [2] | Conservative protection when dependence is structurally uncertain | Can be very underpowered in large families | Safety benchmark and sensitivity bound, not necessarily the sole production rule. |
| BH with dependence diagnostics + stricter downstream evidence | Finance literature emphasizes data-specific Type-I/II calibration [3] | Retains power while adding independent safeguards | Requires careful null and OOS design | Strong candidate architecture for human review. |
| Two-track BH/BY reporting | Compare both procedures and block promotion when conclusions diverge materially | Makes dependence sensitivity visible | More governance complexity | Useful while EGX null evidence is still being accumulated. |
| Resampled or bootstrap FDR calibration | Calibrates to empirical covariance and selection pipeline [3] [4] | Directly estimates realized error under the platform's dependence | Computationally heavier; model choices matter | Recommended research direction before declaring BH safe. |

A product owner could reasonably test a **BH primary / BY safety comparison** at nominal FDR values such as 1%, 2.5%, and 5%, but this memo does not select one. The key acceptance criterion should be the realized null false-discovery distribution and the number of economically distinct promoted families, not the nominal method name alone.

## 3. Jaccard trigger-date overlap as a redundancy flag

### 3.1 What duplicate-detection literature supports

Jaccard similarity is a standard measure for comparing finite sets:

\[
J(A,B)=\frac{|A\cap B|}{|A\cup B|}.
\]

Near-duplicate detection research generally assumes that a similarity threshold is specified for the application; its contribution is often to find all pairs above that threshold efficiently, not to claim that one threshold is universally correct [5]. Draisbach and Naumann emphasize that the similarity measure depends on the data and error process, while the threshold can depend on dataset size and can change as transitive duplicate clusters grow [6].

Examples in the literature and practice span a wide range. A threshold near 0.90 is common when the desired class is conservative near-identity, while 0.70–0.85 is more suitable for broad candidate retrieval or looser near-similarity. These values should not be transported mechanically from text documents to trading events. Trigger-date sets have different semantics: the same market-wide event can cause many candidates to fire, and two patterns may share dates because of regime concentration rather than because they encode the same mechanism.

### 3.2 Transfer to trading-pattern trigger dates

A Jaccard threshold can reasonably be used to **flag possible redundancy**, provided it is not interpreted as proof of independence or identity. The following distortions should be measured:

| Distortion | Effect on raw Jaccard | Implication for EGX patterns |
|---|---|---|
| Sparse trigger sets | One or two shared dates can dominate the ratio | Require minimum set sizes and report intersection count alongside Jaccard. |
| Unequal set sizes | A small pattern can be almost contained in a large one with modest Jaccard | Add directional containment, e.g. `|A∩B|/min(|A|,|B|)`. |
| Market-wide shock dates | Many unrelated patterns fire together | Compare against a date-block null or market-event-adjusted Jaccard. |
| Overlapping holding horizons | Trigger dates may produce overlapping return observations | Redundancy should be based on non-overlapping effective outcome windows as well as trigger dates. |
| Calendar and ticker imbalance | Different opportunity counts change the base rate | Stratify calibration by ticker, horizon, and trigger frequency. |
| Multiple engineered variants | Shared dates may be expected from construction | Use Jaccard as one feature in a family graph, not as the family definition by itself. |

### 3.3 Candidate threshold grid

| Jaccard flag | Interpretation | Reasonable role |
|---:|---|---|
| 0.70 | Broad similarity / candidate retrieval | Use to create a sensitivity envelope; likely too permissive for automatic redundancy collapse. |
| 0.85 | Strong overlap | Plausible primary review flag if minimum trigger counts and containment diagnostics pass. |
| 0.90 | Conservative near-duplicate | Plausible automatic redundancy flag where the cost of collapsing distinct evidence is high. |
| 0.95 or exact match | Near identity | Useful as a high-precision duplicate control, but likely misses economically similar variants. |

The best transfer from duplicate detection is not "choose 0.90"; it is the practice of **calibrating the threshold on labeled pairs and monitoring threshold stability as the dataset grows** [6]. For EGX-Genom, the owner should build a small adjudicated sample of candidate pairs, label them as same underlying signal / related but distinct / independent, and report precision-recall at 0.70, 0.85, 0.90, and 0.95. The family-definition stress test already shows why this matters: mechanically legitimate identity rules changed the family count by an order of magnitude [12].

A particularly defensible design is a two-dimensional redundancy rule: flag pairs when Jaccard exceeds a grid threshold **and** either the smaller trigger set is substantially contained in the larger or the paired outcome windows overlap materially. Retain the graph and connected components for audit; do not silently delete candidates. Select a representative only after applying a predeclared rule independent of realized OOS performance, such as simpler feature expression, lower turnover, or earlier registry timestamp.

## 4. Minimum OOS sample size before trusting expectancy

### 4.1 Why "number of trading days" is not enough

Expectancy is estimated from realized events, not from calendar days alone. If a pattern fires 10 times per year, five years may still produce too few events. Conversely, 300 highly overlapping daily triggers may contain far fewer than 300 independent pieces of evidence. The effective sample size should therefore discount clustered dates, overlapping holding windows, same-shock co-movement, and repeated variants of one underlying candidate.

The repository's holdout evidence illustrates this distinction. The latest final-holdout report states that the median holdout sample size among validated patterns was 59, with a minimum of 5 and maximum of 162, even though 1,773 patterns passed. The report's conclusion is that these results are not individually trustworthy until the correlated-candidate problem is remediated [10]. This is not proof that 59 is always insufficient; it is proof that a nominal holdout count does not settle the trust question.

### 4.2 Evidence-backed range, not a universal rule

The literature does not establish a universal minimum trade count for all strategies. Practitioner discussions often use 30 trades as a bare statistical starting point, 50 as a more useful early floor, and 100–200 or more for a more stable estimate. These are heuristics. The correct minimum depends on the minimum economically meaningful expectancy, return variance, hit-rate, tail risk, transaction costs, and the desired confidence interval.

| OOS evidence band | Effective event count | Calendar guardrail for daily EGX signals | Interpretation |
|---|---:|---:|---|
| Preliminary | 30–50 | At least 3–6 months where feasible | Enough to detect gross failure modes and estimate a rough sign; not enough for strong trust in a noisy expectancy. |
| Intermediate | 50–100 | At least 6–12 months for sparse or regime-sensitive patterns | Reasonable stage for a cautious paper-validation decision if confidence intervals and costs are favorable. |
| Stronger promotion evidence | 100–200+ | At least 12 months or a full relevant regime cycle where practical | More defensible for capital allocation, especially for low-Sharpe or tail-sensitive signals. |
| Sparse-pattern exception | Fewer than 30 | Calendar minimum alone is not sufficient | Remain research/paper-only; report uncertainty rather than forcing a promotion decision. |

For expectancy, the gate should report a confidence interval or a block-bootstrap interval, not only the point estimate. A pattern whose lower confidence bound is negative should not be treated the same as a pattern with positive point expectancy but only five observations. For correlated signals, count **effective events**, not every ticker-date activation. The owner may also choose an event floor separately by horizon, because 5-day overlapping outcomes do not supply the same effective information as 60 independent non-overlapping outcomes.

## 5. Paper-validation / forward-testing window

### 5.1 What the evidence says

Bailey et al. show that ordinary holdout methods can be unreliable for investment backtests and propose CSCV to estimate the probability of backtest overfitting [4]. Wiecki et al. analyze 888 algorithmic trading strategies with **at least six months of OOS performance** and find that common in-sample metrics, including Sharpe ratio, have weak predictive value for OOS performance; they also find a larger backtest/OOS discrepancy when more backtesting was performed [7]. This supports a meaningful live-forward period, but it does not establish six months as a universal industry minimum.

### 5.2 Candidate ranges for EGX daily signals

| Forward-testing band | Calendar period | Minimum live-forward events | Possible interpretation |
|---|---:|---:|---|
| Fast-screening paper test | 1–3 months | 20–30 | Operational and implementation check only; not sufficient for capital trust. |
| Standard paper-validation candidate | 3–6 months | 30–50 | Defensible minimum range for a liquid, reasonably frequent daily signal, provided the signal remains unchanged and costs are modeled. |
| Conservative promotion candidate | 6–12 months | 50–100+ | Better aligned with the six-month OOS cohort evidence and with seasonality/regime exposure. |
| Sparse or slow signal | 12–24 months or until event floor | 30–100+ depending on variance | Calendar period should extend until enough effective events are observed. |

The period should be measured from a **frozen signal specification**. Any change to features, thresholds, holding horizon, universe, execution convention, or risk overlay should create a new version and restart or partially restart paper validation. Otherwise the forward sample becomes a moving target and loses its evidentiary meaning.

The forward test should log every eligible activation, including non-trades caused by liquidity, concentration, or risk constraints. Selective reporting of only executed winners would bias the estimate. A paper-to-live promotion review should compare expected and realized activation rates, slippage, turnover, hit rate, expectancy, drawdown, and regime mix, with all metrics shown against predeclared tolerances.

## 6. Revalidation and staleness cadence

### 6.1 What is and is not established

The reviewed literature emphasizes dependence, overfitting, and OOS degradation, but it does not prescribe one universal "monthly" or "quarterly" revalidation schedule for all quantitative signals. A fixed cadence is a governance choice that should be matched to the signal's half-life, turnover, holding period, and exposure to changing market structure.

The repository already contains a decay-monitor concept that tracks a live sample floor, hit-rate drop, and sign-flip leading to a weakening state rather than silent deletion [9]. That structure is compatible with a layered cadence: continuous measurement, a regular surveillance review, and event-triggered escalation.

### 6.2 Candidate cadence ranges

| Layer | Candidate range | Purpose |
|---|---|---|
| Metric capture | Every eligible activation; daily aggregation where data permits | Preserve a complete outcome ledger and avoid survivorship through selective observation. |
| Surveillance | Weekly or monthly | Detect activation-rate changes, cost/slippage drift, hit-rate deterioration, drawdown, and regime concentration. |
| Formal revalidation | Monthly or quarterly | Re-estimate expectancy, confidence intervals, effective event count, OOS sign, and redundancy/family context. |
| Full redevelopment review | Semiannual or annual, or after major methodology/data changes | Re-run the frozen-data research protocol, null controls, dependence diagnostics, and family-collapse analysis. |
| Immediate event-triggered review | As soon as a trigger occurs | Sign flip, lower confidence bound crossing zero, material drawdown, cost/liquidity breach, activation-rate collapse, or structural market change. |

A rolling N-trade window can complement, but should not replace, the calendar cadence. Candidate windows for owner testing are 30, 50, and 100 effective events, with an additional calendar cap such as 3, 6, or 12 months. The most conservative alarm is the first of the event and calendar conditions to fail. The window should use a block or cluster adjustment where activations overlap.

The owner should distinguish **weakening** from **retirement**. A single bad month should generally trigger investigation or a temporary risk reduction rather than permanent deletion, while a persistent sign flip or repeated failure across independent windows can move a signal to quarantine. A changed signal specification should be versioned as a new pattern rather than edited in place.

## 7. Recommended calibration experiment before finalizing thresholds

The following research plan would convert the ranges above into EGX-specific evidence without prematurely selecting final values.

First, construct a dependence-preserving null. Shuffle or bootstrap at the date-block level, preserving cross-ticker returns, feature-window overlap, trigger clustering, holding-period overlap, and the exact discover → validate → holdout → promotion sequence. Run at least 1,000 null replications for stable tail estimates if computationally feasible. Record BH and BY realized FDR, false discovery proportion, discovery count, family count, and promoted-pattern count.

Second, run a redundancy sensitivity grid. Compare Jaccard 0.70, 0.85, 0.90, and 0.95, add containment and effective-outcome-overlap metrics, and measure family count, component size, representative stability, and retained OOS performance. Do not choose the threshold based on the best realized return. Use an adjudicated pair sample to estimate precision and recall for "same underlying signal."

Third, replace raw holdout counts with effective evidence. For each pattern, report activation count, non-overlapping outcome count, date-block count, ticker count, effective sample-size estimate, and block-bootstrap expectancy interval. Repeat promotion outcomes at effective-event floors 30, 50, 100, and 200.

Fourth, conduct a forward-validation simulation. Freeze a historical promotion date, pretend that all information after that date is live-forward, and evaluate 3-, 6-, 9-, and 12-month windows crossed with 30-, 50-, and 100-event requirements. Measure the fraction of patterns whose sign and expectancy survive the next window, not merely whether they pass the original holdout.

Fifth, evaluate staleness rules using historical replay. Compare monthly, quarterly, rolling-50-event, rolling-100-event, and hybrid event/calendar rules. Score detection delay, false alarms, capital exposure during decay, and the proportion of signals that recover after a temporary weakening episode.

## 8. Decision-oriented range summary

| Calibration question | Evidence-backed range for owner consideration | What must be measured before adoption |
|---|---|---|
| BH vs BY | BH as a power baseline if EGX dependence diagnostics and null simulations support PRDS-like behavior; BY as arbitrary-dependence safety benchmark; optionally BH/BY dual reporting | Realized FDR/FDP under EGX-preserving nulls, power, family size, and economically distinct discoveries. |
| Trigger-date Jaccard | Sensitivity grid 0.70 / 0.85 / 0.90 / 0.95; 0.85–0.90 is the plausible strong-redundancy band, not a universal truth | Labeled-pair precision/recall, minimum set size, containment, outcome-window overlap, and threshold stability as the registry grows. |
| Minimum OOS evidence | 30–50 effective events as preliminary floor; 50–100 intermediate; 100–200+ for stronger trust | Confidence interval, effective-event calculation, overlap/block dependence, costs, and regime coverage. |
| Paper-forward period | 3–6 months plus 30–50 live-forward events for a standard candidate; 6–12 months and 50–100+ for conservative promotion; longer for sparse signals | Frozen specification, all eligible activations, live costs/slippage, regime mix, and OOS sign/expectancy survival. |
| Revalidation cadence | Continuous capture; weekly/monthly surveillance; monthly/quarterly formal review; immediate event-triggered escalation | Detection delay, false-alarm rate, exposure during decay, and recovery behavior under historical replay. |

## 9. Limitations and non-decisions

This memo does not select BH, BY, a Jaccard cutoff, a minimum trade count, a paper-trading duration, or a revalidation schedule. Published quantitative-finance papers often study false discoveries, backtest overfitting, or OOS degradation rather than prescribing operational desk thresholds. Public descriptions of "industry practice" are heterogeneous and frequently lack enough detail to distinguish independent trades from overlapping activations.

The EGX setting adds local constraints: a relatively small universe, potential liquidity and price-limit effects, non-uniform trading calendars, cross-ticker shocks, and sparse pattern activations. Therefore, the product owner should treat external ranges as priors and require the platform's own null simulations and historical forward-replay results before converting any range into a hard gate.

The local repository itself contains a significant warning: current family definitions are highly sensitive, and the public real-data run produced many validated variants that appear to represent repeated underlying tendencies rather than independent discoveries [10] [11] [12]. That finding supports investing in dependence-preserving calibration before wiring any promoted pattern to capital-facing consumers.

## References

[1]: https://doi.org/10.1111/j.2517-6161.1995.tb02031.x "Benjamini and Hochberg (1995), Controlling the False Discovery Rate: A Practical and Powerful Approach to Multiple Testing"

[2]: https://projecteuclid.org/journals/annals-of-statistics/volume-29/issue-4/The-control-of-the-false-discovery-rate-in-multiple-testing/10.1214/aos/1013699998.full "Benjamini and Yekutieli (2001), The Control of the False Discovery Rate in Multiple Testing Under Dependency"

[3]: https://people.duke.edu/~charvey/Research/Published_Papers/P143_False_and_missed.pdf "Harvey and Liu (2020), False (and Missed) Discoveries in Financial Economics"

[4]: https://escholarship.org/uc/item/4w1110bb "Bailey, Borwein, López de Prado, and Zhu (2017), The Probability of Backtest Overfitting"

[5]: https://dl.acm.org/doi/10.1145/2000824.2000825 "Xiao et al. (2011), Efficient Similarity Joins for Near-Duplicate Detection"

[6]: https://www.hpi.uni-potsdam.de/fileadmin/hpi/FG_Naumann/publications/2013/On_Choosing_Thresholds_for_Duplicate_Detection.pdf "Draisbach and Naumann (2013), On Choosing Thresholds for Duplicate Detection"

[7]: https://papers.ssrn.com/sol3/papers.cfm?abstract_id=2745220 "Wiecki, Campbell, Lent, and Stauth (2016), All That Glitters Is Not Gold: Comparing Backtest and Out-of-Sample Performance on a Large Cohort of Trading Algorithms"

[8]: https://doi.org/10.3905/jpm.2014.40.5.094 "Bailey and López de Prado (2014), The Deflated Sharpe Ratio: Correcting for Selection Bias, Backtest Overfitting, and Non-Normality"

[9]: https://raw.githubusercontent.com/shadygad01/EGX-Genom/main/docs/PATTERN_PROMOTION_GATE_DESIGN.md "EGX-Genom, Pattern Promotion Gate Design and Audit Report"

[10]: https://raw.githubusercontent.com/shadygad01/EGX-Genom/main/docs/PATTERN_DISCOVERY_FINAL_HOLDOUT.md "EGX-Genom, Pattern Discovery — Real-Data Final Holdout Run"

[11]: https://raw.githubusercontent.com/shadygad01/EGX-Genom/main/docs/PATTERN_CROSS_TICKER_FAMILY_COLLAPSE.md "EGX-Genom, Cross-Ticker Family-Collapse Analysis"

[12]: https://raw.githubusercontent.com/shadygad01/EGX-Genom/main/docs/PATTERN_FAMILY_DEFINITION_STRESS_TEST.md "EGX-Genom, Family Definition Stress Test"

---

# Part 2 — Reconciliation with `PATTERN_PROMOTION_GATE_DESIGN.md` v2.2 §14

`PATTERN_PROMOTION_GATE_DESIGN.md`'s v2.2 §14 ("Provisional-gate table, with
the exact dependency to resolve") lists 12 provisional gates, each with a
named dependency that must be resolved before it can become Hard. The table
below maps each row Manus's memo actually addresses to the memo section that
addresses it, what the memo adds, and confirms explicitly that none of them
are resolved by this memo alone.

| v2.2 §14 provisional gate | Manus memo section | What the memo adds | Still open? |
|---|---|---|---|
| Promotion-cohort correction: BH vs. BY | Part 1 §2 | Explains BH is not automatically invalid under correlation (the PRDS condition); quantifies the harmonic-penalty cost of switching to BY (≈5.2× more stringent at m=100, ≈9.6× at m=7,899); recommends a dependence-preserving null simulation as the calibration method | **Yes.** Memo §9 explicitly states it does not select BH or BY. v2.2 §14 already names this as "an open policy decision for the user/product owner," and this memo does not change that — it only supplies the evidence base for making the decision. |
| Jaccard overlap clustering threshold | Part 1 §3 | Gives a 4-point candidate grid (0.70/0.85/0.90/0.95) with named distortion factors specific to trigger-date sets (sparse sets, unequal set sizes, market-wide shock dates, overlapping horizons, calendar/ticker imbalance, multiple engineered variants); recommends calibrating against a labeled adjudicated-pair sample rather than importing a text-duplicate-detection value directly | **Yes.** No value is chosen. The labeled-pair calibration study the memo proposes (§7, second paragraph) does not exist yet — same "Calibration via synthetic `control_suite.py` data or disjoint prior-cohort history" dependency v2.2 §14 already names. |
| OOS matched-observation floor | Part 1 §4 | Recommends 30–50 as a "preliminary" floor and 100–200 for "stronger promotion evidence"; explicitly cross-references the repository's own median holdout sample (59, min 5, max 162) as proof that a nominal count and a trustworthy count are different questions | **Yes.** No floor is chosen. The memo frames this as an *effective-event-count* problem (discounting for overlap/clustering), which v2.2 §14 already names as needing "real decision-ledger/paper-validation outcome history (does not exist yet)" — that history is still not built. |
| Paper-validation window (N days / M observations) | Part 1 §5 | Recommends 3–6 months + 30–50 live-forward events as a standard candidate band, citing Wiecki et al. (2016)'s 888-strategy cohort using ≥6 months OOS; explicitly ties window length to signal sparsity rather than a single fixed number | **Yes.** No window is adopted. v2.2 §14 already names "at least one full completed real paper-validation cycle" as the dependency — no such cycle has run. |
| `PROMOTED` revalidation cadence | Part 1 §6 | Recommends a layered cadence (continuous capture → weekly/monthly surveillance → monthly/quarterly formal review → immediate event-triggered review on sign flip/drawdown/cost breach); notes this is compatible with the repository's existing `DecayMonitor` concept | **Yes.** No cadence is fixed. v2.2 §14 already names "a declared periodic re-check interval — none proposed yet" as the dependency; the memo offers ranges to declare from, not a declaration. |
| Same-feature/window redundancy dimension | — not addressed | — | Unaffected by this memo; still needs "a defined collapse/discount rule" per v2.2 §14. |
| Same-feature/threshold redundancy dimension | — not addressed | — | Unaffected by this memo; same dependency as above. |
| Cross-ticker Variant A/B redundancy dimensions | — not addressed | — | Unaffected by this memo; still needs granularity-stability calibration per v2.2 §14. |
| Ticker concentration (HHI) ceiling | — not addressed | — | Unaffected by this memo; still no calibrated ceiling proposed. |
| Bootstrap CI coverage level | — not addressed | — | Unaffected by this memo; still needs real paper-validation history. |
| Economic-rationale substance bar | — not addressed | — | Unaffected by this memo; still needs a human-reviewer agreement study. |
| `INSUFFICIENT_EVIDENCE` staleness/abandonment limit | — not addressed | — | Unaffected by this memo; still needs a declared maximum dwell-time or retry count. |

## What this reconciliation does NOT do

- Does not select a final value for any threshold in either table.
- Does not modify `PATTERN_PROMOTION_GATE_DESIGN.md` itself — that document's
  v2.2 §14 status table is unedited; this is a separate, additive research
  artifact.
- Does not change v2.2's `Implementation Readiness` classification
  (`READY_WITH_BLOCKING_DEPENDENCIES`). BH vs. BY remains an explicit,
  undecided policy question — Manus's own memo agrees (Part 1 §9) — which
  alone is sufficient to withhold `READY_FOR_IMPLEMENTATION` per v2.2's own
  stated bar.
- Does not commit to running any of the five calibration experiments Part 1
  §7 proposes (dependence-preserving null simulation; Jaccard sensitivity
  grid on labeled pairs; effective-event-count re-evaluation of OOS floors;
  forward-validation replay simulation; staleness-rule historical replay).
  Running any of them is new work requiring separate, explicit instruction.

## Coverage summary

Of the 12 provisional gates in v2.2 §14, this memo supplies evidence-backed
candidate ranges for **5**: BH-vs-BY policy, the Jaccard overlap threshold,
the OOS matched-observation floor, the paper-validation window, and the
`PROMOTED` revalidation cadence. The remaining **7** (same-feature/window,
same-feature/threshold, cross-ticker Variant A/B, HHI ceiling, bootstrap CI
coverage, economic-rationale substance bar, `INSUFFICIENT_EVIDENCE`
staleness limit) are untouched by this research and remain exactly as
provisional as v2.2 §14 already states.
