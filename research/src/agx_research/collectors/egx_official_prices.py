"""Official Egyptian Exchange daily price-table collector.

The collector reads the public EGX Today's Market Watch - Stocks - Trading Data
page and only materializes rows that contain a complete OHLCV record. It never
fills missing fields with the last price, so quote-only or malformed rows are
withheld rather than presented as historical bars.
"""

from __future__ import annotations

import re
from datetime import UTC, date, datetime
from html.parser import HTMLParser
from urllib.parse import urlencode

from agx_research.collectors.base import CollectionBatch, Collector
from agx_research.collectors.raw import RawDocument, build_raw_document
from agx_research.data.schemas import PriceBar

_NUMBER = re.compile(r"^-?(?:\d+(?:[.,]\d*)?|[.,]\d+)$")
_DATE = re.compile(r"(?:^|[^0-9])(\d{1,2})[/-](\d{1,2})[/-](\d{2,4})(?:$|[^0-9])")


class _TableParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.tables: list[list[list[str]]] = []
        self._table: list[list[str]] | None = None
        self._row: list[str] | None = None
        self._cell: list[str] | None = None

    def handle_starttag(self, tag, attrs):
        tag = tag.lower()
        if tag == "table" and self._table is None:
            self._table = []
        elif tag == "tr" and self._table is not None:
            self._row = []
        elif tag in {"th", "td"} and self._row is not None:
            self._cell = []

    def handle_endtag(self, tag):
        tag = tag.lower()
        if tag in {"th", "td"} and self._cell is not None and self._row is not None:
            self._row.append(" ".join("".join(self._cell).split()))
            self._cell = None
        elif tag == "tr" and self._row is not None and self._table is not None:
            if self._row:
                self._table.append(self._row)
            self._row = None
        elif tag == "table" and self._table is not None:
            if self._table:
                self.tables.append(self._table)
            self._table = None

    def handle_data(self, data):
        if self._cell is not None:
            self._cell.append(data)


def _norm_header(value: str) -> str:
    return re.sub(r"[^a-z0-9]", "", value.casefold())


def _number(value: str) -> float | None:
    cleaned = value.strip().replace(",", "").replace("%", "")
    if not _NUMBER.fullmatch(cleaned):
        return None
    try:
        return float(cleaned.replace(",", "."))
    except ValueError:
        return None


def _trade_date(value: str, now: datetime) -> date:
    match = _DATE.search(value)
    if not match:
        return now.date()
    day, month, year = (int(part) for part in match.groups())
    year += 2000 if year < 100 else 0
    return date(year, month, day)


class EgxOfficialPriceCollector(Collector):
    """Fetch complete daily OHLCV rows from the public EGX market-watch page."""

    name = "EgxOfficialPriceCollector"
    version = "1.0.0"
    URL = "https://www.egx.com.eg/en/prices.aspx"

    def __init__(self, spec, symbols: list[str], fetcher=None, *, now=None):
        super().__init__(spec, fetcher)
        self.symbols = {symbol.strip().upper() for symbol in symbols if symbol.strip()}
        self._now = now or (lambda: datetime.now(UTC))

    def fetch(self) -> list[RawDocument]:
        payload = self.fetcher.fetch_text(self.URL, self.spec)
        if not payload.strip():
            raise RuntimeError("EGX official prices page returned an empty response.")
        return [
            build_raw_document(
                source_id=self.spec.id,
                collector=self.name,
                collector_version=self.version,
                original_url=f"{self.URL}#{urlencode({'symbols': ','.join(sorted(self.symbols))})}",
                content_text=payload,
                schema_version=self.spec.schema_version,
                license=self.spec.license,
            )
        ]

    def parse(self, document: RawDocument) -> CollectionBatch:
        batch = CollectionBatch(source_id=document.source_id, raw_document_id=document.id)
        parser = _TableParser()
        parser.feed(document.content_text)
        now = self._now()
        wanted = self.symbols
        found: set[str] = set()
        for table in parser.tables:
            if not table:
                continue
            headers = {_norm_header(value): index for index, value in enumerate(table[0])}
            ticker_index = next(
                (headers[key] for key in ("code", "symbol", "ticker", "reuterscode") if key in headers),
                None,
            )
            close_index = next(
                (headers[key] for key in ("last", "lastprice", "price", "close", "closingprice") if key in headers),
                None,
            )
            open_index = next((headers[key] for key in ("open", "openingprice") if key in headers), None)
            high_index = next((headers[key] for key in ("high", "highprice") if key in headers), None)
            low_index = next((headers[key] for key in ("low", "lowprice") if key in headers), None)
            volume_index = next((headers[key] for key in ("volume", "volumeoftrading", "tradedvolume") if key in headers), None)
            if None in (ticker_index, close_index, open_index, high_index, low_index, volume_index):
                continue
            for row in table[1:]:
                if max(ticker_index, close_index, open_index, high_index, low_index, volume_index) >= len(row):
                    continue
                ticker = row[ticker_index].upper().replace(".CA", "")
                if ticker not in wanted or ticker in found:
                    continue
                values = [_number(row[index]) for index in (open_index, high_index, low_index, close_index)]
                volume = _number(row[volume_index])
                if any(value is None for value in values) or volume is None:
                    batch.parse_warnings.append(f"EGX row for {ticker} was incomplete and withheld.")
                    continue
                batch.price_bars.append(
                    PriceBar(
                        ticker=ticker,
                        trade_date=_trade_date(" ".join(row), now),
                        open=values[0],
                        high=values[1],
                        low=values[2],
                        close=values[3],
                        volume=int(volume),
                    )
                )
                found.add(ticker)
        missing = sorted(wanted - found)
        if missing:
            batch.parse_warnings.append(f"EGX official page had no complete rows for: {', '.join(missing)}")
        return batch
