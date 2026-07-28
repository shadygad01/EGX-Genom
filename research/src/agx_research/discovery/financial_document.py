"""Financial document classification: which kind of Investor-Relations
report a discovered link actually is (annual report, quarterly report,
financial statements, presentation, disclosure, or the IR homepage
itself).

Generic and company-agnostic, same posture and same honesty tier as
`collectors.corporate_event_classifier.classify_corporate_event_type()`
and `acquisition_intelligence.legality`'s ToS keyword lists: a declared
starting heuristic (keyword match on URL + anchor text), not calibrated
against a real corpus of EGX company IR pages, because none has been
fetched yet (see `docs/TECHNICAL_DEBT.md` TD-39). A link matching nothing
returns `None` -- correctly non-fabricating -- rather than a guessed
category.
"""

from __future__ import annotations

from enum import Enum


class FinancialDocumentCategory(str, Enum):
    ANNUAL_REPORT = "annual_report"
    QUARTERLY_REPORT = "quarterly_report"
    FINANCIAL_STATEMENTS = "financial_statements"
    PRESENTATION = "presentation"
    DISCLOSURE = "disclosure"
    INVESTOR_RELATIONS_HOME = "investor_relations_home"


# Checked in this order -- more specific document types before the generic
# "investor relations" catch-all, so an "Annual Report" link inside an IR
# section isn't mislabeled just because its surrounding page also says
# "investor relations" somewhere in the anchor text.
_CATEGORY_KEYWORDS: list[tuple[FinancialDocumentCategory, tuple[str, ...]]] = [
    (
        FinancialDocumentCategory.ANNUAL_REPORT,
        ("annual report", "annual-report", "yearly report", "annualreport"),
    ),
    (
        FinancialDocumentCategory.QUARTERLY_REPORT,
        (
            "quarterly report", "quarterly-report", "interim report", "interim-report",
            "half-year", "half year", "q1 ", "q2 ", "q3 ", "q4 ", "1q", "2q", "3q", "4q",
        ),
    ),
    (
        FinancialDocumentCategory.FINANCIAL_STATEMENTS,
        (
            "financial statement", "financial-statement", "income statement",
            "balance sheet", "financials", "cash flow statement",
        ),
    ),
    (
        FinancialDocumentCategory.PRESENTATION,
        ("investor presentation", "earnings call", "presentation"),
    ),
    (
        FinancialDocumentCategory.DISCLOSURE,
        ("disclosure", "material information", "board resolution", "press release"),
    ),
    (
        FinancialDocumentCategory.INVESTOR_RELATIONS_HOME,
        ("investor relations", "investors", "ir home"),
    ),
]


def classify_financial_document(url: str, anchor_text: str = "") -> FinancialDocumentCategory | None:
    """`None` means neither the URL nor the anchor text matched any known
    financial-document keyword -- an ordinary, uncategorized link, not a
    financial document candidate at all.
    """
    haystack = f"{url} {anchor_text}".lower()
    for category, keywords in _CATEGORY_KEYWORDS:
        if any(keyword in haystack for keyword in keywords):
            return category
    return None
