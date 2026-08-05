#!/usr/bin/env python3
"""
exhaustive_price_hunter.py
===========================
Tries EVERY known free source for the 10 missing EGX tickers.

Sources tested (in order):
  1. Yahoo Finance - all possible symbol variants
  2. Mubasher Finance API (MENA-focused, covers EGX)
  3. EGX Official website data endpoint
  4. Investing.com data (where accessible)
  5. Alpha Vantage (free, no key needed for some endpoints)
  6. StockAnalysis.com
  7. MarketWatch quotes
"""

import csv
import json
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import UTC, datetime, timedelta
from pathlib import Path

ROOT       = Path(__file__).parent.parent.parent
PRICES_DIR = ROOT / "research" / "data" / "prices"
PRICES_DIR.mkdir(parents=True, exist_ok=True)

HEADERS_GENERAL = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "application/json, text/html,*/*",
    "Accept-Language": "en-US,en;q=0.9,ar;q=0.8",
}

MISSING = {
    "ACTF":  "Act Financial",
    "AIDC":  "Arabia for Investment and Development",
    "AIHC":  "Arabia Investments Holding",
    "GPIM":  "GPI For Urban Growth",
    "IEEC":  "Industrial & Engineering Projects",
    "KRDI":  "Al Khair River For Dev Agricultural",
    "TANM":  "Tanmiya for Real Estate Investment",
    "TAQA":  "Taqa Arabia",
    "VLMR":  "Valmore Holding",
    "VLMRA": "Valmore Holding-EGP",
}

SOURCE_LOG = {}  # ticker -> {source, status, detail}

def now_ts():
    return int(datetime.now(UTC).timestamp())

def days_ago_ts(d):
    return int((datetime.now(UTC) - timedelta(days=d)).timestamp())

def http_get(url, headers=None, timeout=15):
    h = {**HEADERS_GENERAL, **(headers or {})}
    req = urllib.request.Request(url, headers=h)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.read(), r.status
    except urllib.error.HTTPError as e:
        return None, e.code
    except Exception as e:
        return None, str(e)

def save_csv(ticker, bars):
    path = PRICES_DIR / f"{ticker}.csv"
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["date","open","high","low","close","volume"])
        w.writeheader()
        w.writerows(bars)
    return path

# ─────────────────────────────────────────────────────────────
# SOURCE 1: Yahoo Finance — exhaustive symbol variants
# ─────────────────────────────────────────────────────────────
YAHOO_VARIANTS = {
    "ACTF":  ["ACTF.CA", "ACT.CA", "ACTF.EG", "ACTF", "AAAF.CA"],
    "AIDC":  ["AIDC.CA", "AIDC.EG", "AIDC", "AID.CA"],
    "AIHC":  ["AIHC.CA", "AIHC.EG", "AIHC", "AIH.CA"],
    "GPIM":  ["GPIM.CA", "GPIM.EG", "GPIM", "GPI.CA"],
    "IEEC":  ["IEEC.CA", "IEEC.EG", "IEEC", "IEE.CA", "IIEC.CA"],
    "KRDI":  ["KRDI.CA", "KRDI.EG", "KRDI", "KRD.CA"],
    "TANM":  ["TANM.CA", "TANM.EG", "TANM", "TAN.CA", "TAAN.CA"],
    "TAQA":  ["TAQA.CA", "TAQA.EG", "TAQA", "TQA.CA", "TAQAE.CA", "TAQAEGY.CA"],
    "VLMR":  ["VLMR.CA", "VLMR.EG", "VLMR", "VLM.CA"],
    "VLMRA": ["VLMRA.CA", "VLMRA.EG", "VLMRA", "VLM-A.CA", "VLMR.A.CA"],
}

def try_yahoo(ticker):
    for sym in YAHOO_VARIANTS.get(ticker, [f"{ticker}.CA"]):
        url = (f"https://query1.finance.yahoo.com/v8/finance/chart/{sym}"
               f"?interval=1d&period1={days_ago_ts(400)}&period2={now_ts()}")
        data, _status = http_get(url)
        if data:
            try:
                d = json.loads(data)
                result = d["chart"]["result"][0]
                tss = result.get("timestamp", [])
                q = result["indicators"]["quote"][0]
                bars = []
                for ts, c in zip(tss, q.get("close", [])):
                    if c is None: continue
                    bars.append({"date": datetime.fromtimestamp(ts, tz=UTC).strftime("%Y-%m-%d"),
                                 "open": None, "high": None, "low": None,
                                 "close": round(float(c), 4), "volume": 0})
                if bars and len(bars) >= 3:
                    return bars, f"Yahoo:{sym}"
            except Exception:
                pass
        time.sleep(0.25)
    return None, "Yahoo:FAIL"

# ─────────────────────────────────────────────────────────────
# SOURCE 2: Mubasher Finance API (MENA-focused, covers EGX)
# ─────────────────────────────────────────────────────────────
def try_mubasher(ticker):
    """Mubasher covers EGX with Arabic financial data."""
    # Mubasher public chart endpoint
    url = f"https://www.mubasher.info/api/st/chart-data?symbol={ticker}&exchange=XCAI&period=1Y&type=line"
    data, _status = http_get(url)
    if data:
        try:
            d = json.loads(data)
            # Structure varies — try common patterns
            series = d.get("data") or d.get("series") or d.get("chartData") or []
            if isinstance(series, list) and series:
                bars = []
                for point in series:
                    if isinstance(point, (list, tuple)) and len(point) >= 2:
                        ts, price = point[0], point[1]
                        if price:
                            dt = datetime.fromtimestamp(ts/1000 if ts > 1e10 else ts, tz=UTC)
                            bars.append({"date": dt.strftime("%Y-%m-%d"), "open": None, "high": None,
                                         "low": None, "close": round(float(price), 4), "volume": 0})
                    elif isinstance(point, dict):
                        price = point.get("close") or point.get("value") or point.get("price")
                        date = point.get("date") or point.get("time")
                        if price and date:
                            bars.append({"date": str(date)[:10], "open": None, "high": None,
                                         "low": None, "close": round(float(price), 4), "volume": 0})
                if bars and len(bars) >= 3:
                    return bars, "Mubasher"
        except Exception:
            pass
    time.sleep(0.3)
    return None, "Mubasher:FAIL"

# ─────────────────────────────────────────────────────────────
# SOURCE 3: EGX Official Website
# ─────────────────────────────────────────────────────────────
def try_egx_official(ticker):
    """Try EGX official endpoints."""
    # EGX has a JSON data service
    endpoints = [
        f"https://www.egx.com.eg/ar/stockPriceDetails.aspx?code={ticker}",
        f"https://www.egx.com.eg/en/stockPriceDetails.aspx?code={ticker}",
        f"https://www.egx.com.eg/api/stock/{ticker}/history",
        f"https://www.egx.com.eg/en/equityHistoricalData.aspx?symbol={ticker}",
    ]
    for url in endpoints:
        data, status = http_get(url, timeout=20)
        if data and status == 200:
            text = data.decode("utf-8", errors="ignore")
            # Look for price data in HTML or JSON
            if '"close"' in text.lower() or '"price"' in text.lower() or "EGP" in text:
                # Try to parse as JSON first
                try:
                    json.loads(text)
                    print(f"  [EGX_OFFICIAL] {ticker}: Got JSON response from {url[:60]}")
                    return None, "EGX:partial"
                except Exception:
                    pass
        time.sleep(0.5)
    return None, "EGX:FAIL"

# ─────────────────────────────────────────────────────────────
# SOURCE 4: Alpha Vantage (free, limited)
# ─────────────────────────────────────────────────────────────
def try_alphavantage(ticker):
    """Alpha Vantage free tier - 25 requests/day, no key for demo."""
    # Free demo key
    key = "demo"
    url = (f"https://www.alphavantage.co/query?function=TIME_SERIES_DAILY"
           f"&symbol={ticker}.CAI&apikey={key}&outputsize=compact")
    data, _status = http_get(url)
    if data:
        try:
            d = json.loads(data)
            ts_data = d.get("Time Series (Daily)", {})
            if ts_data:
                bars = []
                for date, vals in sorted(ts_data.items())[-200:]:
                    bars.append({
                        "date": date,
                        "open": round(float(vals.get("1. open", 0)), 4),
                        "high": round(float(vals.get("2. high", 0)), 4),
                        "low": round(float(vals.get("3. low", 0)), 4),
                        "close": round(float(vals.get("4. close", 0)), 4),
                        "volume": int(float(vals.get("5. volume", 0))),
                    })
                if bars:
                    return bars, "AlphaVantage"
        except Exception:
            pass
    time.sleep(1.0)  # AV rate limit
    return None, "AlphaVantage:FAIL"

# ─────────────────────────────────────────────────────────────
# SOURCE 5: Investing.com (via their data API)
# ─────────────────────────────────────────────────────────────
INVESTING_IDS = {
    # Pre-known Investing.com pair IDs for EGX stocks
    "TAQA":  "20662",   # Taqa Arabia - known ID
    "TANM":  None,
    "ACTF":  None,
    "GPIM":  None,
}

def try_investing_com(ticker):
    """Investing.com has EGX data accessible via their chart API."""
    # Try search first
    search_url = f"https://api.investing.com/api/search/v2/search?q={ticker}+Egypt&limit=5"
    headers_inv = {**HEADERS_GENERAL, "X-Site-Current-Path": "/equities", "domain-id": "www"}
    data, _status = http_get(search_url, headers=headers_inv)
    if data:
        try:
            d = json.loads(data)
            hits = d.get("hits", [])
            for hit in hits:
                if hit.get("flag") == "EG" or "egypt" in str(hit).lower():
                    pair_id = hit.get("id") or hit.get("pair_id")
                    symbol = hit.get("symbol", "")
                    print(f"  [INVESTING.COM] {ticker}: found hit id={pair_id} symbol={symbol}")
        except Exception:
            pass
    time.sleep(0.5)
    return None, "Investing:FAIL"

# ─────────────────────────────────────────────────────────────
# SOURCE 6: StockAnalysis.com EGX page
# ─────────────────────────────────────────────────────────────
def try_stockanalysis(ticker):
    """StockAnalysis covers some EGX stocks."""
    url = f"https://stockanalysis.com/stocks/egx/{ticker.lower()}/"
    data, status = http_get(url)
    if data and status == 200:
        text = data.decode("utf-8", errors="ignore")
        if "price" in text.lower() and "EGP" in text:
            print(f"  [STOCKANALYSIS] {ticker}: page found at {url}")
            # Try to extract price data from the page
            # They embed JSON in __NEXT_DATA__
            import re
            match = re.search(r'"close":(\d+\.?\d*)', text)
            if match:
                print(f"  [STOCKANALYSIS] {ticker}: found close={match.group(1)}")
    time.sleep(0.5)
    return None, "StockAnalysis:FAIL"

# ─────────────────────────────────────────────────────────────
# SOURCE 7: MarketWatch EGX
# ─────────────────────────────────────────────────────────────
def try_marketwatch(ticker):
    """MarketWatch covers some international stocks."""
    url = f"https://www.marketwatch.com/investing/stock/{ticker.lower()}/downloadsreturns?startdate=2024-01-01&enddate=2026-08-04&frequency=d&csvdownload=true&downloadpartial=false&newdates=false&countrycode=EG"
    data, status = http_get(url)
    if data and status == 200:
        try:
            text = data.decode("utf-8", errors="ignore")
            if "Date" in text and len(text) > 100:
                lines = text.strip().split("\n")
                bars = []
                for line in lines[1:]:
                    parts = line.split(",")
                    if len(parts) >= 5:
                        try:
                            bars.append({
                                "date": parts[0].strip(),
                                "open": None, "high": None, "low": None,
                                "close": round(float(parts[4].strip()), 4),
                                "volume": 0
                            })
                        except Exception:
                            pass
                if bars:
                    return bars, "MarketWatch"
        except Exception:
            pass
    time.sleep(0.5)
    return None, "MarketWatch:FAIL"

# ─────────────────────────────────────────────────────────────
# SOURCE 8: FinancialModelingPrep (free tier, some intl markets)
# ─────────────────────────────────────────────────────────────
def try_fmp(ticker):
    """FMP free tier - limited but covers some EGX stocks via EGX exchange."""
    url = (f"https://financialmodelingprep.com/api/v3/historical-price-full/EGX:{ticker}"
           f"?apikey=demo&from=2024-01-01")
    data, _status = http_get(url)
    if data:
        try:
            d = json.loads(data)
            hist = d.get("historical", [])
            if hist:
                bars = []
                for item in reversed(hist[-200:]):
                    bars.append({
                        "date": item["date"],
                        "open": item.get("open"), "high": item.get("high"),
                        "low": item.get("low"), "close": item.get("close"),
                        "volume": item.get("volume", 0)
                    })
                if bars:
                    return bars, "FMP"
        except Exception:
            pass
    time.sleep(0.5)
    return None, "FMP:FAIL"

# ─────────────────────────────────────────────────────────────
# SOURCE 9: EODHD (End of Day Historical Data) - free tier
# ─────────────────────────────────────────────────────────────
def try_eodhd(ticker):
    """EODHD has Egypt (EGX) market data, free demo available."""
    url = (f"https://eodhd.com/api/eod/{ticker}.EGX"
           f"?api_token=demo&fmt=json&from=2024-01-01&to=2026-08-04")
    data, _status = http_get(url)
    if data:
        try:
            d = json.loads(data)
            if isinstance(d, list) and d:
                bars = []
                for item in d:
                    if item.get("close"):
                        bars.append({
                            "date": item["date"],
                            "open": item.get("open"), "high": item.get("high"),
                            "low": item.get("low"), "close": item.get("close"),
                            "volume": item.get("volume", 0)
                        })
                if bars:
                    return bars, "EODHD"
        except Exception:
            pass
    time.sleep(0.5)
    return None, "EODHD:FAIL"

# ─────────────────────────────────────────────────────────────
# SOURCE 10: Marketstack (free tier, international stocks)
# ─────────────────────────────────────────────────────────────
def try_marketstack(ticker):
    """Marketstack free tier - covers Egypt (CAI exchange)."""
    url = (f"https://api.marketstack.com/v1/eod"
           f"?access_key=demo&symbols={ticker}.XCAI&limit=200&date_from=2024-01-01")
    data, _status = http_get(url)
    if data:
        try:
            d = json.loads(data)
            hist = d.get("data", [])
            if hist:
                bars = []
                for item in reversed(hist):
                    if item.get("close"):
                        bars.append({
                            "date": item["date"][:10],
                            "open": item.get("open"), "high": item.get("high"),
                            "low": item.get("low"), "close": item.get("close"),
                            "volume": item.get("volume", 0)
                        })
                if bars:
                    return bars, "Marketstack"
        except Exception:
            pass
    time.sleep(0.5)
    return None, "Marketstack:FAIL"

# ─────────────────────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────────────────────
SOURCES = [
    ("Yahoo Finance (all variants)", try_yahoo),
    ("Mubasher Finance API",         try_mubasher),
    ("EGX Official Website",         try_egx_official),
    ("Alpha Vantage (free demo)",    try_alphavantage),
    ("Investing.com API",            try_investing_com),
    ("StockAnalysis.com",            try_stockanalysis),
    ("MarketWatch CSV",              try_marketwatch),
    ("FinancialModelingPrep (demo)", try_fmp),
    ("EODHD (demo key)",             try_eodhd),
    ("Marketstack (demo key)",       try_marketstack),
]

def main():
    print("=== EGX Exhaustive Price Hunter ===")
    print(f"Target: {len(MISSING)} tickers — will not stop until all are found or all sources exhausted\n")

    results = {}
    source_attempts = {t: [] for t in MISSING}

    for ticker, company in MISSING.items():
        print(f"\n{'='*60}")
        print(f"TICKER: {ticker} ({company})")
        found = False

        for src_name, src_fn in SOURCES:
            print(f"  Trying {src_name}...", end=" ", flush=True)
            try:
                bars, detail = src_fn(ticker)
            except Exception as e:
                bars, detail = None, f"ERROR:{e}"

            source_attempts[ticker].append({"source": src_name, "result": detail})

            if bars and len(bars) >= 3:
                save_csv(ticker, bars)
                latest = bars[-1]
                print(f"SUCCESS! {len(bars)} bars, latest={latest['date']}, close={latest['close']}")
                results[ticker] = {"source": src_name, "bars": len(bars),
                                   "latest": latest["date"], "close": latest["close"]}
                found = True
                break
            else:
                print(f"FAIL ({detail})")

        if not found:
            results[ticker] = {"source": "NONE", "bars": 0, "status": "no_data_available"}
            print(f"  !! {ticker}: ALL {len(SOURCES)} sources FAILED")

    # Summary
    print(f"\n{'='*60}")
    print("=== FINAL RESULTS ===\n")
    success = {t: v for t, v in results.items() if v["bars"] > 0}
    failed  = {t: v for t, v in results.items() if v["bars"] == 0}

    print(f"SUCCESS: {len(success)}/{len(MISSING)}")
    for t, v in success.items():
        print(f"  {t:8s} via {v['source']:30s} {v['bars']} bars close={v['close']}")

    print(f"\nFAILED:  {len(failed)}/{len(MISSING)}")
    for t, v in failed.items():
        print(f"  {t:8s} {MISSING[t]}")
        for attempt in source_attempts[t]:
            print(f"           {attempt['source']:30s} -> {attempt['result']}")

    # Save log
    log = {
        "run_at": datetime.now(UTC).isoformat(),
        "sources_tested": [s[0] for s in SOURCES],
        "results": results,
        "source_attempts": source_attempts,
    }
    log_path = PRICES_DIR / "_exhaustive_hunt_log.json"
    with open(log_path, "w", encoding="utf-8") as f:
        json.dump(log, f, indent=2, ensure_ascii=False)
    print(f"\nLog saved: {log_path}")

if __name__ == "__main__":
    main()
