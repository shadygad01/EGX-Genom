"""Official Telecom Egypt investor-relations financial highlights.

Telecom Egypt publishes its latest quarterly result on its public IR homepage
and a detailed release page.  The release is primary issuer data, reachable
without credentials, and contains explicit EGP values for the decision-useful
financial line items below.  This collector deliberately parses only those
labelled highlights; it never guesses values from prose or scanned PDF tables.
"""

from __future__ import annotations

import re
from datetime import date
from html import unescape
from urllib.parse import urljoin

from agx_research.collectors.base import CollectionBatch, Collector
from agx_research.collectors.html_text import visible_text
from agx_research.collectors.raw import RawDocument, build_raw_document
from agx_research.financials.schema import FinancialStatementLineItem

_RELEASE_LINK = re.compile(
    r'''href=["']([^"']*/CorporateNews/PressRelease/\d+/[^"']*Results[^"']*)["']''',
    re.IGNORECASE,
)
_QUARTER = re.compile(r"\bQ([1-4])\s+(20\d{2})\b", re.IGNORECASE)
_EXPLICIT_END = re.compile(
    r"(?:ended|period[- ]end(?:ed)?)\s+(?:on\s+)?(\d{1,2})\s+"
    r"(January|February|March|April|May|June|July|August|September|October|November|December)\s+"
    r"(20\d{2})",
    re.IGNORECASE,
)
_MONTHS = {
    month.lower(): number
    for number, month in enumerate(
        (
            "January", "February", "March", "April", "May", "June",
            "July", "August", "September", "October", "November", "December",
        ),
        start=1,
    )
}

# Ordered and intentionally narrow: every pattern requires both a named metric
# and an explicit EGP amount.  Values in press releases are reported in bn.
_METRICS = (
    (
        "revenue",
        "INCOME_STATEMENT",
        re.compile(r"\bTotal revenue\s+(?:grew\s+[^.]*?\s+)?to\s+EGP\s+([\d.]+)\s*bn\b", re.IGNORECASE),
    ),
    (
        "ebitda",
        "INCOME_STATEMENT",
        re.compile(r"\bEBITDA\s+(?:rose\s+[^.]*?\s+)?to\s+EGP\s+([\d.]+)\s*bn\b", re.IGNORECASE),
    ),
    (
        "net_income",
        "INCOME_STATEMENT",
        re.compile(r"\bNet profit\s+(?:reached|was)\s+EGP\s+([\d.]+)\s*bn\b", re.IGNORECASE),
    ),
    (
        "free_cash_flow",
        "CASH_FLOW",
        re.compile(r"\bFCFF\s+(?:rose\s+)?to\s+EGP\s+([\d.]+)\s*bn\b", re.IGNORECASE),
    ),
)

_DECISION_METRICS = (
    (
        "revenue_growth_yoy",
        "%",
        re.compile(r"\bTotal revenue grew\s+([\d.]+)%\s+YoY\b", re.IGNORECASE),
    ),
    (
        "ebitda_growth_yoy",
        "%",
        re.compile(r"\bEBITDA rose\s+([\d.]+)%\s+YoY\b", re.IGNORECASE),
    ),
    (
        "net_margin",
        "%",
        re.compile(r"\bwith a\s+([\d.]+)%\s+net margin\b", re.IGNORECASE),
    ),
    (
        "net_debt_to_ebitda",
        "x",
        re.compile(r"\bNet debt/EBITDA stood at\s+([\d.]+)x\b", re.IGNORECASE),
    ),
)


def _period_end(text: str) -> date | None:
    explicit = _EXPLICIT_END.search(text)
    if explicit:
        return date(
            int(explicit.group(3)),
            _MONTHS[explicit.group(2).lower()],
            int(explicit.group(1)),
        )
    quarter = _QUARTER.search(text)
    if quarter:
        q, year = int(quarter.group(1)), int(quarter.group(2))
        return date(year, q * 3, 31 if q in (1, 4) else 30)
    return None


class TelecomEgyptFinancialHighlightsCollector(Collector):
    name = "TelecomEgyptFinancialHighlightsCollector"
    version = "1.0.0"

    def fetch(self) -> list[RawDocument]:
        landing = self.fetcher.fetch_text(self.spec.base_url, self.spec)
        match = _RELEASE_LINK.search(landing)
        if match is None:
            raise ValueError("Telecom Egypt IR homepage exposed no quarterly-results release link.")
        release_url = urljoin(self.spec.base_url, unescape(match.group(1)))
        release = self.fetcher.fetch_text(release_url, self.spec)
        return [
            build_raw_document(
                source_id=self.spec.id,
                collector=self.name,
                collector_version=self.version,
                original_url=release_url,
                content_text=release,
                schema_version=self.spec.schema_version,
                license=self.spec.license,
            )
        ]

    def parse(self, document: RawDocument) -> CollectionBatch:
        batch = CollectionBatch(source_id=document.source_id, raw_document_id=document.id)
        text = visible_text(document.content_text)
        period_end = _period_end(text)
        if period_end is None:
            batch.parse_warnings.append("Could not identify the financial reporting period; nothing parsed.")
            return batch

        for line_item, statement_type, pattern in _METRICS:
            match = pattern.search(text)
            if match is None:
                batch.parse_warnings.append(f"Missing labelled {line_item} highlight.")
                continue
            batch.financial_statement_line_items.append(
                FinancialStatementLineItem(
                    ticker="ETEL",
                    period_end_date=period_end,
                    period_type="QUARTERLY",
                    statement_type=statement_type,
                    line_item=line_item,
                    value=float(match.group(1)) * 1_000_000_000,
                    currency="EGP",
                )
            )
        for line_item, unit, pattern in _DECISION_METRICS:
            match = pattern.search(text)
            if match is None:
                batch.parse_warnings.append(f"Missing labelled {line_item} decision metric.")
                continue
            batch.financial_statement_line_items.append(
                FinancialStatementLineItem(
                    ticker="ETEL",
                    period_end_date=period_end,
                    period_type="QUARTERLY",
                    statement_type="KEY_METRICS",
                    line_item=line_item,
                    value=float(match.group(1)),
                    currency=unit,
                )
            )
        return batch
