import subprocess
import sys

from agx_research.discovery.engine import (
    DiscoveryEngine,
    discover_api_documentation,
    discover_company_directory_links,
    discover_pdf_repository,
    discover_rss_feeds,
    discover_sitemap_urls,
    discover_structured_datasets,
    is_sitemap_index,
)
from agx_research.sources.spec import AccessMethod

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
