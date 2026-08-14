"""Primary official-filings collector for EGX, FRA and issuer IR pages.

The collector is deliberately source-agnostic: verified homepage URLs are supplied
by discovery/configuration, never guessed. It follows one level of report links,
archives every fetched payload, and parses only explicit structured tables/CSV files.
PDFs are archived as binary evidence and withheld from canonical financials until a
source-specific parser is attached; this is safer than guessing PDF columns.
"""
from __future__ import annotations

import csv
import io
import re
from urllib.parse import urljoin, urlsplit

from bs4 import BeautifulSoup

from agx_research.collectors.archive import RawArchive
from agx_research.collectors.base import CollectionBatch, Collector
from agx_research.collectors.fetcher import FetchDisallowed, FetchError
from agx_research.collectors.raw import (
    RawDocument,
    build_binary_raw_document,
    build_raw_document,
)
from agx_research.financials.schema import FinancialStatementLineItem

_REPORT_TERMS = (
    "annual report", "quarterly", "financial statement", "financial report",
    "results", "investor relations", "financials", "قوائم مالية", "نتائج الأعمال",
    "تقرير سنوي", "تقرير ربع", "افصاح", "إفصاح",
)
_FILE_EXTENSIONS = (".pdf", ".csv", ".xls", ".xlsx", ".html", ".htm")


class OfficialFilingsCollector(Collector):
    name = "OfficialFilingsCollector"
    version = "1.0.0"

    def __init__(self, spec, *, company_urls: dict[str, str | list[str]], fetcher=None, archive: RawArchive | None = None):
        super().__init__(spec, fetcher)
        self.company_urls: dict[str, list[str]] = {}
        for ticker, urls in company_urls.items():
            normalized = [urls] if isinstance(urls, str) else list(urls)
            self.company_urls[ticker.upper()] = list(dict.fromkeys(u for u in normalized if u))
        self.archive = archive or RawArchive()

    def _candidate_links(self, html: str, page_url: str) -> list[str]:
        soup = BeautifulSoup(html, "html.parser")
        links: list[str] = []
        for anchor in soup.find_all("a", href=True):
            href = urljoin(page_url, str(anchor["href"]))
            if urlsplit(href).scheme not in {"http", "https"}:
                continue
            label = " ".join(anchor.get_text(" ", strip=True).casefold().split())
            path = urlsplit(href).path.casefold()
            if any(term in label for term in _REPORT_TERMS) or path.endswith(_FILE_EXTENSIONS):
                links.append(href)
        return list(dict.fromkeys(links))

    def fetch(self) -> list[RawDocument]:
        documents: list[RawDocument] = []
        seen: set[str] = set()
        for ticker, homepages in sorted(self.company_urls.items()):
            for homepage in homepages:
                try:
                    landing = self.fetcher.fetch_bytes(homepage, self.spec)
                except (FetchDisallowed, FetchError, OSError, UnicodeError):
                    continue
                landing_text = landing.decode("utf-8", errors="replace")
                landing_doc = build_raw_document(
                    source_id=self.spec.id, collector=self.name, collector_version=self.version,
                    original_url=homepage, content_text=landing_text,
                    schema_version=self.spec.schema_version, license=self.spec.license,
                )
                documents.append(landing_doc)
                for url in self._candidate_links(landing_text, homepage):
                    if url in seen or url == homepage:
                        continue
                    seen.add(url)
                    try:
                        payload = self.fetcher.fetch_bytes(url, self.spec)
                    except (FetchDisallowed, FetchError, OSError, UnicodeError):
                        continue
                    content_type = urlsplit(url).path.casefold()
                    if content_type.endswith((".pdf", ".xls", ".xlsx")):
                        documents.append(build_binary_raw_document(
                            source_id=self.spec.id, collector=self.name, collector_version=self.version,
                            original_url=url, content=payload, schema_version=self.spec.schema_version,
                            license=self.spec.license, archive=self.archive,
                        ))
                    else:
                        documents.append(build_raw_document(
                            source_id=self.spec.id, collector=self.name, collector_version=self.version,
                            original_url=url, content_text=payload.decode("utf-8", errors="replace"),
                            schema_version=self.spec.schema_version, license=self.spec.license,
                        ))
        return documents

    def parse(self, document: RawDocument) -> CollectionBatch:
        batch = CollectionBatch(source_id=document.source_id, raw_document_id=document.id)
        ticker = self._ticker_for_url(document.original_url)
        if document.is_binary:
            batch.parse_warnings.append(
                "Binary filing archived with provenance but withheld from canonical financials; "
                "attach a source-specific PDF/XLS parser before promotion."
            )
            return batch
        if not ticker:
            batch.parse_warnings.append("Could not resolve a universe ticker for this filing URL.")
            return batch
        text = document.content_text
        if "<table" in text.casefold():
            text = self._html_table_to_csv(text)
        reader = csv.DictReader(io.StringIO(text))
        if not reader.fieldnames:
            batch.parse_warnings.append("No structured CSV/HTML table header found.")
            return batch
        fields = {self._norm(k): k for k in reader.fieldnames if k}
        period = self._find(fields, "period_end", "period end", "date", "as of", "year")
        metric = self._find(fields, "line_item", "line item", "metric", "item", "particular")
        value = self._find(fields, "value", "amount", "actual")
        if not (period and metric and value):
            batch.parse_warnings.append("Structured filing lacks explicit period/metric/value columns.")
            return batch
        for row in reader:
            try:
                raw_period = str(row.get(period, "")).strip()
                year = int(re.search(r"(19|20)\d{2}", raw_period).group(0))
                metric_name = self._norm(str(row.get(metric, ""))).replace(" ", "_")
                amount = float(str(row.get(value, "")).replace(",", "").strip())
                if not metric_name:
                    continue
                batch.financial_statement_line_items.append(FinancialStatementLineItem(
                    ticker=ticker, period_end_date=f"{year}-12-31", period_type="ANNUAL",
                    statement_type="REPORTED", line_item=metric_name, value=amount, currency="EGP",
                ))
            except (AttributeError, ValueError, TypeError):
                batch.parse_warnings.append("Skipped one row with invalid period or value.")
        return batch

    def _ticker_for_url(self, url: str) -> str | None:
        for ticker, homepages in self.company_urls.items():
            if any(url == homepage or url.startswith(homepage.rstrip("/") + "/") for homepage in homepages):
                return ticker
        return None

    @staticmethod
    def _norm(value: str) -> str:
        return " ".join(value.casefold().replace("_", " ").split())

    @classmethod
    def _find(cls, fields: dict[str, str], *hints: str) -> str | None:
        for field, original in fields.items():
            if any(hint in field for hint in hints):
                return original
        return None

    @staticmethod
    def _html_table_to_csv(html: str) -> str:
        soup = BeautifulSoup(html, "html.parser")
        table = soup.find("table")
        if table is None:
            return ""
        rows = []
        for tr in table.find_all("tr"):
            cells = [c.get_text(" ", strip=True) for c in tr.find_all(["th", "td"])]
            if cells:
                rows.append(cells)
        if not rows:
            return ""
        output = io.StringIO()
        csv.writer(output).writerows(rows)
        return output.getvalue()
