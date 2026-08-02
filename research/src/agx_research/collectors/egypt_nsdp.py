"""Egypt's official National Summary Data Page (NSDP) macro collector."""

from __future__ import annotations

import calendar
import re
from datetime import date
from html.parser import HTMLParser

from agx_research.collectors.base import CollectionBatch, Collector
from agx_research.collectors.raw import RawDocument, build_raw_document
from agx_research.data.schemas import MacroObservation


class _TableRows(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.rows: list[list[str]] = []
        self._row: list[str] | None = None
        self._cell: list[str] | None = None

    def handle_starttag(self, tag: str, attrs) -> None:
        if tag == "tr":
            self._row = []
        elif tag in {"td", "th"} and self._row is not None:
            self._cell = []

    def handle_data(self, data: str) -> None:
        if self._cell is not None:
            self._cell.append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag in {"td", "th"} and self._cell is not None and self._row is not None:
            self._row.append(" ".join("".join(self._cell).split()))
            self._cell = None
        elif tag == "tr" and self._row is not None:
            if self._row:
                self.rows.append(self._row)
            self._row = None


def _period_end(value: str) -> date:
    match = re.fullmatch(r"Q([1-4])/(\d{2,4})", value, re.IGNORECASE)
    if match:
        quarter, year = int(match.group(1)), int(match.group(2))
        year = year + 2000 if year < 100 else year
        month = quarter * 3
        return date(year, month, calendar.monthrange(year, month)[1])
    match = re.fullmatch(r"([A-Za-z]{3})/(\d{2,4})", value)
    if match:
        month = {name: number for number, name in enumerate(calendar.month_abbr) if name}[
            match.group(1).title()
        ]
        year = int(match.group(2))
        year = year + 2000 if year < 100 else year
        return date(year, month, calendar.monthrange(year, month)[1])
    raise ValueError(f"unsupported NSDP period {value!r}")


class EgyptNsdpCollector(Collector):
    """Collect current CBE-produced aggregates republished by Egypt's MPED."""

    name = "EgyptNsdpCollector"
    version = "1.0.0"

    # Exact row labels and units keep similarly named government debt/reserve
    # measures from being silently mixed into these series.
    SERIES = {
        "- Net International Reserves (US$)": (
            "egypt_net_international_reserves_usd",
            "US Mill. $",
        ),
        "5. External debt": ("egypt_external_debt_usd", "US Mill. $"),
    }

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
        parser = _TableRows()
        parser.feed(document.content_text)
        found: set[str] = set()
        for cells in parser.rows:
            if not cells or cells[0] not in self.SERIES:
                continue
            label = cells[0]
            series_id, expected_unit = self.SERIES[label]
            found.add(label)
            try:
                if len(cells) < 4 or cells[1] != expected_unit:
                    raise ValueError(f"unexpected unit/row shape: {cells[:4]!r}")
                value = float(cells[3].replace(",", "")) * 1_000_000
                batch.macro_observations.append(
                    MacroObservation(
                        series_id=series_id,
                        observation_date=_period_end(cells[2]),
                        value=value,
                    )
                )
            except (TypeError, ValueError) as exc:
                batch.parse_warnings.append(f"{label}: unparseable ({exc}); skipped")
        for missing in self.SERIES.keys() - found:
            batch.parse_warnings.append(f"Expected NSDP row missing: {missing}")
        return batch
