from __future__ import annotations

import json
from pathlib import Path
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "results"
SOURCES = ("shaban", "al_refaey")
METRICS = ("ret", "illiquidity", "volatility", "abnormal_volume", "range")
RNG = np.random.default_rng(20260814)
PERMUTATIONS = 200


def robust_edges(source: str, metric: str) -> pd.DataFrame:
    rel_path = OUT / f"{source}_{metric}_relationships.csv"
    val_path = OUT / f"{source}_{metric}_validation.csv"
    if not rel_path.exists() or rel_path.stat().st_size == 0 or not val_path.exists() or val_path.stat().st_size == 0:
        return pd.DataFrame()
    rel = pd.read_csv(rel_path)
    val = pd.read_csv(val_path)
    if rel.empty or val.empty:
        return pd.DataFrame()
    keys = val.loc[val["temporal_status"] == "REPLICATED", ["leader", "follower", "lag"]]
    out = rel.merge(keys.drop_duplicates(), on=["leader", "follower", "lag"], how="inner")
    return out[out["fdr_significant"].astype(bool)].copy()


def network_stats(edges: pd.DataFrame) -> dict:
    if edges.empty:
        return {"edges": 0, "nodes": 0, "top_1pct_edge_share": None, "top_5pct_edge_share": None, "top_10pct_edge_share": None, "median_leader_contribution": None, "max_out_degree": None, "max_in_degree": None, "reciprocal_pairs": 0}
    leader_counts = edges["leader"].value_counts()
    follower_counts = edges["follower"].value_counts()
    n_edges = len(edges)
    n_nodes = len(set(edges["leader"]).union(set(edges["follower"])))
    pair_set = {(r.leader, r.follower) for r in edges.itertuples()}
    reciprocal = sum((b, a) in pair_set for a, b in pair_set) // 2
    def share(frac: float) -> float:
        k = max(1, int(np.ceil(len(leader_counts) * frac)))
        return float(leader_counts.head(k).sum() / n_edges)
    return {"edges": int(n_edges), "nodes": int(n_nodes), "top_1pct_edge_share": share(0.01), "top_5pct_edge_share": share(0.05), "top_10pct_edge_share": share(0.10), "median_leader_contribution": float(leader_counts.median()), "max_out_degree": int(leader_counts.max()), "max_in_degree": int(follower_counts.max()), "reciprocal_pairs": int(reciprocal)}


def null_max_indegree(edges: pd.DataFrame) -> dict:
    if edges.empty:
        return {"permutations": 0, "observed_max_in_degree": None, "null_mean_max_in_degree": None, "null_p_ge_observed": None}
    observed = int(edges["follower"].value_counts().max())
    universe = np.array(sorted(set(edges["leader"]).union(set(edges["follower"]))))
    leaders = edges["leader"].to_numpy()
    maxima = []
    for _ in range(PERMUTATIONS):
        assigned = RNG.choice(universe, size=len(edges), replace=True)
        # Remove self-edges without preserving observed degree counts; this is a counterpart-assignment null.
        self_edges = assigned == leaders
        if self_edges.any():
            assigned[self_edges] = RNG.choice(universe, size=int(self_edges.sum()), replace=True)
        maxima.append(int(pd.Series(assigned).value_counts().max()))
    maxima = np.asarray(maxima)
    return {"permutations": PERMUTATIONS, "observed_max_in_degree": observed, "null_mean_max_in_degree": float(maxima.mean()), "null_p95_max_in_degree": float(np.quantile(maxima, 0.95)), "null_p_ge_observed": float((1 + (maxima >= observed).sum()) / (PERMUTATIONS + 1)), "null_purpose": "uniform randomized counterpart assignment; exploratory only"}


summary = {"sources": {}, "cross_source_replication": {}}
for source in SOURCES:
    summary["sources"][source] = {}
    for metric in METRICS:
        edges = robust_edges(source, metric)
        stats_out = network_stats(edges)
        stats_out["null_model"] = null_max_indegree(edges)
        if not edges.empty:
            leaders = edges.groupby("leader").agg(edge_count=("follower", "size"), unique_followers=("follower", "nunique"), lags=("lag", "nunique")).sort_values(["unique_followers", "edge_count"], ascending=False).head(20).reset_index()
            leaders.to_csv(OUT / f"{source}_{metric}_leaders.csv", index=False)
        summary["sources"][source][metric] = stats_out

for metric in METRICS:
    a = robust_edges("shaban", metric)
    b = robust_edges("al_refaey", metric)
    if a.empty or b.empty:
        summary["cross_source_replication"][metric] = {"shaban_edges": int(len(a)), "al_refaey_edges": int(len(b)), "same_direction_same_lag_edges": 0, "status": "NO_COMPARABLE_ROBUST_EDGES"}
        continue
    ka = a[["leader", "follower", "lag", "direction"]].drop_duplicates()
    kb = b[["leader", "follower", "lag", "direction"]].drop_duplicates()
    inter = ka.merge(kb, on=["leader", "follower", "lag", "direction"], how="inner")
    summary["cross_source_replication"][metric] = {"shaban_edges": int(len(ka)), "al_refaey_edges": int(len(kb)), "same_direction_same_lag_edges": int(len(inter)), "replication_rate_vs_smaller": float(len(inter) / max(1, min(len(ka), len(kb)))), "status": "EXPLORATORY_SOURCE_REPLICATION"}

summary["controls"] = {"market_control": True, "sector_control": False, "sector_control_reason": "No point-in-time sector membership was present in the supplied exploratory datasets; current sector labels would not be temporally safe.", "participant_identity_inferred": False, "investable_alpha_claimed": False}
(OUT / "network_structure_summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
print(json.dumps(summary, ensure_ascii=False, indent=2))
