"""Stooq daily-OHLCV collector.

Endpoint: `https://stooq.com/q/d/l/?s={symbol}&i=d` returns CSV with the
header `Date,Open,High,Low,Close,Volume`. EGX symbols use the `.eg`
suffix (e.g. `comi.eg`); global benchmarks use Stooq's own codes (`^spx`,
`xauusd`, `cb.f` etc.), configured per run, not hardcoded.

Parsing is tolerant: unparseable rows are recorded as warnings, never
silently dropped without trace and never guessed at. Volume may be absent
for indices/FX — recorded as 0 with a warning noting it.
"""

from __future__ import annotations

import csv
import io
from datetime import date

from agx_research.collectors.base import CollectionBatch, Collector
from agx_research.collectors.raw import RawDocument, build_raw_document
from agx_research.data.schemas import PriceBar


class StooqPriceCollector(Collector):
    name = "StooqPriceCollector"
    version = "1.0.0"

    def __init__(self, spec, symbols: dict[str, str], fetcher=None):
        """`symbols` maps AGX ticker -> stooq symbol (e.g. {"COMI": "comi.eg"})."""
        super().__init__(spec, fetcher)
        self.symbols = symbols

    def _url(self, stooq_symbol: str) -> str:
        return f"{self.spec.base_url}?s={stooq_symbol}&i=d"

    def fetch(self) -> list[RawDocument]:
        documents = []
        for ticker, stooq_symbol in sorted(self.symbols.items()):
            url = self._url(stooq_symbol)
            text = self.fetcher.fetch_text(url, self.spec)
            document = build_raw_document(
                source_id=self.spec.id,
                collector=self.name,
                collector_version=self.version,
                original_url=url,
                content_text=text,
                schema_version=self.spec.schema_version,
                license=self.spec.license,
            )
            # The AGX ticker is part of the parse contract; carry it in the URL
            # mapping rather than mutating the document.
            document = document.model_copy(update={"original_url": f"{url}#ticker={ticker}"})
            documents.append(document)
        return documents

    @staticmethod
    def _ticker_from_url(url: str) -> str | None:
        if "#ticker=" in url:
            return url.rsplit("#ticker=", 1)[1] or None
        return None

    def parse(self, document: RawDocument) -> CollectionBatch:
        ticker = self._ticker_from_url(document.original_url)
        batch = CollectionBatch(source_id=document.source_id, raw_document_id=document.id)
        if ticker is None:
            batch.parse_warnings.append("No ticker mapping in document URL; nothing parsed.")
            return batch

        reader = csv.DictReader(io.StringIO(document.content_text))
        expected = {"Date", "Open", "High", "Low", "Close"}
        if reader.fieldnames is None or not expected.issubset(set(reader.fieldnames)):
            batch.parse_warnings.append(
                f"Unexpected header {reader.fieldnames}; expected at least {sorted(expected)}."
            )
            return batch

        for line_number, row in enumerate(reader, start=2):
            try:
                volume_raw = (row.get("Volume") or "").strip()
                if not volume_raw:
                    batch.parse_warnings.append(
                        f"line {line_number}: missing volume (index/FX series?), recorded as 0"
                    )
                batch.price_bars.append(
                    PriceBar(
                        ticker=ticker,
                        trade_date=date.fromisoformat(row["Date"].strip()),
                        open=float(row["Open"]),
                        high=float(row["High"]),
                        low=float(row["Low"]),
                        close=float(row["Close"]),
                        volume=int(float(volume_raw)) if volume_raw else 0,
                    )
                )
            except (ValueError, KeyError) as exc:
                batch.parse_warnings.append(f"line {line_number}: unparseable ({exc}); skipped")
        return batch
