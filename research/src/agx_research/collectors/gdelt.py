"""Free GDELT DOC 2.0 news-metadata collector."""

from __future__ import annotations

import json
from datetime import date, datetime, timedelta
from urllib.parse import urlencode

from agx_research.collectors.base import CollectionBatch, Collector
from agx_research.collectors.raw import RawDocument, build_raw_document
from agx_research.data.schemas import NewsItem
from agx_research.universe.entity_resolution import resolve_ticker_mentions


class GdeltDocCollector(Collector):
    name = "GdeltDocCollector"
    version = "1.1.0"

    def __init__(
        self,
        spec,
        *,
        query: str,
        ticker_hints: dict[str, str] | list[str] | None = None,
        max_records: int = 250,
        timespan: str = "7d",
        start_date: date | None = None,
        end_date: date | None = None,
        window_days: int = 7,
        fetcher=None,
    ):
        super().__init__(spec, fetcher)
        self.query = query
        # See `RssNewsCollector` for the same {ticker: company_name} vs.
        # plain list[str] posture -- both get the upgraded exact-token
        # ticker match via `resolve_ticker_mentions`.
        self.companies: dict[str, str] = (
            dict(ticker_hints) if isinstance(ticker_hints, dict) else {t: "" for t in (ticker_hints or [])}
        )
        self.max_records = min(max(max_records, 1), 250)
        self.timespan = timespan
        self.fetch_warnings: list[str] = []
        # Historical backfill mode: when both dates are given, `fetch()`
        # issues one request per `window_days`-sized slice of
        # [start_date, end_date] using GDELT's absolute `startdatetime`/
        # `enddatetime` parameters instead of the relative `timespan` the
        # daily live run uses -- the only way to reach news older than
        # `timespan` covers. Windowed rather than one wide query because
        # the DOC 2.0 API caps every response at 250 articles regardless
        # of range; a multi-month request would silently drop everything
        # past the cap for a busy query instead of raising.
        self.start_date = start_date
        self.end_date = end_date
        self.window_days = max(window_days, 1)

    def _windows(self) -> list[tuple[datetime, datetime]]:
        assert self.start_date is not None and self.end_date is not None
        windows: list[tuple[datetime, datetime]] = []
        cursor = datetime.combine(self.start_date, datetime.min.time())
        end = datetime.combine(self.end_date, datetime.min.time()) + timedelta(days=1)
        step = timedelta(days=self.window_days)
        while cursor < end:
            window_end = min(cursor + step, end)
            windows.append((cursor, window_end))
            cursor = window_end
        return windows

    def _url_for(self, params: dict) -> str:
        return f"{self.spec.base_url}?{urlencode(params)}"

    def fetch(self) -> list[RawDocument]:
        if self.start_date is None or self.end_date is None:
            url = self._url_for(
                {
                    "query": self.query,
                    "mode": "artlist",
                    "maxrecords": self.max_records,
                    "timespan": self.timespan,
                    "sort": "datedesc",
                    "format": "json",
                }
            )
            text = self.fetcher.fetch_text(url, self.spec)
            return [
                build_raw_document(
                    source_id=self.spec.id,
                    collector=self.name,
                    collector_version=self.version,
                    original_url=url,
                    content_text=text,
                    schema_version=self.spec.schema_version,
                    license=self.spec.license,
                )
            ]

        # Historical backfill mode issues one request per window and can run
        # to over a hundred windows for a multi-year range -- a live run
        # evidenced GDELT returning HTTP 429 on some individual windows
        # partway through an otherwise-succeeding batch (real server-side
        # throttling, not a client-pacing bug; see TD-41). Same posture as
        # `FredCsvCollector`: a failed window is skipped and recorded in
        # `self.fetch_warnings`, not allowed to discard every window
        # already fetched -- only raising if every single window failed.
        documents = []
        self.fetch_warnings = []
        for window_start, window_end in self._windows():
            url = self._url_for(
                {
                    "query": self.query,
                    "mode": "artlist",
                    "maxrecords": self.max_records,
                    "startdatetime": window_start.strftime("%Y%m%d%H%M%S"),
                    "enddatetime": window_end.strftime("%Y%m%d%H%M%S"),
                    "sort": "datedesc",
                    "format": "json",
                }
            )
            try:
                text = self.fetcher.fetch_text(url, self.spec)
            except Exception as exc:  # noqa: BLE001 - fetchers share no exception base
                self.fetch_warnings.append(f"{window_start.date()}..{window_end.date()}: {type(exc).__name__}: {exc}")
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
                "Every GDELT historical window failed: " + "; ".join(self.fetch_warnings)
            )
        return documents

    def parse(self, document: RawDocument) -> CollectionBatch:
        batch = CollectionBatch(source_id=document.source_id, raw_document_id=document.id)
        try:
            payload = json.loads(document.content_text)
        except json.JSONDecodeError as exc:
            batch.parse_warnings.append(f"Invalid JSON: {exc}")
            return batch
        articles = payload.get("articles") if isinstance(payload, dict) else None
        if not isinstance(articles, list):
            batch.parse_warnings.append("Unexpected response shape: missing articles list")
            return batch
        seen: set[str] = set()
        for index, article in enumerate(articles):
            if not isinstance(article, dict):
                batch.parse_warnings.append(f"article {index}: malformed; skipped")
                continue
            title = str(article.get("title") or "").strip()
            url = str(article.get("url") or "").strip()
            raw_date = str(article.get("seendate") or "").strip()
            if not title or not url or not raw_date or url in seen:
                batch.parse_warnings.append(f"article {index}: incomplete or duplicate; skipped")
                continue
            try:
                published = datetime.strptime(raw_date[:15], "%Y%m%dT%H%M%S").date()
            except ValueError:
                batch.parse_warnings.append(f"article {index}: invalid seendate; skipped")
                continue
            matched = resolve_ticker_mentions(title, self.companies)
            batch.news_items.append(
                NewsItem(
                    published_at=published,
                    source=self.spec.id,
                    headline=" ".join(title.split()),
                    tickers=matched,
                    body=url,
                )
            )
            seen.add(url)
        return batch
