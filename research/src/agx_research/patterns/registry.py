"""The Pattern Registry: the persistent lifecycle store for every candidate
that made it far enough to be worth remembering.

Composes `storage.JsonFileRepository` exactly like every other versioned
entity in this codebase (`knowledge/store.py`, `genome/gene.py`) — a
transition never overwrites, it appends a new revision and moves
`validation_status`, so `history(pattern_id)` always reconstructs a
pattern's full lifecycle. A `REJECTED` pattern is never deleted (mission:
"a pattern must never silently disappear... rejected patterns should
remain available for research audit").
"""

from __future__ import annotations

from datetime import date, datetime
from enum import Enum
from pathlib import Path

from pydantic import BaseModel, Field

from agx_research.domain.provenance import Provenance
from agx_research.patterns.candidates import FeatureCondition, PatternCandidate
from agx_research.patterns.robustness import RobustnessResult
from agx_research.patterns.validation import WalkForwardResult
from agx_research.storage.repository import JsonFileRepository


class PatternStatus(str, Enum):
    DISCOVERED = "discovered"
    VALIDATING = "validating"
    VALIDATED = "validated"
    ACTIVE = "active"
    WEAKENING = "weakening"
    REJECTED = "rejected"
    RETIRED = "retired"


class Pattern(BaseModel):
    id: str
    version: int = 1
    definition: str
    ticker: str
    conditions: list[FeatureCondition] = Field(default_factory=list)
    regime_filter: FeatureCondition | None = None
    target_id: str
    horizon_days: int
    discovery_period: tuple[date, date]
    validation_period: tuple[date, date] | None = None
    holdout_period: tuple[date, date] | None = None
    holdout_sample_size: int = 0
    holdout_expectancy: float | None = None
    sample_size: int
    oos_sample_size: int
    expectancy: float
    median_outcome: float
    hit_rate: float
    mfe: float | None = None
    mae: float | None = None
    max_drawdown: float | None = None
    stability: float | None = None
    complexity: int
    regime_dependency: str | None = None
    number_of_tests: int
    is_lead_lag: bool = False
    family_size: int = 1
    family_corrected_p_value: float | None = None
    block_bootstrap_p_value: float | None = None
    deflated_sharpe_ratio: float | None = None
    validation_status: PatternStatus
    confidence: float | None = None
    created_at: datetime = Field(default_factory=datetime.now)
    last_validated_at: datetime | None = None
    rejection_reason: str | None = None
    robustness_passed: bool | None = None
    provenance: Provenance


class PatternRegistry(JsonFileRepository[Pattern]):
    def __init__(self, persist_path: Path | str | None = None):
        super().__init__(Pattern, persist_path)

    def by_status(self, status: PatternStatus) -> list[Pattern]:
        return [p for p in self.all_latest() if p.validation_status == status]

    def transition(
        self,
        pattern_id: str,
        new_status: PatternStatus,
        *,
        reason: str | None = None,
        validated_at: datetime | None = None,
    ) -> Pattern:
        current = self.latest(pattern_id)
        if current is None:
            raise KeyError(f"No pattern {pattern_id!r} in registry")
        updated = current.model_copy(
            update={
                "version": current.version + 1,
                "validation_status": new_status,
                "rejection_reason": reason if new_status is PatternStatus.REJECTED else current.rejection_reason,
                "last_validated_at": validated_at or current.last_validated_at,
            }
        )
        return self.add(updated)


def build_pattern(
    *,
    pattern_id: str,
    candidate: PatternCandidate,
    horizon_days: int,
    walk_forward: WalkForwardResult,
    robustness: RobustnessResult | None,
    discovery_period: tuple[date, date],
    validation_period: tuple[date, date] | None,
    number_of_tests: int,
    status: PatternStatus,
    produced_by: str,
    rejection_reason: str | None = None,
    holdout_period: tuple[date, date] | None = None,
    holdout_sample_size: int = 0,
    holdout_expectancy: float | None = None,
    family_size: int = 1,
    family_corrected_p_value: float | None = None,
    block_bootstrap_p_value: float | None = None,
    deflated_sharpe_ratio: float | None = None,
) -> Pattern:
    """Assembles a `Pattern` from one pipeline run's outputs — the sole
    factory `engine.py` uses, so every field's provenance is traceable to
    exactly the objects that produced it (walk-forward result, robustness
    result, the candidate itself) rather than re-derived ad hoc."""
    distribution = walk_forward.oos_distribution or walk_forward.discovery_distribution
    confidence = None
    if distribution is not None and distribution.p_value_bootstrap is not None:
        confidence = max(0.0, 1.0 - distribution.p_value_bootstrap)

    return Pattern(
        id=pattern_id,
        definition=candidate.definition(),
        ticker=candidate.ticker,
        conditions=candidate.conditions,
        regime_filter=candidate.regime_filter,
        target_id=candidate.target_id,
        horizon_days=horizon_days,
        discovery_period=discovery_period,
        validation_period=validation_period,
        holdout_period=holdout_period,
        holdout_sample_size=holdout_sample_size,
        holdout_expectancy=holdout_expectancy,
        sample_size=(walk_forward.discovery_distribution.sample_count if walk_forward.discovery_distribution else 0),
        oos_sample_size=walk_forward.oos_sample_size,
        expectancy=distribution.expectancy if distribution else 0.0,
        median_outcome=distribution.median_outcome if distribution else 0.0,
        hit_rate=distribution.hit_rate if distribution else 0.0,
        mfe=distribution.mfe_mean if distribution else None,
        mae=distribution.mae_mean if distribution else None,
        max_drawdown=distribution.max_drawdown_mean if distribution else None,
        stability=distribution.stability_score if distribution else None,
        complexity=candidate.complexity,
        regime_dependency=(candidate.regime_filter.describe() if candidate.regime_filter else None),
        number_of_tests=number_of_tests,
        is_lead_lag=candidate.is_lead_lag,
        family_size=family_size,
        family_corrected_p_value=family_corrected_p_value,
        block_bootstrap_p_value=block_bootstrap_p_value,
        deflated_sharpe_ratio=deflated_sharpe_ratio,
        validation_status=status,
        confidence=confidence,
        rejection_reason=rejection_reason,
        robustness_passed=robustness.passed if robustness else None,
        provenance=Provenance(
            produced_by=produced_by,
            produced_at=datetime.now(),
            inputs=[],
        ),
    )


__all__ = ["Pattern", "PatternRegistry", "PatternStatus", "build_pattern"]
