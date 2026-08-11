"""Live pattern activation: evaluates every `VALIDATED`/`ACTIVE` pattern
against today's features and reports which ones currently match.

The output is deliberately never a BUY/SELL recommendation (mission
section 12) — every `PatternActivation` uses the vocabulary the mission
specifies (`ACTIVE_PATTERN`, `HISTORICAL EXPECTANCY`, `CONFIDENCE`,
`CURRENT MATCH`, `REGIME COMPATIBILITY`, `EVIDENCE`) and nothing else. A
pattern whose conditions can't even be evaluated today (a feature missing
for this ticker) is silently skipped, never guessed into a false match.
"""

from __future__ import annotations

import statistics
from datetime import date
from enum import Enum

from pydantic import BaseModel, Field

from agx_research.domain.identifiers import new_id
from agx_research.patterns.features import FeatureSeries
from agx_research.patterns.registry import Pattern, PatternRegistry, PatternStatus


class RegimeCompatibility(str, Enum):
    COMPATIBLE = "compatible"
    UNKNOWN = "unknown"


class PatternActivation(BaseModel):
    id: str
    pattern_id: str
    ticker: str
    as_of: date
    label: str = "ACTIVE_PATTERN"
    current_match: bool = True
    match_quality: float | None = None
    historical_expectancy: float
    confidence: float | None = None
    regime_compatibility: RegimeCompatibility
    evidence: list[str] = Field(default_factory=list)
    invalidation_conditions: list[str] = Field(default_factory=list)


_LIVE_ELIGIBLE_STATUSES = {PatternStatus.VALIDATED, PatternStatus.ACTIVE}


class LiveActivationEngine:
    def __init__(self, registry: PatternRegistry):
        self.registry = registry

    def evaluate(
        self, *, as_of: date, feature_lookup: dict[str, FeatureSeries]
    ) -> list[PatternActivation]:
        activations: list[PatternActivation] = []
        for pattern in self.registry.all_latest():
            if pattern.validation_status not in _LIVE_ELIGIBLE_STATUSES:
                continue
            match, quality = self._evaluate_conditions(pattern, feature_lookup, as_of)
            if match is not True:
                continue
            activations.append(
                PatternActivation(
                    id=new_id("pattern_activation"),
                    pattern_id=pattern.id,
                    ticker=pattern.ticker,
                    as_of=as_of,
                    match_quality=quality,
                    historical_expectancy=pattern.expectancy,
                    confidence=pattern.confidence,
                    regime_compatibility=(
                        RegimeCompatibility.COMPATIBLE
                        if pattern.regime_filter
                        else RegimeCompatibility.UNKNOWN
                    ),
                    evidence=self._evidence(pattern),
                    invalidation_conditions=self._invalidation_conditions(pattern),
                )
            )
        return activations

    @staticmethod
    def _evaluate_conditions(
        pattern: Pattern, feature_lookup: dict[str, FeatureSeries], as_of: date
    ) -> tuple[bool | None, float | None]:
        conditions = list(pattern.conditions) + ([pattern.regime_filter] if pattern.regime_filter else [])
        margins: list[float] = []
        for condition in conditions:
            series = feature_lookup.get(condition.feature_id)
            if series is None:
                return None, None
            value = series.as_of_value(as_of)
            if value is None:
                return None, None
            if not condition.operator.evaluate(value, condition.threshold):
                return False, None
            margins.append(abs(value - condition.threshold))
        quality = (1.0 / (1.0 + statistics.fmean(margins))) if margins else None
        return True, quality

    @staticmethod
    def _evidence(pattern: Pattern) -> list[str]:
        evidence = [c.describe() for c in pattern.conditions]
        if pattern.regime_filter:
            evidence.append(f"[regime] {pattern.regime_filter.describe()}")
        evidence.append(
            f"Discovered {pattern.discovery_period[0]}..{pattern.discovery_period[1]}, "
            f"sample_size={pattern.sample_size}, oos_sample_size={pattern.oos_sample_size}, "
            f"hit_rate={pattern.hit_rate:.1%}, expectancy={pattern.expectancy:+.4f}"
        )
        return evidence

    @staticmethod
    def _invalidation_conditions(pattern: Pattern) -> list[str]:
        return [
            f"Live hit rate materially below the historical {pattern.hit_rate:.1%} over a "
            "meaningful live sample (see decay.py's WEAKENING criteria)",
            f"Live expectancy sign flips against the historical {pattern.expectancy:+.4f}",
            "The feature(s) this pattern conditions on stop being computable for this ticker "
            "(missing price/volume/fundamental data)",
        ]


__all__ = ["LiveActivationEngine", "PatternActivation", "RegimeCompatibility"]
