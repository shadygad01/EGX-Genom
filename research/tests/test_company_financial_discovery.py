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
