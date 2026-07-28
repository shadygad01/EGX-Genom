"""Generic RSS 2.0 / Atom collector: one layout-tolerant parser serving
every feed-publishing outlet in the registry.

Per-source configuration (feed URL, language, entity hints) lives in the
SourceSpec, not in code. Parsing tolerates both RSS `<item>` and Atom
`<entry>` shapes, namespaced or not, and records anything unparseable as a
warning rather than guessing. Only headline/link/date metadata is
collected — full-text handling follows each outlet's own terms.

`classify_corporate_events=True` additionally runs each entry through
`corporate_event_classifier`'s headline keyword heuristic when exactly one
ticker hint matches, populating `batch.corporate_events` alongside the
always-produced `NewsItem` -- the same disclosure viewed two ways, not two
collectors. Off by default: most RSS sources are pure news outlets, not
IR disclosure feeds, where this classification wouldn't be meaningful.

Ticker attribution uses `universe.entity_resolution.resolve_ticker_mentions`
(a real word/token match, not a substring check) whenever `ticker_hints`
is given as a `{ticker: company_name}` mapping; a plain `list[str]` is
still accepted for callers with no company-name data and still gets the
upgraded exact-token ticker match (see that module's docstring for why
`RssNewsCollector`'s prior substring check was a real false-positive risk).
"""

from __future__ import annotations

import xml.etree.ElementTree as ET
from datetime import date, datetime
from email.utils import parsedate_to_datetime

from agx_research.collectors.base import CollectionBatch, Collector
from agx_research.collectors.corporate_event_classifier import classify_corporate_event_type
from agx_research.collectors.raw import RawDocument, fetch_single_text_document
from agx_research.data.schemas import CorporateEvent, NewsItem
from agx_research.universe.entity_resolution import resolve_ticker_mentions


def _local_name(tag: str) -> str:
    return tag.rsplit("}", 1)[-1] if "}" in tag else tag


def _child_text(element: ET.Element, name: str) -> str | None:
    for child in element:
        if _local_name(child.tag) == name and child.text:
            return child.text.strip()
    return None


def _entry_link(element: ET.Element) -> str | None:
    for child in element:
        if _local_name(child.tag) == "link":
            if child.text and child.text.strip():
                return child.text.strip()  # RSS style
            href = child.get("href")
            if href:
                return href  # Atom style
    return None


def _entry_date(element: ET.Element) -> date | None:
    for name in ("pubDate", "published", "updated", "date"):
        raw = _child_text(element, name)
        if not raw:
            continue
        try:
            return parsedate_to_datetime(raw).date()  # RFC 822 (RSS)
        except (TypeError, ValueError):
            pass
        try:
            return datetime.fromisoformat(raw.replace("Z", "+00:00")).date()  # ISO (Atom)
        except ValueError:
            pass
        for pattern in ("%m/%d/%Y %I:%M:%S %p", "%m/%d/%Y %H:%M:%S"):
            try:
                return datetime.strptime(raw, pattern).date()
            except ValueError:
                continue
    return None


class RssNewsCollector(Collector):
    name = "RssNewsCollector"
    version = "1.0.0"

    def __init__(
        self,
        spec,
        feed_url: str,
        *,
        ticker_hints: dict[str, str] | list[str] | None = None,
        classify_corporate_events: bool = False,
        fetcher=None,
    ):
        super().__init__(spec, fetcher)
        self.feed_url = feed_url
        # A plain list (no company-name data) still gets the upgraded
        # exact-token ticker match; an empty display name never matches by
        # name alone (see `resolve_ticker_mentions`'s own guard).
        self.companies: dict[str, str] = (
            dict(ticker_hints) if isinstance(ticker_hints, dict) else {t: "" for t in (ticker_hints or [])}
        )
        # Opt-in: most RSS sources are pure news outlets, not IR disclosure
        # feeds -- classification only makes sense where headlines plausibly
        # announce corporate actions (see `corporate_event_classifier`).
        self.classify_corporate_events = classify_corporate_events

    def fetch(self) -> list[RawDocument]:
        return fetch_single_text_document(
            self.fetcher, self.spec,
            collector_name=self.name, collector_version=self.version, url=self.feed_url,
        )

    def parse(self, document: RawDocument) -> CollectionBatch:
        batch = CollectionBatch(source_id=document.source_id, raw_document_id=document.id)
        try:
            root = ET.fromstring(document.content_text)
        except ET.ParseError as exc:
            batch.parse_warnings.append(f"Feed is not well-formed XML: {exc}")
            return batch

        entries = [e for e in root.iter() if _local_name(e.tag) in ("item", "entry")]
        if not entries:
            batch.parse_warnings.append("No <item>/<entry> elements found in feed.")
            return batch

        for index, entry in enumerate(entries):
            title = _child_text(entry, "title")
            published = _entry_date(entry)
            if not title or published is None:
                batch.parse_warnings.append(f"entry {index}: missing title or date; skipped")
                continue
            link = _entry_link(entry)
            matched = resolve_ticker_mentions(title, self.companies)
            batch.news_items.append(
                NewsItem(
                    published_at=published,
                    source=self.spec.id,
                    headline=" ".join(title.split()),
                    tickers=matched,
                    body=link,  # original URL preserved; full text per-outlet terms
                )
            )
            if self.classify_corporate_events and len(matched) == 1:
                event_type = classify_corporate_event_type(title)
                if event_type is not None:
                    batch.corporate_events.append(
                        CorporateEvent(
                            ticker=matched[0],
                            event_date=published,
                            event_type=event_type,
                            description=" ".join(title.split()),
                            # Headline-only: no numeric detail (split ratio,
                            # dividend amount) can be reliably read off a
                            # title -- see corporate_event_classifier's
                            # module docstring.
                        )
                    )
        return batch
