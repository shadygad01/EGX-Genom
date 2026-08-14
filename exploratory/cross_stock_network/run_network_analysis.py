from __future__ import annotations

import json
import math
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

import numpy as np
import pandas as pd
from scipy import stats

ROOT = Path(__file__).resolve().parent
RAW = ROOT / "raw"
OUT = ROOT / "results"
OUT.mkdir(parents=True, exist_ok=True)
LAGS = (1, 2, 3, 5)
MIN_OBS = 80
DISCOVERY_FRAC = 0.60
ALPHA = 0.05


INDEX_NAMES = {"EGX 30", "EGX 30 CAPPED", "EGX 70 EWI", "EGX 100", "EGX 100 EWI"}


def norm_symbol(path: Path) -> str:
    stem = path.stem
    stem = re.sub(r"\s+Historical Data$", "", stem, flags=re.I)
    return stem.split("_")[0].upper()


def parse_dates(values: pd.Series, source: str) -> pd.Series:
    if source == "shaban":
        return pd.to_datetime(values, errors="coerce", dayfirst=True, format="mixed").dt.tz_localize(None)
    return pd.to_datetime(values, errors="coerce", utc=True).dt.tz_localize(None)


def numeric(series: pd.Series) -> pd.Series:
    cleaned = series.astype(str).str.replace(",", "", regex=False).str.replace("%", "", regex=False)
    multipliers = cleaned.str.extract(r"([KMB])$", expand=False).map({"K": 1e3, "M": 1e6, "B": 1e9}).fillna(1.0)
    cleaned = cleaned.str.replace(r"[KMB]$", "", regex=True)
    return pd.to_numeric(cleaned, errors="coerce") * multipliers


def load_stock(path: Path, source: str) -> pd.DataFrame | None:
    frame = pd.read_csv(path)
    if not {"Date", "Open", "High", "Low"}.issubset(frame.columns):
        return None
    close_col = "Close" if "Close" in frame.columns else "Price" if "Price" in frame.columns else None
    if close_col is None:
        return None
    volume_col = "Volume" if "Volume" in frame.columns else "Vol." if "Vol." in frame.columns else None
    if volume_col is None:
        return None
    out = pd.DataFrame(index=parse_dates(frame["Date"], source))
    out["close"] = numeric(frame[close_col]).to_numpy()
    out["high"] = numeric(frame["High"]).to_numpy()
    out["low"] = numeric(frame["Low"]).to_numpy()
    out["volume"] = numeric(frame[volume_col]).to_numpy()
    out = out[~out.index.isna()].sort_index()
    out = out[~out.index.duplicated(keep="last")]
    out = out[(out["close"] > 0) & (out["high"] > 0) & (out["low"] > 0)]
    if len(out) < MIN_OBS:
        return None
    ret = np.log(out["close"]).diff()
    value = out["close"] * out["volume"]
    out["ret"] = ret.replace([np.inf, -np.inf], np.nan)
    out["range"] = ((out["high"] - out["low"]) / out["close"]).replace([np.inf, -np.inf], np.nan)
    out["amihud_proxy"] = (out["ret"].abs() / value.replace(0, np.nan)).replace([np.inf, -np.inf], np.nan)
    out["illiquidity"] = np.log1p(out["amihud_proxy"].clip(lower=0).fillna(0) * 1e8)
    rolling_median = out["volume"].rolling(20, min_periods=10).median()
    out["abnormal_volume"] = np.log((out["volume"] / rolling_median).replace([np.inf, -np.inf], np.nan))
    out["volatility"] = out["ret"].rolling(20, min_periods=10).std()
    return out


def load_source(source: str) -> dict[str, pd.DataFrame]:
    directory = RAW / source
    paths = sorted(directory.rglob("*.csv"))
    result = {}
    for path in paths:
        symbol = norm_symbol(path)
        if symbol in INDEX_NAMES:
            continue
        frame = load_stock(path, source)
        if frame is not None:
            result[symbol] = frame
    return result


def cross_section(stocks: dict[str, pd.DataFrame], field: str) -> pd.DataFrame:
    values = {symbol: frame[field] for symbol, frame in stocks.items()}
    return pd.DataFrame(values).sort_index()


def ols_one(y: np.ndarray, x: np.ndarray, controls: list[np.ndarray]) -> tuple[float, float, float, int] | None:
    cols = [np.ones(len(y)), x, *controls]
    design = np.column_stack(cols)
    good = np.isfinite(design).all(axis=1) & np.isfinite(y)
    design, y = design[good], y[good]
    n, k = design.shape
    if n < max(MIN_OBS, k + 15):
        return None
    try:
        beta, *_ = np.linalg.lstsq(design, y, rcond=None)
        resid = y - design @ beta
        dof = n - k
        s2 = (resid @ resid) / dof
        cov = s2 * np.linalg.pinv(design.T @ design)
        se = math.sqrt(max(cov[1, 1], 1e-30))
        t = beta[1] / se
        p = 2 * stats.t.sf(abs(t), dof)
        return float(beta[1]), float(t), float(p), int(n)
    except (ValueError, np.linalg.LinAlgError, FloatingPointError):
        return None


def benjamini_hochberg(pvalues: pd.Series) -> pd.Series:
    result = pd.Series(np.nan, index=pvalues.index, dtype=float)
    valid = pvalues.dropna()
    if valid.empty:
        return result
    order = np.argsort(valid.to_numpy())
    sorted_p = valid.to_numpy()[order]
    m = len(sorted_p)
    adjusted = np.minimum.accumulate((sorted_p * m / np.arange(1, m + 1))[::-1])[::-1]
    adjusted = np.clip(adjusted, 0, 1)
    out = pd.Series(adjusted, index=valid.index[order])
    result.loc[out.index] = out
    return result


def relationship_test(source: str, stocks: dict[str, pd.DataFrame], metric: str) -> pd.DataFrame:
    panel = cross_section(stocks, metric).replace([np.inf, -np.inf], np.nan)
    returns = cross_section(stocks, "ret").replace([np.inf, -np.inf], np.nan)
    market = returns.median(axis=1, skipna=True)
    symbols = sorted(panel.columns)
    rows = []
    for lag in LAGS:
        lagged = panel.shift(lag)
        own_lag = panel.shift(1)
        market_lag = market.shift(lag)
        for follower in symbols:
            base = pd.concat([panel[follower], own_lag[follower], market, market_lag], axis=1).dropna()
            if len(base) < MIN_OBS:
                continue
            y = base.iloc[:, 0].to_numpy(dtype=float)
            controls = np.column_stack([np.ones(len(base)), base.iloc[:, 1:].to_numpy(dtype=float)])
            y_res = y - controls @ np.linalg.lstsq(controls, y, rcond=None)[0]
            for leader in symbols:
                if leader == follower:
                    continue
                x_series = lagged[leader].reindex(base.index)
                valid = np.isfinite(x_series.to_numpy(dtype=float))
                if valid.sum() < MIN_OBS:
                    continue
                c = controls[valid]
                x = x_series.to_numpy(dtype=float)[valid]
                yr = y_res[valid]
                x_res = x - c @ np.linalg.lstsq(c, x, rcond=None)[0]
                denom = float(x_res @ x_res)
                if denom <= 1e-18:
                    continue
                beta = float(x_res @ yr / denom)
                residual = yr - beta * x_res
                dof = len(x_res) - c.shape[1] - 1
                if dof <= 0:
                    continue
                se = math.sqrt(max(float(residual @ residual) / dof / denom, 1e-30))
                tstat = beta / se
                pvalue = float(2 * stats.t.sf(abs(tstat), dof))
                rows.append({"source": source, "metric": metric, "leader": leader, "follower": follower, "lag": lag, "beta": beta, "t_stat": float(tstat), "p_value": pvalue, "n_obs": int(len(x_res))})
    result = pd.DataFrame(rows)
    if result.empty:
        return result
    result["q_value"] = benjamini_hochberg(result["p_value"])
    result["raw_significant"] = result["p_value"] < ALPHA
    result["fdr_significant"] = result["q_value"] < ALPHA
    result["direction"] = np.where(result["beta"] > 0, "positive", "negative")
    return result


def temporal_validate(discovery: pd.DataFrame, stocks: dict[str, pd.DataFrame], metric: str) -> pd.DataFrame:
    if discovery.empty:
        return discovery.assign(validation_p=np.nan, validation_beta=np.nan, temporal_status="NO_DATA")
    panel = cross_section(stocks, metric)
    returns = cross_section(stocks, "ret")
    market = returns.median(axis=1, skipna=True)
    cutoff = panel.index.min() + (panel.index.max() - panel.index.min()) * DISCOVERY_FRAC
    rows = []
    for row in discovery.itertuples(index=False):
        if not row.fdr_significant:
            continue
        x = panel[row.leader].shift(int(row.lag)).loc[cutoff:]
        y = panel[row.follower].loc[cutoff:]
        own = panel[row.follower].shift(1).loc[cutoff:]
        mn = market.loc[cutoff:]
        ml = market.shift(int(row.lag)).loc[cutoff:]
        fit = ols_one(y.to_numpy(), x.to_numpy(), [own.to_numpy(), mn.to_numpy(), ml.to_numpy()])
        if fit is None:
            continue
        beta, tstat, pvalue, n = fit
        rows.append({"leader": row.leader, "follower": row.follower, "lag": row.lag, "discovery_beta": row.beta, "validation_beta": beta, "validation_p": pvalue, "validation_n": n, "temporal_status": "REPLICATED" if pvalue < ALPHA and np.sign(beta) == np.sign(row.beta) else "TEMPORALLY_UNSTABLE"})
    return pd.DataFrame(rows)


def summarize(source: str, results: dict[str, pd.DataFrame]) -> dict:
    summary = {"source": source, "metrics": {}}
    for metric, frame in results.items():
        validation = temporal_validate(frame, stocks_cache[source], metric)
        validation_path = OUT / f"{source}_{metric}_validation.csv"
        validation.to_csv(validation_path, index=False)
        frame.to_csv(OUT / f"{source}_{metric}_relationships.csv", index=False)
        robust = validation[validation["temporal_status"] == "REPLICATED"] if not validation.empty else validation
        summary["metrics"][metric] = {
            "pairwise_lag_tests": int(len(frame)),
            "raw_significant": int(frame["raw_significant"].sum()) if not frame.empty else 0,
            "fdr_significant": int(frame["fdr_significant"].sum()) if not frame.empty else 0,
            "temporal_validated": int(len(robust)),
            "concentration_top_leaders": frame["leader"].value_counts().head(10).to_dict() if not frame.empty else {},
        }
    return summary


stocks_cache: dict[str, dict[str, pd.DataFrame]] = {}
all_summaries = []
import argparse

parser = argparse.ArgumentParser()
parser.add_argument("--sources", nargs="+", default=["shaban", "al_refaey"])
parser.add_argument("--metrics", nargs="+", default=["ret", "illiquidity", "volatility", "abnormal_volume", "range"])
args = parser.parse_args()

for source in args.sources:
    stocks = load_source(source)
    stocks_cache[source] = stocks
    metric_results = {metric: relationship_test(source, stocks, metric) for metric in args.metrics}
    all_summaries.append({"source": source, "stock_count": len(stocks), "summary": summarize(source, metric_results)})

(OUT / "summary.json").write_text(json.dumps(all_summaries, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
print(json.dumps(all_summaries, ensure_ascii=False, indent=2, default=str))
