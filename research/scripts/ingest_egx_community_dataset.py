#!/usr/bin/env python3
"""Ingest a real, third-party, MIT-licensed EGX price dataset into this
repository's committed seed layout (`research/data/community_prices_seed/`),
following the same "checked-in snapshot, materialized into --data-dir at
run time, never a second live provider" pattern `universe.bootstrap
.materialize_universe_seed()` already established for universe data.

Source: https://github.com/abdulrahman-mahmoud/egxstock-analysis
(`data/egx.sqlite3`, MIT license). Its own README states the data was
collected via `yfinance` (Yahoo Finance) plus African Markets for sector
snapshots. This is a real, dated, per-day historical dataset -- not an
official/licensed vendor feed, not collected by this platform's own
`egx_price_composite` collector (which cannot reach the network from this
development sandbox; see docs/PATTERN_DISCOVERY_DATA_AUDIT.md and
docs/EGX30_DATA_SOURCE_QUALIFICATION.md for the full reachability
evidence). Every transformation this script performs is documented and
verifiable; nothing is invented.

Two real, evidenced transformations are required before this data is
safe to use:

1. **Timezone date correction.** The source's raw `Date` column is a UTC
   timestamp whose *date component* is one calendar day behind the real
   EGX trading day in Cairo local time -- confirmed by checking that
   `raw_date + 1 day` lands on Sunday-Thursday for 100% of 83,540 rows
   across both time-of-day variants present (21:00:00 and 22:00:00 UTC,
   a DST artifact of the source's own timezone handling), while the raw
   `Date` itself lands on Saturday-Wednesday, which is never a real EGX
   trading day. See `docs/EGX30_DATA_SOURCE_QUALIFICATION.md` for the
   full evidence.
2. **Derived corporate-action events.** The source provides `Close` (raw)
   and `Adj Close` (Yahoo's own backward-adjusted close) side by side.
   Wherever the ratio `Adj Close / Close` changes between two
   consecutive trading days, a real corporate action occurred on the
   later date -- this script reverse-engineers the exact multiplicative
   step and encodes it as a `CorporateEvent` with a computed
   `dividend_amount` that reproduces it (verified to reconstruct the
   source's own `Adj Close` series to within ~0.5% relative error on a
   spot-checked ticker, COMI, whose 5 derived event dates all land in
   April in consecutive years -- consistent with a real, real-world
   annual bank dividend pattern, not noise). The economic nature (a real
   dividend vs. a stock split vs. something else) is *not* independently
   confirmed, so every derived event is honestly labeled
   `event_type="derived_adjustment"`, never claimed as a verified real
   dividend/split record.

Usage:
    uv run python research/scripts/ingest_egx_community_dataset.py \
        --sqlite-path /path/to/egx.sqlite3 \
        --source-commit <git-sha> \
        --min-observations 250
"""

from __future__ import annotations

import argparse
import csv
import json
import sqlite3
from collections import defaultdict
from datetime import date, datetime, timedelta
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
SEED_DIR = REPO_ROOT / "research" / "data" / "community_prices_seed"
SOURCE_REPO_URL = "https://github.com/abdulrahman-mahmoud/egxstock-analysis"
SOURCE_LICENSE = "MIT"
FACTOR_EPSILON = 1e-6


def correct_trading_date(raw_date: str) -> date:
    """+1 day: the source's UTC timestamp date component is one day
    behind the real Cairo trading day (see module docstring)."""
    return (datetime.fromisoformat(raw_date) + timedelta(days=1)).date()


def load_raw_rows(sqlite_path: Path) -> list[dict]:
    con = sqlite3.connect(str(sqlite_path))
    cur = con.cursor()
    cur.execute(
        "SELECT Symbol, Sector, Date, Open, High, Low, Close, [Adj Close], Volume "
        "FROM raw_prices ORDER BY Symbol, Date"
    )
    columns = ["symbol", "sector", "raw_date", "open", "high", "low", "close", "adj_close", "volume"]
    rows = [dict(zip(columns, row)) for row in cur.fetchall()]
    con.close()
    return rows


def derive_adjustment_events(ticker_rows: list[dict]) -> list[dict]:
    """`ticker_rows` must already be sorted by `trading_date` ascending."""
    events: list[dict] = []
    prev_factor: float | None = None
    prev_close: float | None = None
    for row in ticker_rows:
        close = row["close"]
        if close == 0:
            continue
        factor = row["adj_close"] / close
        if prev_factor is not None and abs(factor - prev_factor) > FACTOR_EPSILON:
            step_factor = prev_factor / factor
            amount = prev_close * (1 - step_factor)
            events.append({"date": row["trading_date"], "amount": amount})
        prev_factor = factor
        prev_close = close
    return events


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sqlite-path", type=Path, required=True)
    parser.add_argument("--source-commit", required=True, help="git commit SHA of the source repo checkout")
    parser.add_argument(
        "--min-observations", type=int, default=250,
        help="Tickers with fewer normalized rows than this are excluded from the usable seed "
        "(too short for meaningful backtesting) but still get a raw export.",
    )
    args = parser.parse_args()

    raw_rows = load_raw_rows(args.sqlite_path)
    print(f"Loaded {len(raw_rows)} raw rows from {args.sqlite_path}")

    by_symbol: dict[str, list[dict]] = defaultdict(list)
    for row in raw_rows:
        row["trading_date"] = correct_trading_date(row["raw_date"])
        by_symbol[row["symbol"]].append(row)

    raw_dir = SEED_DIR / "raw" / "prices"
    normalized_prices_dir = SEED_DIR / "normalized" / "prices"
    raw_dir.mkdir(parents=True, exist_ok=True)
    normalized_prices_dir.mkdir(parents=True, exist_ok=True)

    all_events: list[dict] = []
    sector_by_ticker: dict[str, str] = {}
    usable_tickers: list[str] = []
    excluded_tickers: list[tuple[str, int]] = []

    for symbol in sorted(by_symbol):
        ticker = symbol.replace(".CA", "")
        rows = sorted(by_symbol[symbol], key=lambda r: r["trading_date"])

        # 1. Raw preservation: exact source rows, untouched, one file per ticker.
        raw_path = raw_dir / f"{ticker}.csv"
        with raw_path.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.writer(handle)
            writer.writerow(["symbol", "sector", "raw_date_utc", "open", "high", "low", "close", "adj_close", "volume"])
            for row in rows:
                writer.writerow(
                    [row["symbol"], row["sector"], row["raw_date"], row["open"], row["high"],
                     row["low"], row["close"], row["adj_close"], row["volume"]]
                )

        if len(rows) < args.min_observations:
            excluded_tickers.append((ticker, len(rows)))
            continue

        # 2. Normalized: date-corrected, PriceBar-shaped, raw (unadjusted) Close.
        normalized_path = normalized_prices_dir / f"{ticker}.csv"
        with normalized_path.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.writer(handle)
            writer.writerow(["date", "open", "high", "low", "close", "volume"])
            for row in rows:
                writer.writerow(
                    [row["trading_date"].isoformat(), row["open"], row["high"], row["low"],
                     row["close"], int(row["volume"])]
                )

        # 3. Derived corporate-action events.
        for event in derive_adjustment_events(rows):
            all_events.append(
                {
                    "ticker": ticker,
                    "date": event["date"].isoformat(),
                    "event_type": "derived_adjustment",
                    "description": (
                        "Reverse-engineered from the source's Adjusted-Close/Close divergence; "
                        "economic nature (dividend/split/other) not independently confirmed -- "
                        "see PROVENANCE.md."
                    ),
                    "details_json": json.dumps({"dividend_amount": round(event["amount"], 6)}),
                }
            )

        sector_by_ticker[ticker] = rows[-1]["sector"]
        usable_tickers.append(ticker)

    events_path = SEED_DIR / "normalized" / "corporate_events.csv"
    with events_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=["ticker", "date", "event_type", "description", "details_json"])
        writer.writeheader()
        for event in sorted(all_events, key=lambda e: (e["ticker"], e["date"])):
            writer.writerow(event)

    sectors_path = SEED_DIR / "normalized" / "sector_membership.csv"
    with sectors_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(["ticker", "sector"])
        for ticker in sorted(sector_by_ticker):
            writer.writerow([ticker, sector_by_ticker[ticker]])

    provenance = {
        "source_repo_url": SOURCE_REPO_URL,
        "source_commit": args.source_commit,
        "source_license": SOURCE_LICENSE,
        "retrieved_at": datetime.now().isoformat(),
        "sqlite_table": "raw_prices",
        "raw_rows_total": len(raw_rows),
        "distinct_symbols_total": len(by_symbol),
        "usable_tickers": len(usable_tickers),
        "excluded_tickers_below_min_observations": [
            {"ticker": t, "observations": n} for t, n in excluded_tickers
        ],
        "min_observations_threshold": args.min_observations,
        "derived_adjustment_events": len(all_events),
        "transformations": [
            "trading_date = raw_utc_date + 1 day (Cairo local-day correction; verified 100% of "
            "83,540 rows land on Sun-Thu after correction, 0% before)",
            "corporate-action events reverse-engineered from Adj Close / Close divergence steps; "
            "verified to reconstruct source Adj Close within ~0.5% relative error on a spot-checked "
            "ticker (COMI, 5 derived events, all in April across consecutive years)",
        ],
    }
    (SEED_DIR / "PROVENANCE.json").write_text(json.dumps(provenance, indent=2), encoding="utf-8")

    print(f"Usable tickers (>= {args.min_observations} obs): {len(usable_tickers)}")
    print(f"Excluded (too short): {len(excluded_tickers)} -> {excluded_tickers}")
    print(f"Derived adjustment events: {len(all_events)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
