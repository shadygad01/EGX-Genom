"""Free GDELT DOC 2.0 news-metadata collector."""

from __future__ import annotations

import json
from datetime import datetime
from urllib.parse import urlencode

from agx_research.collectors.base import CollectionBatch, Collector
from agx_research.collectors.raw import RawDocument, build_raw_document
from agx_research.data.schemas import NewsItem


class GdeltDocCollector(Collector):
    name = "GdeltDocCollector"
    version = "1.0.0"

    def __init__(
        self,
        spec,
        *,
        query: str,
        ticker_hints: list[str] | None = None,
        max_records: int = 250,
        timespan: str = "7d",
        fetcher=None,
    ):
        super().__init__(spec, fetcher)
        self.query = query
        self.ticker_hints = ticker_hints or []
        self.max_records = min(max(max_records, 1), 250)
        self.timespan = timespan

    def fetch(self) -> list[RawDocument]:
        params = urlencode(
            {
                "query": self.query,
                "mode": "artlist",
                "maxrecords": self.max_records,
                "timespan": self.timespan,
                "sort": "datedesc",
                "format": "json",
            }
        )
        url = f"{self.spec.base_url}?{params}"
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
            lowered = title.lower()
            matched = [ticker for ticker in self.ticker_hints if ticker.lower() in lowered]
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
