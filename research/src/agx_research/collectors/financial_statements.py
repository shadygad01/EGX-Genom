"""FinancialStatementCollector: turns one company's downloadable, structured
financial-statement export (CSV -- income statement / balance sheet / cash
flow line items, long format) into `FinancialStatementLineItem` candidates.

Column order isn't assumed; every column is found by header-text matching
(same posture as `collectors.index_constituents.IndexConstituentCollector`
and the platform's other declared heuristics), since no real company IR
financial-statement export has been fetched yet to verify an exact header
— inventing one would be guessing a wire format, not parsing a real one.

One collector instance serves one company (`ticker` supplied by the
caller, since a per-company export doesn't self-report its own ticker) --
mirrors `IndexConstituentCollector` serving one index per instance.

**Scope note**: `sources.catalog`'s `company_ir` entry's own notes expect
IR disclosures to be PDF/XBRL more often than a clean CSV export -- this
collector covers the structured-export case (a data vendor or IR page
that does publish one), not PDF extraction. A generic PDF-based financial-
statement extractor is deliberately *not* built here, for the same reason
`collectors.pdf.PdfDocumentCollector.parse()` stays abstract: real filing
layouts vary enough that a generic numeric extraction heuristic risks
silently reading the wrong line item's value, not just missing one --
a materially worse failure mode than a missing/blocked column here. That
extraction is left for a concrete, source-verified subclass once a real
PDF layout exists to build and test against (TD-32).
"""

from __future__ import annotations

import csv
import io

from agx_research.collectors.base import CollectionBatch, Collector
from agx_research.collectors.csv_columns import find_column
from agx_research.collectors.raw import RawDocument, fetch_single_text_document
from agx_research.financials.schema import FinancialStatementLineItem

_PERIOD_END_HEADER_HINTS = ("period_end", "period end", "as of", "fiscal period", "date")
_PERIOD_TYPE_HEADER_HINTS = ("period_type", "period type", "frequency")
_STATEMENT_TYPE_HEADER_HINTS = ("statement_type", "statement type", "statement")
_LINE_ITEM_HEADER_HINTS = ("line_item", "line item", "item", "metric")
_VALUE_HEADER_HINTS = ("value", "amount")
_CURRENCY_HEADER_HINTS = ("currency",)

_REQUIRED_COLUMNS = (
    ("period_end_date", _PERIOD_END_HEADER_HINTS),
    ("period_type", _PERIOD_TYPE_HEADER_HINTS),
    ("statement_type", _STATEMENT_TYPE_HEADER_HINTS),
    ("line_item", _LINE_ITEM_HEADER_HINTS),
    ("value", _VALUE_HEADER_HINTS),
)


class FinancialStatementCollector(Collector):
    name = "FinancialStatementCollector"
    version = "1.0.0"

    def __init__(self, spec, ticker: str, fetcher=None):
        super().__init__(spec, fetcher)
        self.ticker = ticker

    def fetch(self) -> list[RawDocument]:
        return fetch_single_text_document(
            self.fetcher, self.spec,
            collector_name=self.name, collector_version=self.version, url=self.spec.base_url,
        )

    def parse(self, document: RawDocument) -> CollectionBatch:
        batch = CollectionBatch(source_id=document.source_id, raw_document_id=document.id)
        reader = csv.reader(io.StringIO(document.content_text))
        header = next(reader, None)
        if not header:
            batch.parse_warnings.append("Empty document; nothing parsed.")
            return batch

        columns: dict[str, int] = {}
        missing: list[str] = []
        for name, hints in _REQUIRED_COLUMNS:
            position = find_column(header, hints)
            if position is None:
                missing.append(name)
            else:
                columns[name] = position
        currency_col = find_column(header, _CURRENCY_HEADER_HINTS)
        if missing:
            batch.parse_warnings.append(
                f"Could not identify column(s) {missing} in header {header}; nothing parsed."
            )
            return batch

        max_col = max(columns.values())
        for line_number, row in enumerate(reader, start=2):
            if len(row) <= max_col:
                batch.parse_warnings.append(f"line {line_number}: malformed row; skipped")
                continue
            try:
                batch.financial_statement_line_items.append(
                    FinancialStatementLineItem(
                        ticker=self.ticker,
                        period_end_date=row[columns["period_end_date"]].strip(),
                        period_type=row[columns["period_type"]].strip().upper(),
                        statement_type=row[columns["statement_type"]].strip().upper(),
                        line_item=row[columns["line_item"]].strip().lower().replace(" ", "_"),
                        value=float(row[columns["value"]].strip()),
                        currency=(
                            row[currency_col].strip()
                            if currency_col is not None and len(row) > currency_col
                            else "EGP"
                        ),
                    )
                )
            except (ValueError, IndexError) as exc:
                batch.parse_warnings.append(f"line {line_number}: unparseable ({exc}); skipped")
        return batch
