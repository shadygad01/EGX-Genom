"""Structured financial tables from StockAnalysis EGX pages.

This is a secondary, public-data fallback. It preserves the URL and period,
uses only visible annual columns, skips TTM/current/growth columns, and never
turns a missing row into a zero. Primary EGX/FRA/issuer filings remain higher
priority when both sources cover the same period.
"""
from __future__ import annotations

import re
from datetime import date
from urllib.parse import urlsplit

from bs4 import BeautifulSoup

from agx_research.collectors.base import CollectionBatch, Collector
from agx_research.collectors.fetcher import FetchDisallowed, FetchError
from agx_research.collectors.raw import RawDocument, build_raw_document
from agx_research.financials.schema import FinancialStatementLineItem

_LABELS = {
    "revenue": ("revenue", "revenue revenue growth"),
    "gross_profit": ("gross profit", "gross profit gross profit growth"),
    "operating_income": ("operating income", "operating income operating income growth"),
    "net_income": ("net income", "net income net income growth"),
    "eps_basic": ("earnings per share", "earnings per share eps growth"),
    "cash_and_equivalents": ("cash & investments", "cash and investments cash and investments growth"),
    "total_debt": ("total debt", "total debt total debt growth"),
    "operating_cash_flow": ("operating cash flow", "operating cash flow operating cash flow growth"),
    "free_cash_flow": ("free cash flow", "free cash flow free cash flow growth"),
}

_DATE_RE = re.compile(r"(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec) ['’]?\d{2}\s+(?:[A-Z][a-z]{2})?\s*(\d{1,2}),\s*(\d{4})")


class StockAnalysisFinancialsCollector(Collector):
    name = "StockAnalysisFinancialsCollector"
    version = "1.0.0"

    def __init__(self, spec, *, tickers: list[str], fetcher=None):
        super().__init__(spec, fetcher)
        self.tickers = sorted({ticker.upper() for ticker in tickers})

    @staticmethod
    def url(ticker: str) -> str:
        return f"https://stockanalysis.com/quote/egx/{ticker}/financials/"

    def fetch(self) -> list[RawDocument]:
        documents = []
        for ticker in self.tickers:
            url = self.url(ticker)
            try:
                html = self.fetcher.fetch_text(url, self.spec)
            except (FetchDisallowed, FetchError, OSError, UnicodeError):
                continue
            if "Financials Overview" not in html and "financials" not in html.casefold():
                continue
            documents.append(build_raw_document(
                source_id=self.spec.id, collector=self.name, collector_version=self.version,
                original_url=url, content_text=html, schema_version=self.spec.schema_version,
                license=self.spec.license,
            ))
        return documents

    def parse(self, document: RawDocument) -> CollectionBatch:
        ticker = self._ticker_from_url(document.original_url)
        batch = CollectionBatch(source_id=document.source_id, raw_document_id=document.id)
        if not ticker:
            batch.parse_warnings.append("Ticker could not be resolved from StockAnalysis URL.")
            return batch
        soup = BeautifulSoup(document.content_text, "html.parser")
        for table in soup.find_all("table"):
            rows = [[cell.get_text(" ", strip=True) for cell in tr.find_all(["th", "td"])] for tr in table.find_all("tr")]
            rows = [r for r in rows if r]
            if len(rows) < 3:
                continue
            headers = rows[0]
            periods = rows[1]
            selected: list[tuple[int, date]] = []
            for idx in range(1, min(len(headers), len(periods))):
                if not str(headers[idx]).strip().upper().startswith("FY "):
                    continue
                match = _DATE_RE.search(periods[idx])
                if not match:
                    continue
                year = int(match.group(2))
                month = self._month_from_period(periods[idx])
                day = int(re.search(r"[A-Z][a-z]{2}\s+(\d{1,2}),", periods[idx]).group(1))
                selected.append((idx, date(year, month, day)))
            if not selected:
                continue
            for row in rows[2:]:
                label = self._normalize(row[0])
                metric = self._metric(label)
                if metric is None:
                    continue
                for idx, period_end in selected:
                    if idx >= len(row):
                        continue
                    value = self._number(row[idx])
                    if value is None:
                        continue
                    batch.financial_statement_line_items.append(FinancialStatementLineItem(
                        ticker=ticker, period_end_date=period_end, period_type="ANNUAL",
                        statement_type=self._statement_type(metric), line_item=metric,
                        value=value, currency="EGP",
                    ))
        if not batch.financial_statement_line_items:
            batch.parse_warnings.append("No supported annual financial rows were parsed.")
        return batch

    @staticmethod
    def _normalize(value: str) -> str:
        return " ".join(value.casefold().replace("&", "&").split())

    @classmethod
    def _metric(cls, label: str) -> str | None:
        for metric, labels in _LABELS.items():
            if label in labels or label.startswith(labels[0] + " "):
                return metric
        if label.endswith(" growth") or label == "growth":
            return None
        return None

    @staticmethod
    def _number(value: str) -> float | None:
        value = value.strip().replace(",", "")
        if not value or value in {"-", "—", "N/A"} or value.endswith("%"):
            return None
        try:
            return float(value.replace("(", "-").replace(")", ""))
        except ValueError:
            return None

    @staticmethod
    def _statement_type(metric: str) -> str:
        if metric in {"cash_and_equivalents", "total_debt"}:
            return "BALANCE_SHEET"
        if metric in {"operating_cash_flow", "free_cash_flow"}:
            return "CASH_FLOW"
        return "INCOME_STATEMENT"

    @staticmethod
    def _month_from_period(value: str) -> int:
        months = {name: i for i, name in enumerate(("Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"), 1)}
        return months[re.search(r"\b(" + "|".join(months) + r")\b", value).group(1)]

    @staticmethod
    def _ticker_from_url(url: str) -> str | None:
        parts = [p for p in urlsplit(url).path.split("/") if p]
        try:
            index = parts.index("egx")
            return parts[index + 1].upper()
        except (ValueError, IndexError):
            return None
