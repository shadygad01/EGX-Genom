from __future__ import annotations

import json
from pathlib import Path
import re
import numpy as np
import pandas as pd
from scipy.cluster.hierarchy import linkage, fcluster
from scipy.spatial.distance import cdist
from scipy.stats import rankdata

ROOT = Path(__file__).resolve().parent
RAW = ROOT / "raw"
OUT = ROOT / "results"
SOURCES = ("shaban", "al_refaey")
RNG = np.random.default_rng(20260814)


def numeric(series):
    cleaned = series.astype(str).str.replace(",", "", regex=False).str.replace("%", "", regex=False)
    mult = cleaned.str.extract(r"([KMB])$", expand=False).map({"K": 1e3, "M": 1e6, "B": 1e9}).fillna(1.0)
    return pd.to_numeric(cleaned.str.replace(r"[KMB]$", "", regex=True), errors="coerce") * mult


def load(source):
    result = {}
    for path in sorted((RAW / source).rglob("*.csv")):
        frame = pd.read_csv(path)
        if not {"Date", "Open", "High", "Low"}.issubset(frame.columns):
            continue
        close = "Close" if "Close" in frame.columns else "Price" if "Price" in frame.columns else None
        volume = "Volume" if "Volume" in frame.columns else "Vol." if "Vol." in frame.columns else None
        if not close or not volume:
            continue
        dates = pd.to_datetime(frame["Date"], errors="coerce", dayfirst=source == "shaban", format="mixed", utc=source != "shaban").dt.tz_localize(None)
        out = pd.DataFrame({"close": numeric(frame[close]).to_numpy(), "high": numeric(frame["High"]).to_numpy(), "low": numeric(frame["Low"]).to_numpy(), "volume": numeric(frame[volume]).to_numpy()}, index=dates)
        out = out[~out.index.isna()].sort_index()
        out = out[~out.index.duplicated(keep="last")]
        out = out[(out.close > 0) & (out.high > 0) & (out.low > 0)]
        if len(out) < 80:
            continue
        out["ret"] = np.log(out.close).diff()
        out["range"] = ((out.high - out.low) / out.close).replace([np.inf, -np.inf], np.nan)
        value = out.close * out.volume
        out["illiquidity"] = np.log1p((out.ret.abs() / value.replace(0, np.nan)).replace([np.inf, -np.inf], np.nan).clip(lower=0).fillna(0) * 1e8)
        out["volatility"] = out.ret.rolling(20, min_periods=10).std()
        med = out.volume.rolling(20, min_periods=10).median()
        out["abnormal_volume"] = np.log((out.volume / med).replace([np.inf, -np.inf], np.nan))
        symbol = re.sub(r"\s+Historical Data$", "", path.stem, flags=re.I).split("_")[0].upper()
        if symbol in {"EGX 30", "EGX 30 CAPPED", "EGX 70 EWI", "EGX 100", "EGX 100 EWI"}:
            continue
        result[symbol] = out
    return result


def features(stocks, end):
    rets = pd.DataFrame({k: v.ret for k, v in stocks.items()}).sort_index()
    market = rets.median(axis=1)
    records = []
    for symbol, frame in stocks.items():
        data = frame.loc[:end]
        records.append({"symbol": symbol, "mean_ret": data.ret.mean(), "vol_ret": data.ret.std(), "mean_volatility": data.volatility.mean(), "mean_illiquidity": data.illiquidity.mean(), "mean_range": data.range.mean(), "mean_abnormal_volume": data.abnormal_volume.mean(), "market_beta": data.ret.cov(market.loc[data.index]) / max(market.loc[data.index].var(), 1e-12)})
    result = pd.DataFrame(records).set_index("symbol").replace([np.inf, -np.inf], np.nan)
    result = result.dropna(thresh=max(3, len(result.columns) - 2))
    result = result.loc[:, result.notna().any(axis=0)]
    result = result.fillna(result.median(numeric_only=True)).fillna(0.0)
    result = result.replace([np.inf, -np.inf], 0.0)
    return result


def cluster_features(discovery, validation):
    med = discovery.median()
    scale = discovery.quantile(.75) - discovery.quantile(.25)
    scale = scale.replace(0, 1.0)
    x = ((discovery - med) / scale).to_numpy(dtype=float)
    tree = linkage(x, method="ward", metric="euclidean")
    labels = fcluster(tree, t=3.0, criterion="distance") - 1
    train_labels = pd.Series(labels, index=discovery.index, name="cluster")
    val_common = validation.index.intersection(discovery.index)
    val_x = ((validation.loc[val_common] - med) / scale).to_numpy(dtype=float)
    centroids = {label: x[labels == label].mean(axis=0) for label in np.unique(labels)}
    val_labels = np.array([min(centroids, key=lambda label: float(np.linalg.norm(row - centroids[label]))) for row in val_x])
    val_series = pd.Series(val_labels, index=val_common)
    return train_labels, val_series, int(len(np.unique(labels)))


def robust_edges(source, metric):
    rp = OUT / f"{source}_{metric}_relationships.csv"
    vp = OUT / f"{source}_{metric}_validation.csv"
    if not rp.exists() or not vp.exists() or rp.stat().st_size == 0 or vp.stat().st_size == 0:
        return pd.DataFrame()
    rel = pd.read_csv(rp)
    val = pd.read_csv(vp)
    if rel.empty or val.empty:
        return pd.DataFrame()
    keys = val.loc[val.temporal_status == "REPLICATED", ["leader", "follower", "lag"]].drop_duplicates()
    return rel.merge(keys, on=["leader", "follower", "lag"], how="inner").query("fdr_significant == True")


summary = {}
for source in SOURCES:
    stocks = load(source)
    if not stocks:
        continue
    dates = sorted(set().union(*[set(frame.index) for frame in stocks.values()]))
    cutoff = dates[int(len(dates) * 0.60)]
    discovery = features(stocks, cutoff)
    validation = features(stocks, dates[-1])
    train_labels, val_labels, cluster_count = cluster_features(discovery, validation)
    cluster_file = OUT / f"{source}_behavior_clusters.csv"
    pd.DataFrame({"cluster": train_labels}).to_csv(cluster_file)
    source_out = {"stock_count": len(stocks), "feature_count": int(len(discovery.columns)), "discovery_cutoff": str(cutoff), "cluster_count": cluster_count, "cluster_size_distribution": train_labels.value_counts().to_dict(), "cluster_stability_ari": None, "metrics": {}}
    common = train_labels.index.intersection(val_labels.index)
    if len(common) > 10:
        a = train_labels.loc[common].to_numpy()
        b = val_labels.loc[common].to_numpy()
        agree = 0.0
        for label in np.unique(a):
            mask = a == label
            if mask.sum() > 1:
                agree += float(pd.Series(b[mask]).value_counts(normalize=True).iloc[0]) * float(mask.sum())
        source_out["cluster_stability_dominant_share"] = float(agree / len(common))
    for metric in ("ret", "illiquidity", "volatility", "abnormal_volume", "range"):
        edges = robust_edges(source, metric)
        if edges.empty:
            continue
        valid_edges = edges[edges.leader.isin(train_labels.index) & edges.follower.isin(train_labels.index)].copy()
        valid_edges["within_cluster"] = valid_edges.apply(lambda row: train_labels[row.leader] == train_labels[row.follower], axis=1)
        observed = float(valid_edges.within_cluster.mean()) if len(valid_edges) else None
        labels = train_labels.to_numpy()
        node_index = {symbol: i for i, symbol in enumerate(train_labels.index)}
        leader_idx = valid_edges["leader"].map(node_index).to_numpy(dtype=int)
        follower_idx = valid_edges["follower"].map(node_index).to_numpy(dtype=int)
        null = []
        for _ in range(200):
            shuffled = RNG.permutation(labels)
            null.append(float(np.mean(shuffled[leader_idx] == shuffled[follower_idx])))
        source_out["metrics"][metric] = {"robust_edges": int(len(valid_edges)), "within_cluster_share": observed, "null_mean_within_cluster_share": float(np.mean(null)) if null else None, "null_p95_within_cluster_share": float(np.quantile(null, .95)) if null else None, "cluster_propagation_candidate": bool(observed is not None and null and observed > np.quantile(null, .95))}
    summary[source] = source_out

(OUT / "cluster_propagation_summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
print(json.dumps(summary, ensure_ascii=False, indent=2))
