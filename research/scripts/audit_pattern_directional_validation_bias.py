"""Mission 3, Step 1.6: Directional Validation-Bias Audit.

Investigates a single, precise question: why do all 1,773 `VALIDATED`
patterns from the real Mission 2 run (`/tmp/agx_real_run/patterns/registry.json`,
3,398 `DISCOVERED`-or-later patterns) have strictly positive expectancy --
zero negative, zero exactly-zero -- among the final `VALIDATED` population?

This script is READ-ONLY against the real registry and testing ledger: it
never mutates `PatternRegistry`, never changes a pattern's `validation_status`,
and never touches any Mission 2/Step-1/Step-1.5 artifact. It also reads the
underlying real EGX price seed data (`research/data/community_prices_seed/`)
directly, independent of the registry, to compute an unconditional
market-drift baseline as corroborating (not primary) evidence.

Family-collapse analysis (Step 1: 22 families; Step 1.5: 22/62/605 across
variants) is explicitly OUT OF SCOPE here per the Step 1.6 instructions --
this script never groups by family and never reads Step 1/1.5 output.

Method: every "why" answered below is either (a) a direct citation of gate
logic actually present in `agx_research.patterns.{robustness,validation,
baselines,evaluation,multiple_testing,multiple_testing_family,engine}` with
exact file/line evidence, or (b) a count/statistic computed directly from
the persisted registry/ledger/price data. Nothing here is assumed.
"""

from __future__ import annotations

import csv
import json
import statistics
from collections import Counter
from pathlib import Path

REGISTRY_PATH = Path("/tmp/agx_real_run/patterns/registry.json")
TESTING_LEDGER_PATH = Path("/tmp/agx_real_run/patterns/testing_ledger.json")
PRICES_DIR = Path(__file__).resolve().parents[1] / "data" / "community_prices_seed" / "normalized" / "prices"
OUTPUT_PATH = Path(__file__).resolve().parents[1] / "data" / "pattern_directional_validation_bias_audit" / "analysis.json"

TRANSACTION_COST_BPS = 20.0  # must match patterns.robustness.DEFAULT_TRANSACTION_COST_BPS
TRANSACTION_COST_FRACTION = TRANSACTION_COST_BPS / 10_000


def load_registry() -> dict[str, list[dict]]:
    with REGISTRY_PATH.open() as f:
        return json.load(f)


def load_testing_ledger() -> dict:
    with TESTING_LEDGER_PATH.open() as f:
        data = json.load(f)
    (ledger_id,) = data.keys()
    (rev,) = data[ledger_id]  # single revision, version 1
    return rev


def revisions_by_pattern(registry: dict[str, list[dict]]) -> tuple[dict[str, dict], dict[str, dict], dict[str, list[dict]]]:
    v1: dict[str, dict] = {}
    latest: dict[str, dict] = {}
    all_sorted: dict[str, list[dict]] = {}
    for pid, revs in registry.items():
        revs_sorted = sorted(revs, key=lambda r: r["version"])
        all_sorted[pid] = revs_sorted
        v1[pid] = next(r for r in revs_sorted if r["version"] == 1)
        latest[pid] = revs_sorted[-1]
    return v1, latest, all_sorted


def sign(x: float) -> str:
    if x > 0:
        return "positive"
    if x < 0:
        return "negative"
    return "zero"


def primary_operator(record: dict) -> str:
    conditions = record.get("conditions") or []
    if not conditions:
        return "no_condition"
    return conditions[0]["operator"]


REJECTION_CATEGORIES = [
    ("WF_insufficient_folds", "Not enough anchor observations"),
    ("WF_oos_floor", "Out-of-sample sample size"),
    ("WF_sign_disagreement", "sign disagrees with the discovery-sample sign"),
    ("ROBUSTNESS_ambiguous", "perturbation(s) flipped sign, or the pattern does not survive transaction costs"),
    ("ROBUSTNESS_insufficient_data", "No perturbation check had enough matched observations"),
    ("BASELINE_failure", "did not beat the buy-and-hold baseline"),
]


def categorize_rejection(reason: str | None) -> str:
    if reason is None:
        return "NO_REASON"
    for label, needle in REJECTION_CATEGORIES:
        if needle in reason:
            return label
    if "Holdout sample size" in reason and "below floor" in reason:
        return "HOLDOUT_sample_floor"
    if "disagrees in sign with the validation-period expectancy" in reason:
        return "HOLDOUT_sign_disagreement"
    return "OTHER_UNCATEGORIZED"


def lifecycle_status_sequence(revs: list[dict]) -> list[str]:
    return [r["validation_status"] for r in revs]


def compute_unconditional_market_drift(tickers: list[str]) -> dict:
    """Independent, registry-free check: mean unadjusted 5d/10d forward
    close-to-close return across the exact 14-ticker universe the real run
    used, computed directly from the raw community-seed price CSVs. This is
    corroborating evidence only -- it uses raw (not corporate-action
    adjusted) closes, unlike the platform's own
    `data.adjustments.adjusted_returns_for_ticker()` pipeline, so it is
    reported with that explicit caveat and is not a substitute for the
    registry-derived findings above."""
    all_5d: list[float] = []
    all_10d: list[float] = []
    per_ticker: dict[str, dict] = {}
    missing: list[str] = []
    for ticker in tickers:
        fp = PRICES_DIR / f"{ticker}.csv"
        if not fp.exists():
            missing.append(ticker)
            continue
        with fp.open() as f:
            rows = list(csv.DictReader(f))
        closes = [float(r["close"]) for r in rows]
        fwd5 = [(closes[i + 5] - closes[i]) / closes[i] for i in range(len(closes) - 5) if closes[i] != 0]
        fwd10 = [(closes[i + 10] - closes[i]) / closes[i] for i in range(len(closes) - 10) if closes[i] != 0]
        all_5d.extend(fwd5)
        all_10d.extend(fwd10)
        per_ticker[ticker] = {
            "n_5d": len(fwd5),
            "mean_5d": statistics.fmean(fwd5) if fwd5 else None,
            "n_10d": len(fwd10),
            "mean_10d": statistics.fmean(fwd10) if fwd10 else None,
        }
    return {
        "caveat": (
            "Computed from raw, unadjusted community-seed close prices, NOT the "
            "platform's own data.adjustments-adjusted return pipeline. Corroborating "
            "evidence for a real positive nominal price drift over the sample window, "
            "not a recomputation of any registry field."
        ),
        "tickers_used": [t for t in tickers if t not in missing],
        "tickers_missing_price_file": missing,
        "unconditional_5d": {
            "n": len(all_5d),
            "mean": statistics.fmean(all_5d) if all_5d else None,
            "median": statistics.median(all_5d) if all_5d else None,
            "hit_rate_positive": (sum(1 for x in all_5d if x > 0) / len(all_5d)) if all_5d else None,
        },
        "unconditional_10d": {
            "n": len(all_10d),
            "mean": statistics.fmean(all_10d) if all_10d else None,
            "median": statistics.median(all_10d) if all_10d else None,
            "hit_rate_positive": (sum(1 for x in all_10d if x > 0) / len(all_10d)) if all_10d else None,
        },
        "per_ticker_mean_5d": {t: v["mean_5d"] for t, v in per_ticker.items()},
    }


def main() -> None:
    registry = load_registry()
    ledger = load_testing_ledger()
    v1, latest, all_revs = revisions_by_pattern(registry)

    total_patterns = len(registry)
    tickers = sorted({r["ticker"] for r in v1.values()})

    # ---- §1/§2: lifecycle-wide sign accounting at the earliest persisted stage (v1 = DISCOVERED) ----
    v1_sign_counts = Counter(sign(r["expectancy"]) for r in v1.values())
    latest_status_counts = Counter(r["validation_status"] for r in latest.values())

    sign_to_latest_status: dict[str, Counter] = {}
    for pid, r in v1.items():
        s = sign(r["expectancy"])
        sign_to_latest_status.setdefault(s, Counter())[latest[pid]["validation_status"]] += 1

    # operator (GT/LT) x v1 expectancy sign
    operator_sign: dict[str, Counter] = {}
    operator_counts = Counter()
    for r in v1.values():
        op = primary_operator(r)
        operator_counts[op] += 1
        operator_sign.setdefault(op, Counter())[sign(r["expectancy"])] += 1

    # ---- §5: operator parity table (discovered -> validated), further by is_lead_lag ----
    operator_stage_table = {}
    for op in operator_counts:
        pids_for_op = [pid for pid, r in v1.items() if primary_operator(r) == op]
        n_discovered = len(pids_for_op)
        n_validated = sum(1 for pid in pids_for_op if latest[pid]["validation_status"] == "validated")
        n_rejected = sum(1 for pid in pids_for_op if latest[pid]["validation_status"] == "rejected")
        operator_stage_table[op] = {
            "discovered": n_discovered,
            "validated": n_validated,
            "rejected": n_rejected,
            "validation_rate_of_discovered": n_validated / n_discovered if n_discovered else None,
        }

    operator_by_lead_lag = {}
    for op in operator_counts:
        for is_ll in (True, False):
            pids = [pid for pid, r in v1.items() if primary_operator(r) == op and r["is_lead_lag"] == is_ll]
            if not pids:
                continue
            n_validated = sum(1 for pid in pids if latest[pid]["validation_status"] == "validated")
            operator_by_lead_lag[f"{op}|is_lead_lag={is_ll}"] = {
                "discovered": len(pids),
                "validated": n_validated,
                "validation_rate": n_validated / len(pids),
            }

    # ---- §7: discovery-pool loss quantification ----
    candidates_generated = ledger["hypotheses_tested"]
    candidates_surviving_fdr = ledger["surviving_after_fdr"]
    candidates_surviving_family_correction_alone = ledger["surviving_after_family_correction"]
    unpersisted_candidates = candidates_generated - candidates_surviving_fdr
    assert candidates_surviving_fdr == total_patterns, "registry pattern count must equal ledger's surviving_after_fdr"

    discovery_pool_loss = {
        "candidates_generated": candidates_generated,
        "candidates_surviving_family_correction_alone": candidates_surviving_family_correction_alone,
        "candidates_surviving_fdr_and_persisted_as_DISCOVERED": candidates_surviving_fdr,
        "unpersisted_candidates": unpersisted_candidates,
        "unpersisted_candidates_pct_of_generated": unpersisted_candidates / candidates_generated,
        "recoverable_fields_for_unpersisted_candidates": [],
        "unrecoverable_fields_for_unpersisted_candidates": [
            "expectancy sign/value",
            "operator (GT/LT)",
            "ticker",
            "feature/target identity",
            "raw or family-corrected p-value",
            "whether it had ANY evaluable discovery-sample distribution "
            "(matched-sample-size floor may have excluded it before a p-value "
            "was ever computed -- discover()'s own discovery_ok/evaluate_outcomes "
            "step, which would separate 'never evaluable' from 'evaluable but "
            "lost family+BH-FDR', has no persisted counterpart anywhere: only "
            "the final surviving_after_fdr and surviving_after_family_correction "
            "totals were written to TestingLedger, not the len(discovery_ok) "
            "intermediate count)",
        ],
        "epistemic_gap_statement": (
            f"{unpersisted_candidates} of {candidates_generated} candidates "
            f"({unpersisted_candidates / candidates_generated:.1%}) generated during the real "
            "Mission 2 run were never written to any artifact -- not the PatternRegistry "
            "(only FDR survivors are persisted, by design: see patterns/engine.py's "
            "discover() and CLAUDE.md's own 'never catalog every raw candidate' rule), "
            "not the TestingLedger (which records only aggregate counts, not per-candidate "
            "records), and not any log, cache, test fixture, or intermediate file this audit "
            "could locate under /tmp/agx_real_run or the repository. Their expectancy sign, "
            "operator, and every other per-candidate attribute are permanently unrecoverable "
            "for this specific run. This is a real, structural gap, not an oversight of this "
            "audit: closing it would require re-running discover() with candidate-level "
            "logging that does not currently exist, and even that would produce a NEW run, "
            "not a reconstruction of this one (discover() is not seeded for candidate-order "
            "determinism across re-runs beyond what the bootstrap p-value's own seed=42 covers)."
        ),
    }

    # ---- §1/§3/§4: gate-by-gate rejection reason categorization for the 1,625 REJECTED patterns ----
    rejected_pids = [pid for pid, r in latest.items() if r["validation_status"] == "rejected"]
    rejection_categories = Counter(categorize_rejection(latest[pid].get("rejection_reason")) for pid in rejected_pids)

    # v1 expectancy stats per rejection category (evidence for whether each gate is positive-only in practice)
    category_v1_expectancy_stats: dict[str, dict] = {}
    for cat in rejection_categories:
        vals = [v1[pid]["expectancy"] for pid in rejected_pids if categorize_rejection(latest[pid].get("rejection_reason")) == cat]
        if not vals:
            continue
        category_v1_expectancy_stats[cat] = {
            "n": len(vals),
            "mean": statistics.fmean(vals),
            "median": statistics.median(vals),
            "min": min(vals),
            "max": max(vals),
            "n_negative_or_zero": sum(1 for v in vals if v <= 0),
            "n_positive": sum(1 for v in vals if v > 0),
        }

    # ROBUSTNESS_ambiguous decomposition: independently determine, from v1.expectancy
    # (which is computed over the same anchor_dates set robustness.run()'s base_dist
    # uses -- see engine.py discover()'s placeholder_wf.discovery_distribution and
    # validate()'s robustness_tester.run(candidate, anchor_dates=anchor_dates, ...)),
    # whether net_of_cost = v1.expectancy - TRANSACTION_COST_FRACTION <= 0 deterministically
    # explains the rejection (transaction-cost floor alone is sufficient), vs > 0 meaning
    # a perturbation-sign-flip must have been at least a contributing cause.
    robustness_ambiguous_pids = [pid for pid in rejected_pids if categorize_rejection(latest[pid].get("rejection_reason")) == "ROBUSTNESS_ambiguous"]
    txn_cost_alone_explains = 0
    must_involve_perturbation_instability = 0
    for pid in robustness_ambiguous_pids:
        net = v1[pid]["expectancy"] - TRANSACTION_COST_FRACTION
        if net <= 0:
            txn_cost_alone_explains += 1
        else:
            must_involve_perturbation_instability += 1
    robustness_ambiguous_decomposition = {
        "total": len(robustness_ambiguous_pids),
        "transaction_cost_floor_alone_deterministically_explains": txn_cost_alone_explains,
        "must_involve_perturbation_sign_instability": must_involve_perturbation_instability,
        "method": (
            "For each ROBUSTNESS_ambiguous-rejected pattern, computed "
            "net_of_cost = v1.expectancy - 0.002 (0.002 = 20bps, matching "
            "patterns.robustness.DEFAULT_TRANSACTION_COST_BPS) independently of the "
            "registry's own stored net_of_cost_expectancy (which is not persisted on "
            "Pattern). net_of_cost <= 0 means transaction_cost_survival = net_expectancy > 0 "
            "(robustness.py line 126) was False by construction, and alone is sufficient to "
            "fail robustness.py line 143's result.passed = agreeing_all AND "
            "transaction_cost_survival, regardless of perturbation outcomes."
        ),
    }

    # HOLDOUT_sign_disagreement: confirm every one of these had POSITIVE validation-period
    # expectancy going in (since only positive-expectancy patterns ever reach VALIDATING at all).
    holdout_sign_dis_pids = [pid for pid in rejected_pids if categorize_rejection(latest[pid].get("rejection_reason")) == "HOLDOUT_sign_disagreement"]
    holdout_sign_disagreement_check = {
        "total": len(holdout_sign_dis_pids),
        "pre_holdout_expectancy_positive": sum(1 for pid in holdout_sign_dis_pids if latest[pid]["expectancy"] > 0),
        "note": (
            "This gate (engine.py final_holdout(), line ~673) is sign-AGREEMENT (holdout "
            "sign must match the validation-period sign), not positive-only in code -- it "
            "would equally reject a would-be-negative pattern whose holdout flipped positive. "
            "But by the time final_holdout() runs, every VALIDATING pattern already has "
            "positive expectancy (enforced upstream by the robustness gate), so in practice "
            "every rejection here is 'positive flipped to negative at holdout', never the "
            "reverse -- a consequence of the upstream population already being 100% positive, "
            "not an independent source of directional bias."
        ),
    }

    # ---- §1: 192 exactly-zero-expectancy v1 patterns -- degenerate-match diagnostic ----
    zero_pids = [pid for pid, r in v1.items() if r["expectancy"] == 0]
    zero_diag_sample = None
    if zero_pids:
        sample_pid = zero_pids[0]
        zero_diag_sample = {
            "pattern_id": sample_pid,
            "v1_record": v1[sample_pid],
        }
    zero_expectancy_diagnostic = {
        "count": len(zero_pids),
        "all_rejected": all(latest[pid]["validation_status"] == "rejected" for pid in zero_pids),
        "target_kinds": dict(Counter(v1[pid]["target_id"].split(":")[0] for pid in zero_pids)),
        "hit_rate_all_zero": all(v1[pid]["hit_rate"] == 0 for pid in zero_pids),
        "interpretation": (
            "Every one of these has expectancy=0.0, median_outcome=0.0, hit_rate=0.0 exactly "
            "-- consistent with a degenerate match where every anchor date the candidate "
            "triggered on had a forward_return of exactly 0.0 for that (thin/illiquid) "
            "ticker-window combination, not a genuine 'no edge' discovery. All were rejected "
            "(via the same net_expectancy>0 robustness gate: 0.0 - 0.002 < 0), so this "
            "degenerate group never reached VALIDATING/VALIDATED and does not change this "
            "audit's conclusion, but it is a distinct, separately-flagged data-quality "
            "artifact, not evidence of a directional selection mechanism."
        ),
        "sample_record": zero_diag_sample,
    }

    # ---- §9 supporting evidence: unconditional market drift, computed independently from raw price data ----
    market_drift = compute_unconditional_market_drift(tickers)

    # ---- code-level gate audit (§3, §4, §6): exact citations ----
    code_audit = [
        {
            "gate": "discover() discovery-sample significance (BH-FDR over family-corrected bootstrap p-values)",
            "file": "research/src/agx_research/patterns/evaluation.py",
            "lines": "43-63 (_bootstrap), 85-125 (evaluate_outcomes)",
            "sign_relative_or_positive_only": "sign_neutral",
            "finding": (
                "_bootstrap()'s p-value is two-sided: "
                "'opposite_side = sum(1 for m in means if (m <= 0) != (observed_mean <= 0))', "
                "p_value = min(1, 2*min(opposite_side, iterations-opposite_side)/iterations). "
                "This treats a strongly negative mean exactly as significant as a strongly "
                "positive one of the same magnitude. No sign preference anywhere in this stage."
            ),
        },
        {
            "gate": "multiple_testing.benjamini_hochberg() / multiple_testing_family.family_corrected_p_value()",
            "file": "research/src/agx_research/patterns/multiple_testing.py, multiple_testing_family.py",
            "lines": "multiple_testing.py:21-37, multiple_testing_family.py:76-77",
            "sign_relative_or_positive_only": "sign_neutral",
            "finding": "Both operate purely on p-value magnitude and family/complexity size. Neither reads expectancy or sign at all.",
        },
        {
            "gate": "validation.WalkForwardValidator.validate() -- OOS-vs-discovery sign agreement",
            "file": "research/src/agx_research/patterns/validation.py",
            "lines": "170-174",
            "sign_relative_or_positive_only": "sign_relative (agreement), not positive-only",
            "finding": (
                "'(oos_distribution.expectancy > 0) != (discovery_distribution.expectancy > 0)' "
                "rejects on DISAGREEMENT, not on negativity. A candidate whose discovery-sample "
                "AND out-of-sample expectancy are both consistently negative passes this gate."
            ),
        },
        {
            "gate": "robustness.RobustnessTester.run() -- transaction_cost_survival",
            "file": "research/src/agx_research/patterns/robustness.py",
            "lines": "124-126, 142-143",
            "sign_relative_or_positive_only": "POSITIVE_ONLY (hard, absolute)",
            "finding": (
                "'net_expectancy = base_dist.expectancy - (transaction_cost_bps / 10_000)'; "
                "'result.transaction_cost_survival = net_expectancy > 0'; "
                "'result.passed = (agreeing == len(executed)) and bool(result.transaction_cost_survival)'. "
                "This tests raw net_expectancy > 0, never abs(net_expectancy) > cost, and never "
                "considers the candidate's signal as a short/inverse position. Any candidate "
                "with expectancy <= 0.002 (20bps) -- negative, zero, or weakly positive -- fails "
                "transaction_cost_survival and therefore fails result.passed unconditionally, "
                "regardless of how consistent its perturbation sign-agreement was."
            ),
        },
        {
            "gate": "engine.validate() -- robustness_result.passed gates REJECTED",
            "file": "research/src/agx_research/patterns/engine.py",
            "lines": "512-533",
            "sign_relative_or_positive_only": "inherits robustness.py's positive-only behavior",
            "finding": (
                "'elif robustness_result is not None and not robustness_result.passed: "
                "reason = ...' -- status defaults to PatternStatus.REJECTED whenever this branch "
                "is taken. This is the exact point where the robustness gate's positive-only "
                "transaction_cost_survival check becomes a hard registry-level REJECTED verdict."
            ),
        },
        {
            "gate": "baselines.beats_baseline() -- net expectancy vs buy-and-hold baseline",
            "file": "research/src/agx_research/patterns/baselines.py",
            "lines": "156-162",
            "sign_relative_or_positive_only": "sign_relative in code (compares to baseline.mean_outcome, not to zero)",
            "finding": (
                "'net_expectancy = distribution.expectancy - (transaction_cost_bps / 10_000); "
                "return net_expectancy > baseline.mean_outcome'. Not hard-coded positive-only, "
                "but empirically becomes an anti-negative filter given this run's real data: "
                "buy_and_hold_baseline().mean_outcome was positive for every one of the 14 "
                "tickers used (see market_drift.per_ticker_mean_5d below), so any negative or "
                "weakly-positive candidate expectancy fails this comparison too, independently "
                "of the robustness gate above."
            ),
        },
        {
            "gate": "engine.final_holdout() -- holdout-vs-validation sign agreement",
            "file": "research/src/agx_research/patterns/engine.py",
            "lines": "673",
            "sign_relative_or_positive_only": "sign_relative (agreement), not positive-only",
            "finding": (
                "'(holdout_distribution.expectancy > 0) != (pattern.expectancy > 0)' -- same "
                "agreement pattern as validation.py:170-174. Never independently positive-only, "
                "but only ever operates on an already-100%-positive input population (see "
                "holdout_sign_disagreement_check above)."
            ),
        },
        {
            "gate": "decay.DecayMonitor.check() -- live-vs-historical sign flip (not part of discover/validate/final_holdout; live-monitoring only)",
            "file": "research/src/agx_research/patterns/decay.py",
            "lines": "88-92",
            "sign_relative_or_positive_only": "sign_relative (agreement), not positive-only",
            "finding": "Out of scope for this audit's lifecycle (applies post-VALIDATED, in live monitoring), included only for completeness of the sign-logic search requested in Step 1.6 section 6.",
        },
        {
            "gate": "candidates.ConditionOperator.GT/LT and _single_conditions()/_median_condition()",
            "file": "research/src/agx_research/patterns/candidates.py",
            "lines": "41-46, 178-194",
            "sign_relative_or_positive_only": "N/A -- feature-threshold direction, not outcome-expectancy sign",
            "finding": (
                "_single_conditions() generates BOTH GT and LT at every quantile threshold "
                "(line 186: 'for op in (ConditionOperator.GT, ConditionOperator.LT)'). "
                "_median_condition() (used for two/three-feature interactions and regime "
                "filters) generates ONLY GT (line 194: 'operator=ConditionOperator.GT'). This "
                "is a real asymmetry in candidate GENERATION (more GT candidates exist overall "
                "than LT), but it is an asymmetry in which FEATURE CONDITION is tested, not in "
                "the sign of the resulting outcome/expectancy -- see operator_stage_table below, "
                "where LT-conditioned survivors are, if anything, MORE likely to have positive "
                "expectancy than GT-conditioned ones, ruling this out as the explanation for the "
                "zero-negative finding."
            ),
        },
        {
            "gate": "transaction_costs.py -- separate diagnostic module (Phase 15 cost-sensitivity sweep)",
            "file": "research/src/agx_research/patterns/transaction_costs.py",
            "lines": "83",
            "sign_relative_or_positive_only": "POSITIVE_ONLY (same pattern as robustness.py, but NOT wired into discover()/validate()/final_holdout())",
            "finding": (
                "'survives_default_cost = (gross_expectancy - DEFAULT_TRANSACTION_COST_BPS / 10_000) > 0' "
                "-- confirms the same long-only 'net expectancy must be positive' assumption "
                "recurs in a second, independent module. Not imported by engine.py (verified: "
                "engine.py's import block does not include transaction_costs), so it does not "
                "itself gate any pattern's registry status -- it is a separate, CLI-driven "
                "sensitivity-sweep report. Included here because it shows the long-only "
                "assumption is a recurring pattern across the package, not a one-off accident "
                "in a single function."
            ),
        },
    ]

    # ---- classification ----
    classification = {
        "category": "E",
        "label": "Mixed explanation with two independently-evidenced components",
        "components": [
            {
                "id": "C",
                "label": "Statistical/data-generating asymmetry",
                "evidence": [
                    "94.3% (3,202/3,398) of DISCOVERED (v1) patterns already have positive "
                    "expectancy BEFORE any validate()-stage gate runs, despite discover()'s "
                    "significance test (evaluation.py's bootstrap p-value) being genuinely "
                    "two-sided/sign-neutral.",
                    "Independent, registry-free computation of unconditional mean forward "
                    "returns directly from the real EGX price seed data across the same "
                    "14-ticker universe (see market_drift below) shows a strong positive "
                    "nominal drift (+0.83%/5 trading days, +1.68%/10 trading days, pooled "
                    "across tickers) despite a near-coin-flip 49.2% unconditional up-day rate "
                    "-- i.e. up moves are larger than down moves on average, consistent with a "
                    "nominal-currency-inflation-driven upward-biased market over this real "
                    "sample window (2022-2025-ish), not a code artifact.",
                    "Both GT- and LT-conditioned survivors are overwhelmingly positive "
                    "(92.9% and 98.6% respectively -- LT is if anything MORE positive), which "
                    "rules out a simple 'one operator direction is coded wrong' explanation and "
                    "is consistent with both directions inheriting the same underlying positive "
                    "market drift.",
                    "1,007 of 1,625 rejections (62%) were BASELINE_failure: patterns with "
                    "genuinely positive expectancy (mean +1.11%, range +0.46% to +1.83%) that "
                    "still failed to beat their own ticker's buy-and-hold baseline -- direct "
                    "evidence the baseline itself (a real per-ticker market-drift measurement) "
                    "was high enough to eliminate even solidly positive candidates, which is "
                    "only possible if the underlying market drift is itself strongly positive.",
                ],
            },
            {
                "id": "B",
                "label": "Accidental implementation bias (long-only assumption baked into two independent gates)",
                "evidence": [
                    "robustness.py:126's 'transaction_cost_survival = net_expectancy > 0' is a "
                    "hard, absolute (not sign-relative, not abs()-based) positive-only test that "
                    "would reject ANY negative-expectancy pattern outright, in ANY market regime "
                    "-- this is a real, independent, additive source of directional selection, "
                    "not merely a restatement of the market-drift finding above.",
                    "The identical 'net_expectancy > 0' pattern recurs verbatim in "
                    "transaction_costs.py:83, a separate module -- suggesting the long-only "
                    "framing (never modeling a short/inverse position for a negative-expectancy "
                    "signal) is a consistent, if never explicitly documented, design assumption "
                    "across the patterns package, not a one-off typo.",
                    "511 rejections were categorized ROBUSTNESS_ambiguous; of these, 400 are "
                    "deterministically explained by the transaction-cost floor alone "
                    "(v1.expectancy - 0.002 <= 0), independent of any perturbation-sign-flip "
                    "evidence -- a directly quantified lower bound on how many rejections this "
                    "one code-level gate alone caused.",
                    "No docstring, comment, or design doc anywhere in patterns/ (all read fresh "
                    "for this audit) frames this as a deliberate 'long-only, positive-expectancy "
                    "patterns only' design decision -- live.py's own docstring instead frames "
                    "the package as deliberately direction-agnostic ('never a BUY/SELL label'), "
                    "which is in tension with a gate that hard-codes long-only economics.",
                ],
            },
        ],
        "why_not_A": (
            "No code, docstring, or doc anywhere in patterns/ states 'reject negative-expectancy "
            "patterns because only long signals are tradeable' or equivalent -- robustness.py's "
            "own docstring frames transaction_cost_survival purely in terms of realistic cost "
            "modeling, not directional intent. Absence of any such statement across every file "
            "read for this audit is the basis for ruling out full intentionality."
        ),
        "why_not_pure_C": (
            "The market-drift explanation alone does not account for the 400 ROBUSTNESS_ambiguous "
            "rejections deterministically caused by the fixed 20bps floor regardless of regime, nor "
            "for the fact that the SAME 'net_expectancy > 0' (not baseline-relative) code pattern "
            "recurs in a second, independent module (transaction_costs.py) -- a code-level "
            "mechanism exists that would reproduce (part of) this bias even in a flat or "
            "negative-drift market."
        ),
        "why_not_pure_B": (
            "The code-level transaction-cost gate alone does not explain why 94.3% of patterns "
            "were ALREADY positive at the DISCOVERED stage, before that gate ever runs -- "
            "discover()'s own significance test is genuinely two-sided and sign-neutral (verified "
            "by direct code reading), so the pre-gate skew must trace to the data itself, not to "
            "engine code."
        ),
        "why_not_D": (
            "Sufficient evidence was directly recoverable from the persisted registry, testing "
            "ledger, and (independently) the raw real price data to support both components "
            "above with specific counts and code citations -- this is not a case where the "
            "decisive evidence is unrecoverable. (The upstream ~4,501-candidate discovery-pool "
            "loss IS a genuine, separately-flagged unrecoverable gap -- see "
            "discovery_pool_loss above -- but it does not block this classification, since the "
            "94.3%-positive-at-DISCOVERED finding and the code-level gate citations are both "
            "independent of that unrecoverable pool.)"
        ),
    }

    result = {
        "audit": "Mission 3 Step 1.6: Directional Validation-Bias Audit",
        "primary_question": "Why does the VALIDATED population (1,773/1,773) contain zero negative-expectancy and zero zero-expectancy patterns?",
        "scope_note": (
            "Family-collapse grouping (Step 1's 22 families; Step 1.5's 22/62/605 variants) is "
            "explicitly out of scope -- this analysis never reads Step 1/1.5 artifacts and never "
            "groups patterns by family. All findings below are at the individual-pattern / "
            "pipeline-gate level, per the Step 1.6 instructions."
        ),
        "registry_summary": {
            "total_patterns": total_patterns,
            "tickers_in_run": tickers,
            "v1_status_counts": dict(Counter(r["validation_status"] for r in v1.values())),
            "latest_status_counts": dict(latest_status_counts),
        },
        "lifecycle_directional_trace": {
            "v1_discovered_expectancy_sign_counts": dict(v1_sign_counts),
            "sign_to_final_status": {k: dict(v) for k, v in sign_to_latest_status.items()},
            "interpretation": (
                "Of 3,398 DISCOVERED patterns, 3,202 (94.3%) already had positive expectancy, "
                "192 (5.6%) exactly zero, and only 4 (0.1%) negative -- BEFORE validate() ever "
                "runs. 100% of the negative group and 100% of the zero group ended REJECTED; "
                "1,773/3,202 (55.4%) of the positive group reached VALIDATED, the remaining "
                "1,429 positive patterns were REJECTED by later gates (see "
                "rejection_reason_categories below)."
            ),
        },
        "operator_parity": {
            "v1_operator_counts": dict(operator_counts),
            "operator_x_expectancy_sign_at_v1": {k: dict(v) for k, v in operator_sign.items()},
            "operator_stage_table": operator_stage_table,
            "operator_by_lead_lag": operator_by_lead_lag,
            "interpretation": (
                "GT and LT survivors are both overwhelmingly positive-expectancy (92.9% and "
                "98.6% of each operator's v1 population respectively), and LT's validation rate "
                "(discovered->validated) is comparable to GT's -- see operator_stage_table. This "
                "rules out 'one specific operator direction is structurally blocked' as an "
                "explanation; the bias is not operator-specific."
            ),
        },
        "rejection_reason_categories": dict(rejection_categories),
        "category_v1_expectancy_stats": category_v1_expectancy_stats,
        "robustness_ambiguous_decomposition": robustness_ambiguous_decomposition,
        "holdout_sign_disagreement_check": holdout_sign_disagreement_check,
        "zero_expectancy_diagnostic": zero_expectancy_diagnostic,
        "discovery_pool_loss": discovery_pool_loss,
        "market_drift_independent_check": market_drift,
        "code_audit": code_audit,
        "classification": classification,
        "limitations": [
            "The exact discovery-floor intermediate count (len(discovery_ok) inside discover(), "
            "i.e. candidates with an evaluable distribution before family-correction/BH-FDR) was "
            "never persisted for this run and cannot be reconstructed -- see "
            "discovery_pool_loss.epistemic_gap_statement.",
            "The per-candidate operator/sign/ticker identity of the 4,501 candidates that never "
            "reached DISCOVERED is permanently unrecoverable for this specific run.",
            "The market-drift corroborating check uses raw, unadjusted close prices, not the "
            "platform's own corporate-action-adjusted return pipeline (data.adjustments) -- "
            "reported as directional/order-of-magnitude corroborating evidence only, per its own "
            "caveat field above, not as a recomputation of any registry field.",
            "beats_baseline()'s exact baseline.mean_outcome value used for each individual "
            "BASELINE_failure rejection was never persisted on the Pattern record (it is computed "
            "ephemerally inside validate() and not stored) -- this audit infers the mechanism from "
            "(a) the code (baselines.py:156-162) and (b) the independently-computed per-ticker "
            "drift in market_drift_independent_check, not from a stored per-pattern baseline value.",
        ],
    }
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with OUTPUT_PATH.open("w") as f:
        json.dump(result, f, indent=2, default=str, sort_keys=True)
    print(f"Wrote {OUTPUT_PATH}")
    print(f"v1 sign counts: {dict(v1_sign_counts)}")
    print(f"rejection categories: {dict(rejection_categories)}")


if __name__ == "__main__":
    main()
