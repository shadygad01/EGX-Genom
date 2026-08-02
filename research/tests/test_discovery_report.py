"""Discovery workflow support: `plan_discovery_targets`/`run_discovery_report`
scope which sources are even eligible, and the incremental cache (TTL,
input-fingerprint drift, force) around real (fake-backed) discovery runs.
"""

from datetime import datetime, timedelta

from agx_research.acquisition_intelligence.discovery_report import (
    DiscoveryHistoryRepository,
    build_discovery_metrics,
    plan_discovery_targets,
    run_discovery_report,
)
from agx_research.acquisition_intelligence.domain_resolution import ProbeResult
from agx_research.acquisition_intelligence.engine import AcquisitionIntelligenceEngine
from agx_research.acquisition_intelligence.target import TargetOrganization
from agx_research.sources.registry import SourceRegistry
from agx_research.sources.spec import AccessMethod, SourceCategory, SourceSpec, SourceStatus

HOMEPAGE_WITH_RSS = """
<html><head>
<link rel="alternate" type="application/rss+xml" title="News" href="/feed.xml">
</head><body>hello</body></html>
"""

HOMEPAGE_WITH_NOTHING = "<html><body>nothing here</body></html>"


def make_spec(**overrides) -> SourceSpec:
    defaults = dict(
        id="testorg", name="Test Org", category=SourceCategory.NEWS,
        access_method=AccessMethod.RSS_FEED, status=SourceStatus.PLANNED,
        reliability_score=0.6, freshness_score=0.9,
    )
    defaults.update(overrides)
    return SourceSpec(**defaults)


def make_target(**overrides) -> TargetOrganization:
    defaults = dict(
        id="testorg", name="Test Org", category=SourceCategory.NEWS,
        domain_hints=["testorg.com"], existing_source_id="testorg",
    )
    defaults.update(overrides)
    return TargetOrganization(**defaults)


class FakeWayback:
    def __init__(self, *, cdx=None):
        self.cdx = cdx or [["timestamp"], ["20200101000000"], ["20250101000000"]]

    def check_availability(self, url):
        return {"archived_snapshots": {}}

    def cdx_snapshots(self, url):
        return self.cdx


class CountingProber:
    """Wraps a reachable-url set so tests can assert how many times the
    engine actually touched the network -- what proves the cache skipped a
    real re-probe rather than merely returning the same answer by luck.
    """

    def __init__(self, reachable_urls: set[str]):
        self.reachable_urls = reachable_urls
        self.calls = 0

    def __call__(self, url):
        self.calls += 1
        return ProbeResult(url=url, reachable=url in self.reachable_urls, status_code=200 if url in self.reachable_urls else None)


def make_engine(registry, *, reachable_urls, page_text=HOMEPAGE_WITH_RSS, prober=None):
    prober = prober or CountingProber(reachable_urls)
    engine = AcquisitionIntelligenceEngine(
        prober=prober,
        fetch_text=lambda url: page_text,
        robots_checker=lambda url: True,
        registry=registry,
        wayback=FakeWayback(),
    )
    return engine, prober


def test_plan_discovery_targets_scopes_out_integrated_and_per_constituent_sources():
    registry = SourceRegistry()
    registry.add(make_spec(id="targeted", status=SourceStatus.PLANNED))
    registry.add(make_spec(id="untargeted", status=SourceStatus.PLANNED))
    registry.add(make_spec(id="leg", status=SourceStatus.PLANNED, integrated_via="composite"))
    registry.add(make_spec(id="already_live", status=SourceStatus.IMPLEMENTED))

    targets = [
        make_target(id="targeted", existing_source_id="targeted"),
        make_target(id="marker", existing_source_id="marker_source", per_constituent=True),
    ]

    targeted, untargeted = plan_discovery_targets(registry, targets)

    assert [spec.id for spec, _ in targeted] == ["targeted"]
    assert [spec.id for spec in untargeted] == ["untargeted"]


def test_run_discovery_report_verifies_a_reachable_rss_target():
    registry = SourceRegistry()
    registry.add(make_spec())
    engine, prober = make_engine(
        registry, reachable_urls={"https://testorg.com", "https://testorg.com/feed.xml"}
    )
    history = DiscoveryHistoryRepository()

    outcomes, candidates = run_discovery_report(engine, registry, [make_target()], history)

    assert len(outcomes) == 1
    outcome = outcomes[0]
    assert outcome.verification_result == "verified_reachable"
    assert outcome.discovered_endpoints == ["https://testorg.com/feed.xml"]
    assert outcome.confidence > 0
    assert "RssNewsCollector" in outcome.recommendation
    assert outcome.from_cache is False
    assert any(c.selected for c in candidates)


def test_run_discovery_report_never_claims_verified_when_the_candidate_url_itself_failed_every_probe():
    # Reproduces the real skynews_arabia_economy incident: the homepage
    # resolves and a candidate feed URL is discovered on it (so a candidate
    # exists and gets selected -- ranking a candidate above no candidate is
    # deliberate, see ranking.py), but the discovered feed URL itself never
    # returned a successful probe. Before this fix, this outcome was still
    # labelled "verified_reachable" with a "flip to IMPLEMENTED" recommendation
    # -- which is exactly how that source was wrongly promoted and then failed
    # with a real HTTP 404 in production.
    registry = SourceRegistry()
    registry.add(make_spec())
    engine, prober = make_engine(registry, reachable_urls={"https://testorg.com"})
    history = DiscoveryHistoryRepository()

    outcomes, candidates = run_discovery_report(engine, registry, [make_target()], history)

    assert len(outcomes) == 1
    outcome = outcomes[0]
    assert outcome.verification_result == "candidate_selected_unconfirmed"
    assert "No successful probe" in " ".join(outcome.evidence)
    assert "Do not flip to IMPLEMENTED" in outcome.recommendation
    assert any(c.selected for c in candidates)


def test_run_discovery_report_reports_untargeted_source_without_fabricating():
    registry = SourceRegistry()
    registry.add(make_spec(id="no_target_source"))
    engine, _ = make_engine(registry, reachable_urls=set())
    history = DiscoveryHistoryRepository()

    outcomes, candidates = run_discovery_report(engine, registry, [], history)

    assert len(outcomes) == 1
    assert outcomes[0].verification_result == "not_targeted"
    assert outcomes[0].discovered_endpoints == []
    assert candidates == []


def test_run_discovery_report_reports_unreachable_domain_honestly():
    registry = SourceRegistry()
    registry.add(make_spec())
    engine, prober = make_engine(registry, reachable_urls=set())  # nothing reachable
    history = DiscoveryHistoryRepository()

    outcomes, _ = run_discovery_report(engine, registry, [make_target()], history)

    assert outcomes[0].verification_result == "no_reachable_domain"
    assert outcomes[0].confidence == 0.0
    assert prober.calls > 0  # a real probe was attempted, nothing assumed


def test_second_run_within_ttl_serves_cached_result_without_reprobing():
    registry = SourceRegistry()
    registry.add(make_spec())
    engine, prober = make_engine(
        registry, reachable_urls={"https://testorg.com", "https://testorg.com/feed.xml"}
    )
    history = DiscoveryHistoryRepository()
    now = datetime(2026, 1, 1)

    run_discovery_report(engine, registry, [make_target()], history, ttl_days=30, now=now)
    calls_after_first_run = prober.calls

    outcomes, _ = run_discovery_report(
        engine, registry, [make_target()], history, ttl_days=30, now=now + timedelta(days=5),
    )

    assert prober.calls == calls_after_first_run  # no new probe issued
    assert outcomes[0].from_cache is True
    assert outcomes[0].verification_result == "verified_reachable"


def test_ttl_expiry_forces_a_fresh_reprobe():
    registry = SourceRegistry()
    registry.add(make_spec())
    engine, prober = make_engine(
        registry, reachable_urls={"https://testorg.com", "https://testorg.com/feed.xml"}
    )
    history = DiscoveryHistoryRepository()
    now = datetime(2026, 1, 1)

    run_discovery_report(engine, registry, [make_target()], history, ttl_days=7, now=now)
    calls_after_first_run = prober.calls

    outcomes, _ = run_discovery_report(
        engine, registry, [make_target()], history, ttl_days=7, now=now + timedelta(days=8),
    )

    assert prober.calls > calls_after_first_run
    assert outcomes[0].from_cache is False


def test_changed_domain_hints_force_a_fresh_reprobe_even_within_ttl():
    registry = SourceRegistry()
    registry.add(make_spec())
    engine, prober = make_engine(
        registry, reachable_urls={"https://testorg.com", "https://testorg.com/feed.xml"}
    )
    history = DiscoveryHistoryRepository()
    now = datetime(2026, 1, 1)

    run_discovery_report(engine, registry, [make_target()], history, ttl_days=30, now=now)
    calls_after_first_run = prober.calls

    changed_target = make_target(domain_hints=["testorg.com", "testorg.net"])
    outcomes, _ = run_discovery_report(
        engine, registry, [changed_target], history, ttl_days=30, now=now + timedelta(days=1),
    )

    assert prober.calls > calls_after_first_run
    assert outcomes[0].from_cache is False


def test_force_ids_bypasses_a_still_fresh_cache():
    registry = SourceRegistry()
    registry.add(make_spec())
    engine, prober = make_engine(
        registry, reachable_urls={"https://testorg.com", "https://testorg.com/feed.xml"}
    )
    history = DiscoveryHistoryRepository()
    now = datetime(2026, 1, 1)

    run_discovery_report(engine, registry, [make_target()], history, ttl_days=30, now=now)
    calls_after_first_run = prober.calls

    outcomes, _ = run_discovery_report(
        engine, registry, [make_target()], history, ttl_days=30,
        now=now + timedelta(days=1), force_ids={"testorg"},
    )

    assert prober.calls > calls_after_first_run
    assert outcomes[0].from_cache is False


def test_build_discovery_metrics_aggregates_counts():
    registry = SourceRegistry()
    registry.add(make_spec(id="reachable"))
    registry.add(make_spec(id="unreachable"))
    engine, _ = make_engine(
        registry, reachable_urls={"https://testorg.com", "https://testorg.com/feed.xml"}
    )
    history = DiscoveryHistoryRepository()
    started = datetime(2026, 1, 1, 12, 0, 0)

    outcomes, _ = run_discovery_report(
        engine, registry,
        [
            make_target(id="reachable", existing_source_id="reachable"),
            make_target(id="unreachable", existing_source_id="unreachable", domain_hints=["nope.invalid"]),
        ],
        history, now=started,
    )
    metrics = build_discovery_metrics(outcomes, started_at=started, finished_at=started + timedelta(seconds=5))

    assert metrics["sources_in_report"] == 2
    assert metrics["sources_verified_reachable"] == 1
    assert metrics["by_verification_result"]["verified_reachable"] == 1
    assert metrics["duration_seconds"] == 5.0
