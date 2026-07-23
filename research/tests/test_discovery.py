from agx_research.discovery.engine import (
    DiscoveryEngine,
    discover_api_documentation,
    discover_pdf_repository,
    discover_rss_feeds,
    discover_sitemap_urls,
    discover_structured_datasets,
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
