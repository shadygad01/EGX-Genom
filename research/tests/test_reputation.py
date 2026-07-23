from agx_research.sources.reputation import SourceMetricsRepository, compute_reputation


def test_record_run_accumulates_counters_across_versions():
    repo = SourceMetricsRepository()
    repo.record_run("x", succeeded=True, records_expected=10, records_produced=8)
    metrics = repo.record_run("x", succeeded=True, records_expected=10, records_produced=9)

    assert metrics.version == 2
    assert metrics.runs_total == 2
    assert metrics.runs_succeeded == 2
    assert metrics.records_produced_total == 17


def test_consecutive_failures_reset_on_success():
    repo = SourceMetricsRepository()
    repo.record_run("x", succeeded=False, records_expected=1, records_produced=0)
    repo.record_run("x", succeeded=False, records_expected=1, records_produced=0)
    metrics = repo.record_run("x", succeeded=True, records_expected=1, records_produced=1)
    assert metrics.consecutive_failures == 0
    assert metrics.consecutive_successes == 1

    metrics = repo.record_run("x", succeeded=False, records_expected=1, records_produced=0)
    assert metrics.consecutive_failures == 1
    assert metrics.consecutive_successes == 0


def test_no_observations_yields_no_composite_never_a_fabricated_default():
    metrics = SourceMetricsRepository().latest("nonexistent")
    assert metrics is None


def test_compute_reputation_no_runs_is_all_none():
    from agx_research.sources.reputation import SourceMetrics

    score = compute_reputation(SourceMetrics(id="x"))
    assert score.composite is None
    assert score.observations == 0


def test_compute_reputation_composite_uses_only_measured_dimensions():
    repo = SourceMetricsRepository()
    metrics = repo.record_run(
        "x", succeeded=True, records_expected=10, records_produced=10,
        confidence_score=0.9, freshness_score=1.0, coverage_score=1.0,
    )
    score = compute_reputation(metrics)
    assert score.accuracy == 0.9
    assert score.freshness == 1.0
    assert score.coverage == 1.0
    assert score.latency is None  # never measured -- excluded, not defaulted
    assert score.composite is not None


def test_schema_change_after_first_sighting_is_tracked():
    repo = SourceMetricsRepository()
    repo.record_run("x", succeeded=True, records_expected=1, records_produced=1, schema_version="1.0")
    metrics = repo.record_run(
        "x", succeeded=True, records_expected=1, records_produced=1, schema_version="2.0"
    )
    assert metrics.schema_changes_total == 1
    assert metrics.schema_versions_seen == ["1.0", "2.0"]


def test_corroboration_feeds_duplicate_rate():
    repo = SourceMetricsRepository()
    metrics = repo.record_run(
        "x", succeeded=True, records_expected=1, records_produced=1,
        corroborated_candidates=1, new_candidates=1,
    )
    score = compute_reputation(metrics)
    assert score.duplicate_rate == 0.5
