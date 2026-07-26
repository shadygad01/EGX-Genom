"""FRED CSV collector for global macro series.

Endpoint: `https://fred.stlouisfed.org/graph/fredgraph.csv?id={SERIES}`
returns `observation_date,{SERIES}` CSV (historically `DATE,{SERIES}`) where `.` marks a missing observation
(dropped with a warning, never imputed).
"""

from __future__ import annotations

import csv
import io
from datetime import date

from agx_research.collectors.base import CollectionBatch, Collector
from agx_research.collectors.raw import RawDocument, build_raw_document
from agx_research.data.schemas import MacroObservation


class FredCsvCollector(Collector):
    name = "FredCsvCollector"
    version = "1.0.0"

    def __init__(self, spec, series_ids: list[str], fetcher=None):
        super().__init__(spec, fetcher)
        self.series_ids = series_ids
        self.fetch_warnings: list[str] = []

    def fetch(self) -> list[RawDocument]:
        documents = []
        self.fetch_warnings = []
        for series_id in sorted(self.series_ids):
            url = f"{self.spec.base_url}?id={series_id}"
            try:
                text = self.fetcher.fetch_text(url, self.spec)
            except Exception as exc:  # noqa: BLE001 - fetchers share no exception base
                self.fetch_warnings.append(f"{series_id}: {type(exc).__name__}: {exc}")
                continue
            documents.append(
                build_raw_document(
                    source_id=self.spec.id,
                    collector=self.name,
                    collector_version=self.version,
                    original_url=url,
                    content_text=text,
                    schema_version=self.spec.schema_version,
                    license=self.spec.license,
                )
            )
        if not documents:
            raise RuntimeError(
                "Every configured FRED series failed: " + "; ".join(self.fetch_warnings)
            )
        return documents

    def parse(self, document: RawDocument) -> CollectionBatch:
        batch = CollectionBatch(source_id=document.source_id, raw_document_id=document.id)
        reader = csv.reader(io.StringIO(document.content_text))
        header = next(reader, None)
        date_header = header[0].strip().lower() if header else ""
        if not header or len(header) != 2 or date_header not in {"date", "observation_date"}:
            batch.parse_warnings.append(
                f"Unexpected header {header}; expected [DATE|observation_date, <SERIES>]."
            )
            return batch
        series_id = header[1].strip()

        for line_number, row in enumerate(reader, start=2):
            if len(row) != 2:
                batch.parse_warnings.append(f"line {line_number}: malformed row; skipped")
                continue
            raw_value = row[1].strip()
            if raw_value == ".":
                batch.parse_warnings.append(f"line {line_number}: missing observation; dropped")
                continue
            try:
                batch.macro_observations.append(
                    MacroObservation(
                        series_id=series_id,
                        observation_date=date.fromisoformat(row[0].strip()),
                        value=float(raw_value),
                    )
                )
            except ValueError as exc:
                batch.parse_warnings.append(f"line {line_number}: unparseable ({exc}); skipped")
        return batch
