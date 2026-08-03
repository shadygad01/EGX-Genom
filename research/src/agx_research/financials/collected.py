"""CollectedFinancialStatementProvider: reads the local-CSV layout
`collectors.service.CollectionService` materializes financial statement
line items into -- mirrors `data.mock_provider.LocalCsvDataProvider`'s
"collected data reads through the same interface as everything else"
pattern, and `universe.collected.CollectedUniverseProvider`'s "empty, never
fabricated, when nothing's been collected" contract.

Layout: `<data_dir>/financial_statements/<TICKER>.csv`, columns
`period_end_date,period_type,statement_type,line_item,value,currency`.
"""

from __future__ import annotations

import csv
from datetime import date
from pathlib import Path

from agx_research.financials.provider import FinancialStatementProvider
from agx_research.financials.schema import FinancialStatementLineItem


class CollectedFinancialStatementProvider(FinancialStatementProvider):
    def __init__(self, data_dir: Path | str):
        self.data_dir = Path(data_dir)

    def get_line_items(
        self, ticker: str, start: date, end: date, *, statement_type: str | None = None
    ) -> list[FinancialStatementLineItem]:
        path = self.data_dir / "financial_statements" / f"{ticker}.csv"
        if not path.exists():
            return []

        items = []
        with path.open(newline="", encoding="utf-8-sig") as f:
            for row in csv.DictReader(f):
                period_end_date = date.fromisoformat(row["period_end_date"])
                if not (start <= period_end_date <= end):
                    continue
                if statement_type is not None and row["statement_type"] != statement_type:
                    continue
                items.append(
                    FinancialStatementLineItem(
                        ticker=ticker,
                        period_end_date=period_end_date,
                        period_type=row["period_type"],
                        statement_type=row["statement_type"],
                        line_item=row["line_item"],
                        value=float(row["value"]),
                        currency=row.get("currency") or "EGP",
                    )
                )
        return sorted(items, key=lambda i: (i.period_end_date, i.statement_type, i.line_item))

