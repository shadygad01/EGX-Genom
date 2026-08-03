"""Family B PDF financial-statement collector: a company's own quarterly
earnings-release PDF, specifically its "period-comparison summary table"
(a header like `EGP mn 1Q25 1Q26 YoY Change` followed by rows like
`Revenues 865.6 1,066.8 23%`) -- see docs/COLLECTOR_TEMPLATE_TAXONOMY.md,
"Family B -- PDF report repository".

This parser exists only because real extracted text from two real,
already-discovered earnings-release PDFs (RMDA's and TMGH's 1Q26 releases,
fetched live via a GitHub Actions run with real network egress -- this
sandbox has none) was inspected first. Two real risks that inspection
surfaced, both guarded against below:

1. Free-form narrative prose phrases the same figures differently company
   to company (Juhayna: "records a 26% y-o-y increase in net revenue to
   reach EGP 8.6 billion"; Oriental Weavers: "Revenue grew 9% YoY to reach
   EGP 6.9B") -- a single generic regex over prose does not generalize
   across issuers the way `telecom_egypt_financials.py`'s ETEL-specific
   patterns do for one company. This collector therefore only ever reads
   the *structured summary table*, never prose, and reports a warning
   (never a guess) when a document has no such table.
2. The same document also contains unrelated tables shaped identically to
   the one we want (RMDA's per-channel "Sales"/"Volumes Sold" breakdown;
   TMGH's per-segment "Real Estate"/"Hospitality" revenue rows) -- a bare
   `<label> <number> <number> <pct>` regex matches those too. Only the
   fixed, explicitly-evidenced label whitelist below is ever recorded;
   every other row that structurally matches is silently skipped, never
   guessed into a canonical line item it doesn't represent.
"""

from __future__ import annotations

import re
from datetime import date

from agx_research.collectors.archive import RawArchive
from agx_research.collectors.base import CollectionBatch
from agx_research.collectors.fetcher import HttpFetcher
from agx_research.collectors.pdf import PdfDocumentCollector
from agx_research.collectors.raw import RawDocument
from agx_research.financials.schema import FinancialStatementLineItem
from agx_research.sources.spec import SourceSpec

_HEADER_RE = re.compile(
    r"^EGP\s*mn\s+(\d)Q(\d{2})\s+(\d)Q(\d{2})\s+(?:YoY\s+Change|Chg\s*%)\s*$",
    re.MULTILINE,
)
_ROW_RE = re.compile(
    r"^([A-Za-z][A-Za-z &]+?)\s+([\d,]+\.\d+)\s+([\d,]+\.\d+)\s+[+-]?[\d.]+%?\s*(?:pp)?\s*$",
    re.MULTILINE,
)

# Evidenced directly against RMDA's and TMGH's real 1Q26 earnings-release
# summary tables -- not a guessed "generic financial vocabulary". Grow this
# only after inspecting another real document's real table labels.
_LABEL_MAP: dict[str, tuple[str, str]] = {
    "Revenues": ("INCOME_STATEMENT", "revenue"),
    "Revenue": ("INCOME_STATEMENT", "revenue"),
    "Gross Profit": ("INCOME_STATEMENT", "gross_profit"),
    "EBITDA": ("INCOME_STATEMENT", "ebitda"),
    "EBIT": ("INCOME_STATEMENT", "operating_income"),
    "Operating Profit": ("INCOME_STATEMENT", "operating_income"),
    "Net Profit": ("INCOME_STATEMENT", "net_income"),
    "Reported Net Income": ("INCOME_STATEMENT", "net_income"),
    "Recurring Net Income": ("KEY_METRICS", "recurring_net_income"),
}

_QUARTER_END_MONTH = {1: 3, 2: 6, 3: 9, 4: 12}


def _quarter_end(quarter: int, two_digit_year: int) -> date:
    year = 2000 + two_digit_year
    month = _QUARTER_END_MONTH[quarter]
    day = 31 if month in (3, 12) else 30
    return date(year, month, day)


def parse_earnings_summary_table(
    text: str, ticker: str
) -> tuple[list[FinancialStatementLineItem], list[str]]:
    """Pure function: real extracted PDF text in, real line items (or an
    honest empty list with warnings) out. See module docstring for the
    two real risks this guards against.
    """
    items: list[FinancialStatementLineItem] = []
    warnings: list[str] = []
    header = _HEADER_RE.search(text)
    if header is None:
        warnings.append(
            "No 'EGP mn <period> <period> ...' summary table header found; nothing parsed."
        )
        return items, warnings

    q1, y1, q2, y2 = (int(header.group(i)) for i in range(1, 5))
    period_a = _quarter_end(q1, y1)
    period_b = _quarter_end(q2, y2)
    period_end = max(period_a, period_b)
    value_group = 3 if period_b >= period_a else 2

    seen_line_items: set[str] = set()
    for match in _ROW_RE.finditer(text):
        label = match.group(1).strip()
        mapped = _LABEL_MAP.get(label)
        if mapped is None:
            continue
        statement_type, line_item = mapped
        if line_item in seen_line_items:
            continue
        seen_line_items.add(line_item)
        raw_value = match.group(value_group).replace(",", "")
        items.append(
            FinancialStatementLineItem(
                ticker=ticker,
                period_end_date=period_end,
                period_type="QUARTERLY",
                statement_type=statement_type,
                line_item=line_item,
                value=float(raw_value) * 1_000_000,
                currency="EGP",
            )
        )

    if not items:
        warnings.append(
            "Summary table header found but no whitelisted line-item labels matched."
        )
    return items, warnings


class CompanyEarningsTablePdfCollector(PdfDocumentCollector):
    """One instance per company; `urls` is the company's own currently-known
    real earnings-release PDF URL(s) (from `sources.catalog`, refreshed by a
    maintainer when the weekly discovery workflow finds a newer release --
    see AD-53/AD-54's existing catalog-sync precedent). A stale URL fails
    an honest, visible `FetchError`, never a silent wrong value.
    """

    name = "CompanyEarningsTablePdfCollector"
    version = "1.0.0"

    def __init__(
        self,
        spec: SourceSpec,
        ticker: str,
        urls: list[str],
        *,
        archive: RawArchive,
        fetcher: HttpFetcher | None = None,
    ):
        super().__init__(spec, urls, archive=archive, fetcher=fetcher)
        self.ticker = ticker

    def parse(self, document: RawDocument) -> CollectionBatch:
        batch = CollectionBatch(source_id=document.source_id, raw_document_id=document.id)
        text = self.extract_text(document)
        items, warnings = parse_earnings_summary_table(text, self.ticker)
        batch.financial_statement_line_items.extend(items)
        batch.parse_warnings.extend(warnings)
        return batch
