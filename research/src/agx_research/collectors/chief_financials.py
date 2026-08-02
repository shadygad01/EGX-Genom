"""Structured historical EGX fundamentals published by Chief Capital.

Chief exposes each covered company's historical metrics as an ordinary public
CSV referenced by the public company page.  The files are built from public
EGX filings, require no account or key, and are not disallowed by robots.txt.
The collector discovers the currently published company pages on every run and
only materialises tickers that are part of AGX's declared universe.

No value is inferred.  Empty cells and unknown columns are skipped, and every
materialised value remains traceable to the exact CSV raw document.
"""

from __future__ import annotations

import csv
import io
import re

from agx_research.collectors.base import CollectionBatch, Collector
from agx_research.collectors.fetcher import FetchDisallowed, FetchError
from agx_research.collectors.raw import RawDocument, build_raw_document
from agx_research.financials.schema import FinancialStatementLineItem
from agx_research.universe.sector import SectorClassification

# Real, live-verified index pagination is `page/N/` (WordPress convention),
# confirmed reachable through page 2. The number of real pages is not known
# in advance -- rather than hardcode a guessed total, this walks forward
# until a page adds no new company link or the fetch itself fails, so
# coverage grows automatically as Chief Capital publishes more companies.
# The cap only guards against an unexpected infinite series of empty-but-
# fetchable pages; it is not a declared real page count.
_MAX_INDEX_PAGES = 20

_COMPANY_LINK_RE = re.compile(
    r'href=["\'](?P<url>https://chiefcapitalco\.com/companies/[^"\']+/)["\']', re.IGNORECASE
)
_TICKER_RE = re.compile(
    r"Ticker:\s*<[^>]+>\s*(?P<ticker>[A-Z0-9]{2,10})\s*<", re.IGNORECASE
)
_CSV_RE = re.compile(
    r'csvURL:\s*["\'](?P<url>https://[^"\']+\.csv)["\']', re.IGNORECASE
)
# Chief's own CSV URLs embed the real category Chief Capital itself filed
# the company under, e.g. ".../egx-egyptian-stock-exchange/banks/metrics.csv/
# commercial-international-bank-egypt-cib.csv" -- a real fact about the
# company already present in every fetch, not a guess. Not asserted to be
# a complete industry taxonomy; only what Chief's own URL states.
_SECTOR_FROM_URL_RE = re.compile(
    r"egx-egyptian-stock-exchange/(?P<sector>[a-z0-9-]+)/", re.IGNORECASE
)


def _sector_from_csv_url(csv_url: str) -> str | None:
    match = _SECTOR_FROM_URL_RE.search(csv_url)
    if match is None:
        return None
    return match.group("sector").replace("-", " ").strip().title() or None

# (canonical line item, statement type).  Source headers not listed here are
# intentionally ignored instead of being guessed into an accounting concept.
_COLUMN_MAP: dict[str, tuple[str, str]] = {
    "Assets": ("total_assets", "BALANCE_SHEET"),
    "Liabilities": ("total_liabilities", "BALANCE_SHEET"),
    "BookValue": ("total_equity", "BALANCE_SHEET"),
    "Revenue": ("revenue", "INCOME_STATEMENT"),
    "GrossProfit": ("gross_profit", "INCOME_STATEMENT"),
    "NetProfit": ("net_income", "INCOME_STATEMENT"),
    "NetProfitToShareholders": ("net_income_attributable", "INCOME_STATEMENT"),
    "EPS": ("eps_basic", "INCOME_STATEMENT"),
    "EBITDA": ("ebitda", "INCOME_STATEMENT"),
    "OCF": ("operating_cash_flow", "CASH_FLOW"),
    "FCF": ("free_cash_flow", "CASH_FLOW"),
    "SharesOutstanding": ("shares_outstanding", "BALANCE_SHEET"),
    "TotalDebt": ("total_debt", "BALANCE_SHEET"),
    # Historical reported/derived multiples are retained as source facts and
    # displayed separately; FairValueEngine never mistakes them for cash flow.
    "P/E": ("historical_pe", "VALUATION"),
    "P/BV": ("historical_pb", "VALUATION"),
    "ClosingPrice": ("historical_closing_price", "VALUATION"),
}


class ChiefFinancialsCollector(Collector):
    name = "ChiefFinancialsCollector"
    version = "1.0.0"

    def __init__(self, spec, *, tickers: list[str], fetcher=None):
        super().__init__(spec, fetcher)
        self.tickers = {ticker.upper() for ticker in tickers}
        self.fetch_warnings: list[str] = []

    def fetch(self) -> list[RawDocument]:
        company_urls: set[str] = set()
        # Page 1 failing is a real fetch failure (propagates, same as every
        # other collector) -- only page 2+ failing is treated as "reached
        # the end of real pagination" and stops the walk gracefully.
        html = self.fetcher.fetch_text(self.spec.base_url, self.spec)
        company_urls.update(match.group("url") for match in _COMPANY_LINK_RE.finditer(html))
        for page_number in range(2, _MAX_INDEX_PAGES + 1):
            page_url = f"{self.spec.base_url}page/{page_number}/"
            try:
                html = self.fetcher.fetch_text(page_url, self.spec)
            except (FetchError, FetchDisallowed) as exc:
                self.fetch_warnings.append(f"index page {page_number}: {type(exc).__name__}: {exc}")
                break
            found = {match.group("url") for match in _COMPANY_LINK_RE.finditer(html)}
            if not found - company_urls:
                # No company link on this page is new -- either the same
                # page repeated (end of real pagination) or an empty page.
                break
            company_urls.update(found)

        documents: list[RawDocument] = []
        for company_url in sorted(company_urls):
            html = self.fetcher.fetch_text(company_url, self.spec)
            ticker_match = _TICKER_RE.search(html)
            csv_match = _CSV_RE.search(html)
            if ticker_match is None or csv_match is None:
                self.fetch_warnings.append(f"No ticker/CSV declaration on {company_url}")
                continue
            ticker = ticker_match.group("ticker").upper()
            if ticker not in self.tickers:
                continue
            csv_url = csv_match.group("url")
            content = self.fetcher.fetch_text(csv_url, self.spec)
            documents.append(
                build_raw_document(
                    source_id=self.spec.id,
                    collector=self.name,
                    collector_version=self.version,
                    original_url=csv_url,
                    content_text=f"# ticker={ticker}\n{content}",
                    schema_version=self.spec.schema_version,
                    license=self.spec.license,
                )
            )
        return documents

    def parse(self, document: RawDocument) -> CollectionBatch:
        batch = CollectionBatch(source_id=document.source_id, raw_document_id=document.id)
        first, _, payload = document.content_text.partition("\n")
        if not first.startswith("# ticker="):
            batch.parse_warnings.append("Missing ticker metadata; document withheld.")
            return batch
        ticker = first.removeprefix("# ticker=").strip().upper()
        if ticker not in self.tickers:
            batch.parse_warnings.append(f"Ticker {ticker} is outside the declared universe.")
            return batch

        sector = _sector_from_csv_url(document.original_url)
        if sector is not None:
            batch.sector_classifications.append(
                SectorClassification(
                    ticker=ticker,
                    sector=sector,
                    source_id=document.source_id,
                    observed_date=document.fetched_at.date(),
                )
            )

        reader = csv.DictReader(io.StringIO(payload))
        if not reader.fieldnames or "Year" not in reader.fieldnames:
            batch.parse_warnings.append("CSV has no Year column; document withheld.")
            return batch
        mapped = {column: _COLUMN_MAP[column] for column in reader.fieldnames if column in _COLUMN_MAP}
        if not mapped:
            batch.parse_warnings.append("CSV contains no recognised decision fields.")
            return batch

        for row_number, row in enumerate(reader, start=2):
            try:
                year = int((row.get("Year") or "").strip())
            except ValueError:
                batch.parse_warnings.append(f"row {row_number}: invalid year; skipped")
                continue
            for column, (line_item, statement_type) in mapped.items():
                raw = (row.get(column) or "").strip().replace(",", "")
                if not raw:
                    continue
                try:
                    value = float(raw)
                except ValueError:
                    batch.parse_warnings.append(
                        f"row {row_number} column {column}: non-numeric value; skipped"
                    )
                    continue
                batch.financial_statement_line_items.append(
                    FinancialStatementLineItem(
                        ticker=ticker,
                        period_end_date=f"{year}-12-31",
                        period_type="ANNUAL",
                        statement_type=statement_type,
                        line_item=line_item,
                        value=value,
                        currency="EGP",
                    )
                )
        return batch
