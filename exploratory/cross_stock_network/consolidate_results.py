from __future__ import annotations

import json
from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "results"
SOURCES = ("shaban", "al_refaey")
METRICS = ("ret", "illiquidity", "volatility", "abnormal_volume", "range")

all_results = []
for source in SOURCES:
    metrics = {}
    for metric in METRICS:
        rel_path = OUT / f"{source}_{metric}_relationships.csv"
        val_path = OUT / f"{source}_{metric}_validation.csv"
        if not rel_path.exists():
            continue
        if rel_path.stat().st_size == 0:
            metrics[metric] = {"pairwise_lag_tests": 0, "raw_significant": 0, "fdr_significant": 0, "temporal_validated": 0, "validation_rows": 0, "status": "NO_VALID_TESTS"}
            continue
        try:
            rel = pd.read_csv(rel_path)
        except pd.errors.EmptyDataError:
            metrics[metric] = {"pairwise_lag_tests": 0, "raw_significant": 0, "fdr_significant": 0, "temporal_validated": 0, "validation_rows": 0, "status": "NO_VALID_TESTS"}
            continue
        val = pd.read_csv(val_path) if val_path.exists() and val_path.stat().st_size > 0 else pd.DataFrame()
        replicated = int((val.get("temporal_status", pd.Series(dtype=str)) == "REPLICATED").sum())
        metrics[metric] = {
            "pairwise_lag_tests": int(len(rel)),
            "raw_significant": int(rel.get("raw_significant", pd.Series(dtype=bool)).sum()),
            "fdr_significant": int(rel.get("fdr_significant", pd.Series(dtype=bool)).sum()),
            "temporal_validated": replicated,
            "validation_rows": int(len(val)),
            "top_leaders_by_all_tests": rel["leader"].value_counts().head(10).to_dict() if "leader" in rel else {},
            "top_leaders_by_fdr": rel.loc[rel.get("fdr_significant", False), "leader"].value_counts().head(10).to_dict() if "leader" in rel else {},
        }
    if metrics:
        all_results.append({"source": source, "metrics": metrics})
(OUT / "summary_all_metrics.json").write_text(json.dumps(all_results, ensure_ascii=False, indent=2), encoding="utf-8")
print(json.dumps(all_results, ensure_ascii=False, indent=2))
