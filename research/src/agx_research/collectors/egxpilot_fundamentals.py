"""No-key EGXpilot market-fundamental snapshots for the full AGX universe.

Only numeric facts are collected.  EGXpilot's own recommendation and AI text
are deliberately ignored so an opaque third-party opinion can never become an
AGX decision.  Snapshot-labelled fields are kept distinct from audited annual
statement fields; only shares outstanding is derived mechanically from market
capitalisation / price when the API omits its otherwise equivalent field.
"""

from __future__ import annotations

import json
from datetime import date, datetime
from urllib.parse import urlsplit

from agx_research.collectors.base import CollectionBatch, Collector
from agx_research.collectors.fetcher import FetchDisallowed, FetchError
from agx_research.collectors.raw import RawDocument, build_raw_document
from agx_research.data.schemas import PriceBar
from agx_research.financials.schema import FinancialStatementLineItem


class EgxPilotFundamentalsCollector(Collector):
    name = "EgxPilotFundamentalsCollector"
    version = "1.0.0"

    def __init__(self, spec, *, tickers: list[str], fetcher=None):
        super().__init__(spec, fetcher)
        self.tickers = sorted(set(tickers))
        self.fetch_warnings: list[str] = []

    def fetch(self) -> list[RawDocument]:
        documents: list[RawDocument] = []
        origin = f"{urlsplit(self.spec.base_url).scheme}://{urlsplit(self.spec.base_url).netloc}"
        for ticker in self.tickers:
            endpoints = (
                ("fundamentals", f"{self.spec.base_url}{ticker}"),
                ("history", f"{origin}/api/stockanalysis/{ticker}"),
            )
            for kind, url in endpoints:
                try:
                    content = self.fetcher.fetch_text(url, self.spec)
                except (FetchError, FetchDisallowed) as exc:
                    self.fetch_warnings.append(
                        f"{ticker}/{kind}: {type(exc).__name__}: {exc}"
                    )
                    continue
                documents.append(
                    build_raw_document(
                        source_id=self.spec.id,
                        collector=self.name,
                        collector_version=self.version,
                        original_url=f"{url}#kind={kind}",
                        content_text=content,
                        schema_version=self.spec.schema_version,
                        license=self.spec.license,
                    )
                )
        if not documents and self.fetch_warnings:
            sample = "; ".join(self.fetch_warnings[:3])
            raise FetchError(
                f"EGXpilot returned no usable ticker documents ({len(self.fetch_warnings)} failures): "
                f"{sample}"
            )
        return documents

    def parse(self, document: RawDocument) -> CollectionBatch:
        batch = CollectionBatch(source_id=document.source_id, raw_document_id=document.id)
        try:
            payload = json.loads(document.content_text)
        except json.JSONDecodeError as exc:
            batch.parse_warnings.append(f"Invalid JSON snapshot: {exc}")
            return batch
        if "history" in payload:
            return self._parse_history(payload, batch)
        try:
            updated = datetime.fromisoformat(payload["updatedAt"]).date()
            stock = payload["stock"]
            ticker = str(stock["Symbol"]).upper()
        except (KeyError, TypeError, ValueError) as exc:
            batch.parse_warnings.append(f"Invalid stock snapshot: {exc}")
            return batch
        if ticker not in self.tickers:
            batch.parse_warnings.append(f"Ticker {ticker} is outside the declared universe.")
            return batch

        def number(name: str) -> float | None:
            raw = stock.get(name)
            if raw in (None, ""):
                return None
            try:
                return float(str(raw).replace(",", ""))
            except ValueError:
                batch.parse_warnings.append(f"{ticker} {name}: non-numeric value skipped")
                return None

        facts = {
            "market_cap": number("MarketCap"),
            "market_pe": number("PE"),
            "market_eps": number("EPS"),
            "market_dividend_per_share": number("Dividend"),
            "market_dividend_yield": number("Yield"),
            "market_beta": number("Beta"),
            "market_revenue": number("Revenue"),
        }
        shares = number("Shares")
        price = number("LastPrice")
        if shares is None and facts["market_cap"] is not None and price and price > 0:
            shares = facts["market_cap"] / price
        if shares is not None:
            facts["shares_outstanding"] = shares

        for line_item, value in facts.items():
            if value is None:
                continue
            batch.financial_statement_line_items.append(
                FinancialStatementLineItem(
                    ticker=ticker,
                    period_end_date=updated,
                    period_type="SNAPSHOT",
                    statement_type="MARKET_FUNDAMENTALS",
                    line_item=line_item,
                    value=value,
                    currency="EGP",
                )
            )
        if not batch.financial_statement_line_items:
            batch.parse_warnings.append(f"{ticker}: no numeric market fundamentals")
        return batch

    def _parse_history(self, payload: dict, batch: CollectionBatch) -> CollectionBatch:
        ticker = str(payload.get("symbol", "")).upper()
        if ticker not in self.tickers:
            batch.parse_warnings.append(f"Ticker {ticker or '<missing>'} is outside the universe.")
            return batch
        rows = payload.get("history")
        if not isinstance(rows, list):
            batch.parse_warnings.append(f"{ticker}: history is not a list")
            return batch
        for row in rows:
            try:
                batch.price_bars.append(
                    PriceBar(
                        ticker=ticker,
                        trade_date=date.fromisoformat(str(row["time"])),
                        open=float(row["open"]),
                        high=float(row["high"]),
                        low=float(row["low"]),
                        close=float(row["close"]),
                        volume=int(float(row["volume"])),
                    )
                )
            except (KeyError, TypeError, ValueError):
                continue
        if not batch.price_bars:
            batch.parse_warnings.append(f"{ticker}: no valid OHLCV history")
        return batch
