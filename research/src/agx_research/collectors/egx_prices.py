"""Multi-provider EGX daily-price collector.

The collector is intentionally one capability adapter: Yahoo supplies deep
history, StockAnalysis supplies the recent daily overlap, and Mubasher is a
post-close snapshot fallback for a symbol that neither historical leg updates.
Symbols are injected by the production ``UniverseProvider``; this module owns
no index constituent list.
"""

from __future__ import annotations

import html
import json
import re
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, date, datetime, time
from urllib.parse import parse_qs, urlencode, urlsplit
from zoneinfo import ZoneInfo

from agx_research.collectors.base import CollectionBatch, Collector
from agx_research.collectors.raw import RawDocument, build_raw_document
from agx_research.data.schemas import CorporateEvent, PriceBar

_CAIRO = ZoneInfo("Africa/Cairo")
_MARKET_CLOSE = time(14, 30)
_NUMBER = r"-?(?:\d+(?:\.\d*)?|\.\d+)"
_SA_ROW = re.compile(
    rf"\{{a:(?P<adjusted>{_NUMBER}),c:(?P<close>{_NUMBER}),"
    rf"h:(?P<high>{_NUMBER}),l:(?P<low>{_NUMBER}),o:(?P<open>{_NUMBER}),"
    rf't:"(?P<date>\d{{4}}-\d{{2}}-\d{{2}})",v:(?P<volume>{_NUMBER})'
)


class EgxCompositePriceCollector(Collector):
    """Fetch and merge three public EGX price surfaces per Universe symbol."""

    name = "EgxCompositePriceCollector"
    version = "1.0.0"

    def __init__(self, spec, symbols: list[str], fetcher=None, *, now=None):
        super().__init__(spec, fetcher)
        self.symbols = sorted({symbol.strip().upper() for symbol in symbols if symbol.strip()})
        self._now = now or (lambda: datetime.now(_CAIRO))
        self.fetch_failures: dict[str, list[str]] = {}

    @staticmethod
    def yahoo_url(ticker: str) -> str:
        query = urlencode({"range": "max", "interval": "1d", "events": "div,splits"})
        return f"https://query1.finance.yahoo.com/v8/finance/chart/{ticker}.CA?{query}"

    @staticmethod
    def stockanalysis_urls(ticker: str) -> tuple[str, str]:
        base = "https://stockanalysis.com/quote/egx"
        return (f"{base}/{ticker}/history/", f"{base}/{ticker}.CA/history/")

    @staticmethod
    def mubasher_url(ticker: str) -> str:
        return f"https://english.mubasher.info/markets/EGX/stocks/{ticker}/"

    def _document(
        self, provider: str, ticker: str, url: str, payload: str, **metadata
    ) -> RawDocument:
        fragment = urlencode({"provider": provider, "ticker": ticker, **metadata})
        return build_raw_document(
            source_id=self.spec.id,
            collector=self.name,
            collector_version=self.version,
            original_url=f"{url}#{fragment}",
            content_text=payload,
            schema_version=self.spec.schema_version,
            license=self.spec.license,
        )

    def _try_fetch(self, ticker: str, provider: str, urls: tuple[str, ...]):
        errors: list[str] = []
        for url in urls:
            try:
                return url, self.fetcher.fetch_text(url, self.spec)
            except Exception as exc:  # noqa: BLE001 - injected fetchers share no exception base
                errors.append(f"{type(exc).__name__}: {exc}")
        self.fetch_failures.setdefault(ticker, []).append(f"{provider}: {' | '.join(errors)}")
        return None

    @staticmethod
    def _latest_yahoo_date(payload: str) -> date | None:
        try:
            result = json.loads(payload)["chart"]["result"][0]
            timestamps = result.get("timestamp") or []
            quote = result["indicators"]["quote"][0]
            fields = ("open", "high", "low", "close", "volume")
            arrays = {field: quote.get(field) or [] for field in fields}
            complete_timestamps = [
                timestamp
                for index, timestamp in enumerate(timestamps)
                if all(
                    index < len(arrays[field]) and arrays[field][index] is not None
                    for field in fields
                )
            ]
            return (
                datetime.fromtimestamp(max(complete_timestamps), UTC).date()
                if complete_timestamps
                else None
            )
        except (KeyError, IndexError, TypeError, ValueError, json.JSONDecodeError):
            return None

    def _fetch_symbol(self, ticker: str, now: datetime) -> list[RawDocument]:
        documents: list[RawDocument] = []
        yahoo_latest = None
        yahoo = self._try_fetch(ticker, "yahoo", (self.yahoo_url(ticker),))
        if yahoo:
            url, payload = yahoo
            yahoo_latest = self._latest_yahoo_date(payload)
            documents.append(self._document("yahoo", ticker, url, payload))

        stock = self._try_fetch(ticker, "stockanalysis", self.stockanalysis_urls(ticker))
        if stock:
            url, payload = stock
            documents.append(self._document("stockanalysis", ticker, url, payload))

        # Mubasher exposes an intraday snapshot, not a dated historical API.
        # Only infer today's trading date after the Sun-Thu session closes,
        # and only when Yahoo is missing/stale and StockAnalysis is absent.
        stale_yahoo = yahoo_latest is None or (now.date() - yahoo_latest).days > 3
        market_closed = now.weekday() in {6, 0, 1, 2, 3} and now.time() >= _MARKET_CLOSE
        if stock is None and stale_yahoo and market_closed:
            mubasher = self._try_fetch(ticker, "mubasher", (self.mubasher_url(ticker),))
            if mubasher:
                url, payload = mubasher
                documents.append(
                    self._document(
                        "mubasher",
                        ticker,
                        url,
                        payload,
                        trade_date=now.date().isoformat(),
                        market_complete="true",
                    )
                )
        return documents

    def fetch(self) -> list[RawDocument]:
        now = self._now()
        if now.tzinfo is None:
            now = now.replace(tzinfo=_CAIRO)
        now = now.astimezone(_CAIRO)

        # Network latency dominates a 101-symbol run. Fetch a small bounded
        # number of symbols concurrently, then consume futures in Universe
        # order so each ticker's provider overwrite order and the archive are
        # deterministic.
        with ThreadPoolExecutor(max_workers=min(6, max(1, len(self.symbols)))) as executor:
            futures = [executor.submit(self._fetch_symbol, ticker, now) for ticker in self.symbols]
            documents = [document for future in futures for document in future.result()]
        if not documents:
            raise RuntimeError(
                "Every Yahoo, StockAnalysis and eligible Mubasher request failed; "
                "no EGX price document was collected."
            )
        return documents

    @staticmethod
    def _metadata(url: str) -> dict[str, str]:
        values = parse_qs(urlsplit(url).fragment)
        return {key: items[-1] for key, items in values.items() if items}

    @classmethod
    def provider_for_document(cls, document: RawDocument) -> str | None:
        """Return the registry id of the provider leg that produced a raw document."""
        provider = cls._metadata(document.original_url).get("provider")
        return {
            "yahoo": "yahoo_finance",
            "stockanalysis": "stockanalysis",
            "mubasher": "mubasher",
        }.get(provider)

    @staticmethod
    def _parse_yahoo(document: RawDocument, ticker: str, batch: CollectionBatch) -> None:
        try:
            result = json.loads(document.content_text)["chart"]["result"][0]
            timestamps = result.get("timestamp") or []
            quote = result["indicators"]["quote"][0]
        except (KeyError, IndexError, TypeError, json.JSONDecodeError) as exc:
            batch.parse_warnings.append(f"Yahoo payload has no chart result: {exc}")
            return

        fields = ("open", "high", "low", "close", "volume")
        arrays = {field: quote.get(field) or [] for field in fields}
        for index, timestamp in enumerate(timestamps):
            try:
                values = {field: arrays[field][index] for field in fields}
                if any(value is None for value in values.values()):
                    continue
                batch.price_bars.append(
                    PriceBar(
                        ticker=ticker,
                        trade_date=datetime.fromtimestamp(timestamp, UTC).date(),
                        open=float(values["open"]),
                        high=float(values["high"]),
                        low=float(values["low"]),
                        close=float(values["close"]),
                        volume=int(values["volume"]),
                    )
                )
            except (IndexError, TypeError, ValueError):
                continue

        events = result.get("events") or {}
        for kind, event_type in (("dividends", "dividend"), ("splits", "stock_split")):
            for event in events.get(kind, {}).values():
                try:
                    event_date = datetime.fromtimestamp(event["date"], UTC).date()
                except (KeyError, TypeError, ValueError, OSError):
                    continue
                details = {
                    key: event[key]
                    for key in ("amount", "numerator", "denominator", "splitRatio")
                    if key in event
                }
                batch.corporate_events.append(
                    CorporateEvent(
                        ticker=ticker,
                        event_date=event_date,
                        event_type=event_type,
                        description=f"Yahoo Finance reported {event_type.replace('_', ' ')}",
                        details=details,
                    )
                )

    @staticmethod
    def _parse_stockanalysis(document: RawDocument, ticker: str, batch: CollectionBatch) -> None:
        for match in _SA_ROW.finditer(document.content_text):
            try:
                batch.price_bars.append(
                    PriceBar(
                        ticker=ticker,
                        trade_date=date.fromisoformat(match["date"]),
                        open=float(match["open"]),
                        high=float(match["high"]),
                        low=float(match["low"]),
                        close=float(match["close"]),
                        volume=int(float(match["volume"])),
                    )
                )
            except ValueError:
                continue
        if not batch.price_bars:
            batch.parse_warnings.append("StockAnalysis embedded history rows were not found.")

    @staticmethod
    def _mubasher_value(text: str, label: str) -> str | None:
        patterns = (
            rf">\s*{re.escape(label)}\s*<.*?market-summary__block-number[^>]*>\s*([^<]+)",
            rf"{re.escape(label)}\s*</[^>]+>\s*<[^>]*>\s*([^<]+)",
        )
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE | re.DOTALL)
            if match:
                return html.unescape(match.group(1)).strip().replace(",", "")
        return None

    @classmethod
    def _parse_mubasher(
        cls, document: RawDocument, ticker: str, metadata: dict[str, str], batch: CollectionBatch
    ) -> None:
        close_match = re.search(
            r"market-summary__last-price[^>]*>\s*([\d,.]+)",
            document.content_text,
            re.IGNORECASE,
        )
        values = {
            key: cls._mubasher_value(document.content_text, label)
            for key, label in (
                ("open", "Open"),
                ("high", "High"),
                ("low", "Low"),
                ("volume", "Volume"),
            )
        }
        if not close_match or any(value is None for value in values.values()):
            batch.parse_warnings.append("Mubasher market summary fields were incomplete.")
            return
        try:
            batch.price_bars.append(
                PriceBar(
                    ticker=ticker,
                    trade_date=date.fromisoformat(metadata["trade_date"]),
                    open=float(values["open"]),
                    high=float(values["high"]),
                    low=float(values["low"]),
                    close=float(close_match.group(1).replace(",", "")),
                    volume=int(float(values["volume"])),
                )
            )
        except (KeyError, ValueError) as exc:
            batch.parse_warnings.append(f"Mubasher snapshot was invalid: {exc}")

    def parse(self, document: RawDocument) -> CollectionBatch:
        metadata = self._metadata(document.original_url)
        batch = CollectionBatch(source_id=document.source_id, raw_document_id=document.id)
        ticker = metadata.get("ticker")
        provider = metadata.get("provider")
        if not ticker or not provider:
            batch.parse_warnings.append("Provider/ticker provenance metadata is missing.")
            return batch
        if provider == "yahoo":
            self._parse_yahoo(document, ticker, batch)
        elif provider == "stockanalysis":
            self._parse_stockanalysis(document, ticker, batch)
        elif provider == "mubasher":
            self._parse_mubasher(document, ticker, metadata, batch)
        else:
            batch.parse_warnings.append(f"Unknown provider {provider!r}.")
        return batch
