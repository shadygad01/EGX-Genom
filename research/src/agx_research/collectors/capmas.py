"""CAPMAS public indicator API collector.

The official CAPMAS web application calls the unauthenticated JSON API on
port 8080. Its published usage notice permits general/research use with
CAPMAS attribution and prohibits resale/direct commercial exploitation.
Only named aggregate filters are configured here; regional/category rows
are never combined into a single series by guesswork.
"""

from __future__ import annotations

import calendar
import json
from datetime import date
from urllib.parse import parse_qs, urlparse

from agx_research.collectors.base import CollectionBatch, Collector
from agx_research.collectors.raw import RawDocument, build_raw_document
from agx_research.data.schemas import MacroObservation


class CapmasIndicatorCollector(Collector):
    name = "CapmasIndicatorCollector"
    version = "1.0.0"

    def __init__(
        self,
        spec,
        indicators: dict[int, dict[str, str]],
        *,
        sub_subject_id: int = 13,
        fetcher=None,
    ):
        """Configure ``{indicator_id: {English filter name: local series_id}}``."""
        super().__init__(spec, fetcher)
        self.indicators = indicators
        self.sub_subject_id = sub_subject_id

    def fetch(self) -> list[RawDocument]:
        documents = []
        for indicator_id in sorted(self.indicators):
            url = (
                f"{self.spec.base_url}/Indicator/IndicatorFilter"
                f"?IndicatorId={indicator_id}&SubSubjectId={self.sub_subject_id}"
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
        if not isinstance(rows, list) or payload.get("state") is not True:
            batch.parse_warnings.append("Unexpected response shape or unsuccessful API state")
            return batch

        query = parse_qs(urlparse(document.original_url).query)
        try:
            indicator_id = int(query["IndicatorId"][0])
        except (KeyError, TypeError, ValueError):
            batch.parse_warnings.append("IndicatorId missing or invalid in document URL")
            return batch
        configured = self.indicators.get(indicator_id, {})

        for group in rows:
            if not isinstance(group, dict):
                continue
            english_name = next(
                (
                    item.get("name")
                    for item in group.get("filterTranslations", [])
                    if item.get("locale") == "en"
                ),
                None,
            )
            series_id = configured.get(english_name or "")
            if series_id is None:
                continue
            for observation in group.get("data", []):
                try:
                    year = int(observation["year"])
                    month = observation.get("month")
                    quarter = observation.get("quarter")
                    if month is not None:
                        month = int(month)
                    elif quarter is not None:
                        month = int(quarter) * 3
                    else:
                        month = 12
                    batch.macro_observations.append(
                        MacroObservation(
                            series_id=series_id,
                            observation_date=date(
                                year, month, calendar.monthrange(year, month)[1]
                            ),
                            value=float(observation["value"]),
                        )
                    )
                except (KeyError, TypeError, ValueError) as exc:
                    batch.parse_warnings.append(
                        f"{english_name}: unparseable observation ({exc}); skipped"
                    )
        return batch
