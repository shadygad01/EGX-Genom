from agx_research.collectors.fetcher import FetchError, HttpFetcher
from agx_research.discovery.company_financial_discovery import discover_company_financial_sources
from agx_research.discovery.company_financial_registry import (
    CompanyFinancialSourceRecord,
    CompanyFinancialSourceRegistry,
    CompanyRegistryStatus,
)
from agx_research.discovery.financial_document import FinancialDocumentCategory

IR_PAGE = """
<html><body>
<a href="/reports/annual-report-2025.pdf">Annual Report 2025</a>
<a href="/reports/q1-2026.pdf">Q1 2026 Results</a>
</body></html>
"""


class _FakeFetcher(HttpFetcher):
    """Bypasses real network I/O entirely -- fixtures only, per this
    codebase's "unit tests never hit the network" convention.
    """

    def __init__(self, *, html: str | None = None, raise_error: Exception | None = None):
        super().__init__()
        self._html = html
        self._raise_error = raise_error

    def robots_status(self, url):
        return True

    def fetch_text(self, url, spec):
        if self._raise_error is not None:
            raise self._raise_error
        return self._html


class _MultiPageFetcher(HttpFetcher):
    """Returns different HTML per URL -- what the one-level IR traversal
    tests need (`_FakeFetcher` above returns the same content regardless
    of URL, which cannot exercise a homepage vs. IR-page distinction).
    """

    def __init__(self, *, pages: dict[str, str], raise_for: set[str] | None = None):
        super().__init__()
        self._pages = pages
        self._raise_for = raise_for or set()
        self.fetched_urls: list[str] = []

    def robots_status(self, url):
        return True

    def fetch_text(self, url, spec):
        self.fetched_urls.append(url)
        if url in self._raise_for:
            raise FetchError(f"boom: {url}")
        return self._pages[url]


def _base_record(ticker="COMI") -> CompanyFinancialSourceRecord:
    return CompanyFinancialSourceRecord(
        id=ticker, ticker=ticker, company_name="Test Co", index_membership=["EGX30"]
    )


def test_discover_company_financial_sources_records_categorized_documents():
    fetcher = _FakeFetcher(html=IR_PAGE)
    result = discover_company_financial_sources(fetcher, _base_record(), "https://example.com/")
    assert result.status == CompanyRegistryStatus.DISCOVERED
    assert result.homepage_url == "https://example.com/"
    assert result.robots_allowed is True
    categories = {doc.category for doc in result.documents}
    assert FinancialDocumentCategory.ANNUAL_REPORT in categories
    assert all(doc.evidence for doc in result.documents)


def test_discover_company_financial_sources_records_blocked_reason_on_fetch_failure():
    fetcher = _FakeFetcher(raise_error=FetchError("boom"))
    result = discover_company_financial_sources(fetcher, _base_record(), "https://example.com/")
    assert result.status == CompanyRegistryStatus.BLOCKED
    assert "FetchError" in result.blocked_reason
    assert result.documents == []


def test_discover_company_financial_sources_blocked_when_nothing_categorizable():
    fetcher = _FakeFetcher(html="<a href='/about'>About</a>")
    result = discover_company_financial_sources(fetcher, _base_record(), "https://example.com/")
    assert result.status == CompanyRegistryStatus.BLOCKED
    assert result.blocked_reason is not None


def test_discover_company_financial_sources_never_mutates_input_record():
    original = _base_record()
    discover_company_financial_sources(_FakeFetcher(html=IR_PAGE), original, "https://example.com/")
    assert original.status == CompanyRegistryStatus.PENDING
    assert original.documents == []


def test_follows_investor_relations_home_link_one_level_deep():
    # Real shape from the first live discovery run: the homepage links only
    # the IR section itself; the actual report pages are one click deeper
    # (docs/COLLECTOR_TEMPLATE_TAXONOMY.md's Gap 1).
    homepage_html = '<a href="/investor-relations">Investor Relations</a>'
    ir_page_html = """
    <a href="/investor-relations/financial-statements">Financial Statements</a>
    <a href="/investor-relations/annual-report">Annual Report</a>
    """
    fetcher = _MultiPageFetcher(
        pages={
            "https://example.com/": homepage_html,
            "https://example.com/investor-relations": ir_page_html,
        }
    )
    result = discover_company_financial_sources(fetcher, _base_record(), "https://example.com/")

    assert result.status == CompanyRegistryStatus.DISCOVERED
    categories = {doc.category for doc in result.documents}
    assert FinancialDocumentCategory.FINANCIAL_STATEMENTS in categories
    assert FinancialDocumentCategory.ANNUAL_REPORT in categories
    assert "https://example.com/investor-relations" in fetcher.fetched_urls


def test_ignores_non_navigable_ir_home_anchors():
    homepage_html = """
    <a href="#">Investor Relations</a>
    <a href="javascript:void(0);">Investor Relations</a>
    <a href="#tab-mega-123">Investor Relations</a>
    <a href="/investor-relations">Investor Relations</a>
    """
    fetcher = _MultiPageFetcher(
        pages={
            "https://example.com/": homepage_html,
            "https://example.com/investor-relations": "<a href='/investor-relations/financial-statements'>Financial Statements</a>",
        }
    )
    discover_company_financial_sources(fetcher, _base_record(), "https://example.com/")

    # Only the homepage and the one real, navigable IR-home URL are
    # fetched -- never the homepage itself again under a bare fragment,
    # and never a javascript: pseudo-URL.
    assert fetcher.fetched_urls == [
        "https://example.com/",
        "https://example.com/investor-relations",
    ]


def test_failed_ir_followup_fetch_does_not_lose_level_one_evidence():
    homepage_html = """
    <a href="/financial-statements">Financial Statements</a>
    <a href="/investor-relations">Investor Relations</a>
    """
    fetcher = _MultiPageFetcher(
        pages={"https://example.com/": homepage_html},
        raise_for={"https://example.com/investor-relations"},
    )
    result = discover_company_financial_sources(fetcher, _base_record(), "https://example.com/")

    assert result.status == CompanyRegistryStatus.DISCOVERED
    categories = {doc.category for doc in result.documents}
    assert FinancialDocumentCategory.FINANCIAL_STATEMENTS in categories


def test_traversal_does_not_recurse_beyond_one_level():
    homepage_html = '<a href="/investor-relations">Investor Relations</a>'
    ir_page_html = '<a href="/investor-relations/deeper">Investor Relations</a>'
    fetcher = _MultiPageFetcher(
        pages={
            "https://example.com/": homepage_html,
            "https://example.com/investor-relations": ir_page_html,
            "https://example.com/investor-relations/deeper": "<a href='/x'>Annual Report</a>",
        }
    )
    discover_company_financial_sources(fetcher, _base_record(), "https://example.com/")

    assert "https://example.com/investor-relations/deeper" not in fetcher.fetched_urls


def test_deduplicates_documents_found_on_both_homepage_and_ir_page():
    homepage_html = """
    <a href="/investor-relations">Investor Relations</a>
    <a href="/annual-report">Annual Report</a>
    """
    ir_page_html = '<a href="/annual-report">Annual Report</a>'
    fetcher = _MultiPageFetcher(
        pages={
            "https://example.com/": homepage_html,
            "https://example.com/investor-relations": ir_page_html,
        }
    )
    result = discover_company_financial_sources(fetcher, _base_record(), "https://example.com/")

    annual_report_docs = [
        d for d in result.documents if d.category == FinancialDocumentCategory.ANNUAL_REPORT
    ]
    assert len(annual_report_docs) == 1


def test_registry_resumable_skip_only_true_for_validated(tmp_path):
    registry = CompanyFinancialSourceRegistry(tmp_path / "registry.json")
    assert registry.is_resumable_skip("COMI") is False

    registry.record(_base_record().model_copy(update={"status": CompanyRegistryStatus.BLOCKED}))
    assert registry.is_resumable_skip("COMI") is False

    registry.record(_base_record().model_copy(update={"status": CompanyRegistryStatus.VALIDATED}))
    assert registry.is_resumable_skip("COMI") is True


def test_registry_record_versions_instead_of_overwriting(tmp_path):
    registry = CompanyFinancialSourceRegistry(tmp_path / "registry.json")
    registry.record(_base_record())
    registry.record(_base_record().model_copy(update={"status": CompanyRegistryStatus.DISCOVERED}))
    latest = registry.latest("COMI")
    assert latest.version == 2
    assert latest.status == CompanyRegistryStatus.DISCOVERED
    assert len(registry.history("COMI")) == 2
