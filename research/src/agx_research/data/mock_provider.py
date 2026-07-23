"""A local-CSV backed DataProvider for development and tests.

Layout expected under `root`:

    prices/<TICKER>.csv          columns: date,open,high,low,close,volume
    corporate_events.csv         columns: ticker,date,event_type,description,details_json
                                  (details_json is an optional JSON object, e.g.
                                  {"split_ratio": 2.0} or {"dividend_amount": 3.5};
                                  defaults to {} if the column is missing/blank --
                                  see data/adjustments.py for how it's used)
    macro/<SERIES_ID>.csv        columns: date,value
    news.csv                     columns: date,source,headline,tickers,body
                                  (tickers is a "|"-separated list, body optional)

This is a stand-in for a real EGX data vendor integration and should not be
treated as a source of truth for research conclusions.
"""

from __future__ import annotations

import csv
import json
from datetime import date
from pathlib import Path

from agx_research.data.provider import DataProvider
from agx_research.data.schemas import CorporateEvent, MacroObservation, NewsItem, PriceBar


def _parse_date(raw: str) -> date:
    return date.fromisoformat(raw)


class MockDataProvider(DataProvider):
    def __init__(self, root: Path | str):
        self.root = Path(root)

    def get_price_history(self, ticker: str, start: date, end: date) -> list[PriceBar]:
        path = self.root / "prices" / f"{ticker}.csv"
        if not path.exists():
            return []
        bars = []
        with path.open(newline="") as f:
            for row in csv.DictReader(f):
                trade_date = _parse_date(row["date"])
                if start <= trade_date <= end:
                    bars.append(
                        PriceBar(
                            ticker=ticker,
                            trade_date=trade_date,
                            open=float(row["open"]),
                            high=float(row["high"]),
                            low=float(row["low"]),
                            close=float(row["close"]),
                            volume=int(row["volume"]),
                        )
                    )
        return sorted(bars, key=lambda b: b.trade_date)

    def get_corporate_events(
        self, ticker: str, start: date, end: date
    ) -> list[CorporateEvent]:
        path = self.root / "corporate_events.csv"
        if not path.exists():
            return []
        events = []
        with path.open(newline="") as f:
            for row in csv.DictReader(f):
                if row["ticker"] != ticker:
                    continue
                event_date = _parse_date(row["date"])
                if start <= event_date <= end:
                    raw_details = (row.get("details_json") or "").strip()
                    events.append(
                        CorporateEvent(
                            ticker=ticker,
                            event_date=event_date,
                            event_type=row["event_type"],
                            description=row["description"],
                            details=json.loads(raw_details) if raw_details else {},
                        )
                    )
        return sorted(events, key=lambda e: e.event_date)

    def get_macro_series(
        self, series_id: str, start: date, end: date
    ) -> list[MacroObservation]:
        path = self.root / "macro" / f"{series_id}.csv"
        if not path.exists():
            return []
        observations = []
        with path.open(newline="") as f:
            for row in csv.DictReader(f):
                observation_date = _parse_date(row["date"])
                if start <= observation_date <= end:
                    observations.append(
                        MacroObservation(
                            series_id=series_id,
                            observation_date=observation_date,
                            value=float(row["value"]),
                        )
                    )
        return sorted(observations, key=lambda o: o.observation_date)

    def get_news(self, ticker: str | None, start: date, end: date) -> list[NewsItem]:
        path = self.root / "news.csv"
        if not path.exists():
            return []
        items = []
        with path.open(newline="") as f:
            for row in csv.DictReader(f):
                published_at = _parse_date(row["date"])
                if not (start <= published_at <= end):
                    continue
                tickers = [t for t in row["tickers"].split("|") if t]
                if ticker is not None and ticker not in tickers:
                    continue
                items.append(
                    NewsItem(
                        published_at=published_at,
                        source=row["source"],
                        headline=row["headline"],
                        tickers=tickers,
                        body=row.get("body") or None,
                    )
                )
        return sorted(items, key=lambda n: n.published_at)


# `MockDataProvider` was always just a local-CSV-backed DataProvider; the
# "mock" framing described its placeholder *content* (synthetic test
# fixtures), not its mechanism. Real data collected by `collectors/` is
# materialized into the same CSV layout and read through this same class
# under this clearer alias -- collected real data needs no new provider.
LocalCsvDataProvider = MockDataProvider
