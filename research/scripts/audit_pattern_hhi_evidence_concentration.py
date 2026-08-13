"""Mission 3 -- HHI Evidence-Concentration Audit.

Applies the diagnostic HHI (Herfindahl-Hirschman Index) bands Manus AI's
calibration research proposed (`docs/PATTERN_PROMOTION_GATE_CALIBRATION_RESEARCH_PART2.md`
Part 1 Section 5.2: <0.15 / 0.15-0.25 / 0.25-0.40 / >0.40) to the real
Mission 2 registry's cross-ticker families, reporting how many families
(and how many patterns) fall into each band.

This is a **read-only, descriptive audit**, in the same spirit as Step 1's
`analyze_cross_ticker_family_collapse.py` (Table 4 of which already
reports the aggregate mean/median HHI across all families -- 0.169 / 0.150
-- but not a per-family distribution across bands). It:

  - Never chooses or adopts an HHI ceiling. It only counts how many
    families fall into each of Manus's proposed diagnostic bands.
  - Never modifies the registry, any `Pattern.validation_status`, or any
    other persisted field.
  - Never creates a `PromotionCase` or any promotion/rejection verdict.
  - Reuses the real family-construction and HHI logic already established
    by Step 1 (`cross_ticker_family_key`, `is_ambiguous_lead_lag`,
    `strip_ticker_and_window`, `hhi`), copied here unmodified rather than
    reinvented, since `research/scripts/` is not an importable package
    (no `__init__.py`) -- see that script's own docstring for the full
    methodology rationale.

Reports HHI under **two** declared denominators, per Manus's own point
that "the denominator must be declared... [member count, matched
observations, and equal ticker weights] produce different HHIs":

  1. `member_count` -- one vote per pattern-family-member (matches Step
     1's own Table 4 methodology exactly, for direct comparability).
  2. `matched_observations` -- weighted by each pattern's own
     `sample_size` (a family where one ticker's patterns individually
     matched far more observations is more concentrated under this
     denominator than under member-count alone).
"""

from __future__ import annotations

import json
import re
import statistics
from collections import Counter, defaultdict
from pathlib import Path

REGISTRY_PATH = Path("/tmp/agx_real_run/patterns/registry.json")
OUTPUT_PATH = (
    Path(__file__).resolve().parents[1] / "data" / "pattern_hhi_evidence_concentration_audit" / "analysis.json"
)

_WINDOW_SUFFIX_RE = re.compile(r"_\d+d$")

# Manus AI's proposed diagnostic bands (PATTERN_PROMOTION_GATE_CALIBRATION_RESEARCH_PART2.md
# Part 1 Section 5.2). Reported here as-is -- not adopted, not calibrated,
# not a pass/fail gate. Band boundaries are inclusive on the lower edge.
HHI_BANDS = [
    ("diffuse (<0.15)", 0.0, 0.15),
    ("moderate (0.15-0.25)", 0.15, 0.25),
    ("high (0.25-0.40)", 0.25, 0.40),
    ("very_concentrated (>0.40)", 0.40, float("inf")),
]


def band_for(value: float) -> str:
    for label, lo, hi in HHI_BANDS:
        if lo <= value < hi:
            return label
    return HHI_BANDS[-1][0]


def load_registry() -> dict[str, list[dict]]:
    with REGISTRY_PATH.open() as f:
        return json.load(f)


def latest_revisions(registry: dict[str, list[dict]]) -> dict[str, dict]:
    return {pid: sorted(revs, key=lambda r: r["version"])[-1] for pid, revs in registry.items()}


def strip_ticker_and_window(feature_or_target_id: str) -> tuple[str, str]:
    base, ticker = feature_or_target_id.rsplit(":", 1)
    stripped = _WINDOW_SUFFIX_RE.sub("", base)
    return stripped, ticker


def is_ambiguous_lead_lag(record: dict) -> bool:
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


def cross_ticker_family_key(record: dict) -> str | None:
    if is_ambiguous_lead_lag(record):
        return None
    conditions = record.get("conditions") or []
    if not conditions:
        return None
    primary_feature_id = conditions[0]["feature_id"]
    if ":" not in primary_feature_id:
        return None
    feature_base, _ticker = strip_ticker_and_window(primary_feature_id)
    target_id = record["target_id"]
    if ":" not in target_id:
        return None
    target_base, _target_ticker = strip_ticker_and_window(target_id)
    regime_flag = "regime" if record.get("regime_filter") else "no_regime"
    return f"{feature_base}|{target_base}|{regime_flag}"


def hhi(shares: list[float]) -> float:
    total = sum(shares)
    if total == 0:
        return 0.0
    return sum((s / total) ** 2 for s in shares)


def main() -> None:
    registry = load_registry()
    latest = latest_revisions(registry)

    validated_pids = [pid for pid, r in latest.items() if r["validation_status"] == "validated"]

    families: dict[str, list[str]] = defaultdict(list)
    excluded = 0
    for pid in validated_pids:
        key = cross_ticker_family_key(latest[pid])
        if key is None:
            excluded += 1
        else:
            families[key].append(pid)

    per_family_records = []
    for key, members in families.items():
        ticker_member_counts = Counter(latest[pid]["ticker"] for pid in members)
        member_count_hhi = hhi(list(ticker_member_counts.values()))

        obs_by_ticker: dict[str, int] = defaultdict(int)
        for pid in members:
            obs_by_ticker[latest[pid]["ticker"]] += latest[pid]["sample_size"]
        matched_obs_hhi = hhi(list(obs_by_ticker.values()))

        per_family_records.append(
            {
                "family_key": key,
                "member_count": len(members),
                "unique_tickers": len(ticker_member_counts),
                "member_count_hhi": member_count_hhi,
                "member_count_band": band_for(member_count_hhi),
                "matched_observations_hhi": matched_obs_hhi,
                "matched_observations_band": band_for(matched_obs_hhi),
                "total_matched_observations": sum(obs_by_ticker.values()),
                "dominant_ticker_by_observations": max(obs_by_ticker, key=obs_by_ticker.get),
                "dominant_ticker_observation_share": max(obs_by_ticker.values()) / sum(obs_by_ticker.values()),
            }
        )

    def band_summary(field: str) -> dict:
        counts = Counter(rec[field] for rec in per_family_records)
        pattern_counts: Counter = Counter()
        for rec in per_family_records:
            pattern_counts[rec[field]] += rec["member_count"]
        n_families = len(per_family_records)
        n_patterns = sum(rec["member_count"] for rec in per_family_records)
        return {
            label: {
                "family_count": counts.get(label, 0),
                "family_pct": (counts.get(label, 0) / n_families) if n_families else None,
                "pattern_count": pattern_counts.get(label, 0),
                "pattern_pct": (pattern_counts.get(label, 0) / n_patterns) if n_patterns else None,
            }
            for label, _lo, _hi in HHI_BANDS
        }

    member_count_hhis = [rec["member_count_hhi"] for rec in per_family_records]
    matched_obs_hhis = [rec["matched_observations_hhi"] for rec in per_family_records]

    most_concentrated = sorted(per_family_records, key=lambda r: r["matched_observations_hhi"], reverse=True)[:10]

    result = {
        "analysis": "Mission 3 -- HHI Evidence-Concentration Audit",
        "purpose": (
            "Descriptive only. Buckets the real Mission 2 registry's cross-ticker families "
            "into Manus AI's proposed diagnostic HHI bands "
            "(PATTERN_PROMOTION_GATE_CALIBRATION_RESEARCH_PART2.md Part 1 Section 5.2). "
            "Does not adopt, calibrate, or select any HHI ceiling. Does not compute a "
            "pass/fail verdict for any pattern or family. Does not modify the registry."
        ),
        "scope": {
            "population": "The 1,773 real PatternStatus.VALIDATED patterns in the Mission 2 registry.",
            "family_construction": (
                "Identical cross_ticker_family_key methodology as "
                "analyze_cross_ticker_family_collapse.py (Step 1): strip ticker + window suffix "
                "from the primary feature and target, keep regime-filter presence as a "
                "component. Ambiguous lead/lag patterns (primary condition references a peer "
                "ticker) are excluded from family construction, same as Step 1."
            ),
            "excluded_ambiguous_or_unkeyable": excluded,
            "n_families_analyzed": len(families),
            "n_patterns_analyzed": sum(len(m) for m in families.values()),
        },
        "hhi_bands_used": {label: [lo, hi] for label, lo, hi in HHI_BANDS},
        "member_count_hhi": {
            "median": statistics.median(member_count_hhis) if member_count_hhis else None,
            "mean": statistics.fmean(member_count_hhis) if member_count_hhis else None,
            "band_summary": band_summary("member_count_band"),
            "note": (
                "One vote per family member (pattern), regardless of how many observations that "
                "pattern individually matched. Identical methodology and denominator to Step 1's "
                "Table 4 (median 0.150, mean 0.169 there) -- this section's median/mean should "
                "reproduce those values exactly; the band breakdown here is new."
            ),
        },
        "matched_observations_hhi": {
            "median": statistics.median(matched_obs_hhis) if matched_obs_hhis else None,
            "mean": statistics.fmean(matched_obs_hhis) if matched_obs_hhis else None,
            "band_summary": band_summary("matched_observations_band"),
            "note": (
                "Weighted by each pattern's own sample_size (matched observations), not member "
                "count. A family where one ticker's patterns matched far more observations than "
                "others is more concentrated under this denominator, even if member counts are "
                "balanced. This is a NEW metric -- Step 1 did not compute this variant."
            ),
        },
        "most_concentrated_families_by_matched_observations": most_concentrated,
        "non_decisions": (
            "This audit selects no HHI ceiling, computes no promotion/rejection verdict, creates "
            "no PromotionCase, and modifies no persisted registry data. It is evidence for a "
            "future product-owner calibration decision (PATTERN_PROMOTION_GATE_DESIGN.md v2.2 "
            "Section 14's HHI ceiling row), not a decision itself."
        ),
    }

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with OUTPUT_PATH.open("w") as f:
        json.dump(result, f, indent=2, default=str, sort_keys=True)
    print(f"Wrote {OUTPUT_PATH}")
    print(f"n_families={len(families)}, excluded={excluded}")
    print("member_count band summary:", band_summary("member_count_band"))
    print("matched_observations band summary:", band_summary("matched_observations_band"))


if __name__ == "__main__":
    main()
