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

Arabic keywords (`docs/COLLECTOR_TEMPLATE_TAXONOMY.md`'s Gap 2, closed
here): most EGX company sites are Arabic-first or bilingual, and the
keyword list was English-only until now -- real evidence this mattered is
Eastern Company's real, live-fetched disclosure page, whose only match was
an English URL slug (`/disclosures_ar/`); its actual Arabic anchor text
("الإفصاحات") would never have matched. Standard Egyptian corporate/EGX
disclosure terminology, same declared-starting-heuristic posture as the
English list -- not calibrated against a real corpus yet either.
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
        (
            "annual report", "annual-report", "yearly report", "annualreport",
            # Arabic: "annual report" / "the annual report(s)"
            "التقرير السنوي", "تقرير سنوي", "التقارير السنوية",
        ),
    ),
    (
        FinancialDocumentCategory.QUARTERLY_REPORT,
        (
            "quarterly report", "quarterly-report", "interim report", "interim-report",
            "half-year", "half year", "q1 ", "q2 ", "q3 ", "q4 ", "1q", "2q", "3q", "4q",
            # Arabic: quarterly/half-year report, period results/earnings release
            "التقرير الربع سنوي", "تقرير ربع سنوي", "التقارير الربع سنوية",
            "تقرير نصف سنوي", "التقرير النصف سنوي",
            "نتائج الربع", "نتائج الأعمال", "النتائج المالية", "الإعلان عن النتائج",
            "الربع الأول", "الربع الثاني", "الربع الثالث", "الربع الرابع",
        ),
    ),
    (
        FinancialDocumentCategory.FINANCIAL_STATEMENTS,
        (
            "financial statement", "financial-statement", "income statement",
            "balance sheet", "financials", "cash flow statement",
            # Arabic: financial statements/data, balance sheet, income/cash-flow statement
            "القوائم المالية", "البيانات المالية", "الميزانية العمومية",
            "قائمة الدخل", "قائمة التدفقات النقدية",
        ),
    ),
    (
        FinancialDocumentCategory.PRESENTATION,
        (
            "investor presentation", "earnings call", "presentation",
            # Arabic: investor presentation, analyst conference
            "العرض التقديمي", "عرض تقديمي للمستثمرين", "مؤتمر المحللين",
        ),
    ),
    (
        FinancialDocumentCategory.DISCLOSURE,
        (
            "disclosure", "material information", "board resolution", "press release",
            # Arabic: disclosure(s), material information, board resolutions, press release
            "الإفصاحات", "إفصاح", "المعلومات الجوهرية", "قرارات مجلس الإدارة", "بيان صحفي",
        ),
    ),
    (
        FinancialDocumentCategory.INVESTOR_RELATIONS_HOME,
        (
            "investor relations", "investors", "ir home",
            # Arabic: investor relations, investors page
            "علاقات المستثمرين", "صفحة المستثمرين", "المستثمرين",
        ),
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
