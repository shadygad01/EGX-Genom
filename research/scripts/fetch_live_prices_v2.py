#!/usr/bin/env python3
"""
fetch_live_prices_v2.py
=======================
Smart price fetcher:
  1. Reads the EXACT ticker list from universe.json (the ground truth)
  2. Tries multiple Yahoo Finance symbol formats per ticker
  3. Logs every attempt and result
  4. Target: 101/101 with real data

Yahoo Finance formats tried for each EGX ticker:
  - TICKER.CA   (Cairo Stock Exchange, primary)
  - TICKER.EG   (Egypt suffix, alternative)
  - TICKER      (bare, some EGX stocks listed globally)
"""

import csv
import json
import time
import urllib.request
import urllib.error
from datetime import datetime, timezone, timedelta
from pathlib import Path

ROOT        = Path(__file__).parent.parent
PRICES_DIR  = ROOT / "data" / "prices"
UNIVERSE    = ROOT / "data" / "dashboard" / "universe.json"
PRICES_DIR.mkdir(parents=True, exist_ok=True)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Accept": "application/json",
}

def ts_range(days: int = 400):
    now   = int(datetime.now(timezone.utc).timestamp())
    start = int((datetime.now(timezone.utc) - timedelta(days=days)).timestamp())
    return start, now

def yahoo_fetch(symbol: str, days: int = 400) -> list[dict]:
    start, now = ts_range(days)
    url = (
        f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}"
        f"?interval=1d&period1={start}&period2={now}&events=history"
    )
    req = urllib.request.Request(url, headers=HEADERS)
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read())
    except urllib.error.HTTPError as e:
        if e.code == 404:
            return []
        raise
    except Exception:
        return []

    try:
        result   = data["chart"]["result"][0]
        tss      = result.get("timestamp", [])
        q        = result["indicators"]["quote"][0]
        opens    = q.get("open",   [None]*len(tss))
        highs    = q.get("high",   [None]*len(tss))
        lows     = q.get("low",    [None]*len(tss))
        closes   = q.get("close",  [None]*len(tss))
        volumes  = q.get("volume", [None]*len(tss))
    except (KeyError, IndexError, TypeError):
        return []

    bars = []
    for ts, o, h, l, c, v in zip(tss, opens, highs, lows, closes, volumes):
        if c is None:
            continue
        bars.append({
            "date":   datetime.fromtimestamp(ts, tz=timezone.utc).strftime("%Y-%m-%d"),
            "open":   round(float(o), 4) if o else None,
            "high":   round(float(h), 4) if h else None,
            "low":    round(float(l), 4) if l else None,
            "close":  round(float(c), 4),
            "volume": int(v) if v else 0,
        })
    return bars


def fetch_ticker_multi_format(ticker: str) -> tuple[list[dict], str]:
    """
    Try multiple Yahoo Finance symbol formats for a single EGX ticker.
    Returns (bars, successful_symbol) or ([], "").
    """
    # Priority order of formats to try
    formats = [
        f"{ticker}.CA",   # Cairo Stock Exchange (primary)
        f"{ticker}.EG",   # Egypt alternative
        ticker,           # bare (some dual-listed)
    ]
    for fmt in formats:
        try:
            bars = yahoo_fetch(fmt, days=400)
            if bars and len(bars) >= 3:
                return bars, fmt
        except Exception:
            pass
        time.sleep(0.2)
    return [], ""


def save_csv(ticker: str, bars: list[dict]) -> None:
    path = PRICES_DIR / f"{ticker}.csv"
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["date","open","high","low","close","volume"])
        w.writeheader()
        w.writerows(bars)


def load_universe() -> dict[str, str]:
    with open(UNIVERSE, encoding="utf-8") as f:
        data = json.load(f)
    return data["constituents"]   # {ticker: company_name}


def main():
    print("=== EGX Live Price Fetcher v2 (101/101 target) ===\n")
    universe = load_universe()
    tickers  = sorted(universe.keys())
    print(f"Universe: {len(tickers)} tickers from universe.json\n")

    success_map   = {}   # ticker -> {bars, symbol, company}
    failed        = []

    for i, ticker in enumerate(tickers, 1):
        company = universe[ticker]
        # Check if we already have good data from previous run
        existing = PRICES_DIR / f"{ticker}.csv"
        if existing.exists():
            with open(existing, encoding="utf-8") as f:
                rows = list(csv.DictReader(f))
            if rows and len(rows) >= 10:
                latest = rows[-1]["date"]
                # Fresh enough? (within 5 days for weekends)
                latest_dt = datetime.strptime(latest, "%Y-%m-%d").replace(tzinfo=timezone.utc)
                if (datetime.now(timezone.utc) - latest_dt).days <= 5:
                    print(f"[{i:03d}/{len(tickers)}] {ticker:6s} CACHED  {len(rows)} bars latest={latest} close={rows[-1]['close']}")
                    success_map[ticker] = {"bars": len(rows), "symbol": f"{ticker}.CA(cache)", "latest": latest, "close": rows[-1]["close"]}
                    continue

        print(f"[{i:03d}/{len(tickers)}] {ticker:6s} FETCH  {company[:35]:<35} ... ", end="", flush=True)
        bars, sym = fetch_ticker_multi_format(ticker)

        if bars:
            save_csv(ticker, bars)
            latest = bars[-1]["date"]
            close  = bars[-1]["close"]
            print(f"OK  via {sym:12s} {len(bars)} bars latest={latest} close={close}")
            success_map[ticker] = {"bars": len(bars), "symbol": sym, "latest": latest, "close": close}
        else:
            print(f"NO DATA (all formats failed)")
            failed.append((ticker, company))

        # Polite rate limit: 60 req/min max
        time.sleep(0.45)

    # ── Summary ──────────────────────────────────────────────────────────────
    print(f"\n{'='*60}")
    print(f"SUCCESS: {len(success_map)}/{len(tickers)}")
    print(f"FAILED:  {len(failed)}/{len(tickers)}")

    if failed:
        print(f"\nTickers with NO data:")
        for t, c in failed:
            print(f"  {t:8s} {c}")

    # Manifest
    manifest = {
        "fetched_at":     datetime.now(timezone.utc).isoformat(),
        "source":         "Yahoo Finance (.CA / .EG / bare)",
        "universe_file":  "universe.json",
        "total_universe": len(tickers),
        "success_count":  len(success_map),
        "failed_count":   len(failed),
        "success":        {t: v for t, v in success_map.items()},
        "failed":         [t for t, _ in failed],
    }
    with open(PRICES_DIR / "_manifest.json", "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2, ensure_ascii=False)

    pct = len(success_map) / len(tickers) * 100
    print(f"\nCoverage: {pct:.1f}%  ({len(success_map)}/{len(tickers)})")
    print(f"Manifest: {PRICES_DIR / '_manifest.json'}")


if __name__ == "__main__":
    main()
