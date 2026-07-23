"""Financial Modeling Prep (FMP) collector -- code-complete, catalogued
`NEEDS_KEY`.

Endpoint: `https://financialmodelingprep.com/api/v3/historical-price-full/
{SYMBOL}?apikey={KEY}`, FMP's documented free-tier JSON shape:

    {"symbol": "AAPL", "historical": [{"date": "YYYY-MM-DD", "open": ..,
    "high": .., "low": .., "close": .., "volume": .., ...}, ...]}

Same NEEDS_KEY posture as `AlphaVantageCollector`: the key is a user-supplied
credential passed in explicitly, and the seed catalog entry stays NEEDS_KEY
until the user supplies one and an operator flips the status -- this class
existing does not make the source collectable.
"""

from __future__ import annotations

import json
from datetime import date

from agx_research.collectors.base import CollectionBatch, Collector
from agx_research.collectors.raw import RawDocument, build_raw_document
from agx_research.data.schemas import PriceBar


class FmpCollector(Collector):
    name = "FmpCollector"
    version = "1.0.0"

    def __init__(self, spec, symbols: list[str], *, api_key: str, fetcher=None):
        super().__init__(spec, fetcher)
        self.symbols = symbols
        self.api_key = api_key

    def fetch(self) -> list[RawDocument]:
        documents = []
        for symbol in sorted(self.symbols):
            url = f"{self.spec.base_url}/historical-price-full/{symbol}?apikey={self.api_key}"
            text = self.fetcher.fetch_text(url, self.spec)
            documents.append(
                build_raw_document(
                    source_id=self.spec.id,
                    collector=self.name,
                    collector_version=self.version,
                    original_url=url.split("?apikey=")[0],
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
            batch.parse_warnings.append(f"FMP error: {payload['Error Message']}")
            return batch

        symbol = payload.get("symbol")
        history = payload.get("historical")
        if symbol is None or history is None:
            batch.parse_warnings.append(f"Unexpected response shape: keys={list(payload)}")
            return batch

        for entry in history:
            try:
                batch.price_bars.append(
                    PriceBar(
                        ticker=symbol,
                        trade_date=date.fromisoformat(entry["date"]),
                        open=float(entry["open"]),
                        high=float(entry["high"]),
                        low=float(entry["low"]),
                        close=float(entry["close"]),
                        volume=int(entry["volume"]),
                    )
                )
            except (KeyError, TypeError, ValueError) as exc:
                batch.parse_warnings.append(f"{entry.get('date', '?')}: unparseable ({exc}); skipped")

        return batch
