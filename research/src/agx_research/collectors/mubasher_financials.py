"""Mubasher financial-statement fallback.

Mubasher pages expose a structured `midata.financialStatement` object in the
HTML. We parse that object as disclosed, preserve its currency and period label,
and never infer missing/null values. It is a secondary source and is lower
priority than EGX/FRA/issuer documents.
"""
from __future__ import annotations

import ast
import re
from datetime import date

from agx_research.collectors.base import CollectionBatch, Collector
from agx_research.collectors.fetcher import FetchDisallowed, FetchError
from agx_research.collectors.raw import RawDocument, build_raw_document
from agx_research.financials.schema import FinancialStatementLineItem

_LABEL_MAP = {
    "Total Assets": "total_assets",
    "Total Liabilities": "total_liabilities",
    "Total Owners' Equity & Minority Interest Equity": "total_equity",
    "Net Income or Loss": "net_income",
    "Gross Profit": "gross_profit",
    "Net Cash Flow from (Used In) Operating Activities": "operating_cash_flow",
    "Net Change In Cash & Cash Equivalents": "cash_and_equivalents_change",
    "Net Cash Flow from (Used In) Investing Activities": "investing_cash_flow",
    "Net Cash Flow from (Used In) Financing Activities": "financing_cash_flow",
}


class MubasherFinancialsCollector(Collector):
    name = "MubasherFinancialsCollector"
    version = "1.0.0"

    def __init__(self, spec, *, tickers: list[str], fetcher=None):
        super().__init__(spec, fetcher)
        self.tickers = sorted({ticker.upper() for ticker in tickers})

    @staticmethod
    def url(ticker: str) -> str:
        return f"https://english.mubasher.info/markets/EGX/stocks/{ticker}/financial-statements/"

    def fetch(self) -> list[RawDocument]:
        documents = []
        for ticker in self.tickers:
            try:
                html = self.fetcher.fetch_text(self.url(ticker), self.spec)
            except (FetchDisallowed, FetchError, OSError, UnicodeError):
                continue
            if "midata.financialStatement" not in html:
                continue
            documents.append(build_raw_document(
                source_id=self.spec.id, collector=self.name, collector_version=self.version,
                original_url=self.url(ticker), content_text=html,
                schema_version=self.spec.schema_version, license=self.spec.license,
            ))
        return documents

    def parse(self, document: RawDocument) -> CollectionBatch:
        ticker = self._ticker_from_url(document.original_url)
        batch = CollectionBatch(source_id=document.source_id, raw_document_id=document.id)
        if not ticker:
            batch.parse_warnings.append("Ticker could not be resolved from Mubasher URL.")
            return batch
        payload = self._extract_object(document.content_text)
        if payload is None:
            batch.parse_warnings.append("Mubasher financialStatement object not found or invalid.")
            return batch
        currency = payload.get("currency") or "EGP"
        for period in payload.get("periods", []):
            label = str(period.get("label", ""))
            period_type = "ANNUAL" if "Fourth Quarter" in label else "QUARTERLY"
            for section in period.get("sections", []):
                statement_type = self._statement_type(section.get("label", ""))
                for record in section.get("records", []):
                    metric = _LABEL_MAP.get(record.get("label"))
                    if metric is None:
                        continue
                    for year_text, raw_value in (record.get("values") or {}).items():
                        if raw_value is None:
                            continue
                        try:
                            year = int(year_text)
                            value = float(raw_value)
                        except (TypeError, ValueError):
                            continue
                        batch.financial_statement_line_items.append(FinancialStatementLineItem(
                            ticker=ticker,
                            period_end_date=self._period_end(year, period_type, label),
                            period_type=period_type,
                            statement_type=statement_type,
                            line_item=metric,
                            value=value,
                            currency=currency,
                        ))
        if batch.financial_statement_line_items:
            # Mubasher may expose the same statement value twice: once in
            # absolute EGP and once in thousands. Collapse only exact
            # ticker/period/metric duplicates and choose the absolute-scale
            # value when the ratio is approximately 1,000. Do not average
            # conflicting accounting values.
            grouped={}
            balance_metrics={'total_assets','total_liabilities','total_equity'}
            for item in batch.financial_statement_line_items:
                period_key=None if item.line_item in balance_metrics else item.period_type
                grouped.setdefault((item.line_item,item.period_end_date,period_key),[]).append(item)
            deduped=[]
            absolute_metrics={'total_assets','total_liabilities','total_equity','net_income','gross_profit','operating_cash_flow','cash_and_equivalents_change','investing_cash_flow','financing_cash_flow'}
            for key,group in grouped.items():
                if len(group)==1:
                    deduped.append(group[0])
                    continue
                vals=[abs(float(x.value)) for x in group if x.value not in (None,0)]
                if vals and max(vals)/min(vals)>=900 and max(vals)/min(vals)<=1100:
                    chosen=max(group,key=lambda x:abs(float(x.value))) if key[0] in absolute_metrics else min(group,key=lambda x:abs(float(x.value)))
                    batch.parse_warnings.append(f"Collapsed Mubasher scale duplicate for {key[0]} {key[1]} using absolute-scale value.")
                    deduped.append(chosen)
                else:
                    # Preserve the last disclosed record but expose the
                    # conflict; downstream validation can reject it.
                    batch.parse_warnings.append(f"Conflicting duplicate Mubasher values for {key[0]} {key[1]}.")
                    deduped.append(group[-1])
            batch.financial_statement_line_items=deduped
        if not batch.financial_statement_line_items:
            batch.parse_warnings.append("No mapped financial statement records found.")
        return batch

    @staticmethod
    def _extract_object(html: str) -> dict | None:
        marker = "midata.financialStatement ="
        start = html.find(marker)
        if start < 0:
            return None
        start += len(marker)
        while start < len(html) and html[start].isspace():
            start += 1
        depth = 0
        quote = None
        escaped = False
        end = None
        for idx in range(start, len(html)):
            char = html[idx]
            if quote:
                if escaped:
                    escaped = False
                elif char == "\\":
                    escaped = True
                elif char == quote:
                    quote = None
                continue
            if char in "'\"":
                quote = char
            elif char == "{":
                depth += 1
            elif char == "}":
                depth -= 1
                if depth == 0:
                    end = idx + 1
                    break
        if end is None:
            return None
        raw = html[start:end].replace("null", "None").replace("true", "True").replace("false", "False")
        try:
            value = ast.literal_eval(raw)
        except (SyntaxError, ValueError):
            return None
        return value if isinstance(value, dict) else None

    @staticmethod
    def _ticker_from_url(url: str) -> str | None:
        match = re.search(r"/stocks/([^/]+)/financial-statements", url)
        return match.group(1).upper() if match else None

    @staticmethod
    def _statement_type(label: str) -> str:
        if "Balance" in label:
            return "BALANCE_SHEET"
        if "Cash" in label:
            return "CASH_FLOW"
        return "INCOME_STATEMENT"

    @staticmethod
    def _period_end(year: int, period_type: str, label: str) -> date:
        if period_type == "ANNUAL":
            return date(year, 12, 31)
        if "First Quarter" in label:
            return date(year, 3, 31)
        if "Second Quarter" in label:
            return date(year, 6, 30)
        if "Third Quarter" in label:
            return date(year, 9, 30)
        return date(year, 12, 31)
