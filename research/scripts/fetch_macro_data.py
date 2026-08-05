#!/usr/bin/env python3
"""
fetch_macro_data.py
===================
Fetches real macroeconomic data for Egypt from free public APIs:
  - EGP/USD exchange rate: Yahoo Finance (EGPUSD=X) — free, no key
  - Egypt CPI inflation:   World Bank Open Data API — free, no key
  - Egypt interest rate:   World Bank (FR.INR.RINR) — proxy via real rate
  - Brent crude oil price: Yahoo Finance (BZ=F) — free, no key
  - Egypt GDP growth:      World Bank (NY.GDP.MKTP.KD.ZG) — free, no key

Output:
  research/data/macro/EGP_USD.csv
  research/data/macro/egypt_cpi_inflation.csv
  research/data/macro/BRENT_USD.csv
  research/data/macro/egypt_interest_rate.csv
  research/data/macro/egypt_gdp_growth.csv
  research/data/macro/macro_snapshot.json  ← unified for decision engine
"""

import csv
import json
import time
import urllib.error
import urllib.request
from datetime import datetime, timedelta
from pathlib import Path

ROOT = Path(__file__).parent.parent
MACRO_DIR = ROOT / "data" / "macro"
MACRO_DIR.mkdir(parents=True, exist_ok=True)

# ── helpers ─────────────────────────────────────────────────────────────────
HEADERS = {"User-Agent": "Mozilla/5.0 (research/egx-genom)", "Accept": "application/json"}

def http_get(url: str, timeout: int = 20) -> dict | list | None:
    req = urllib.request.Request(url, headers=HEADERS)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read())
    except Exception as e:
        print(f"  [HTTP ERR] {url[:80]}: {e}")
        return None

def save_csv(path: Path, rows: list[dict], fields: list[str]) -> None:
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)

# ── 1. EGP/USD from Yahoo Finance ──────────────────────────────────────────
def fetch_egp_usd(days: int = 365) -> list[dict]:
    print("Fetching EGP/USD (Yahoo Finance: EGPUSD=X) ...")
    now = int(datetime.utcnow().timestamp())
    start = int((datetime.utcnow() - timedelta(days=days)).timestamp())
    url = (
        f"https://query1.finance.yahoo.com/v8/finance/chart/EGPUSD=X"
        f"?interval=1d&period1={start}&period2={now}&events=history"
    )
    data = http_get(url)
    if not data:
        return []
    try:
        result = data["chart"]["result"][0]
        timestamps = result["timestamp"]
        closes = result["indicators"]["quote"][0]["close"]
    except (KeyError, IndexError, TypeError):
        print("  [PARSE ERR] EGP/USD")
        return []

    rows = []
    for ts, c in zip(timestamps, closes):
        if c is None:
            continue
        rows.append({
            "date": datetime.utcfromtimestamp(ts).strftime("%Y-%m-%d"),
            "value": round(float(c), 4),
        })
    print(f"  → {len(rows)} observations. Latest: {rows[-1] if rows else 'none'}")
    return rows

# ── 2. Egypt CPI from World Bank ───────────────────────────────────────────
def fetch_worldbank(indicator: str, label: str, years: int = 10) -> list[dict]:
    print(f"Fetching {label} (World Bank: {indicator}) ...")
    url = (
        f"https://api.worldbank.org/v2/country/EG/indicator/{indicator}"
        f"?format=json&mrv={years}&per_page=50"
    )
    data = http_get(url)
    if not data or len(data) < 2:
        return []
    rows = []
    for item in data[1]:
        if item.get("value") is None:
            continue
        rows.append({
            "date": f"{item['date']}-12-31",
            "value": round(float(item["value"]), 4),
        })
    rows.sort(key=lambda r: r["date"])
    print(f"  → {len(rows)} observations. Latest: {rows[-1] if rows else 'none'}")
    return rows

# ── 3. Brent Crude from Yahoo Finance ──────────────────────────────────────
def fetch_brent(days: int = 365) -> list[dict]:
    print("Fetching Brent Crude (Yahoo Finance: BZ=F) ...")
    now = int(datetime.utcnow().timestamp())
    start = int((datetime.utcnow() - timedelta(days=days)).timestamp())
    url = (
        f"https://query1.finance.yahoo.com/v8/finance/chart/BZ%3DF"
        f"?interval=1d&period1={start}&period2={now}&events=history"
    )
    data = http_get(url)
    if not data:
        return []
    try:
        result = data["chart"]["result"][0]
        timestamps = result["timestamp"]
        closes = result["indicators"]["quote"][0]["close"]
    except (KeyError, IndexError, TypeError):
        print("  [PARSE ERR] Brent")
        return []

    rows = []
    for ts, c in zip(timestamps, closes):
        if c is None:
            continue
        rows.append({
            "date": datetime.utcfromtimestamp(ts).strftime("%Y-%m-%d"),
            "value": round(float(c), 2),
        })
    print(f"  → {len(rows)} observations. Latest: {rows[-1] if rows else 'none'}")
    return rows

# ── 4. Egypt T-bill proxy (91-day) from World Bank ─────────────────────────
def fetch_interest_rate() -> list[dict]:
    # FR.INR.RINR = real interest rate — WB publishes annually
    return fetch_worldbank("FR.INR.RINR", "Egypt Real Interest Rate", years=10)

# ── 5. GDP growth ───────────────────────────────────────────────────────────
def fetch_gdp_growth() -> list[dict]:
    return fetch_worldbank("NY.GDP.MKTP.KD.ZG", "Egypt GDP Growth %", years=10)

# ── Build unified macro snapshot ────────────────────────────────────────────
def build_snapshot(
    egp_usd: list[dict],
    cpi: list[dict],
    brent: list[dict],
    interest: list[dict],
    gdp: list[dict],
) -> dict:
    """Build the unified macro_snapshot.json consumed by the decision engine."""
    def latest_val(rows: list[dict]) -> float | None:
        return rows[-1]["value"] if rows else None

    def latest_date(rows: list[dict]) -> str | None:
        return rows[-1]["date"] if rows else None

    # EGP trend: compare last 30 days
    egp_current = latest_val(egp_usd)
    egp_30d_ago = None
    if len(egp_usd) >= 30:
        egp_30d_ago = egp_usd[-30]["value"]
    egp_change_pct = None
    if egp_current and egp_30d_ago and egp_30d_ago > 0:
        egp_change_pct = round((egp_current - egp_30d_ago) / egp_30d_ago * 100, 2)

    # Inflation classification
    cpi_current = latest_val(cpi)
    inflation_regime = "unknown"
    if cpi_current is not None:
        if cpi_current > 25:
            inflation_regime = "very_high"
        elif cpi_current > 15:
            inflation_regime = "high"
        elif cpi_current > 7:
            inflation_regime = "moderate"
        else:
            inflation_regime = "low"

    # Decision implications
    implications = []
    if egp_change_pct is not None:
        if egp_change_pct < -2:
            implications.append("EGP depreciation favors exporters (ETEL, EAST, AMOC, EFID)")
        elif egp_change_pct > 2:
            implications.append("EGP appreciation favors importers and banks")
        else:
            implications.append("EGP broadly stable — currency risk neutral")

    if cpi_current is not None:
        if cpi_current > 20:
            implications.append(f"High inflation ({cpi_current:.1f}%) compresses real returns — prefer hard-asset and exporter stocks")
        elif cpi_current > 10:
            implications.append(f"Elevated inflation ({cpi_current:.1f}%) — monitor CBE rate decisions")
        else:
            implications.append(f"Inflation normalizing ({cpi_current:.1f}%) — improving real purchasing power")

    brent_current = latest_val(brent)
    if brent_current is not None:
        if brent_current > 90:
            implications.append(f"High oil (${brent_current:.0f}/bbl) benefits AMOC, EGCH; adds cost pressure for manufacturers")
        elif brent_current < 70:
            implications.append(f"Low oil (${brent_current:.0f}/bbl) benefits downstream industries, compresses upstream")
        else:
            implications.append(f"Oil at ${brent_current:.0f}/bbl — moderate impact on EGX energy names")

    return {
        "as_of": datetime.utcnow().strftime("%Y-%m-%d"),
        "egp_usd": {
            "current": egp_current,
            "date": latest_date(egp_usd),
            "change_30d_pct": egp_change_pct,
            "series_length": len(egp_usd),
        },
        "cpi_inflation_pct": {
            "current": cpi_current,
            "date": latest_date(cpi),
            "regime": inflation_regime,
        },
        "brent_usd": {
            "current": brent_current,
            "date": latest_date(brent),
        },
        "interest_rate_real_pct": {
            "current": latest_val(interest),
            "date": latest_date(interest),
        },
        "gdp_growth_pct": {
            "current": latest_val(gdp),
            "date": latest_date(gdp),
        },
        "decision_implications": implications,
        "sources": {
            "egp_usd": "Yahoo Finance (EGPUSD=X)",
            "cpi": "World Bank Open Data (FP.CPI.TOTL.ZG)",
            "brent": "Yahoo Finance (BZ=F)",
            "interest_rate": "World Bank Open Data (FR.INR.RINR)",
            "gdp": "World Bank Open Data (NY.GDP.MKTP.KD.ZG)",
        },
    }


def main():
    print("=== EGX Macro Data Fetcher ===\n")

    # Fetch all series
    egp_usd   = fetch_egp_usd(days=400)
    time.sleep(0.5)
    cpi       = fetch_worldbank("FP.CPI.TOTL.ZG", "Egypt CPI Inflation %", years=12)
    time.sleep(0.3)
    brent     = fetch_brent(days=400)
    time.sleep(0.5)
    interest  = fetch_interest_rate()
    time.sleep(0.3)
    gdp       = fetch_gdp_growth()

    # Save CSVs
    if egp_usd:
        save_csv(MACRO_DIR / "EGP_USD.csv", egp_usd, ["date", "value"])
        print(f"  Saved: EGP_USD.csv ({len(egp_usd)} rows)")

    if cpi:
        save_csv(MACRO_DIR / "egypt_cpi_inflation.csv", cpi, ["date", "value"])
        print(f"  Saved: egypt_cpi_inflation.csv ({len(cpi)} rows)")

    if brent:
        save_csv(MACRO_DIR / "BRENT_USD.csv", brent, ["date", "value"])
        print(f"  Saved: BRENT_USD.csv ({len(brent)} rows)")

    if interest:
        save_csv(MACRO_DIR / "egypt_interest_rate.csv", interest, ["date", "value"])
        print(f"  Saved: egypt_interest_rate.csv ({len(interest)} rows)")

    if gdp:
        save_csv(MACRO_DIR / "egypt_gdp_growth.csv", gdp, ["date", "value"])
        print(f"  Saved: egypt_gdp_growth.csv ({len(gdp)} rows)")

    # Build + save unified snapshot
    snapshot = build_snapshot(egp_usd, cpi, brent, interest, gdp)
    snap_path = MACRO_DIR / "macro_snapshot.json"
    with open(snap_path, "w", encoding="utf-8") as f:
        json.dump(snapshot, f, indent=2, ensure_ascii=False)
    print("  Saved: macro_snapshot.json")

    print("\n=== Macro Snapshot ===")
    print(json.dumps(snapshot, indent=2, ensure_ascii=False))
    print("\nDone.")


if __name__ == "__main__":
    main()
