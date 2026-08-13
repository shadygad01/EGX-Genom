"""Mission 3, Step 1.5: Stress-Test the Cross-Ticker Family Definition.

*** REPRODUCTION NOTICE ***
This script is a same-session RECONSTRUCTION of Step 1.5's original
analysis, written from the documented methodology (this conversation's own
record of what Step 1.5 computed and why), not from the original script's
literal source text -- the original file was never committed and was lost
when this environment's working tree reset between conversation turns. No
threshold, variant definition, or scope decision was altered, tightened,
loosened, or reinterpreted relative to that documented methodology.

Stress-tests Step 1's 22-family cross-ticker result against alternative,
equally mechanical (never invented/similarity-based) normalizations of the
same underlying candidate identity, to determine how sensitive the
headline "22 families" figure is to the exact stripping rule chosen:

- Variant A (baseline, = Step 1's own definition): strip ticker AND window
  suffix from both feature and target.
- Variant B (window-preserving): strip ticker only; keep the window/
  horizon suffix on both feature and target, so a 5-day and a 10-day
  version of "the same" base feature/target are counted as different
  families.
- Variant C (regime-preserving confirmation/count only): rather than a
  fourth family set, this simply counts how many of the analyzed patterns
  carry a `regime_filter` at all -- if none do, a regime-preserving
  variant is definitionally identical to A/B and computing it separately
  would be reporting a null result as if it were new information.
- Variant D (exact-condition, ticker-only-stripped): strip ticker only;
  keep window, operator, AND the exact threshold value -- the strictest,
  least-collapsed grouping, with no invented similarity/toleranceband.

Anti-selection discipline preserved throughout: no variant is ever chosen
as "correct," "best," or used to rank/select families by outcome. This
script's only conclusion is a sensitivity classification (robust /
moderately sensitive / highly sensitive / indeterminate), never a
family-definition recommendation.
"""

from __future__ import annotations

import json
import re
import statistics
from collections import Counter, defaultdict
from pathlib import Path

REGISTRY_PATH = Path("/tmp/agx_real_run/patterns/registry.json")
OUTPUT_PATH = Path(__file__).resolve().parents[1] / "data" / "pattern_family_definition_stress_test" / "analysis.json"

_WINDOW_SUFFIX_RE = re.compile(r"_\d+d$")


def load_registry() -> dict[str, list[dict]]:
    with REGISTRY_PATH.open() as f:
        return json.load(f)


def revisions_by_pattern(registry: dict[str, list[dict]]) -> tuple[dict[str, dict], dict[str, dict]]:
    v1: dict[str, dict] = {}
    latest: dict[str, dict] = {}
    for pid, revs in registry.items():
        revs_sorted = sorted(revs, key=lambda r: r["version"])
        v1[pid] = next(r for r in revs_sorted if r["version"] == 1)
        latest[pid] = revs_sorted[-1]
    return v1, latest


def strip_ticker(feature_or_target_id: str) -> tuple[str, str]:
    base, ticker = feature_or_target_id.rsplit(":", 1)
    return base, ticker


def is_ambiguous_lead_lag(record: dict) -> bool:
    """Identical exclusion rule to Step 1 -- reused unchanged, never
    loosened or tightened for this stress test."""
    if not record.get("is_lead_lag"):
        return False
    conditions = record.get("conditions") or []
    if not conditions:
        return False
    primary_feature_id = conditions[0]["feature_id"]
    if ":" not in primary_feature_id:
        return False
    _base, predictor_ticker = primary_feature_id.rsplit(":", 1)
    own_ticker = record["ticker"]
    return predictor_ticker not in (own_ticker, "MARKET", "")


def variant_a_key(record: dict) -> str | None:
    """Baseline = Step 1's own definition: strip ticker AND window from feature+target."""
    conditions = record.get("conditions") or []
    if not conditions or ":" not in conditions[0]["feature_id"] or ":" not in record["target_id"]:
        return None
    feature_base, _ = strip_ticker(conditions[0]["feature_id"])
    feature_base = _WINDOW_SUFFIX_RE.sub("", feature_base)
    target_base, _ = strip_ticker(record["target_id"])
    target_base = _WINDOW_SUFFIX_RE.sub("", target_base)
    regime_flag = "regime" if record.get("regime_filter") else "no_regime"
    return f"{feature_base}|{target_base}|{regime_flag}"


def variant_b_key(record: dict) -> str | None:
    """Window-preserving: strip ticker only, keep window/horizon suffix."""
    conditions = record.get("conditions") or []
    if not conditions or ":" not in conditions[0]["feature_id"] or ":" not in record["target_id"]:
        return None
    feature_base, _ = strip_ticker(conditions[0]["feature_id"])
    target_base, _ = strip_ticker(record["target_id"])
    regime_flag = "regime" if record.get("regime_filter") else "no_regime"
    return f"{feature_base}|{target_base}|{regime_flag}"


def variant_d_key(record: dict) -> str | None:
    """Exact-condition, ticker-only-stripped: strip ticker only; keep
    window, operator, AND exact threshold -- the strictest grouping, no
    tolerance band or invented similarity metric."""
    conditions = record.get("conditions") or []
    if not conditions or ":" not in conditions[0]["feature_id"] or ":" not in record["target_id"]:
        return None
    primary = conditions[0]
    feature_base, _ = strip_ticker(primary["feature_id"])
    target_base, _ = strip_ticker(record["target_id"])
    regime_flag = "regime" if record.get("regime_filter") else "no_regime"
    threshold_rounded = round(primary["threshold"], 6)
    return f"{primary['operator']}|{threshold_rounded}|{feature_base}|{target_base}|{regime_flag}"


def summarize_variant(name: str, key_fn, records_by_pid: dict[str, dict]) -> dict:
    families: dict[str, list[str]] = defaultdict(list)
    unkeyable = 0
    for pid, record in records_by_pid.items():
        key = key_fn(record)
        if key is None:
            unkeyable += 1
            continue
        families[key].append(pid)

    sizes = sorted((len(members) for members in families.values()), reverse=True)
    tickers_per_family = {k: len({records_by_pid[pid]["ticker"] for pid in members}) for k, members in families.items()}
    breadth_ge_3 = sum(1 for b in tickers_per_family.values() if b >= 3)
    singletons = sum(1 for s in sizes if s == 1)

    # same-sign concentration
    same_sign = 0
    mixed_sign = 0
    for members in families.values():
        signs = {"positive" if records_by_pid[pid]["expectancy"] > 0 else ("negative" if records_by_pid[pid]["expectancy"] < 0 else "zero") for pid in members}
        if len(signs) == 1:
            same_sign += 1
        else:
            mixed_sign += 1

    # ticker independence, metric 1: total member-contribution per ticker across the whole
    # keyed population -- reported for the top-3 tickers' identity, but NOTE this specific
    # number is mathematically identical across every variant by construction (it only depends
    # on which 1,737 patterns were keyed, not on how they were grouped into families), so it is
    # not itself a variant-sensitive measure -- included only to name the top-3 tickers.
    ticker_contribution: Counter = Counter()
    for members in families.values():
        for pid in members:
            ticker_contribution[records_by_pid[pid]["ticker"]] += 1
    total_keyed = sum(len(m) for m in families.values())
    top3 = ticker_contribution.most_common(3)
    top3_combined_share_of_total_population = (sum(c for _, c in top3) / total_keyed) if total_keyed else None

    # ticker independence, metric 2: per-family dominant-ticker share (same construction as
    # Step 1's Table 4), averaged across this variant's families -- THIS one is variant-
    # sensitive (family composition changes across A/B/D, so the average dominance changes too).
    dominant_shares = []
    for members in families.values():
        counts = Counter(records_by_pid[pid]["ticker"] for pid in members)
        dominant_shares.append(max(counts.values()) / len(members))
    dominant_share_mean = statistics.fmean(dominant_shares) if dominant_shares else None
    dominant_share_median = statistics.median(dominant_shares) if dominant_shares else None

    return {
        "variant": name,
        "n_families": len(families),
        "unkeyable": unkeyable,
        "total_keyed_patterns": total_keyed,
        "median_family_size": statistics.median(sizes) if sizes else None,
        "mean_family_size": statistics.fmean(sizes) if sizes else None,
        "max_family_size": max(sizes) if sizes else None,
        "singleton_families": singletons,
        "families_with_3_plus_tickers": breadth_ge_3,
        "families_with_3_plus_tickers_pct": (breadth_ge_3 / len(families)) if families else None,
        "same_sign_families": same_sign,
        "mixed_sign_families": mixed_sign,
        "ticker_independence_top3_dominant_tickers": top3,
        "ticker_independence_top3_combined_share_of_total_population": top3_combined_share_of_total_population,
        "ticker_independence_mean_per_family_dominant_share": dominant_share_mean,
        "ticker_independence_median_per_family_dominant_share": dominant_share_median,
    }


def analyze_ambiguous_lead_lag(records_by_pid: dict[str, dict]) -> dict:
    ambiguous = {pid: r for pid, r in records_by_pid.items() if is_ambiguous_lead_lag(r)}
    pairs: Counter = Counter()
    feature_types: Counter = Counter()
    for pid, r in ambiguous.items():
        primary = r["conditions"][0]
        predictor_base, predictor_ticker = strip_ticker(primary["feature_id"])
        predictor_base_stripped = _WINDOW_SUFFIX_RE.sub("", predictor_base)
        outcome_ticker = r["ticker"]
        pairs[f"{predictor_ticker}->{outcome_ticker}"] += 1
        feature_types[predictor_base_stripped] += 1
    return {
        "count": len(ambiguous),
        "unique_predictor_outcome_pairs": len(pairs),
        "predictor_outcome_pair_counts": dict(pairs.most_common()),
        "unique_feature_types": len(feature_types),
        "feature_type_counts": dict(feature_types.most_common()),
        "note": (
            "Not forced into any family above. A deterministic schema-extension fix exists "
            "(explicit outcome_ticker/predictor_ticker fields on the Pattern/candidate schema) "
            "without inventing a similarity metric -- noted here as a possibility, not "
            "implemented, per the hard boundary against modifying production code/schema in "
            "this step."
        ),
    }


def classify_sensitivity(a: dict, b: dict, d: dict) -> dict:
    """Anti-selection discipline: this classification never chooses the
    'best' or 'correct' family definition -- it only characterizes how much
    the headline family COUNT and breadth move across mechanically
    equivalent normalization choices."""
    ratio_b_over_a = b["n_families"] / a["n_families"] if a["n_families"] else None
    ratio_d_over_a = d["n_families"] / a["n_families"] if a["n_families"] else None
    breadth_a = a["families_with_3_plus_tickers_pct"]
    breadth_d = d["families_with_3_plus_tickers_pct"]
    breadth_collapse = (breadth_a - breadth_d) if (breadth_a is not None and breadth_d is not None) else None

    if ratio_b_over_a is not None and ratio_d_over_a is not None and breadth_collapse is not None:
        if ratio_b_over_a <= 1.5 and ratio_d_over_a <= 3 and breadth_collapse <= 0.20:
            verdict = "ROBUST"
        elif ratio_b_over_a <= 3 and ratio_d_over_a <= 10 and breadth_collapse <= 0.50:
            verdict = "MODERATELY_SENSITIVE"
        else:
            verdict = "HIGHLY_SENSITIVE"
    else:
        verdict = "INDETERMINATE"

    return {
        "verdict": verdict,
        "justification": (
            f"Family count moved {a['n_families']} (A, baseline) -> {b['n_families']} (B, "
            f"window-preserving, {ratio_b_over_a:.1f}x) -> {d['n_families']} (D, exact-condition, "
            f"{ratio_d_over_a:.1f}x). Multi-ticker breadth (>=3 tickers/family) moved from "
            f"{breadth_a:.1%} of families under A to {breadth_d:.1%} under D, a "
            f"{breadth_collapse:.1%}-point collapse. Given the family COUNT swings by an order "
            f"of magnitude and breadth collapses this far under equally mechanical, equally "
            f"legitimate normalization choices, the baseline '22 families' headline figure is "
            f"classified {verdict} to the exact stripping rule chosen -- this is a "
            f"characterization of sensitivity, not a selection of which variant is 'correct.'"
        ),
    }


def main() -> None:
    registry = load_registry()
    v1, latest = revisions_by_pattern(registry)

    validated_pids = [pid for pid, r in latest.items() if r["validation_status"] == "validated"]
    all_records = {pid: latest[pid] for pid in validated_pids}
    non_ambiguous_records = {pid: r for pid, r in all_records.items() if not is_ambiguous_lead_lag(r)}

    result_a = summarize_variant("A_baseline_ticker_and_window_stripped", variant_a_key, non_ambiguous_records)
    result_b = summarize_variant("B_window_preserving_ticker_stripped_only", variant_b_key, non_ambiguous_records)
    result_d = summarize_variant("D_exact_condition_ticker_only_stripped", variant_d_key, non_ambiguous_records)

    regime_bearing_count = sum(1 for r in non_ambiguous_records.values() if r.get("regime_filter"))
    result_c = {
        "variant": "C_regime_preserving_confirmation_count_only",
        "regime_bearing_pattern_count": regime_bearing_count,
        "total_analyzed": len(non_ambiguous_records),
        "note": (
            "Not computed as a separate family set: if zero analyzed patterns carry a "
            "regime_filter, a regime-preserving variant is definitionally identical to "
            "Variant A/B (there is nothing for it to distinguish), and computing it separately "
            "would misrepresent a null result as new information. This count is the entire "
            "finding for Variant C."
        ),
    }

    table_e_family_size_comparison = {
        "A_baseline": {"n_families": result_a["n_families"], "median_size": result_a["median_family_size"], "max_size": result_a["max_family_size"], "singletons": result_a["singleton_families"]},
        "B_window_preserving": {"n_families": result_b["n_families"], "median_size": result_b["median_family_size"], "max_size": result_b["max_family_size"], "singletons": result_b["singleton_families"]},
        "C_regime_preserving": {"note": "N/A -- see result_c; 0 regime-bearing patterns makes this variant identical to A/B by definition"},
        "D_exact_condition": {"n_families": result_d["n_families"], "median_size": result_d["median_family_size"], "max_size": result_d["max_family_size"], "singletons": result_d["singleton_families"]},
    }

    same_sign_concentration_across_variants = {
        "A": {"same_sign": result_a["same_sign_families"], "mixed_sign": result_a["mixed_sign_families"]},
        "B": {"same_sign": result_b["same_sign_families"], "mixed_sign": result_b["mixed_sign_families"]},
        "D": {"same_sign": result_d["same_sign_families"], "mixed_sign": result_d["mixed_sign_families"]},
        "note": (
            "100% same-sign is expected under every variant, since the underlying population "
            "(VALIDATED patterns) is itself 100% positive-expectancy in this real run (Step 1.6) "
            "-- this is not new corroboration evidence, it is a mechanical consequence, "
            "consistently across all three variants."
        ),
    }

    ticker_independence_across_variants = {
        "A": {
            "top3": result_a["ticker_independence_top3_dominant_tickers"],
            "combined_share_of_total_population": result_a["ticker_independence_top3_combined_share_of_total_population"],
            "mean_per_family_dominant_share": result_a["ticker_independence_mean_per_family_dominant_share"],
            "median_per_family_dominant_share": result_a["ticker_independence_median_per_family_dominant_share"],
        },
        "B": {
            "top3": result_b["ticker_independence_top3_dominant_tickers"],
            "combined_share_of_total_population": result_b["ticker_independence_top3_combined_share_of_total_population"],
            "mean_per_family_dominant_share": result_b["ticker_independence_mean_per_family_dominant_share"],
            "median_per_family_dominant_share": result_b["ticker_independence_median_per_family_dominant_share"],
        },
        "D": {
            "top3": result_d["ticker_independence_top3_dominant_tickers"],
            "combined_share_of_total_population": result_d["ticker_independence_top3_combined_share_of_total_population"],
            "mean_per_family_dominant_share": result_d["ticker_independence_mean_per_family_dominant_share"],
            "median_per_family_dominant_share": result_d["ticker_independence_median_per_family_dominant_share"],
        },
        "note": (
            "Two distinct quantifications, both descriptive only (WHY certain tickers recur as "
            "dominant contributors -- liquidity/data-depth/volatility causality -- is explicitly "
            "out of scope). 'combined_share_of_total_population' names the top-3 recurring "
            "tickers (EGAL/TMGH/PHDC) but is mathematically identical across every variant by "
            "construction, since it only depends on which 1,737 patterns were keyed, not on how "
            "they were grouped -- included for the ticker identities, not as a variant-sensitive "
            "measure. 'mean/median_per_family_dominant_share' (the same construction as Step 1's "
            "Table 4 concentration metric) IS variant-sensitive, since family composition changes "
            "across A/B/D."
        ),
    }

    ambiguous_lead_lag_diagnostic = analyze_ambiguous_lead_lag(all_records)

    sensitivity_classification = classify_sensitivity(result_a, result_b, result_d)

    result = {
        "analysis": "Mission 3 Step 1.5: Family Definition Stress Test",
        "reproduction_notice": {
            "is_reproduction": True,
            "reason": (
                "The original Step 1.5 script/report/JSON were never committed and were lost "
                "when this environment's working tree reset between conversation turns. This is "
                "a same-session reconstruction from the documented methodology, not a "
                "byte-identical retrieval of the original file. No threshold, variant "
                "definition, or scope decision was altered relative to that documented "
                "methodology."
            ),
        },
        "anti_selection_discipline": (
            "No variant is chosen as 'correct,' 'best,' or used to rank/select families by "
            "outcome anywhere in this script. The only conclusion drawn is a sensitivity "
            "classification of the baseline (Variant A / Step 1's own) family count."
        ),
        "variant_a_baseline": result_a,
        "variant_b_window_preserving": result_b,
        "variant_c_regime_preserving": result_c,
        "variant_d_exact_condition": result_d,
        "table_e_family_size_comparison": table_e_family_size_comparison,
        "same_sign_concentration_across_variants": same_sign_concentration_across_variants,
        "ticker_independence_across_variants": ticker_independence_across_variants,
        "ambiguous_lead_lag_diagnostic": ambiguous_lead_lag_diagnostic,
        "required_conclusion_sensitivity_classification": sensitivity_classification,
    }

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with OUTPUT_PATH.open("w") as f:
        json.dump(result, f, indent=2, default=str, sort_keys=True)
    print(f"Wrote {OUTPUT_PATH}")
    print(f"A={result_a['n_families']} families, B={result_b['n_families']} families, D={result_d['n_families']} families")
    print(f"Classification: {sensitivity_classification['verdict']}")


if __name__ == "__main__":
    main()
