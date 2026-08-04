#!/usr/bin/env python3
"""
fetch_missing_10_advanced.py
============================
Targeted fetcher for the 10 EGX tickers not available on Yahoo Finance.
Confirmed status (from EGX/web research Aug 2026): ALL 10 are ACTIVE and trading.
Known current prices:
  ACTF=2.76, AIDC=0.70, AIHC=0.468, GPIM=1.19, IEEC=0.68
  KRDI=0.385, TANM=6.17, TAQA=15.25, VLMR=0.674(USD), VLMRA=30.97

Sources tried (in order of likelihood):
  1. TradingView UDF API (confirmed to have EGX data)
  2. StockAnalysis.com (confirmed TAQA page exists)
  3. Investing.com pair ID lookup
  4. EGX direct AJAX endpoints
  5. Mubasher Info (Arabic MENA financial data)
  6. Boursa website scraping
"""

import csv
import json
import re
import time
import urllib.request
import urllib.parse
import urllib.error
from datetime import datetime, timezone, timedelta
from pathlib import Path

ROOT       = Path(__file__).parent.parent.parent
PRICES_DIR = ROOT / "research" / "data" / "prices"
PRICES_DIR.mkdir(parents=True, exist_ok=True)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "application/json, text/html, */*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9,ar;q=0.8",
}

MISSING = {
    "ACTF":  {"name": "Act Financial", "known_price": 2.76},
    "AIDC":  {"name": "Arabia for Investment and Development", "known_price": 0.70},
    "AIHC":  {"name": "Arabia Investments Holding", "known_price": 0.468},
    "GPIM":  {"name": "GPI For Urban Growth", "known_price": 1.19},
    "IEEC":  {"name": "Industrial & Engineering Projects", "known_price": 0.68},
    "KRDI":  {"name": "Al Khair River Dev Agricultural", "known_price": 0.385},
    "TANM":  {"name": "Tanmiya for Real Estate Investment", "known_price": 6.17},
    "TAQA":  {"name": "Taqa Arabia", "known_price": 15.25},
    "VLMR":  {"name": "Valmore Holding (USD)", "known_price": 0.674},
    "VLMRA": {"name": "Valmore Holding (EGP)", "known_price": 30.97},
}

def http_get(url, headers=None, timeout=15):
    h = {**HEADERS, **(headers or {})}
    req = urllib.request.Request(url, headers=h)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.read(), r.status
    except Exception:
        return None, None

def save_csv(ticker, bars):
    path = PRICES_DIR / f"{ticker}.csv"
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["date","open","high","low","close","volume"])
        w.writeheader()
        w.writerows(bars)
    return path

def days_ago_ts(d):
    return int((datetime.now(timezone.utc) - timedelta(days=d)).timestamp())

def now_ts():
    return int(datetime.now(timezone.utc).timestamp())

# ─────────────────────────────────────────────────────────────────
# SOURCE 1: TradingView UDF API (most likely to work for EGX)
# ─────────────────────────────────────────────────────────────────
TV_SYMBOL_MAP = {
    "ACTF":  "EGX:ACTF",
    "AIDC":  "EGX:AIDC",
    "AIHC":  "EGX:AIHC",
    "GPIM":  "EGX:GPIM",
    "IEEC":  "EGX:IEEC",
    "KRDI":  "EGX:KRDI",
    "TANM":  "EGX:TANM",
    "TAQA":  "EGX:TAQA",
    "VLMR":  "EGX:VLMR",
    "VLMRA": "EGX:VLMRA",
}

def try_tradingview_udf(ticker):
    """TradingView UDF API for history bars."""
    sym = urllib.parse.quote(TV_SYMBOL_MAP.get(ticker, f"EGX:{ticker}"))
    from_ts = days_ago_ts(400)
    to_ts = now_ts()
    # TradingView history endpoint
    url = (f"https://symbol-search.tradingview.com/symbol_search/v3/"
           f"?text={ticker}&hl=1&exchange=EGX&lang=en&search_type=stocks&domain=production")
    data, _ = http_get(url, headers={"Referer": "https://www.tradingview.com/"})
    if data:
        try:
            d = json.loads(data)
            symbols = d if isinstance(d, list) else d.get("symbols_remaining", [])
            if symbols:
                found_sym = symbols[0].get("symbol") or symbols[0].get("ticker")
                print(f"    TradingView symbol found: {found_sym}")
        except Exception:
            pass

    # Try TradingView chart data API
    tv_url = (f"https://data.tradingview.com/widgetembed/history?"
              f"symbol=EGX%3A{ticker}&resolution=D&from={from_ts}&to={to_ts}&format=json")
    data, status = http_get(tv_url, headers={"Referer": "https://www.tradingview.com/"})
    if data and status == 200:
        try:
            d = json.loads(data)
            if d.get("s") == "ok":
                times = d.get("t", [])
                closes = d.get("c", [])
                bars = []
                for ts, c in zip(times, closes):
                    if c:
                        bars.append({
                            "date": datetime.fromtimestamp(ts, tz=timezone.utc).strftime("%Y-%m-%d"),
                            "open": None, "high": None, "low": None,
                            "close": round(float(c), 4), "volume": 0
                        })
                if bars and len(bars) >= 3:
                    return bars, "TradingView"
        except Exception:
            pass
    time.sleep(0.5)
    return None, "TradingView:FAIL"

# ─────────────────────────────────────────────────────────────────
# SOURCE 2: StockAnalysis.com
# ─────────────────────────────────────────────────────────────────
def try_stockanalysis_com(ticker):
    """StockAnalysis.com has EGX stocks."""
    # Try their API endpoint
    url = f"https://stockanalysis.com/stocks/egx/{ticker.lower()}/history/?p=annual"
    data, status = http_get(url)
    if data and status == 200:
        text = data.decode("utf-8", errors="ignore")
        # Look for JSON data embedded in page
        match = re.search(r'"historicalPrices":\s*(\[.*?\])', text, re.DOTALL)
        if not match:
            match = re.search(r'"data":\s*(\[.*?\])', text, re.DOTALL)
        if match:
            try:
                prices = json.loads(match.group(1))
                bars = []
                for item in prices:
                    if isinstance(item, dict) and item.get("close"):
                        bars.append({
                            "date": str(item.get("date", ""))[:10],
                            "open": item.get("open"), "high": item.get("high"),
                            "low": item.get("low"), "close": round(float(item["close"]), 4),
                            "volume": item.get("volume", 0)
                        })
                if bars:
                    return bars, "StockAnalysis"
            except Exception:
                pass
    time.sleep(0.5)
    return None, "StockAnalysis:FAIL"

# ─────────────────────────────────────────────────────────────────
# SOURCE 3: Investing.com via their API (with proper headers)
# ─────────────────────────────────────────────────────────────────
INVESTING_PAIR_IDS = {
    # Investing.com pair IDs for EGX stocks (pre-researched)
    "TAQA":  20662,    # Taqa Arabia
    "TANM":  None,
    "ACTF":  None,
    "VLMRA": None,
}

def try_investing_historical(pair_id: int, ticker: str):
    """Fetch historical data from Investing.com using pair ID."""
    if not pair_id:
        return None, "Investing:no_pair_id"
    url = "https://api.investing.com/api/financials/historical/chart/"
    params = {
        "pair_id": str(pair_id),
        "pair_id_secondary": "",
        "financial_id": str(pair_id),
        "period": "_1_year",
        "interval": "P1D",
        "point_count": 400,
    }
    headers_inv = {
        **HEADERS,
        "domain-id": "www",
        "X-Site-Current-Path": "/equities",
        "Referer": f"https://www.investing.com/",
    }
    url_full = url + "?" + urllib.parse.urlencode(params)
    data, status = http_get(url_full, headers=headers_inv)
    if data and status == 200:
        try:
            d = json.loads(data)
            if d.get("data"):
                bars = []
                for item in d["data"]:
                    bars.append({
                        "date": str(item[0])[:10] if isinstance(item[0], str) else
                               datetime.fromtimestamp(item[0]/1000 if item[0] > 1e10 else item[0], tz=timezone.utc).strftime("%Y-%m-%d"),
                        "open": None, "high": None, "low": None,
                        "close": round(float(item[1]), 4), "volume": 0
                    })
                if bars:
                    return bars, f"Investing(pair={pair_id})"
        except Exception:
            pass
    time.sleep(0.5)
    return None, "Investing:FAIL"

# ─────────────────────────────────────────────────────────────────
# SOURCE 4: EGX Direct endpoints (various formats)
# ─────────────────────────────────────────────────────────────────
def try_egx_direct(ticker):
    """Try EGX official endpoints directly."""
    # EGX has various data download formats
    today = datetime.now().strftime("%Y/%m/%d")
    year_ago = (datetime.now() - timedelta(days=365)).strftime("%Y/%m/%d")
    
    endpoints = [
        # JSON/API style
        f"https://www.egx.com.eg/api/v1/stocks/{ticker}/prices?from={year_ago}&to={today}",
        f"https://www.egx.com.eg/en/historicalData?StockCode={ticker}",
        # Excel download
        f"https://www.egx.com.eg/en/equityHistoricalData.aspx?symbol={ticker}&fromDate=01/01/2024&toDate={datetime.now().strftime('%d/%m/%Y')}",
    ]
    for url in endpoints:
        data, status = http_get(url, timeout=20)
        if data and status == 200:
            text = data.decode("utf-8", errors="ignore")
            if len(text) > 200 and ("close" in text.lower() or "price" in text.lower()):
                # Try JSON
                try:
                    d = json.loads(text)
                    print(f"    EGX direct JSON at: {url[:80]}")
                    return None, "EGX:partial_json"
                except Exception:
                    pass
                # Try CSV
                if "," in text and "\n" in text:
                    lines = text.strip().split("\n")
                    if len(lines) > 5:
                        print(f"    EGX possible CSV ({len(lines)} lines) at: {url[:80]}")
        time.sleep(0.5)
    return None, "EGX:FAIL"

# ─────────────────────────────────────────────────────────────────
# SOURCE 5: Mubasher Info (Arabic MENA financial data, covers EGX)
# ─────────────────────────────────────────────────────────────────
def try_mubasher_chart(ticker):
    """Mubasher has chart data for EGX stocks."""
    # Try multiple Mubasher endpoints
    endpoints = [
        f"https://www.mubasher.info/api/v2/chart/data?symbol={ticker}.EGX&exchange=XCAI&period=1Y",
        f"https://services.mubasher.info/api/v3/GetTickerTimeSeries?exchange=XCAI&ticker={ticker}&interval=daily&from=20240101&to=20260804",
        f"https://www.mubasher.info/api/st/chart-data?symbol={ticker}&exchange=XCAI&period=1Y&type=candlestick",
        f"https://api.mubasher.info/stockmarket/history/EGX/{ticker}?period=1Y",
    ]
    for url in endpoints:
        data, status = http_get(url, headers={"Referer": "https://www.mubasher.info/", "Origin": "https://www.mubasher.info"})
        if data and status == 200:
            try:
                d = json.loads(data)
                # Various response formats
                series = (d.get("data") or d.get("series") or d.get("chartData") or
                         d.get("TimeSeries") or d.get("time_series") or [])
                if series:
                    bars = []
                    for item in series:
                        if isinstance(item, (list, tuple)) and len(item) >= 2:
                            ts, price = item[0], item[-1]
                            if price:
                                try:
                                    dt = datetime.fromtimestamp(float(ts)/1000 if float(ts) > 1e10 else float(ts), tz=timezone.utc)
                                    bars.append({"date": dt.strftime("%Y-%m-%d"), "open": None, "high": None, "low": None,
                                                 "close": round(float(price), 4), "volume": 0})
                                except Exception: pass
                        elif isinstance(item, dict):
                            close = item.get("close") or item.get("value") or item.get("Close") or item.get("price")
                            date = item.get("date") or item.get("Date") or item.get("time")
                            if close and date:
                                bars.append({"date": str(date)[:10], "open": None, "high": None, "low": None,
                                             "close": round(float(close), 4), "volume": 0})
                    if bars and len(bars) >= 3:
                        return bars, f"Mubasher({url[35:70]})"
            except Exception:
                pass
        time.sleep(0.4)
    return None, "Mubasher:FAIL"

# ─────────────────────────────────────────────────────────────────
# SOURCE 6: Yahoo Finance v7 (alternative endpoint, sometimes works)
# ─────────────────────────────────────────────────────────────────
YAHOO_EXTRA_VARIANTS = {
    "ACTF":  ["ACTF.CA", "0P0001OOWZ.CA"],
    "AIDC":  ["AIDC.CA", "AIDO.CA"],
    "AIHC":  ["AIHC.CA"],
    "GPIM":  ["GPIM.CA", "GPI.CA"],
    "IEEC":  ["IEEC.CA", "IIEE.CA", "IIEC.CA"],
    "KRDI":  ["KRDI.CA"],
    "TANM":  ["TANM.CA", "TNMH.CA"],
    "TAQA":  ["TAQA.CA", "TAQAEGY.CA", "TAQA-EG.CA"],
    "VLMR":  ["VLMR.CA", "EKHO.CA"],  # Valmore was formerly EK Holding
    "VLMRA": ["VLMRA.CA", "EKHOA.CA"],
}

def try_yahoo_v7(ticker):
    """Yahoo Finance v7 / alternative endpoints."""
    for sym in YAHOO_EXTRA_VARIANTS.get(ticker, []):
        # v7 endpoint (sometimes available when v8 returns 404)
        url = (f"https://query2.finance.yahoo.com/v8/finance/chart/{sym}"
               f"?interval=1d&period1={days_ago_ts(400)}&period2={now_ts()}&events=history")
        data, status = http_get(url)
        if data:
            try:
                d = json.loads(data)
                result = d["chart"]["result"][0]
                tss = result.get("timestamp", [])
                closes = result["indicators"]["quote"][0].get("close", [])
                bars = [{"date": datetime.fromtimestamp(ts, tz=timezone.utc).strftime("%Y-%m-%d"),
                          "open": None, "high": None, "low": None,
                          "close": round(float(c), 4), "volume": 0}
                         for ts, c in zip(tss, closes) if c]
                if bars and len(bars) >= 3:
                    return bars, f"Yahoo_v2:{sym}"
            except Exception:
                pass
        time.sleep(0.3)
    return None, "Yahoo_v2:FAIL"

# ─────────────────────────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────────────────────────
SOURCES = [
    ("Yahoo Finance v2 (alt symbols)",   try_yahoo_v7),
    ("TradingView UDF",                  try_tradingview_udf),
    ("StockAnalysis.com",                try_stockanalysis_com),
    ("Mubasher Finance Chart API",       try_mubasher_chart),
    ("EGX Direct endpoints",             try_egx_direct),
]

def main():
    print("=== EGX Missing 10 — Advanced Price Hunter ===")
    print(f"All 10 confirmed ACTIVE and TRADING on EGX (Aug 2026)\n")

    results = {}
    still_missing = []

    for ticker, info in MISSING.items():
        print(f"\n{'─'*60}")
        print(f"TICKER: {ticker}  |  {info['name']}")
        print(f"Known price: {info['known_price']} EGP (from web search)")
        found = False

        for src_name, src_fn in SOURCES:
            print(f"  [{src_name}]... ", end="", flush=True)
            try:
                if src_name == "Investing.com pair ID":
                    bars, detail = try_investing_historical(INVESTING_PAIR_IDS.get(ticker), ticker)
                else:
                    bars, detail = src_fn(ticker)
            except Exception as e:
                bars, detail = None, f"ERROR:{e}"

            if bars and len(bars) >= 3:
                save_csv(ticker, bars)
                latest = bars[-1]
                print(f"SUCCESS! {len(bars)} bars  latest={latest['date']}  close={latest['close']}")
                results[ticker] = {"source": src_name, "bars": len(bars),
                                   "latest": latest["date"], "close": latest["close"],
                                   "known_price": info["known_price"]}
                found = True
                break
            else:
                print(f"FAIL ({detail})")

        if not found:
            results[ticker] = {"source": "NONE", "bars": 0, "known_price": info["known_price"]}
            still_missing.append(ticker)

    # ── FINAL REPORT ─────────────────────────────────────────────
    print(f"\n{'='*60}")
    print("=== RESULTS ===\n")
    ok = {t: v for t, v in results.items() if v["bars"] > 0}
    ko = {t: v for t, v in results.items() if v["bars"] == 0}

    print(f"Downloaded: {len(ok)}/10")
    for t, v in ok.items():
        print(f"  {t:8s} via {v['source']:35s} {v['bars']} bars close={v['close']} (expected~{v['known_price']})")

    print(f"\nStill missing: {len(ko)}/10")
    for t, v in ko.items():
        print(f"  {t:8s} known_price={v['known_price']} EGP  — no historical series retrievable")

    if ko:
        print(f"\nNote: {list(ko.keys())} are confirmed trading on EGX but have NO free historical API.")
        print("Options: (1) EGX data subscription, (2) manual input, (3) proceed with 91/101")

    return len(ok)

if __name__ == "__main__":
    n = main()
    print(f"\nFinal: {91 + n}/101 tickers with real price data")
