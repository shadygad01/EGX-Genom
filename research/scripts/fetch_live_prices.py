#!/usr/bin/env python3
"""
fetch_live_prices.py
====================
Fetches real EGX stock prices for all 101 EGX30+EGX70 constituents
from Yahoo Finance (free, no API key required).

Tickers are mapped to Yahoo Finance format: SYMBOL.CA
Output: research/data/prices/{TICKER}.csv  (date,open,high,low,close,volume)
"""

import csv
import json
import time
import urllib.error
import urllib.request
from datetime import datetime, timedelta
from pathlib import Path

# ── paths ──────────────────────────────────────────────────────────────────
ROOT = Path(__file__).parent.parent
PRICES_DIR = ROOT / "data" / "prices"
UNIVERSE_FILE = ROOT / "data" / "dashboard" / "universe.json"
MARKET_STATE_FILE = ROOT / "data" / "dashboard" / "market_state.json"
PRICES_DIR.mkdir(parents=True, exist_ok=True)

# ── EGX30 + EGX70 full universe (101 tickers) ─────────────────────────────
# Yahoo Finance uses TICKER.CA for Cairo Stock Exchange
EGX_TICKERS = [
    "ABUK","ACTF","ADIB","AFDI","AFMC","AIDC","AIHC","ALCN","AMER","AMIA",
    "AMOC","ARAB","ARCC","ASCM","ASPI","ATLC","ATQA","BIOC","BTFH","CCAP",
    "CIEB","CNFN","COMI","COSG","CSAG","DAPH","DSCW","EAST","ECAP","EFID",
    "EFIH","EGAL","EGCH","EGTS","EHDR","ELSH","EMFD","ENGC","ETEL","ETRS",
    "EXPA","FWRY","GBCO","GPIM","HDBK","HELI","HRHO","ICFC","IDRE","IEEC",
    "IFAP","ISMA","ISMQ","ISPH","JUFO","KABO","KRDI","LCSW","LECB","LMLI",
    "MCDI","MFPC","MFSD","MGIC","MNHD","MOIL","MPCI","MRSE","NASR","NBIF",
    "NCGC","OCDI","OFHC","OMRO","OREG","ORWE","OTLH","PHAR","PHDC","PIOH",
    "PORT","PPAP","PRKU","REAM","RORE","RSRS","SGBC","SKPC","SMFL","SNCO",
    "SOFI","SPMD","SUGR","SWDY","TALM","TMGH","UEGC","UNIС","UNIH","UNIT",
    "VFIN",
]

def yahoo_url(ticker: str, period1: int, period2: int) -> str:
    symbol = f"{ticker}.CA"
    return (
        f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}"
        f"?interval=1d&period1={period1}&period2={period2}&events=history"
    )

def fetch_ticker(ticker: str, days: int = 365) -> list[dict]:
    """Fetch OHLCV from Yahoo Finance. Returns list of bar dicts."""
    now = int(datetime.utcnow().timestamp())
    start = int((datetime.utcnow() - timedelta(days=days)).timestamp())
    url = yahoo_url(ticker, start, now)

    req = urllib.request.Request(url, headers={
        "User-Agent": "Mozilla/5.0 (research/egx-genom)",
        "Accept": "application/json",
    })
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read())
    except (urllib.error.HTTPError, urllib.error.URLError, Exception) as e:
        print(f"  [SKIP] {ticker}: {e}")
        return []

    try:
        result = data["chart"]["result"][0]
        timestamps = result.get("timestamp", [])
        indicators = result["indicators"]
        quote = indicators["quote"][0]
        opens  = quote.get("open",   [None]*len(timestamps))
        highs  = quote.get("high",   [None]*len(timestamps))
        lows   = quote.get("low",    [None]*len(timestamps))
        closes = quote.get("close",  [None]*len(timestamps))
        volumes= quote.get("volume", [None]*len(timestamps))
    except (KeyError, IndexError) as e:
        print(f"  [PARSE_ERR] {ticker}: {e}")
        return []

    bars = []
    for ts, o, h, l, c, v in zip(timestamps, opens, highs, lows, closes, volumes):
        if c is None:
            continue
        date_str = datetime.utcfromtimestamp(ts).strftime("%Y-%m-%d")
        bars.append({
            "date":   date_str,
            "open":   round(float(o), 4) if o else None,
            "high":   round(float(h), 4) if h else None,
            "low":    round(float(l), 4) if l else None,
            "close":  round(float(c), 4),
            "volume": int(v) if v else 0,
        })
    return bars


def save_ticker(ticker: str, bars: list[dict]) -> None:
    path = PRICES_DIR / f"{ticker}.csv"
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["date","open","high","low","close","volume"])
        writer.writeheader()
        writer.writerows(bars)


def main():
    print("=== EGX Live Price Fetcher ===")
    print(f"Fetching {len(EGX_TICKERS)} tickers from Yahoo Finance (.CA suffix)")
    print(f"Output: {PRICES_DIR}\n")

    success, skipped = [], []

    for i, ticker in enumerate(EGX_TICKERS, 1):
        print(f"[{i:03d}/{len(EGX_TICKERS)}] {ticker}.CA ... ", end="", flush=True)
        bars = fetch_ticker(ticker, days=400)  # ~16 months for safety
        if bars:
            save_ticker(ticker, bars)
            print(f"OK  ({len(bars)} bars, latest={bars[-1]['date']}, close={bars[-1]['close']})")
            success.append(ticker)
        else:
            skipped.append(ticker)
            print("NO DATA")
        # Polite rate limiting — Yahoo allows ~60/min
        time.sleep(0.4)

    print("\n=== DONE ===")
    print(f"Success: {len(success)}/{len(EGX_TICKERS)}")
    print(f"Skipped: {len(skipped)}")
    if skipped:
        print(f"Tickers with no data: {', '.join(skipped)}")

    # Write a summary manifest
    manifest_path = PRICES_DIR / "_manifest.json"
    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump({
            "fetched_at": datetime.utcnow().isoformat(),
            "source": "Yahoo Finance (.CA)",
            "success_count": len(success),
            "skipped_count": len(skipped),
            "success": success,
            "skipped": skipped,
        }, f, indent=2, ensure_ascii=False)
    print(f"\nManifest written: {manifest_path}")


if __name__ == "__main__":
    main()
