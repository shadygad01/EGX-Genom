"""Source Reputation Engine: continuous, mechanical measurement of how much
the platform should trust a source, replacing declared priors with earned
history exactly as `docs/DATA_ACQUISITION.md` promises for `data_quality_score`.

`SourceMetrics` is a plain, versioned counter accumulator (one per source,
stored through the same `JsonFileRepository` every other store uses) — no
judgment lives in it. `compute_reputation()` is the pure function that turns
those counters into the charter's nine named dimensions (availability,
accuracy, freshness, coverage, latency, correction rate, duplicate rate,
schema stability, historical usefulness) plus a composite score. A dimension
with no observations yet is `None` — the same "never fabricate a measurement"
rule `collectors.quality.assess_quality` already follows for
`consistency_score` — and is excluded from the composite mean rather than
defaulted to some assumed value.

This closes `docs/TECHNICAL_DEBT.md` #13: `SourceRegistry.record_measured_quality`
existed with nothing calling it. `CollectionService` now records a
`SourceMetrics` update on every run and writes the resulting reputation score
back via `record_measured_quality` + `SourceRegistry.reputation_score`.
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

from pydantic import BaseModel, Field

from agx_research.storage.repository import JsonFileRepository


class SourceMetrics(BaseModel):
    """Raw, versioned counters for one source. Never edited in place —
    `record_run` always appends the next version via the repository.
    """

    id: str  # == source_id
    version: int = 1
    runs_total: int = 0
    runs_succeeded: int = 0
    records_expected_total: int = 0
    records_produced_total: int = 0
    confidence_sum: float = 0.0
    confidence_count: int = 0
    freshness_sum: float = 0.0
    freshness_count: int = 0
    coverage_sum: float = 0.0
    coverage_count: int = 0
    latency_seconds_sum: float = 0.0
    latency_count: int = 0
    materialized_total: int = 0
    withheld_total: int = 0
    corroborated_candidates_total: int = 0  # candidates matching an existing event (version > 1)
    new_candidates_total: int = 0
    corrections_total: int = 0  # EventPlatform.supersede() calls traced to this source
    schema_changes_total: int = 0  # distinct schema_version values ever observed
    schema_versions_seen: list[str] = Field(default_factory=list)
    consecutive_failures: int = 0  # resets to 0 on any success; drives health.py's DOWN detection
    consecutive_successes: int = 0
    first_run_at: datetime | None = None
    last_run_at: datetime | None = None


class SourceMetricsRepository(JsonFileRepository[SourceMetrics]):
    def __init__(self, persist_path: Path | str | None = None):
        super().__init__(SourceMetrics, persist_path)

    def record_run(
        self,
        source_id: str,
        *,
        succeeded: bool,
        records_expected: int,
        records_produced: int,
        confidence_score: float | None = None,
        freshness_score: float | None = None,
        coverage_score: float | None = None,
        latency_seconds: float | None = None,
        materialized: bool = False,
        corroborated_candidates: int = 0,
        new_candidates: int = 0,
        corrections: int = 0,
        schema_version: str | None = None,
        occurred_at: datetime | None = None,
    ) -> SourceMetrics:
        occurred_at = occurred_at or datetime.now()
        existing = self.latest(source_id)
        current = existing or SourceMetrics(id=source_id)
        updates: dict = {
            "version": current.version + 1 if existing else 1,
            "runs_total": current.runs_total + 1,
            "runs_succeeded": current.runs_succeeded + (1 if succeeded else 0),
            "records_expected_total": current.records_expected_total + records_expected,
            "records_produced_total": current.records_produced_total + records_produced,
            "materialized_total": current.materialized_total + (1 if materialized else 0),
            "withheld_total": current.withheld_total + (0 if materialized else 1),
            "corroborated_candidates_total": (
                current.corroborated_candidates_total + corroborated_candidates
            ),
            "new_candidates_total": current.new_candidates_total + new_candidates,
            "corrections_total": current.corrections_total + corrections,
            "consecutive_failures": 0 if succeeded else current.consecutive_failures + 1,
            "consecutive_successes": current.consecutive_successes + 1 if succeeded else 0,
            "first_run_at": current.first_run_at or occurred_at,
            "last_run_at": occurred_at,
        }
        if confidence_score is not None:
            updates["confidence_sum"] = current.confidence_sum + confidence_score
            updates["confidence_count"] = current.confidence_count + 1
        if freshness_score is not None:
            updates["freshness_sum"] = current.freshness_sum + freshness_score
            updates["freshness_count"] = current.freshness_count + 1
        if coverage_score is not None:
            updates["coverage_sum"] = current.coverage_sum + coverage_score
            updates["coverage_count"] = current.coverage_count + 1
        if latency_seconds is not None:
            updates["latency_seconds_sum"] = current.latency_seconds_sum + latency_seconds
            updates["latency_count"] = current.latency_count + 1
        if schema_version is not None and schema_version not in current.schema_versions_seen:
            updates["schema_versions_seen"] = [*current.schema_versions_seen, schema_version]
            updates["schema_changes_total"] = current.schema_changes_total + (
                1 if current.schema_versions_seen else 0  # first sighting isn't a "change"
            )

        return self.add(current.model_copy(update=updates))


class ReputationScore(BaseModel):
    availability: float | None = None
    accuracy: float | None = None
    freshness: float | None = None
    coverage: float | None = None
    latency: float | None = None
    correction_rate: float | None = None  # already inverted: 1.0 = no corrections
    duplicate_rate: float | None = None  # already inverted: 1.0 = no duplicates observed
    schema_stability: float | None = None
    historical_usefulness: float | None = None
    composite: float | None = None
    observations: int = 0


_LATENCY_TARGET_SECONDS = 5.0  # a fetch at or under this is full latency credit


def _latency_score(average_latency: float) -> float:
    if average_latency <= _LATENCY_TARGET_SECONDS:
        return 1.0
    # decays toward 0 as latency grows to 10x the target; documented, not arbitrary
    return max(0.0, 1.0 - (average_latency - _LATENCY_TARGET_SECONDS) / (9 * _LATENCY_TARGET_SECONDS))


def compute_reputation(metrics: SourceMetrics) -> ReputationScore:
    score = ReputationScore()

    if metrics.runs_total > 0:
        score.availability = metrics.runs_succeeded / metrics.runs_total
        score.historical_usefulness = metrics.materialized_total / metrics.runs_total
        score.correction_rate = max(0.0, 1.0 - metrics.corrections_total / metrics.runs_total)
        score.schema_stability = max(
            0.0, 1.0 - metrics.schema_changes_total / metrics.runs_total
        )
    if metrics.confidence_count > 0:
        score.accuracy = metrics.confidence_sum / metrics.confidence_count
    if metrics.freshness_count > 0:
        score.freshness = metrics.freshness_sum / metrics.freshness_count
    if metrics.coverage_count > 0:
        score.coverage = metrics.coverage_sum / metrics.coverage_count
    if metrics.latency_count > 0:
        score.latency = _latency_score(metrics.latency_seconds_sum / metrics.latency_count)
    total_candidates = metrics.corroborated_candidates_total + metrics.new_candidates_total
    if total_candidates > 0:
        score.duplicate_rate = max(
            0.0, 1.0 - metrics.corroborated_candidates_total / total_candidates
        )

    measured = [
        v
        for v in (
            score.availability,
            score.accuracy,
            score.freshness,
            score.coverage,
            score.latency,
            score.correction_rate,
            score.duplicate_rate,
            score.schema_stability,
            score.historical_usefulness,
        )
        if v is not None
    ]
    score.observations = len(measured)
    score.composite = sum(measured) / len(measured) if measured else None
    return score
