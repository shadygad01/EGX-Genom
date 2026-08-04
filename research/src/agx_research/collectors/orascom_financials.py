"""Official Orascom Construction investor-relations result highlights."""

from __future__ import annotations

import re
from datetime import date
from html import unescape
from urllib.parse import urljoin

from agx_research.collectors.base import CollectionBatch, Collector
from agx_research.collectors.raw import RawDocument, build_raw_document
from agx_research.financials.schema import FinancialStatementLineItem

_RESULT_LINK = re.compile(
    r'''href=["']([^"']*/updates/orascom-construction-reports[^"']*(?:q[1-4]|fy)[^"']*)["']''',
    re.IGNORECASE,
)
_TAG = re.compile(r"<[^>]+>")
_SPACE = re.compile(r"\s+")
_PERIOD = re.compile(r"\b(Q([1-4])|FY)\s*(20\d{2})\b", re.IGNORECASE)
_HIGHLIGHTS = re.compile(
    r"Revenue of USD\s+([\d,]+(?:\.\d+)?)\s+million,\s*"
    r"EBITDA of USD\s+([\d,]+(?:\.\d+)?)\s+million,\s*and\s*"
    r"net profit attributable to shareholders of USD\s+([\d,]+(?:\.\d+)?)\s+million",
    re.IGNORECASE,
)


def _visible_text(html: str) -> str:
    without_scripts = re.sub(r"<script[\s\S]*?</script>", " ", html, flags=re.IGNORECASE)
    without_styles = re.sub(r"<style[\s\S]*?</style>", " ", without_scripts, flags=re.IGNORECASE)
    return _SPACE.sub(" ", unescape(_TAG.sub(" ", without_styles))).strip()


def _number(value: str) -> float:
    return float(value.replace(",", ""))


class OrascomFinancialHighlightsCollector(Collector):
    """Collect only explicitly labelled headline values from the issuer site."""

    name = "OrascomFinancialHighlightsCollector"
    version = "1.0.0"

    def fetch(self) -> list[RawDocument]:
        archive = self.fetcher.fetch_text(self.spec.base_url, self.spec)
        match = _RESULT_LINK.search(archive)
        if match is None:
            raise ValueError("Orascom updates archive exposed no quarterly/FY results article.")
        result_url = urljoin(self.spec.base_url, unescape(match.group(1)))
        result = self.fetcher.fetch_text(result_url, self.spec)
        return [
            build_raw_document(
                source_id=self.spec.id,
                collector=self.name,
                collector_version=self.version,
                original_url=result_url,
                content_text=result,
                schema_version=self.spec.schema_version,
                license=self.spec.license,
            )
        ]

    def parse(self, document: RawDocument) -> CollectionBatch:
        batch = CollectionBatch(source_id=document.source_id, raw_document_id=document.id)
        text = _visible_text(document.content_text)
        period = _PERIOD.search(text)
        highlights = _HIGHLIGHTS.search(text)
        if period is None or highlights is None:
            batch.parse_warnings.append(
                "Missing an explicit reporting period or labelled USD result highlights; nothing parsed."
            )
            return batch

        period_name, quarter, year_text = period.groups()
        year = int(year_text)
        if period_name.upper() == "FY":
            period_end, period_type = date(year, 12, 31), "ANNUAL"
        else:
            q = int(quarter)
            period_end = date(year, q * 3, 31 if q in (1, 4) else 30)
            period_type = "QUARTERLY"

        # The issuer highlight explicitly states "attributable to
        # shareholders" -- Chief Capital's own collector already
        # distinguishes this from total consolidated net profit as
        # `net_income_attributable` (`NetProfitToShareholders`), so this
        # must use the same label rather than the generic `net_income`,
        # which would silently conflate the two concepts.
        for line_item, raw_value in zip(
            ("revenue", "ebitda", "net_income_attributable"), highlights.groups(), strict=True
        ):
            batch.financial_statement_line_items.append(
                FinancialStatementLineItem(
                    ticker="ORAS",
                    period_end_date=period_end,
                    period_type=period_type,
                    statement_type="INCOME_STATEMENT",
                    line_item=line_item,
                    value=_number(raw_value) * 1_000_000,
                    currency="USD",
                )
            )
        return batch
