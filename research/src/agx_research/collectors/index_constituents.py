"""IndexConstituentCollector: turns a downloadable constituent-list CSV into
`IndexConstituent` candidates -- the Universe Engine's collection half.

Column order isn't assumed; the ticker and company-name columns are found
by header-text matching (same "declared heuristic, calibrate once a real
page exists" posture as `discovery.discover_company_directory_links` and
`acquisition_intelligence.legality`'s keyword lists), since no real EGX
constituent-list export has been fetched yet to verify an exact header —
inventing one would be guessing a wire format, not parsing a real one.

One collector instance serves one index (EGX30, EGX70, ...); `spec` names
the concrete endpoint once one is verified (`sources.catalog`'s
`egx_official` stays `PLANNED` until then -- see `AD-24`).
"""

from __future__ import annotations

import csv
import io

from agx_research.collectors.base import CollectionBatch, Collector
from agx_research.collectors.raw import RawDocument, build_raw_document
from agx_research.universe.constituent import IndexConstituent

_TICKER_HEADER_HINTS = ("ticker", "symbol", "code")
_NAME_HEADER_HINTS = ("name", "company")


def _find_column(header: list[str], hints: tuple[str, ...]) -> int | None:
    for position, column in enumerate(header):
        normalized = column.strip().lower()
        if any(hint in normalized for hint in hints):
            return position
    return None


class IndexConstituentCollector(Collector):
    name = "IndexConstituentCollector"
    version = "1.0.0"

    def __init__(self, spec, index: str, fetcher=None):
        super().__init__(spec, fetcher)
        self.index = index

    def fetch(self) -> list[RawDocument]:
        text = self.fetcher.fetch_text(self.spec.base_url, self.spec)
        return [
            build_raw_document(
                source_id=self.spec.id,
                collector=self.name,
                collector_version=self.version,
                original_url=self.spec.base_url,
                content_text=text,
                schema_version=self.spec.schema_version,
                license=self.spec.license,
            )
        ]

    def parse(self, document: RawDocument) -> CollectionBatch:
        batch = CollectionBatch(source_id=document.source_id, raw_document_id=document.id)
        reader = csv.reader(io.StringIO(document.content_text))
        header = next(reader, None)
        if not header:
            batch.parse_warnings.append("Empty document; nothing parsed.")
            return batch

        ticker_col = _find_column(header, _TICKER_HEADER_HINTS)
        name_col = _find_column(header, _NAME_HEADER_HINTS)
        if ticker_col is None or name_col is None:
            batch.parse_warnings.append(
                f"Could not identify ticker/name columns in header {header}; nothing parsed."
            )
            return batch

        as_of = document.fetched_at.date()
        for line_number, row in enumerate(reader, start=2):
            if len(row) <= max(ticker_col, name_col):
                batch.parse_warnings.append(f"line {line_number}: malformed row; skipped")
                continue
            ticker = row[ticker_col].strip()
            company_name = row[name_col].strip()
            if not ticker or not company_name:
                batch.parse_warnings.append(f"line {line_number}: missing ticker/name; skipped")
                continue
            batch.index_constituents.append(
                IndexConstituent(
                    index=self.index, ticker=ticker, company_name=company_name, as_of_date=as_of,
                )
            )
        return batch
