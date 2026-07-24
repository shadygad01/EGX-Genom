"""Source Health Monitoring: detect operational failure modes automatically
and produce alerts, per `docs/DATA_ACQUISITION.md`'s program scope (layout
changes, RSS/API failures, schema drift, auth failures, broken parsers,
missing files, expired certs).

`HealthMonitor.evaluate_run` is called once per collection attempt (wired
from `collectors.service.CollectionService`) with the concrete signals that
run already produced -- it invents nothing: a "layout change" alert only
fires when a *previously producing* source suddenly parses zero records
(the actual, measurable symptom of a layout change), never a guess about
*why*. Alerts are append-only (`HealthAlertRepository`); nothing is
overwritten, so the alert history is itself an audit trail.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from pathlib import Path

from pydantic import BaseModel, Field

from agx_research.domain.identifiers import new_id
from agx_research.sources.reputation import SourceMetrics
from agx_research.sources.spec import HealthStatus
from agx_research.storage.repository import JsonFileRepository


class AlertKind(str, Enum):
    FETCH_FAILURE = "fetch_failure"
    AUTH_FAILURE = "auth_failure"
    SCHEMA_DRIFT = "schema_drift"
    LAYOUT_CHANGE = "layout_change"  # previously-producing source now parses zero records
    ZERO_YIELD = "zero_yield"  # fetch succeeded but parsing produced zero usable records
    STALENESS = "staleness"
    MISSING_FILE = "missing_file"
    ROBOTS_DISALLOWED = "robots_disallowed"
    PARSER_BROKEN = "parser_broken"  # parse raised or every record failed validation
    CONSECUTIVE_FAILURES = "consecutive_failures"


class AlertSeverity(str, Enum):
    WARNING = "warning"
    CRITICAL = "critical"


class HealthAlert(BaseModel):
    id: str
    version: int = 1
    source_id: str
    kind: AlertKind
    severity: AlertSeverity
    detected_at: datetime = Field(default_factory=datetime.now)
    message: str
    resolved_at: datetime | None = None


class HealthAlertRepository(JsonFileRepository[HealthAlert]):
    def __init__(self, persist_path: Path | str | None = None):
        super().__init__(HealthAlert, persist_path)

    def open_alerts(self, source_id: str) -> list[HealthAlert]:
        return [
            a
            for a in self.all_latest()
            if a.source_id == source_id and a.resolved_at is None
        ]

    def resolve(self, alert_id: str) -> HealthAlert:
        current = self.latest(alert_id)
        if current is None:
            raise KeyError(f"No alert with id {alert_id}")
        return self.add(
            current.model_copy(update={"version": current.version + 1, "resolved_at": datetime.now()})
        )


# Thresholds are declared policy, documented and adjustable -- not derived
# from any calibration study (none exists yet; see docs/TECHNICAL_DEBT.md).
_DOWN_AFTER_CONSECUTIVE_FAILURES = 3
_DEGRADED_AFTER_CONSECUTIVE_FAILURES = 1
_STALENESS_FLOOR = 0.3


class HealthMonitor:
    def __init__(self, alerts: HealthAlertRepository | None = None):
        self.alerts = alerts or HealthAlertRepository()

    def evaluate_run(
        self,
        source_id: str,
        metrics: SourceMetrics,
        *,
        fetch_succeeded: bool,
        fetch_error: str | None = None,
        auth_error: bool = False,
        robots_disallowed: bool = False,
        parser_raised: bool = False,
        records_produced: int = 0,
        had_produced_before: bool = False,
        freshness_score: float | None = None,
        schema_version_changed: bool = False,
        file_missing: bool = False,
    ) -> tuple[HealthStatus, list[HealthAlert]]:
        """`metrics` must already reflect this run (call after
        `SourceMetricsRepository.record_run`) so `consecutive_failures`
        reads the post-run count.
        """
        new_alerts: list[HealthAlert] = []

        def alert(kind: AlertKind, severity: AlertSeverity, message: str) -> None:
            new_alerts.append(
                HealthAlert(
                    id=new_id("healthalert"), source_id=source_id, kind=kind,
                    severity=severity, message=message,
                )
            )

        if file_missing:
            alert(AlertKind.MISSING_FILE, AlertSeverity.CRITICAL, "Expected artifact not found.")
        if robots_disallowed:
            alert(AlertKind.ROBOTS_DISALLOWED, AlertSeverity.WARNING, "robots.txt disallows fetch.")
        if auth_error:
            alert(AlertKind.AUTH_FAILURE, AlertSeverity.CRITICAL, "Authentication failed.")
        elif not fetch_succeeded:
            alert(
                AlertKind.FETCH_FAILURE, AlertSeverity.WARNING,
                fetch_error or "Fetch failed.",
            )
        if parser_raised:
            alert(AlertKind.PARSER_BROKEN, AlertSeverity.CRITICAL, "Parser raised on a fetched document.")
        elif fetch_succeeded and records_produced == 0 and had_produced_before:
            alert(
                AlertKind.LAYOUT_CHANGE, AlertSeverity.WARNING,
                "Source previously produced records; this run's parse produced none "
                "(possible layout/schema change).",
            )
        elif fetch_succeeded and records_produced == 0:
            # Connection succeeded (HTTP-level) but parsing produced zero usable
            # records -- e.g. an anti-bot challenge page, a wrong endpoint, or an
            # unexpected format. Unlike LAYOUT_CHANGE this fires even with no
            # prior successful run, so a source's very first live attempt can
            # never be silently reported HEALTHY on zero yield (a real gap this
            # closes: the previous `had_produced_before` gate meant a source's
            # first-ever run producing zero records raised no alert at all).
            alert(
                AlertKind.ZERO_YIELD, AlertSeverity.WARNING,
                "Fetch succeeded (HTTP-level) but parsing produced zero usable "
                "records this run.",
            )
        if schema_version_changed:
            alert(AlertKind.SCHEMA_DRIFT, AlertSeverity.WARNING, "Declared schema_version changed.")
        if freshness_score is not None and freshness_score < _STALENESS_FLOOR:
            alert(
                AlertKind.STALENESS, AlertSeverity.WARNING,
                f"Freshness score {freshness_score:.2f} below floor {_STALENESS_FLOOR}.",
            )
        if metrics.consecutive_failures >= _DOWN_AFTER_CONSECUTIVE_FAILURES:
            alert(
                AlertKind.CONSECUTIVE_FAILURES, AlertSeverity.CRITICAL,
                f"{metrics.consecutive_failures} consecutive failed runs.",
            )

        for a in new_alerts:
            self.alerts.add(a)

        health = self._derive_health(metrics, new_alerts)
        return health, new_alerts

    @staticmethod
    def _derive_health(metrics: SourceMetrics, new_alerts: list[HealthAlert]) -> HealthStatus:
        if metrics.consecutive_failures >= _DOWN_AFTER_CONSECUTIVE_FAILURES:
            return HealthStatus.DOWN
        if metrics.consecutive_failures >= _DEGRADED_AFTER_CONSECUTIVE_FAILURES or any(
            a.severity == AlertSeverity.CRITICAL for a in new_alerts
        ):
            return HealthStatus.DEGRADED
        if new_alerts:
            return HealthStatus.DEGRADED
        return HealthStatus.HEALTHY
