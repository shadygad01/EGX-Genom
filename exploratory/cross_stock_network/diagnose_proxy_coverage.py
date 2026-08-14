from pathlib import Path
import re
import pandas as pd
import numpy as np

ROOT = Path(__file__).resolve().parent / "raw"

def numeric(series):
    cleaned = series.astype(str).str.replace(",", "", regex=False).str.replace("%", "", regex=False)
    mult = cleaned.str.extract(r"([KMB])$", expand=False).map({"K": 1e3, "M": 1e6, "B": 1e9}).fillna(1.0)
    return pd.to_numeric(cleaned.str.replace(r"[KMB]$", "", regex=True), errors="coerce") * mult

def load(source):
    result = {}
    for path in sorted((ROOT / source).rglob("*.csv")):
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
        result[path.stem.split("_")[0].upper()] = out
    return result

for source in ("shaban", "al_refaey"):
    stocks = load(source)
    print(source, "stocks", len(stocks))
    for metric in ("ret", "illiquidity", "volatility", "abnormal_volume", "range"):
        panel = pd.DataFrame({k: v[metric] for k, v in stocks.items()}).sort_index()
        counts = panel.notna().sum(axis=0)
        print(metric, "columns", len(panel.columns), "min_nonnull", int(counts.min()) if len(counts) else 0, "median_nonnull", int(counts.median()) if len(counts) else 0, "rows", len(panel))
