"""Market-wide EGX disclosure collector from EAC Finance's public bulletin mirror.

The source publishes the announcement headline, Reuters ticker, publication
timestamp, announcement body, and the original ``egx.com.eg`` attachment link
in ordinary server-rendered HTML.  Its robots.txt allows collection.  Keeping
the original EGX attachment URL on every news item makes the mirror a discovery
and transport layer without losing the first-party document provenance.
"""

from __future__ import annotations

import html
import re
from datetime import date

from agx_research.collectors.base import CollectionBatch, Collector
from agx_research.collectors.corporate_event_classifier import classify_corporate_event_type
from agx_research.collectors.raw import RawDocument, build_raw_document
from agx_research.data.schemas import CorporateEvent, NewsItem

_CARD_RE = re.compile(
    r'<h5 class="card-title">(?P<title>.*?)</h5>\s*'
    r'<p class="card-text">(?P<body>.*?)</p>.*?'
    r'<p class="card-text mb-1"><small class="text-muted">(?P<date>.*?)</small>',
    re.IGNORECASE | re.DOTALL,
)
_TAG_RE = re.compile(r"<[^>]+>")
_TICKER_RE = re.compile(r"\b([A-Z][A-Z0-9]{1,9})\.CA\b", re.IGNORECASE)
_EGX_LINK_RE = re.compile(
    r'href=["\'](?P<url>https?://(?:www\.)?egx\.com\.eg/[^"\']+)["\']', re.IGNORECASE
)


def _text(value: str) -> str:
    value = re.sub(r"<br\s*/?>", " ", value, flags=re.IGNORECASE)
    return " ".join(html.unescape(_TAG_RE.sub(" ", value)).split())


class EgxDisclosureCollector(Collector):
    """Collect the newest market-wide disclosure pages, newest first."""

    name = "EgxDisclosureCollector"
    version = "1.0.0"

    def __init__(self, spec, *, tickers: list[str], pages: int = 5, fetcher=None):
        super().__init__(spec, fetcher)
        self.tickers = {ticker.upper() for ticker in tickers}
        self.pages = pages

    def fetch(self) -> list[RawDocument]:
        documents: list[RawDocument] = []
        for page in range(1, self.pages + 1):
            url = self.spec.base_url if page == 1 else f"{self.spec.base_url}?page={page}"
            content = self.fetcher.fetch_text(url, self.spec)
            documents.append(
                build_raw_document(
                    source_id=self.spec.id,
                    collector=self.name,
                    collector_version=self.version,
                    original_url=url,
                    content_text=content,
                    schema_version=self.spec.schema_version,
                    license=self.spec.license,
                )
            )
        return documents

    def parse(self, document: RawDocument) -> CollectionBatch:
        batch = CollectionBatch(source_id=document.source_id, raw_document_id=document.id)
        cards = list(_CARD_RE.finditer(document.content_text))
        if not cards:
            batch.parse_warnings.append("No disclosure cards found in page HTML.")
            return batch

        for index, card in enumerate(cards):
            title = _text(card.group("title"))
            body_html = card.group("body")
            body = _text(body_html)
            ticker_match = _TICKER_RE.search(f"{title} {body}")
            if ticker_match is None:
                continue
            ticker = ticker_match.group(1).upper()
            if ticker not in self.tickers:
                continue
            try:
                published = date.fromisoformat(_text(card.group("date")).split()[0])
            except ValueError:
                batch.parse_warnings.append(f"card {index}: invalid publication date; skipped")
                continue

            egx_link = _EGX_LINK_RE.search(body_html)
            source_url = html.unescape(egx_link.group("url")) if egx_link else document.original_url
            batch.news_items.append(
                NewsItem(
                    published_at=published,
                    source=self.spec.id,
                    headline=title,
                    tickers=[ticker],
                    body=source_url,
                )
            )
            event_type = classify_corporate_event_type(f"{title} {body}")
            if event_type is not None:
                batch.corporate_events.append(
                    CorporateEvent(
                        ticker=ticker,
                        event_date=published,
                        event_type=event_type,
                        description=title,
                    )
                )
        return batch
