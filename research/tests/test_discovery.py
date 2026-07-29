import subprocess
import sys

from agx_research.discovery.engine import (
    DiscoveryEngine,
    discover_api_documentation,
    discover_company_directory_links,
    discover_financial_documents,
    discover_pdf_repository,
    discover_rss_feeds,
    discover_sitemap_urls,
    discover_structured_datasets,
    is_sitemap_index,
)
from agx_research.discovery.financial_document import FinancialDocumentCategory
from agx_research.sources.spec import AccessMethod

IR_PAGE = """
<html><body>
<a href="/reports/annual-report-2025.pdf">Annual Report 2025</a>
<a href="/reports/q1-2026.pdf">Q1 2026 Results</a>
<a href="/reports/financial-statements.xlsx">Financial Statements</a>
<a href="/investor-relations">Investor Relations</a>
<a href="/about-us">About Us</a>
</body></html>
"""


def test_discover_financial_documents_categorizes_each_match():
    found = discover_financial_documents(IR_PAGE, "https://example.com/")
    by_category = {category: candidate for candidate, category in found}
    assert (
        by_category[FinancialDocumentCategory.ANNUAL_REPORT].discovered_url
        == "https://example.com/reports/annual-report-2025.pdf"
    )
    assert by_category[FinancialDocumentCategory.ANNUAL_REPORT].access_method_guess == AccessMethod.PDF_DOWNLOAD
    assert by_category[FinancialDocumentCategory.QUARTERLY_REPORT].discovered_url == (
        "https://example.com/reports/q1-2026.pdf"
    )
    assert (
        by_category[FinancialDocumentCategory.FINANCIAL_STATEMENTS].access_method_guess
        == AccessMethod.CSV_DOWNLOAD
    )
    assert by_category[FinancialDocumentCategory.INVESTOR_RELATIONS_HOME].discovered_url == (
        "https://example.com/investor-relations"
    )


def test_discover_financial_documents_ignores_unrelated_links():
    found = discover_financial_documents(IR_PAGE, "https://example.com/")
    urls = {candidate.discovered_url for candidate, _ in found}
    assert "https://example.com/about-us" not in urls


def test_discover_financial_documents_dedups_repeated_links():
    html = IR_PAGE + '<a href="/reports/annual-report-2025.pdf">Annual Report (again)</a>'
    found = DiscoveryEngine().scan_financial_documents(html, "https://example.com/")
    annual_report_urls = [c.discovered_url for c, cat in found if cat == FinancialDocumentCategory.ANNUAL_REPORT]
    assert len(annual_report_urls) == 1

HOMEPAGE = """
<html><head>
<link rel="alternate" type="application/rss+xml" title="News Feed" href="/feed.xml">
<link rel="stylesheet" href="/style.css">
</head><body>
<a href="/reports/q1-2026.pdf">Q1 2026</a>
<a href="/reports/q2-2026.pdf">Q2 2026</a>
<a href="/reports/q3-2026.pdf">Q3 2026</a>
<a href="/data/prices.csv">Prices CSV</a>
<a href="/data/macro.json">Macro JSON</a>
</body></html>
"""


def test_discover_rss_feeds_finds_autodiscovery_link():
    candidates = discover_rss_feeds(HOMEPAGE, "https://example.com/")
    assert len(candidates) == 1
    assert candidates[0].discovered_url == "https://example.com/feed.xml"
    assert candidates[0].access_method_guess == AccessMethod.RSS_FEED


def test_discover_rss_feeds_ignores_non_feed_links():
    candidates = discover_rss_feeds("<link rel='stylesheet' href='/x.css'>", "https://example.com/")
    assert candidates == []


def test_discover_pdf_repository_needs_minimum_links():
    candidates = discover_pdf_repository(HOMEPAGE, "https://example.com/ir", min_pdf_links=3)
    assert len(candidates) == 1
    assert candidates[0].discovered_url == "https://example.com/ir"
    assert candidates[0].access_method_guess == AccessMethod.PDF_DOWNLOAD


def test_discover_pdf_repository_below_threshold_returns_nothing():
    candidates = discover_pdf_repository(HOMEPAGE, "https://example.com/ir", min_pdf_links=10)
    assert candidates == []


def test_discover_structured_datasets_finds_csv_and_json():
    candidates = discover_structured_datasets(HOMEPAGE, "https://example.com/")
    urls = {c.discovered_url for c in candidates}
    assert "https://example.com/data/prices.csv" in urls
    assert "https://example.com/data/macro.json" in urls
    assert len(candidates) == 2


def test_discover_sitemap_urls_extracts_loc_entries():
    sitemap = "<urlset><url><loc>https://example.com/a</loc></url><url><loc>https://example.com/b</loc></url></urlset>"
    candidates = discover_sitemap_urls(sitemap, "https://example.com/sitemap.xml")
    assert {c.discovered_url for c in candidates} == {"https://example.com/a", "https://example.com/b"}


def test_discover_sitemap_urls_classifies_structured_extensions_not_blanket_scrape():
    sitemap = (
        "<urlset>"
        "<url><loc>https://example.com/data/prices.csv</loc></url>"
        "<url><loc>https://example.com/about</loc></url>"
        "</urlset>"
    )
    candidates = discover_sitemap_urls(sitemap, "https://example.com/sitemap.xml")
    by_url = {c.discovered_url: c for c in candidates}
    assert by_url["https://example.com/data/prices.csv"].access_method_guess == AccessMethod.CSV_DOWNLOAD
    assert by_url["https://example.com/about"].access_method_guess == AccessMethod.HTML_SCRAPE


def test_discover_sitemap_urls_resolves_a_relative_loc_entry():
    # Non-compliant real-world sitemap (sitemaps.org requires absolute
    # <loc> entries, but a live run against a real site's sitemap found one
    # that wasn't) -- resolved against page_url the same way every other
    # discovery function resolves a relative href, not passed through raw.
    sitemap = "<urlset><url><loc>/relative/path</loc></url></urlset>"
    candidates = discover_sitemap_urls(sitemap, "https://example.com/sitemap.xml")
    assert {c.discovered_url for c in candidates} == {"https://example.com/relative/path"}


def test_discover_sitemap_urls_recovers_a_scheme_and_host_free_loc_entry():
    # A live run against a real site's real sitemap crashed several stages
    # downstream (robots_status building "f'{scheme}://{netloc}/robots.txt'"
    # from a <loc> entry with neither, since this function previously passed
    # the raw <loc> text through with no resolution at all) on exactly this
    # shape. urljoin recovers it against the sitemap's own URL instead of
    # producing a malformed candidate no caller could safely fetch.
    sitemap = "<urlset><url><loc>///not-a-real-url</loc></url></urlset>"
    candidates = discover_sitemap_urls(sitemap, "https://example.com/sitemap.xml")
    assert {c.discovered_url for c in candidates} == {"https://example.com/not-a-real-url"}


def test_discover_sitemap_urls_skips_an_entry_urljoin_cannot_resolve_to_a_fetchable_url():
    # A scheme urllib has no fetch handler for (no relative-URL semantics
    # to fall back to) is a genuinely unresolvable entry, not a malformed-
    # but-recoverable one -- skipped rather than turned into a candidate.
    sitemap = "<urlset><url><loc>javascript:void(0)</loc></url></urlset>"
    candidates = discover_sitemap_urls(sitemap, "https://example.com/sitemap.xml")
    assert candidates == []


def test_is_sitemap_index_detects_sitemapindex_root():
    index = '<sitemapindex><sitemap><loc>https://example.com/sitemap-a.xml</loc></sitemap></sitemapindex>'
    assert is_sitemap_index(index) is True
    assert is_sitemap_index("<urlset><url><loc>https://example.com/a</loc></url></urlset>") is False


def test_discover_api_documentation_finds_conventional_spec_links():
    html = '<a href="/api-docs/swagger.json">API Docs</a><a href="/about">About</a>'
    candidates = discover_api_documentation(html, "https://example.com/")
    assert len(candidates) == 1
    assert candidates[0].discovered_url == "https://example.com/api-docs/swagger.json"
    assert candidates[0].access_method_guess == AccessMethod.JSON_API


def test_engine_scan_page_dedups_and_aggregates_all_heuristics():
    engine = DiscoveryEngine()
    candidates = engine.scan_page(HOMEPAGE, "https://example.com/")
    methods = {c.discovery_method for c in candidates}
    assert len(candidates) == 4  # 1 rss + 1 pdf-repo + 2 structured datasets
    assert len(methods) == 3


DIRECTORY_PAGE = """
<html><body>
<a href="/companies/comi">Commercial International Bank</a>
<a href="/companies/etel">Telecom Egypt Co.</a>
<a href="/news">Latest News</a>
<a href="https://external-site.example/investors"><b>Elsewedy</b> Electric</a>
</body></html>
"""

_DIRECTORY_COMPANIES = {
    "COMI": "Commercial International Bank",
    "ETEL": "Telecom Egypt",
    "SWDY": "Elsewedy Electric",
    "HRHO": "EFG Hermes Holding",  # not on the page -- must not match anything
}


def test_discover_company_directory_links_matches_by_name_token_overlap():
    found = discover_company_directory_links(DIRECTORY_PAGE, "https://egx.com.eg/", _DIRECTORY_COMPANIES)
    assert found["COMI"] == "https://egx.com.eg/companies/comi"
    assert found["ETEL"] == "https://egx.com.eg/companies/etel"


def test_discover_company_directory_links_reads_text_across_nested_tags():
    found = discover_company_directory_links(DIRECTORY_PAGE, "https://egx.com.eg/", _DIRECTORY_COMPANIES)
    assert found["SWDY"] == "https://external-site.example/investors"


def test_discover_company_directory_links_never_matches_a_company_not_on_the_page():
    found = discover_company_directory_links(DIRECTORY_PAGE, "https://egx.com.eg/", _DIRECTORY_COMPANIES)
    assert "HRHO" not in found


def test_discover_company_directory_links_ignores_unrelated_anchors():
    found = discover_company_directory_links(DIRECTORY_PAGE, "https://egx.com.eg/", _DIRECTORY_COMPANIES)
    assert set(found) == {"COMI", "ETEL", "SWDY"}


def test_discover_company_directory_links_returns_empty_for_no_matches():
    html = "<a href='/x'>Unrelated Link</a>"
    assert discover_company_directory_links(html, "https://example.com/", _DIRECTORY_COMPANIES) == {}


def test_discovery_package_imports_cleanly_as_the_first_module_in_a_fresh_process():
    """Regression test for a real circular-import bug found this phase:
    `agx_research.discovery` (via `discovery.candidate` -> `sources.spec` ->
    `sources` package __init__ -> `sources.qualification` -> `discovery.
    candidate.SourceCandidate`) used to fail if `discovery` was the very
    first AGX module touched in a process, because nothing in the existing
    test suite ever imported it first. A regular in-process import can't
    reproduce this (the module is already cached by the time this test
    file's own top-of-file import runs), so this spawns a fresh interpreter.
    """
    result = subprocess.run(
        [sys.executable, "-c", "from agx_research.discovery import DiscoveryEngine"],
        capture_output=True, text=True, timeout=30,
    )
    assert result.returncode == 0, result.stderr
