"""AcquisitionIntelligenceEngine end-to-end tests: every network-touching
dependency (prober/fetch_text/robots_checker/wayback) is a fake, so this
exercises the real orchestration logic with no network involved.
"""

from agx_research.acquisition_intelligence.continuity import AcquisitionContinuityMonitor
from agx_research.acquisition_intelligence.domain_resolution import ProbeResult
from agx_research.acquisition_intelligence.engine import AcquisitionIntelligenceEngine
from agx_research.acquisition_intelligence.target import TargetOrganization
from agx_research.sources.registry import SourceRegistry
from agx_research.sources.spec import HealthStatus, LifecycleState, SourceCategory, SourceStatus

HOMEPAGE_WITH_RSS = """
<html><head>
<link rel="alternate" type="application/rss+xml" title="News" href="/feed.xml">
</head><body>hello</body></html>
"""

HOMEPAGE_WITH_NOTHING = "<html><body>nothing here</body></html>"


def make_target(**overrides) -> TargetOrganization:
    defaults = dict(id="testorg", name="Test Org", category=SourceCategory.NEWS, domain_hints=["testorg.com"])
    defaults.update(overrides)
    return TargetOrganization(**defaults)


class FakeWayback:
    def __init__(self, *, availability=None, cdx=None):
        self.availability = availability or {"archived_snapshots": {}}
        self.cdx = cdx or []

    def check_availability(self, url):
        return self.availability

    def cdx_snapshots(self, url):
        return self.cdx


def reachable_prober(reachable_urls: set[str]):
    def prober(url):
        return ProbeResult(url=url, reachable=url in reachable_urls, status_code=200 if url in reachable_urls else None)
    return prober


def test_no_reachable_domain_reports_reason_and_does_not_register():
    registry = SourceRegistry()
    engine = AcquisitionIntelligenceEngine(
        prober=reachable_prober(set()),  # nothing reachable
        fetch_text=lambda url: HOMEPAGE_WITH_RSS,
        robots_checker=lambda url: True,
        registry=registry,
    )
    result = engine.run_for_target(make_target())
    assert result.registered is False
    assert "No reachable domain" in result.reason
    assert registry.latest("testorg") is None


def test_homepage_unfetchable_reports_reason():
    registry = SourceRegistry()
    engine = AcquisitionIntelligenceEngine(
        prober=reachable_prober({"https://testorg.com"}),
        fetch_text=lambda url: None,
        robots_checker=lambda url: True,
        registry=registry,
    )
    result = engine.run_for_target(make_target())
    assert result.registered is False
    assert "could not be fetched" in result.reason


def test_no_candidates_discovered_reports_reason():
    registry = SourceRegistry()
    engine = AcquisitionIntelligenceEngine(
        prober=reachable_prober({"https://testorg.com"}),
        fetch_text=lambda url: HOMEPAGE_WITH_NOTHING,
        robots_checker=lambda url: True,
        registry=registry,
    )
    result = engine.run_for_target(make_target())
    assert result.registered is False
    assert "No acquisition-method candidates" in result.reason


def test_robots_disallow_blocks_the_only_candidate():
    registry = SourceRegistry()
    engine = AcquisitionIntelligenceEngine(
        prober=reachable_prober({"https://testorg.com", "https://testorg.com/feed.xml"}),
        fetch_text=lambda url: HOMEPAGE_WITH_RSS,
        robots_checker=lambda url: False,  # everything disallowed
        registry=registry,
    )
    result = engine.run_for_target(make_target())
    assert result.registered is False
    assert "legality gate" in result.reason
    assert registry.latest("testorg") is None


def test_successful_run_registers_planned_spec_and_begins_qualification():
    registry = SourceRegistry()
    wayback = FakeWayback(cdx=[["timestamp"], ["20200101000000"], ["20250101000000"]])
    engine = AcquisitionIntelligenceEngine(
        prober=reachable_prober({"https://testorg.com", "https://testorg.com/feed.xml"}),
        fetch_text=lambda url: HOMEPAGE_WITH_RSS,
        robots_checker=lambda url: True,
        registry=registry,
        wayback=wayback,
    )
    result = engine.run_for_target(make_target(existing_source_id="testorg"))

    assert result.registered is True
    spec = registry.latest("testorg")
    assert spec is not None
    assert spec.status == SourceStatus.PLANNED  # never auto-implemented
    assert spec.collector == "RssNewsCollector"
    assert spec.lifecycle_state == LifecycleState.QUARANTINE  # qualification began
    assert spec.base_url == "https://testorg.com/feed.xml"


def test_re_running_same_target_updates_existing_spec_not_duplicate():
    registry = SourceRegistry()
    engine = AcquisitionIntelligenceEngine(
        prober=reachable_prober({"https://testorg.com", "https://testorg.com/feed.xml"}),
        fetch_text=lambda url: HOMEPAGE_WITH_RSS,
        robots_checker=lambda url: True,
        registry=registry,
    )
    target = make_target(existing_source_id="testorg")
    engine.run_for_target(target)
    engine.run_for_target(target)

    spec = registry.latest("testorg")
    assert spec.version >= 2
    assert len(registry.all_latest()) == 1


def test_exclude_urls_lets_alternative_method_win():
    homepage = """
    <html><head>
    <link rel="alternate" type="application/rss+xml" href="/feed.xml">
    </head><body><a href="/data/prices.csv">Prices</a></body></html>
    """
    registry = SourceRegistry()
    engine = AcquisitionIntelligenceEngine(
        prober=reachable_prober({
            "https://testorg.com", "https://testorg.com/feed.xml", "https://testorg.com/data/prices.csv",
        }),
        fetch_text=lambda url: homepage,
        robots_checker=lambda url: True,
        registry=registry,
    )
    target = make_target(existing_source_id="testorg")

    first = engine.run_for_target(target)
    assert first.selected.candidate.discovered_url == "https://testorg.com/feed.xml"

    second = engine.run_for_target(target, exclude_urls={"https://testorg.com/feed.xml"})
    assert second.selected.candidate.discovered_url == "https://testorg.com/data/prices.csv"


def test_continuity_monitor_recovers_down_source_with_alternative_method():
    homepage = """
    <html><head>
    <link rel="alternate" type="application/rss+xml" href="/feed.xml">
    </head><body><a href="/data/prices.csv">Prices</a></body></html>
    """
    registry = SourceRegistry()
    engine = AcquisitionIntelligenceEngine(
        prober=reachable_prober({
            "https://testorg.com", "https://testorg.com/feed.xml", "https://testorg.com/data/prices.csv",
        }),
        fetch_text=lambda url: homepage,
        robots_checker=lambda url: True,
        registry=registry,
    )
    target = make_target(existing_source_id="testorg")
    engine.run_for_target(target)

    # Simulate the RSS feed failing in production: health goes DOWN.
    registry.update_health("testorg", HealthStatus.DOWN)

    monitor = AcquisitionContinuityMonitor(engine, [target])
    results = monitor.check_and_recover(registry)

    assert len(results) == 1
    assert results[0].registered is True
    assert results[0].selected.candidate.discovered_url == "https://testorg.com/data/prices.csv"


def test_run_catalog_processes_targets_in_priority_order():
    registry = SourceRegistry()
    call_order = []

    def prober(url):
        call_order.append(url)
        return ProbeResult(url=url, reachable=False)

    engine = AcquisitionIntelligenceEngine(
        prober=prober, fetch_text=lambda url: None, robots_checker=lambda url: True,
        registry=registry,
    )
    low = make_target(id="low_priority", domain_hints=["low.com"], priority=10)
    high = make_target(id="high_priority", domain_hints=["high.com"], priority=1)

    engine.run_catalog([low, high])

    # high_priority's domain is probed before low_priority's, regardless of
    # input list order.
    assert call_order.index("https://high.com") < call_order.index("https://low.com")


def test_run_catalog_feeds_company_directory_hints_into_later_targets():
    directory_html = """
    <html><head>
    <link rel="alternate" type="application/rss+xml" href="/feed.xml">
    </head><body><a href="https://testco.example/">Test Company</a></body></html>
    """
    company_html = """
    <html><head>
    <link rel="alternate" type="application/rss+xml" href="/ir-feed.xml">
    </head><body>hello</body></html>
    """
    reachable = {
        "https://directory.com", "https://directory.com/feed.xml",
        "https://testco.example", "https://testco.example/ir-feed.xml",
    }
    pages = {
        "https://directory.com": directory_html,
        "https://testco.example": company_html,
    }

    registry = SourceRegistry()
    engine = AcquisitionIntelligenceEngine(
        prober=reachable_prober(reachable),
        fetch_text=lambda url: pages.get(url),
        robots_checker=lambda url: True,
        registry=registry,
    )
    directory_target = make_target(
        id="directory", name="Directory Org", domain_hints=["directory.com"], priority=1,
    )
    company_target = make_target(
        id="company_ir_tco", name="Test Company Investor Relations",
        domain_hints=[], priority=2, company_ticker="TCO",
    )

    results = engine.run_catalog(
        [company_target, directory_target], companies={"TCO": "Test Company"},
    )

    directory_result = next(r for r in results if r.target_id == "directory")
    company_result = next(r for r in results if r.target_id == "company_ir_tco")
    assert directory_result.registered is True
    # The company target had no domain hints of its own -- it only resolved
    # because the directory's own page linked to "Test Company".
    assert company_result.registered is True
    assert company_result.resolved_domain.domain == "testco.example"


def test_run_catalog_never_overrides_a_targets_own_domain_hints():
    directory_html = '<html><body><a href="https://wrong-domain.example/">Test Company</a></body></html>'
    reachable = {"https://directory.com", "https://real-domain.example"}
    pages = {"https://directory.com": directory_html}

    registry = SourceRegistry()
    engine = AcquisitionIntelligenceEngine(
        prober=reachable_prober(reachable),
        fetch_text=lambda url: pages.get(url),
        robots_checker=lambda url: True,
        registry=registry,
    )
    directory_target = make_target(id="directory", domain_hints=["directory.com"], priority=1)
    company_target = make_target(
        id="company_ir_tco", domain_hints=["real-domain.example"], priority=2, company_ticker="TCO",
    )

    results = engine.run_catalog(
        [company_target, directory_target], companies={"TCO": "Test Company"},
    )
    company_result = next(r for r in results if r.target_id == "company_ir_tco")
    # Resolved via its own hint, not the (wrong) discovered directory link.
    assert company_result.resolved_domain.domain == "real-domain.example"


def test_sitemap_fallback_discovers_dataset_when_homepage_has_no_candidates():
    """The exact Zawya-class gap: a homepage is reachable and returns real
    content, but its own markup has no RSS/PDF/dataset/API-doc link -- the
    engine must still try the standards-based sitemap protocol (robots.txt's
    `Sitemap:` directive here) before giving up.
    """
    robots_txt = "User-agent: *\nDisallow: /private\nSitemap: https://testorg.com/my-sitemap.xml\n"
    sitemap_xml = (
        '<?xml version="1.0"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'
        "<url><loc>https://testorg.com/data/prices.csv</loc></url>"
        "<url><loc>https://testorg.com/about</loc></url>"
        "</urlset>"
    )
    pages = {
        "https://testorg.com": HOMEPAGE_WITH_NOTHING,
        "https://testorg.com/robots.txt": robots_txt,
        "https://testorg.com/my-sitemap.xml": sitemap_xml,
    }
    registry = SourceRegistry()
    engine = AcquisitionIntelligenceEngine(
        prober=reachable_prober({
            "https://testorg.com", "https://testorg.com/data/prices.csv", "https://testorg.com/about",
        }),
        fetch_text=lambda url: pages.get(url),
        robots_checker=lambda url: True,
        registry=registry,
    )
    result = engine.run_for_target(make_target(existing_source_id="testorg"))

    assert result.registered is True
    assert result.selected.candidate.discovered_url == "https://testorg.com/data/prices.csv"


def test_sitemap_index_is_followed_one_level():
    index_xml = (
        '<?xml version="1.0"?><sitemapindex xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'
        "<sitemap><loc>https://testorg.com/sitemap-data.xml</loc></sitemap>"
        "</sitemapindex>"
    )
    nested_xml = (
        '<?xml version="1.0"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'
        "<url><loc>https://testorg.com/data/prices.csv</loc></url>"
        "</urlset>"
    )
    pages = {
        "https://testorg.com": HOMEPAGE_WITH_NOTHING,
        "https://testorg.com/sitemap.xml": index_xml,
        "https://testorg.com/sitemap-data.xml": nested_xml,
    }
    registry = SourceRegistry()
    engine = AcquisitionIntelligenceEngine(
        prober=reachable_prober({"https://testorg.com", "https://testorg.com/data/prices.csv"}),
        fetch_text=lambda url: pages.get(url),
        robots_checker=lambda url: True,
        registry=registry,
    )
    result = engine.run_for_target(make_target(existing_source_id="testorg"))

    assert result.registered is True
    assert result.selected.candidate.discovered_url == "https://testorg.com/data/prices.csv"


def test_no_sitemap_available_still_reports_the_original_reason():
    registry = SourceRegistry()
    engine = AcquisitionIntelligenceEngine(
        prober=reachable_prober({"https://testorg.com"}),
        fetch_text=lambda url: HOMEPAGE_WITH_NOTHING if url == "https://testorg.com" else None,
        robots_checker=lambda url: True,
        registry=registry,
    )
    result = engine.run_for_target(make_target())
    assert result.registered is False
    assert "No acquisition-method candidates" in result.reason


def test_continuity_monitor_skips_per_constituent_targets():
    registry = SourceRegistry()
    engine = AcquisitionIntelligenceEngine(
        prober=reachable_prober(set()), fetch_text=lambda url: None, robots_checker=lambda url: True,
        registry=registry,
    )
    from agx_research.sources.spec import AccessMethod, SourceSpec

    registry.add(SourceSpec(
        id="company_ir", name="IR", category=SourceCategory.COMPANY,
        access_method=AccessMethod.PDF_DOWNLOAD, status=SourceStatus.PLANNED,
        health_status=HealthStatus.DOWN, reliability_score=0.5, freshness_score=0.5,
    ))
    target = make_target(id="company_ir", existing_source_id="company_ir", per_constituent=True)
    monitor = AcquisitionContinuityMonitor(engine, [target])
    assert monitor.check_and_recover(registry) == []
