"""Mission 3, Step 1: Cross-Ticker Family-Collapse Analysis.

*** REPRODUCTION NOTICE ***
This script is a same-session RECONSTRUCTION of Step 1's original analysis,
written from the documented methodology (this conversation's own record of
what Step 1 computed and why), not from the original script's literal
source text -- the original file was never committed and was lost when this
environment's working tree reset between turns. It is labeled as a
reproduction throughout its own output (see `reproduction_notice` in the
JSON), per the explicit instruction not to silently regenerate and claim
original provenance. The methodology below preserves the original's stated
design exactly as documented: no threshold, family-key component, or
scope decision was altered, tightened, loosened, or reinterpreted.

Analyzes the real Mission 2 registry's 1,773 `PatternStatus.VALIDATED`
patterns and determines how many independent underlying signal FAMILIES
exist once ticker identity is removed from the family definition.

`multiple_testing_family.candidate_family_key()` (imported and reused
as-is, unmodified, from the real installed package) already groups
same-ticker candidates that re-test the same underlying idea. This script
builds one NEW, additional, ticker-agnostic key
(`cross_ticker_family_key`) purely by inverting the `feature_id =
f"{feature_key}:{ticker}"` naming convention already used throughout
`patterns/features.py`/`patterns/targets.py` -- never by inventing a new
similarity/clustering metric. Component:

    cross_ticker_family_key = stripped_primary_feature_base
                             | stripped_target_kind
                             | regime_presence

Both "stripped_*" components remove the ticker suffix (`rsplit(":", 1)`)
and then strip a trailing `_<N>d` window/horizon suffix via the same
regex shape `candidate_family_key()` itself already uses
(`re.sub(r"_\\d+d(?=:)", "", ...)` there; here applied post-ticker-split as
`re.sub(r"_\\d+d$", "", ...)`), so two patterns testing "the same base
feature predicting the same kind of target, regardless of ticker AND
regardless of exact window/horizon" collapse into the same family --
exactly the mechanical, non-invented normalization the original analysis
used.

Patterns whose primary condition references a PEER ticker's own feature
(lead/lag patterns where the predictor identity is not the pattern's own
ticker and not "MARKET") are a genuine, irreducible ambiguity for
cross-ticker grouping (group by predictor? by outcome ticker? neither?) --
these are excluded from the main family analysis and reported separately,
never silently forced into a family.
"""

from __future__ import annotations

import json
import re
import statistics
from collections import Counter, defaultdict
from pathlib import Path

from agx_research.patterns.candidates import FeatureCondition, PatternCandidate
from agx_research.patterns.multiple_testing_family import candidate_family_key

REGISTRY_PATH = Path("/tmp/agx_real_run/patterns/registry.json")
OUTPUT_PATH = Path(__file__).resolve().parents[1] / "data" / "pattern_cross_ticker_family_collapse" / "analysis.json"

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


def strip_ticker_and_window(feature_or_target_id: str) -> tuple[str, str]:
    """Inverts the `key:ticker` convention (`rsplit(":", 1)`), then strips a
    trailing `_<N>d` window/horizon suffix. Returns (stripped_base, ticker)."""
    base, ticker = feature_or_target_id.rsplit(":", 1)
    stripped = _WINDOW_SUFFIX_RE.sub("", base)
    return stripped, ticker


def reconstruct_candidate(pattern_id: str, record: dict) -> PatternCandidate:
    """Mirrors `engine.py`'s own PatternCandidate reconstruction pattern
    (used identically in `validate()`/`final_holdout()`), so the real,
    unmodified `candidate_family_key()` can be called on real data."""
    conditions = [FeatureCondition(**c) for c in (record.get("conditions") or [])]
    regime_filter = FeatureCondition(**record["regime_filter"]) if record.get("regime_filter") else None
    return PatternCandidate(
        id=pattern_id,
        ticker=record["ticker"],
        conditions=conditions,
        regime_filter=regime_filter,
        target_id=record["target_id"],
        complexity=record["complexity"],
        is_lead_lag=record.get("is_lead_lag", False),
    )


def is_ambiguous_lead_lag(record: dict) -> tuple[bool, str]:
    """A lead/lag pattern whose primary condition references a PEER
    ticker's own feature (not self, not MARKET) is genuinely ambiguous for
    cross-ticker grouping -- excluded, never silently resolved."""
    if not record.get("is_lead_lag"):
        return False, ""
    conditions = record.get("conditions") or []
    if not conditions:
        return False, ""
    primary_feature_id = conditions[0]["feature_id"]
    if ":" not in primary_feature_id:
        return False, ""
    _base, predictor_ticker = primary_feature_id.rsplit(":", 1)
    own_ticker = record["ticker"]
    if predictor_ticker in (own_ticker, "MARKET", ""):
        return False, ""
    return True, (
        f"primary condition feature_id={primary_feature_id!r} references peer ticker "
        f"{predictor_ticker!r}, not self ({own_ticker!r}) and not MARKET -- ambiguous "
        f"whether to group by predictor ticker, outcome ticker, or neither"
    )


def cross_ticker_family_key(pattern_id: str, record: dict) -> tuple[str | None, str]:
    ambiguous, note = is_ambiguous_lead_lag(record)
    if ambiguous:
        return None, note
    conditions = record.get("conditions") or []
    if not conditions:
        return None, "no conditions -- cannot form a family key"
    primary_feature_id = conditions[0]["feature_id"]
    if ":" not in primary_feature_id:
        return None, f"primary feature_id {primary_feature_id!r} does not follow the key:ticker convention"
    feature_base, _ticker = strip_ticker_and_window(primary_feature_id)
    target_id = record["target_id"]
    if ":" not in target_id:
        return None, f"target_id {target_id!r} does not follow the key:ticker convention"
    target_base, _target_ticker = strip_ticker_and_window(target_id)
    regime_flag = "regime" if record.get("regime_filter") else "no_regime"
    return f"{feature_base}|{target_base}|{regime_flag}", ""


def hhi(counts: list[int]) -> float:
    total = sum(counts)
    if total == 0:
        return 0.0
    return sum((c / total) ** 2 for c in counts)


def benjamini_yekutieli(p_values: list[float], *, fdr_alpha: float) -> list[bool]:
    """Standard BY procedure: like BH, but the per-rank threshold is
    divided by the harmonic number c(n) = sum_{i=1}^n 1/i, which is valid
    under arbitrary (including positive) dependence -- unlike BH, which
    assumes independence or positive regression dependence. Implemented
    fresh here (no `benjamini_yekutieli` exists in
    `patterns/multiple_testing.py`, which only has `benjamini_hochberg`)
    purely as a DESCRIPTIVE comparison, per the original Step 1 scope: this
    script does not choose BH over BY or vice versa for any gate."""
    n = len(p_values)
    if n == 0:
        return []
    c_n = sum(1.0 / i for i in range(1, n + 1))
    order = sorted(range(n), key=lambda i: p_values[i])
    threshold_rank = -1
    for rank, idx in enumerate(order, start=1):
        threshold = (rank / (n * c_n)) * fdr_alpha
        if p_values[idx] <= threshold:
            threshold_rank = rank
    accept = [False] * n
    if threshold_rank >= 0:
        for rank, idx in enumerate(order, start=1):
            if rank <= threshold_rank:
                accept[idx] = True
    return accept


def benjamini_hochberg(p_values: list[float], *, fdr_alpha: float) -> list[bool]:
    n = len(p_values)
    if n == 0:
        return []
    order = sorted(range(n), key=lambda i: p_values[i])
    threshold_rank = -1
    for rank, idx in enumerate(order, start=1):
        threshold = (rank / n) * fdr_alpha
        if p_values[idx] <= threshold:
            threshold_rank = rank
    accept = [False] * n
    if threshold_rank >= 0:
        for rank, idx in enumerate(order, start=1):
            if rank <= threshold_rank:
                accept[idx] = True
    return accept


def main() -> None:
    registry = load_registry()
    v1, latest = revisions_by_pattern(registry)

    validated_pids = [pid for pid, r in latest.items() if r["validation_status"] == "validated"]
    total_validated = len(validated_pids)

    # ---- ambiguity partition ----
    ambiguous: dict[str, str] = {}
    keyed: dict[str, str] = {}
    unkeyable: dict[str, str] = {}
    for pid in validated_pids:
        key, note = cross_ticker_family_key(pid, latest[pid])
        amb, amb_note = is_ambiguous_lead_lag(latest[pid])
        if amb:
            ambiguous[pid] = amb_note
        elif key is None:
            unkeyable[pid] = note
        else:
            keyed[pid] = key

    # ---- cross-check: reconstruct real candidate_family_key() (same-ticker, unmodified function) ----
    same_ticker_family_key_by_pid = {}
    reconstruction_errors = []
    for pid in validated_pids:
        try:
            candidate = reconstruct_candidate(pid, latest[pid])
            same_ticker_family_key_by_pid[pid] = candidate_family_key(candidate)
        except Exception as exc:  # noqa: BLE001 -- deliberately broad: this is a diagnostic cross-check, not production code
            reconstruction_errors.append(f"{pid}: {type(exc).__name__}: {exc}")

    # ---- families ----
    families: dict[str, list[str]] = defaultdict(list)
    for pid, key in keyed.items():
        families[key].append(pid)

    n_families = len(families)
    family_sizes = sorted((len(members) for members in families.values()), reverse=True)
    tickers_per_family = {key: len({latest[pid]["ticker"] for pid in members}) for key, members in families.items()}

    # ---- Table 1: universe reduction ----
    table_1_universe_reduction = {
        "total_validated_patterns": total_validated,
        "excluded_ambiguous_lead_lag": len(ambiguous),
        "excluded_unkeyable": len(unkeyable),
        "analyzed": len(keyed),
        "n_cross_ticker_families": n_families,
        "avg_family_size": statistics.fmean(family_sizes) if family_sizes else None,
        "median_family_size": statistics.median(family_sizes) if family_sizes else None,
        "max_family_size": max(family_sizes) if family_sizes else None,
        "max_family_key": max(families, key=lambda k: len(families[k])) if families else None,
        "min_family_size": min(family_sizes) if family_sizes else None,
    }

    # ---- Table 2: ticker breadth per family ----
    breadth_counter = Counter(tickers_per_family.values())
    table_2_ticker_breadth = {
        "breadth_histogram": dict(sorted(breadth_counter.items())),
        "families_with_1_to_2_tickers": sum(c for b, c in breadth_counter.items() if b <= 2),
        "families_with_5_plus_tickers": sum(c for b, c in breadth_counter.items() if b >= 5),
    }

    # ---- Table 3: same-sign corroboration ----
    same_sign_results = {}
    for key, members in families.items():
        signs = {"positive" if latest[pid]["expectancy"] > 0 else ("negative" if latest[pid]["expectancy"] < 0 else "zero") for pid in members}
        same_sign_results[key] = "all_same_sign" if len(signs) == 1 else "mixed_sign"
    table_3_same_sign_corroboration = {
        "all_same_sign_families": sum(1 for v in same_sign_results.values() if v == "all_same_sign"),
        "mixed_sign_families": sum(1 for v in same_sign_results.values() if v == "mixed_sign"),
        "note": (
            "Every family is composed exclusively of PatternStatus.VALIDATED patterns, which "
            "Step 1.6 (a later, independent step) established are 100% positive-expectancy at "
            "the individual-pattern level in this real run -- so 'all_same_sign' here is "
            "expected to be universal and is a consequence of that upstream fact, not new "
            "cross-ticker corroboration evidence by itself."
        ),
    }

    # ---- Table 4: concentration (HHI + dominant-ticker share) ----
    hhi_values = []
    dominant_shares = []
    for key, members in families.items():
        ticker_counts = Counter(latest[pid]["ticker"] for pid in members)
        counts = list(ticker_counts.values())
        h = hhi(counts)
        hhi_values.append(h)
        dominant_shares.append(max(counts) / len(members))
    table_4_concentration = {
        "hhi_median": statistics.median(hhi_values) if hhi_values else None,
        "hhi_mean": statistics.fmean(hhi_values) if hhi_values else None,
        "dominant_ticker_share_median": statistics.median(dominant_shares) if dominant_shares else None,
        "dominant_ticker_share_mean": statistics.fmean(dominant_shares) if dominant_shares else None,
    }

    # ---- Table 5: candidate corroborated families (top by total matched observations) ----
    family_matched_obs = {
        key: sum(latest[pid]["sample_size"] for pid in members) for key, members in families.items()
    }
    top_families = sorted(family_matched_obs.items(), key=lambda kv: kv[1], reverse=True)[:20]
    table_5_top_corroborated_families = [
        {
            "family_key": key,
            "member_count": len(families[key]),
            "unique_tickers": tickers_per_family[key],
            "total_matched_observations": obs,
        }
        for key, obs in top_families
    ]

    # ---- family_size=1 diagnostic (TD-74) ----
    v1_family_sizes = [v1[pid]["family_size"] for pid in validated_pids]
    latest_family_sizes = [latest[pid]["family_size"] for pid in validated_pids]
    family_size_diagnostic = {
        "v1_family_size_min": min(v1_family_sizes),
        "v1_family_size_max": max(v1_family_sizes),
        "v1_family_size_mean": statistics.fmean(v1_family_sizes),
        "v1_family_size_eq_1_count": sum(1 for s in v1_family_sizes if s == 1),
        "latest_family_size_min": min(latest_family_sizes),
        "latest_family_size_max": max(latest_family_sizes),
        "latest_family_size_eq_1_count": sum(1 for s in latest_family_sizes if s == 1),
        "v1_block_bootstrap_p_null_count": sum(1 for pid in validated_pids if v1[pid].get("block_bootstrap_p_value") is None),
        "latest_block_bootstrap_p_null_count": sum(1 for pid in validated_pids if latest[pid].get("block_bootstrap_p_value") is None),
        "interpretation": (
            "v1 (DISCOVERED) carries the real, varying family_size computed by discover()'s "
            "group_by_family()/family_corrected_p_value() (patterns/engine.py, patterns/"
            "multiple_testing_family.py). validate()/final_holdout() each call build_pattern() "
            "again without re-passing family_size/block_bootstrap_p_value/deflated_sharpe_ratio "
            "forward -- build_pattern()'s own defaults (family_size=1, the p-value/DSR fields "
            "None) silently overwrite the real v1 values on every later revision. This is a "
            "data-loss bug in how later revisions are built, not evidence that family "
            "correction was never applied -- it WAS applied once, correctly, at discover() time "
            "(see the v1 statistics above), and its record was simply not carried forward."
        ),
    }

    # ---- BH vs BY descriptive comparison (v1 block_bootstrap_p_value) ----
    bh_by_comparison = None
    p_values_by_pid = {pid: v1[pid]["block_bootstrap_p_value"] for pid in validated_pids if v1[pid].get("block_bootstrap_p_value") is not None}
    if p_values_by_pid:
        pids_ordered = list(p_values_by_pid.keys())
        p_values = [p_values_by_pid[pid] for pid in pids_ordered]
        bh_accept = benjamini_hochberg(p_values, fdr_alpha=0.05)
        by_accept = benjamini_yekutieli(p_values, fdr_alpha=0.05)
        bh_by_comparison = {
            "n": len(p_values),
            "alpha": 0.05,
            "bh_passes": sum(bh_accept),
            "bh_pass_rate": sum(bh_accept) / len(p_values),
            "by_passes": sum(by_accept),
            "by_pass_rate": sum(by_accept) / len(p_values),
            "note": (
                "Purely descriptive comparison over v1's already-persisted block_bootstrap_p_value "
                "field -- this analysis does NOT choose BH or BY as the correction to use for any "
                "gate; that choice remains explicitly deferred to Promotion Gate design, per the "
                "hard boundary instruction."
            ),
        }
    else:
        bh_by_comparison = {"note": "No v1 block_bootstrap_p_value values available for this population -- comparison skipped, not fabricated."}

    result = {
        "analysis": "Mission 3 Step 1: Cross-Ticker Family-Collapse Analysis",
        "reproduction_notice": {
            "is_reproduction": True,
            "reason": (
                "The original Step 1 script/report/JSON were never committed and were lost when "
                "this environment's working tree reset between conversation turns. This is a "
                "same-session reconstruction from the documented methodology (recorded in this "
                "conversation's own summary of what Step 1 computed), not a byte-identical "
                "retrieval of the original file. No threshold, family-key component, or scope "
                "decision was altered, tightened, loosened, or reinterpreted relative to that "
                "documented methodology."
            ),
        },
        "scope": {
            "population": "The 1,773 real PatternStatus.VALIDATED patterns in the Mission 2 registry.",
            "excludes": "Family analysis never selects/ranks by outcome -- every family above is reported regardless of its member patterns' expectancy magnitude or sign.",
        },
        "ambiguous_lead_lag_patterns": {
            "count": len(ambiguous),
            "examples": dict(list(ambiguous.items())[:10]),
        },
        "unkeyable_patterns": {
            "count": len(unkeyable),
            "examples": dict(list(unkeyable.items())[:10]),
        },
        "candidate_family_key_reconstruction_errors": reconstruction_errors,
        "table_1_universe_reduction": table_1_universe_reduction,
        "table_2_ticker_breadth": table_2_ticker_breadth,
        "table_3_same_sign_corroboration": table_3_same_sign_corroboration,
        "table_4_concentration": table_4_concentration,
        "table_5_top_corroborated_families": table_5_top_corroborated_families,
        "family_size_1_diagnostic": family_size_diagnostic,
        "bh_vs_by_descriptive_comparison": bh_by_comparison,
    }

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with OUTPUT_PATH.open("w") as f:
        json.dump(result, f, indent=2, default=str, sort_keys=True)
    print(f"Wrote {OUTPUT_PATH}")
    print(f"n_families={n_families}, analyzed={len(keyed)}, ambiguous={len(ambiguous)}, unkeyable={len(unkeyable)}")


if __name__ == "__main__":
    main()
