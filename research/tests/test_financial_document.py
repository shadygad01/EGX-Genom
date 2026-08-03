from agx_research.discovery.financial_document import (
    FinancialDocumentCategory,
    classify_financial_document,
)


def test_classifies_annual_report_by_anchor_text():
    assert (
        classify_financial_document("https://example.com/files/2025.pdf", "Annual Report 2025")
        == FinancialDocumentCategory.ANNUAL_REPORT
    )


def test_classifies_annual_report_by_url_slug():
    assert (
        classify_financial_document("https://example.com/downloads/annual-report-2025.pdf", "")
        == FinancialDocumentCategory.ANNUAL_REPORT
    )


def test_classifies_quarterly_report():
    assert (
        classify_financial_document("https://example.com/q1-2026.pdf", "Q1 2026 Results")
        == FinancialDocumentCategory.QUARTERLY_REPORT
    )


def test_classifies_financial_statements():
    assert (
        classify_financial_document("https://example.com/reports/fs.pdf", "Financial Statements")
        == FinancialDocumentCategory.FINANCIAL_STATEMENTS
    )


def test_classifies_investor_relations_home_as_catch_all():
    assert (
        classify_financial_document("https://example.com/investor-relations", "Investor Relations")
        == FinancialDocumentCategory.INVESTOR_RELATIONS_HOME
    )


def test_unmatched_link_returns_none_not_a_guess():
    assert classify_financial_document("https://example.com/about-us", "About Us") is None


def test_more_specific_category_wins_over_generic_ir_keyword():
    # Anchor text mentions "investor relations" but the link is clearly an
    # annual report -- the more specific category must win, not be
    # overridden by the generic IR catch-all appearing later in the list.
    assert (
        classify_financial_document(
            "https://example.com/ir/annual-report-2025.pdf", "Investor Relations - Annual Report"
        )
        == FinancialDocumentCategory.ANNUAL_REPORT
    )


def test_classifies_real_arabic_disclosure_anchor_text():
    # Real evidence this mattered: Eastern Company's (EAST) actual, live-
    # fetched disclosures page only matched before via its English URL
    # slug (/disclosures_ar/) -- its real Arabic anchor text below would
    # not have matched the pre-Arabic-vocabulary keyword list at all.
    assert (
        classify_financial_document("https://www.easternegypt.com/disclosures_ar/", "الإفصاحات")
        == FinancialDocumentCategory.DISCLOSURE
    )


def test_classifies_arabic_annual_report():
    assert (
        classify_financial_document("https://example.com/reports/2025", "التقرير السنوي 2025")
        == FinancialDocumentCategory.ANNUAL_REPORT
    )


def test_classifies_arabic_quarterly_report():
    assert (
        classify_financial_document("https://example.com/q3-2026", "نتائج الربع الثالث 2026")
        == FinancialDocumentCategory.QUARTERLY_REPORT
    )


def test_classifies_arabic_financial_statements():
    assert (
        classify_financial_document("https://example.com/fs", "القوائم المالية")
        == FinancialDocumentCategory.FINANCIAL_STATEMENTS
    )


def test_classifies_arabic_investor_relations_home_as_catch_all():
    assert (
        classify_financial_document("https://example.com/ir", "علاقات المستثمرين")
        == FinancialDocumentCategory.INVESTOR_RELATIONS_HOME
    )


def test_arabic_specific_category_still_wins_over_generic_ir_keyword():
    assert (
        classify_financial_document(
            "https://example.com/ir/annual-2025", "علاقات المستثمرين - التقرير السنوي"
        )
        == FinancialDocumentCategory.ANNUAL_REPORT
    )
