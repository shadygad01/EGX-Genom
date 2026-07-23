"""AlphaVantage collector -- code-complete, catalogued `NEEDS_KEY`.

Endpoint: `https://www.alphavantage.co/query?function=TIME_SERIES_DAILY
&symbol={SYMBOL}&apikey={KEY}&outputsize=full`, AlphaVantage's documented
free-tier JSON shape:

    {"Meta Data": {...}, "Time Series (Daily)": {"YYYY-MM-DD": {"1. open":
    "..", "2. high": "..", "3. low": "..", "4. close": "..", "5. volume":
    ".."}, ...}}

The API key is a user-supplied credential (`api_key` constructor argument,
sourced from wherever the user stores it -- never hardcoded, never defaulted
to a placeholder that looks real). Per `docs/DATA_ACQUISITION.md`'s NEEDS_KEY
policy, the seed catalog entry stays `SourceStatus.NEEDS_KEY` regardless of
this class existing -- `Collector.__init__` refuses to construct against any
spec that isn't `IMPLEMENTED`, so this collector cannot run until the user
supplies a key and an operator explicitly flips the catalog status (a
one-line config change, not a code change -- exactly the "small adapter"
the platform promises).
"""

from __future__ import annotations

import json
from datetime import date

from agx_research.collectors.base import CollectionBatch, Collector
from agx_research.collectors.raw import RawDocument, build_raw_document
from agx_research.data.schemas import PriceBar


class AlphaVantageCollector(Collector):
    name = "AlphaVantageCollector"
    version = "1.0.0"

    def __init__(self, spec, symbols: list[str], *, api_key: str, fetcher=None):
        super().__init__(spec, fetcher)
        self.symbols = symbols
        self.api_key = api_key

    def fetch(self) -> list[RawDocument]:
        documents = []
        for symbol in sorted(self.symbols):
            url = (
                f"{self.spec.base_url}?function=TIME_SERIES_DAILY&symbol={symbol}"
                f"&apikey={self.api_key}&outputsize=full"
            )
            text = self.fetcher.fetch_text(url, self.spec)
            documents.append(
                build_raw_document(
                    source_id=self.spec.id,
                    collector=self.name,
                    collector_version=self.version,
                    # the key never enters stored provenance
                    original_url=url.split("&apikey=")[0],
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

        if "Error Message" in payload:
            batch.parse_warnings.append(f"AlphaVantage error: {payload['Error Message']}")
            return batch
        if "Note" in payload:  # rate-limit notice, documented API behavior
            batch.parse_warnings.append(f"AlphaVantage rate-limit notice: {payload['Note']}")
            return batch

        meta = payload.get("Meta Data", {})
        symbol = meta.get("2. Symbol")
        series = payload.get("Time Series (Daily)")
        if symbol is None or series is None:
            batch.parse_warnings.append(f"Unexpected response shape: keys={list(payload)}")
            return batch

        for day, values in series.items():
            try:
                batch.price_bars.append(
                    PriceBar(
                        ticker=symbol,
                        trade_date=date.fromisoformat(day),
                        open=float(values["1. open"]),
                        high=float(values["2. high"]),
                        low=float(values["3. low"]),
                        close=float(values["4. close"]),
                        volume=int(float(values["5. volume"])),
                    )
                )
            except (KeyError, TypeError, ValueError) as exc:
                batch.parse_warnings.append(f"{day}: unparseable ({exc}); skipped")

        return batch
