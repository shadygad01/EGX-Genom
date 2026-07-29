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
