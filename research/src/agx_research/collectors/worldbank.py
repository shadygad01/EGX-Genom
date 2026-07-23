"""World Bank Open Data collector for Egypt macro indicators.

Endpoint: `https://api.worldbank.org/v2/country/{country}/indicator/{indicator}
?format=json&per_page=1000` -- the World Bank's documented, free, no-key v2
REST API. Same confidence tier as the already-implemented FRED/Stooq
endpoints: a canonical, decades-stable public API shape, not a guessed one.

Response shape (a 2-element JSON array; see World Bank API documentation):
`[ {page, pages, per_page, total, ...}, [ {indicator: {id, value}, country:
{id, value}, countryiso3code, date, value, unit, obs_status, decimal}, ... ]
]`. A `null` `value` is a missing observation for that year (common for
recent/incomplete years) and is dropped with a warning, never imputed.
"""

from __future__ import annotations

import json
from datetime import date

from agx_research.collectors.base import CollectionBatch, Collector
from agx_research.collectors.raw import RawDocument, build_raw_document
from agx_research.data.schemas import MacroObservation


class WorldBankCollector(Collector):
    name = "WorldBankCollector"
    version = "1.0.0"

    def __init__(self, spec, indicators: dict[str, str], *, country: str = "EGY", fetcher=None):
        """`indicators`: {World Bank indicator code: series_id to store it as}."""
        super().__init__(spec, fetcher)
        self.indicators = indicators
        self.country = country

    def fetch(self) -> list[RawDocument]:
        documents = []
        for indicator_code in sorted(self.indicators):
            url = (
                f"{self.spec.base_url}/country/{self.country}/indicator/{indicator_code}"
                "?format=json&per_page=1000"
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

        if (
            not isinstance(payload, list)
            or len(payload) != 2
            or not isinstance(payload[1], list)
        ):
            batch.parse_warnings.append(f"Unexpected response shape: {type(payload).__name__}")
            return batch

        series_id = self.indicators.get(
            self._indicator_code_from_url(document.original_url), None
        )
        if series_id is None:
            batch.parse_warnings.append(
                f"Could not resolve indicator code from URL {document.original_url}"
            )
            return batch

        for entry in payload[1]:
            if not isinstance(entry, dict):
                batch.parse_warnings.append(f"Malformed entry: {entry!r}")
                continue
            year = entry.get("date")
            value = entry.get("value")
            if value is None:
                batch.parse_warnings.append(f"{year}: missing observation; dropped")
                continue
            try:
                batch.macro_observations.append(
                    MacroObservation(
                        series_id=series_id,
                        # World Bank annual indicators carry only a year;
                        # normalized to Dec 31 of that year, documented here
                        # rather than silently assumed by a caller.
                        observation_date=date(int(year), 12, 31),
                        value=float(value),
                    )
                )
            except (TypeError, ValueError) as exc:
                batch.parse_warnings.append(f"{year}: unparseable ({exc}); skipped")

        return batch

    @staticmethod
    def _indicator_code_from_url(url: str) -> str:
        return url.split("/indicator/")[-1].split("?")[0]
