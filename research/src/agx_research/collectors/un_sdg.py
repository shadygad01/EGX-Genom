"""United Nations SDG API collector for Egypt macro observations.

The UN Statistics Division exposes a free, no-key JSON API at
``unstats.un.org/SDGAPI``.  One request is made per SDG indicator and only
explicitly configured series codes are materialized; disaggregated rows are
not silently mixed into an aggregate macro time series.
"""

from __future__ import annotations

import json
from datetime import date
from urllib.parse import parse_qs, urlparse

from agx_research.collectors.base import CollectionBatch, Collector
from agx_research.collectors.raw import RawDocument, build_raw_document
from agx_research.data.schemas import MacroObservation


class UnSdgCollector(Collector):
    name = "UnSdgCollector"
    version = "1.0.0"

    def __init__(
        self,
        spec,
        series: dict[str, dict[str, str]],
        *,
        area_code: str = "818",
        fetcher=None,
    ):
        """Configure ``{indicator: {UN series code: local series_id}}``."""
        super().__init__(spec, fetcher)
        self.series = series
        self.area_code = area_code

    def fetch(self) -> list[RawDocument]:
        documents = []
        for indicator in sorted(self.series):
            url = (
                f"{self.spec.base_url}/Indicator/Data?indicator={indicator}"
                f"&areaCode={self.area_code}&pageSize=1000"
            )
            text = self.fetcher.fetch_text(url, self.spec)
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
        return documents

    def parse(self, document: RawDocument) -> CollectionBatch:
        batch = CollectionBatch(source_id=document.source_id, raw_document_id=document.id)
        try:
            payload = json.loads(document.content_text)
        except json.JSONDecodeError as exc:
            batch.parse_warnings.append(f"Invalid JSON: {exc}")
            return batch

        rows = payload.get("data") if isinstance(payload, dict) else None
        if not isinstance(rows, list):
            batch.parse_warnings.append("Unexpected response shape: missing data array")
            return batch

        indicator = parse_qs(urlparse(document.original_url).query).get("indicator", [None])[0]
        configured = self.series.get(indicator or "", {})
        if not configured:
            batch.parse_warnings.append(f"Unconfigured indicator in URL: {indicator!r}")
            return batch

        for row in rows:
            if not isinstance(row, dict):
                batch.parse_warnings.append(f"Malformed row: {row!r}")
                continue
            un_series = row.get("series")
            if un_series not in configured:
                continue
            year = row.get("timePeriodStart")
            value = row.get("value")
            try:
                batch.macro_observations.append(
                    MacroObservation(
                        series_id=configured[un_series],
                        observation_date=date(int(float(year)), 12, 31),
                        value=float(value),
                    )
                )
            except (TypeError, ValueError) as exc:
                batch.parse_warnings.append(
                    f"{un_series} {year}: unparseable observation ({exc}); skipped"
                )
        return batch
