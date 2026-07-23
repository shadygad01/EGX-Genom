import pytest

from agx_research.discovery.candidate import DiscoveryMethod, SourceCandidate
from agx_research.sources.qualification import apply_promotion, evaluate_promotion, register_candidate
from agx_research.sources.registry import SourceRegistry
from agx_research.sources.reputation import SourceMetricsRepository
from agx_research.sources.spec import (
    AccessMethod,
    HealthStatus,
    LifecycleState,
    SourceCategory,
    SourceSpec,
    SourceStatus,
)


def make_spec(**overrides) -> SourceSpec:
    defaults = dict(
        id="test_source",
        name="Test Source",
        category=SourceCategory.MARKET_DATA,
        access_method=AccessMethod.CSV_DOWNLOAD,
        status=SourceStatus.IMPLEMENTED,
        lifecycle_state=LifecycleState.CANDIDATE,
        reliability_score=0.8,
        freshness_score=0.9,
    )
    defaults.update(overrides)
    return SourceSpec(**defaults)


def test_no_run_history_stays_candidate():
    decision = evaluate_promotion(make_spec(), None)
    assert not decision.changed
    assert decision.recommended_stage == LifecycleState.CANDIDATE


def test_one_successful_run_promotes_to_quarantine():
    metrics_repo = SourceMetricsRepository()
    metrics = metrics_repo.record_run("test_source", succeeded=True, records_expected=1, records_produced=1)
    decision = evaluate_promotion(make_spec(), metrics)
    assert decision.recommended_stage == LifecycleState.QUARANTINE


def test_insufficient_runs_for_evaluation_stays_at_quarantine():
    metrics_repo = SourceMetricsRepository()
    metrics = metrics_repo.record_run("test_source", succeeded=True, records_expected=1, records_produced=1)
    decision = evaluate_promotion(
        make_spec(lifecycle_state=LifecycleState.QUARANTINE), metrics
    )
    assert not decision.changed


def test_five_runs_promotes_quarantine_to_evaluation():
    metrics_repo = SourceMetricsRepository()
    metrics = None
    for _ in range(5):
        metrics = metrics_repo.record_run(
            "test_source", succeeded=True, records_expected=1, records_produced=1,
            confidence_score=0.9, freshness_score=0.9, coverage_score=0.9,
        )
    decision = evaluate_promotion(make_spec(lifecycle_state=LifecycleState.QUARANTINE), metrics)
    assert decision.recommended_stage == LifecycleState.EVALUATION


def test_low_composite_blocks_trusted_promotion():
    metrics_repo = SourceMetricsRepository()
    metrics = None
    for _ in range(25):
        metrics = metrics_repo.record_run(
            "test_source", succeeded=True, records_expected=10, records_produced=1,
            confidence_score=0.2, freshness_score=0.2, coverage_score=0.1,
        )
    decision = evaluate_promotion(make_spec(lifecycle_state=LifecycleState.EVALUATION), metrics)
    assert not decision.changed
    assert "Composite reputation" in decision.reason


def test_high_composite_promotes_evaluation_to_trusted():
    metrics_repo = SourceMetricsRepository()
    metrics = None
    for _ in range(25):
        metrics = metrics_repo.record_run(
            "test_source", succeeded=True, records_expected=1, records_produced=1,
            confidence_score=0.95, freshness_score=0.95, coverage_score=1.0,
        )
    decision = evaluate_promotion(make_spec(lifecycle_state=LifecycleState.EVALUATION), metrics)
    assert decision.recommended_stage == LifecycleState.TRUSTED


def test_down_health_demotes_one_stage_regardless_of_history():
    metrics_repo = SourceMetricsRepository()
    metrics = None
    for _ in range(25):
        metrics = metrics_repo.record_run(
            "test_source", succeeded=True, records_expected=1, records_produced=1,
            confidence_score=0.95, freshness_score=0.95, coverage_score=1.0,
        )
    spec = make_spec(lifecycle_state=LifecycleState.TRUSTED, health_status=HealthStatus.DOWN)
    decision = evaluate_promotion(spec, metrics)
    assert decision.recommended_stage == LifecycleState.EVALUATION


def test_apply_promotion_persists_only_when_changed():
    registry = SourceRegistry()
    registry.add(make_spec())
    metrics_repo = SourceMetricsRepository()
    metrics = metrics_repo.record_run("test_source", succeeded=True, records_expected=1, records_produced=1)

    decision = evaluate_promotion(registry.latest("test_source"), metrics)
    updated = apply_promotion(registry, decision)
    assert updated is not None
    assert updated.lifecycle_state == LifecycleState.QUARANTINE
    assert updated.version == 2

    unchanged = apply_promotion(registry, evaluate_promotion(updated, None))
    # None history -> recommends CANDIDATE, which *is* a change from QUARANTINE
    assert unchanged is not None
    assert unchanged.lifecycle_state == LifecycleState.CANDIDATE


def test_register_candidate_always_starts_at_candidate_and_planned():
    registry = SourceRegistry()
    candidate = SourceCandidate(
        discovered_url="https://example.com/feed.xml",
        origin_page_url="https://example.com",
        discovery_method=DiscoveryMethod.RSS_AUTODISCOVERY,
        access_method_guess=AccessMethod.RSS_FEED,
        evidence="<link>",
    )
    spec = register_candidate(
        registry, candidate,
        source_id="example_feed", name="Example Feed", category=SourceCategory.NEWS,
    )
    assert spec.lifecycle_state == LifecycleState.CANDIDATE
    assert spec.status == SourceStatus.PLANNED
    assert spec.reliability_score < 0.5  # conservative unreviewed prior


def test_register_candidate_rejects_duplicate_id():
    registry = SourceRegistry()
    registry.add(make_spec(id="dup"))
    candidate = SourceCandidate(
        discovered_url="https://example.com/feed.xml",
        origin_page_url="https://example.com",
        discovery_method=DiscoveryMethod.RSS_AUTODISCOVERY,
        access_method_guess=AccessMethod.RSS_FEED,
    )
    with pytest.raises(ValueError):
        register_candidate(registry, candidate, source_id="dup", name="x", category=SourceCategory.NEWS)
