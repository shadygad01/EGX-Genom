from agx_research.sources.health import AlertKind, HealthAlertRepository, HealthMonitor
from agx_research.sources.reputation import SourceMetricsRepository
from agx_research.sources.spec import HealthStatus


def _metrics_after_failures(n: int):
    repo = SourceMetricsRepository()
    metrics = None
    for _ in range(n):
        metrics = repo.record_run("x", succeeded=False, records_expected=1, records_produced=0)
    return metrics


def test_single_failure_is_degraded_not_down():
    monitor = HealthMonitor(HealthAlertRepository())
    metrics = _metrics_after_failures(1)
    status, alerts = monitor.evaluate_run("x", metrics, fetch_succeeded=False)
    assert status == HealthStatus.DEGRADED
    assert any(a.kind == AlertKind.FETCH_FAILURE for a in alerts)


def test_three_consecutive_failures_is_down():
    monitor = HealthMonitor(HealthAlertRepository())
    metrics = _metrics_after_failures(3)
    status, alerts = monitor.evaluate_run("x", metrics, fetch_succeeded=False)
    assert status == HealthStatus.DOWN
    assert any(a.kind == AlertKind.CONSECUTIVE_FAILURES for a in alerts)


def test_healthy_run_produces_no_alerts():
    repo = SourceMetricsRepository()
    metrics = repo.record_run("x", succeeded=True, records_expected=1, records_produced=1)
    monitor = HealthMonitor(HealthAlertRepository())
    status, alerts = monitor.evaluate_run(
        "x", metrics, fetch_succeeded=True, records_produced=1, freshness_score=0.9
    )
    assert status == HealthStatus.HEALTHY
    assert alerts == []


def test_previously_producing_source_going_to_zero_records_flags_layout_change():
    repo = SourceMetricsRepository()
    metrics = repo.record_run("x", succeeded=True, records_expected=1, records_produced=1)
    monitor = HealthMonitor(HealthAlertRepository())
    status, alerts = monitor.evaluate_run(
        "x", metrics, fetch_succeeded=True, records_produced=0, had_produced_before=True,
    )
    assert any(a.kind == AlertKind.LAYOUT_CHANGE for a in alerts)


def test_parser_raised_is_critical_and_degrades():
    repo = SourceMetricsRepository()
    metrics = repo.record_run("x", succeeded=True, records_expected=1, records_produced=0)
    monitor = HealthMonitor(HealthAlertRepository())
    status, alerts = monitor.evaluate_run("x", metrics, fetch_succeeded=True, parser_raised=True)
    assert any(a.kind == AlertKind.PARSER_BROKEN for a in alerts)
    assert status == HealthStatus.DEGRADED


def test_staleness_below_floor_flags_alert():
    repo = SourceMetricsRepository()
    metrics = repo.record_run("x", succeeded=True, records_expected=1, records_produced=1)
    monitor = HealthMonitor(HealthAlertRepository())
    _, alerts = monitor.evaluate_run(
        "x", metrics, fetch_succeeded=True, records_produced=1, freshness_score=0.1,
    )
    assert any(a.kind == AlertKind.STALENESS for a in alerts)


def test_alerts_are_persisted_and_resolvable():
    alerts_repo = HealthAlertRepository()
    monitor = HealthMonitor(alerts_repo)
    metrics = _metrics_after_failures(1)
    monitor.evaluate_run("x", metrics, fetch_succeeded=False)

    open_alerts = alerts_repo.open_alerts("x")
    assert len(open_alerts) >= 1
    resolved = alerts_repo.resolve(open_alerts[0].id)
    assert resolved.resolved_at is not None
    assert alerts_repo.open_alerts("x") == [a for a in open_alerts if a.id != resolved.id]
