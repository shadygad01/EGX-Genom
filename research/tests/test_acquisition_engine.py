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
