"""Robustness testing: a validated candidate must not depend on one
arbitrary parameter (the mission's own example: `RS > 83.17` working while
`RS > 82`/`RS > 84` both fail is a likely overfit).

Every check here degrades honestly rather than fabricating a result when
the data is too thin to run it — consistent with this whole package's
posture (`docs/PATTERN_DISCOVERY_DATA_AUDIT.md` already establishes that
today's real data is far too shallow for most of these checks to produce
anything but "insufficient data," which is the correct, non-fabricated
answer, not a bug in this module).
"""

from __future__ import annotations

import statistics
from datetime import date

from pydantic import BaseModel, Field

from agx_research.patterns.candidates import FeatureCondition, PatternCandidate
from agx_research.patterns.evaluation import OutcomeDistribution, evaluate_outcomes
from agx_research.patterns.features import FeatureSeries
from agx_research.patterns.targets import TargetSeries

MIN_ROBUSTNESS_SAMPLE = 10
DEFAULT_THRESHOLD_DELTAS: tuple[float, ...] = (-0.25, -0.1, 0.1, 0.25)
DEFAULT_TRANSACTION_COST_BPS = 20.0


class ParameterSensitivity(BaseModel):
    label: str
    sample_size: int
    expectancy: float | None = None
    same_sign_as_base: bool | None = None


class RobustnessResult(BaseModel):
    candidate_id: str
    base_expectancy: float | None = None
    threshold_sensitivity: list[ParameterSensitivity] = Field(default_factory=list)
    lookback_sensitivity: list[ParameterSensitivity] = Field(default_factory=list)
    horizon_sensitivity: list[ParameterSensitivity] = Field(default_factory=list)
    regime_breakdown: dict[str, OutcomeDistribution | None] = Field(default_factory=dict)
    calendar_period_breakdown: dict[str, OutcomeDistribution | None] = Field(default_factory=dict)
    transaction_cost_survival: bool | None = None
    net_of_cost_expectancy: float | None = None
    passed: bool = False
    checks_run: int = 0
    notes: list[str] = Field(default_factory=list)


def _match_outcomes(
    candidate: PatternCandidate,
    dates: list[date],
    feature_lookup: dict[str, FeatureSeries],
    target: TargetSeries,
) -> list[float]:
    outcomes = []
    for d in dates:
        value = target.value_at(d)
        if value is None:
            continue
        if candidate.matches(feature_lookup, d):
            outcomes.append(value)
    return outcomes


class RobustnessTester:
    def __init__(
        self,
        *,
        min_sample: int = MIN_ROBUSTNESS_SAMPLE,
        threshold_deltas: tuple[float, ...] = DEFAULT_THRESHOLD_DELTAS,
        transaction_cost_bps: float = DEFAULT_TRANSACTION_COST_BPS,
    ):
        self.min_sample = min_sample
        self.threshold_deltas = threshold_deltas
        self.transaction_cost_bps = transaction_cost_bps

    def run(
        self,
        candidate: PatternCandidate,
        *,
        anchor_dates: list[date],
        feature_lookup: dict[str, FeatureSeries],
        target: TargetSeries,
        nearby_feature_ids: dict[str, list[str]] | None = None,
        nearby_targets: list[TargetSeries] | None = None,
        regime_feature: FeatureSeries | None = None,
        calendar_periods: dict[str, list[date]] | None = None,
    ) -> RobustnessResult:
        nearby_feature_ids = nearby_feature_ids or {}
        base_outcomes = _match_outcomes(candidate, anchor_dates, feature_lookup, target)
        base_dist = evaluate_outcomes(base_outcomes)
        result = RobustnessResult(
            candidate_id=candidate.id,
            base_expectancy=base_dist.expectancy if base_dist else None,
        )
        if base_dist is None:
            result.notes.append("Base sample too small to run any robustness check.")
            return result
        base_sign = base_dist.expectancy > 0

        result.threshold_sensitivity = self._threshold_sensitivity(
            candidate, anchor_dates, feature_lookup, target, base_sign
        )
        result.lookback_sensitivity = self._nearby_feature_sensitivity(
            candidate, anchor_dates, feature_lookup, target, nearby_feature_ids, base_sign
        )
        if nearby_targets:
            result.horizon_sensitivity = self._nearby_horizon_sensitivity(
                candidate, anchor_dates, feature_lookup, nearby_targets, base_sign
            )
        if regime_feature is not None:
            result.regime_breakdown = self._regime_breakdown(
                candidate, anchor_dates, feature_lookup, target, regime_feature
            )
        if calendar_periods:
            result.calendar_period_breakdown = {
                label: evaluate_outcomes(_match_outcomes(candidate, dates, feature_lookup, target))
                for label, dates in calendar_periods.items()
            }

        net_expectancy = base_dist.expectancy - (self.transaction_cost_bps / 10_000)
        result.net_of_cost_expectancy = net_expectancy
        result.transaction_cost_survival = net_expectancy > 0

        checks = [
            *result.threshold_sensitivity,
            *result.lookback_sensitivity,
            *result.horizon_sensitivity,
        ]
        executed = [c for c in checks if c.same_sign_as_base is not None]
        result.checks_run = len(executed)
        if not executed:
            result.notes.append(
                "No perturbation check had enough matched observations to run — "
                "robustness is unproven, not disproven, given current data depth."
            )
            result.passed = False
        else:
            agreeing = sum(1 for c in executed if c.same_sign_as_base)
            result.passed = (agreeing == len(executed)) and bool(result.transaction_cost_survival)
            if not result.passed:
                result.notes.append(
                    f"{len(executed) - agreeing}/{len(executed)} perturbation(s) flipped sign, "
                    "or the pattern does not survive transaction costs — likely overfit to one "
                    "arbitrary parameter setting."
                )
        return result

    def _threshold_sensitivity(
        self,
        candidate: PatternCandidate,
        anchor_dates: list[date],
        feature_lookup: dict[str, FeatureSeries],
        target: TargetSeries,
        base_sign: bool,
    ) -> list[ParameterSensitivity]:
        if not candidate.conditions:
            return []
        primary = candidate.conditions[0]
        series = feature_lookup.get(primary.feature_id)
        if series is None:
            return []
        values = [v for v in series.values if v is not None]
        if len(values) < 5:
            return []
        spread = statistics.pstdev(values)
        if spread == 0:
            return []

        out: list[ParameterSensitivity] = []
        for delta in self.threshold_deltas:
            perturbed = FeatureCondition(
                feature_id=primary.feature_id,
                operator=primary.operator,
                threshold=primary.threshold + delta * spread,
            )
            variant = candidate.model_copy(update={"conditions": [perturbed, *candidate.conditions[1:]]})
            outcomes = _match_outcomes(variant, anchor_dates, feature_lookup, target)
            dist = evaluate_outcomes(outcomes)
            out.append(
                ParameterSensitivity(
                    label=f"threshold{delta:+.0%}_stdev",
                    sample_size=len(outcomes),
                    expectancy=dist.expectancy if dist else None,
                    same_sign_as_base=(
                        (dist.expectancy > 0) == base_sign
                        if dist is not None and dist.sample_count >= self.min_sample
                        else None
                    ),
                )
            )
        return out

    def _nearby_feature_sensitivity(
        self,
        candidate: PatternCandidate,
        anchor_dates: list[date],
        feature_lookup: dict[str, FeatureSeries],
        target: TargetSeries,
        nearby_feature_ids: dict[str, list[str]],
        base_sign: bool,
    ) -> list[ParameterSensitivity]:
        if not candidate.conditions:
            return []
        primary = candidate.conditions[0]
        out: list[ParameterSensitivity] = []
        for alt_id in nearby_feature_ids.get(primary.feature_id, []):
            if alt_id not in feature_lookup:
                continue
            variant_condition = FeatureCondition(
                feature_id=alt_id, operator=primary.operator, threshold=primary.threshold
            )
            variant = candidate.model_copy(update={"conditions": [variant_condition, *candidate.conditions[1:]]})
            outcomes = _match_outcomes(variant, anchor_dates, feature_lookup, target)
            dist = evaluate_outcomes(outcomes)
            out.append(
                ParameterSensitivity(
                    label=f"lookback_variant:{alt_id}",
                    sample_size=len(outcomes),
                    expectancy=dist.expectancy if dist else None,
                    same_sign_as_base=(
                        (dist.expectancy > 0) == base_sign
                        if dist is not None and dist.sample_count >= self.min_sample
                        else None
                    ),
                )
            )
        return out

    def _nearby_horizon_sensitivity(
        self,
        candidate: PatternCandidate,
        anchor_dates: list[date],
        feature_lookup: dict[str, FeatureSeries],
        nearby_targets: list[TargetSeries],
        base_sign: bool,
    ) -> list[ParameterSensitivity]:
        out: list[ParameterSensitivity] = []
        for alt_target in nearby_targets:
            outcomes = _match_outcomes(candidate, anchor_dates, feature_lookup, alt_target)
            dist = evaluate_outcomes(outcomes)
            out.append(
                ParameterSensitivity(
                    label=f"horizon_variant:{alt_target.id}",
                    sample_size=len(outcomes),
                    expectancy=dist.expectancy if dist else None,
                    same_sign_as_base=(
                        (dist.expectancy > 0) == base_sign
                        if dist is not None and dist.sample_count >= self.min_sample
                        else None
                    ),
                )
            )
        return out

    def _regime_breakdown(
        self,
        candidate: PatternCandidate,
        anchor_dates: list[date],
        feature_lookup: dict[str, FeatureSeries],
        target: TargetSeries,
        regime_feature: FeatureSeries,
    ) -> dict[str, OutcomeDistribution | None]:
        values = [v for v in regime_feature.values if v is not None]
        if len(values) < 5:
            return {}
        median = statistics.median(values)
        buckets = {"above_median": [], "below_median": []}
        for d in anchor_dates:
            regime_value = regime_feature.as_of_value(d)
            if regime_value is None:
                continue
            bucket = "above_median" if regime_value >= median else "below_median"
            buckets[bucket].append(d)
        return {
            label: evaluate_outcomes(_match_outcomes(candidate, dates, feature_lookup, target))
            for label, dates in buckets.items()
        }


__all__ = [
    "DEFAULT_THRESHOLD_DELTAS",
    "DEFAULT_TRANSACTION_COST_BPS",
    "MIN_ROBUSTNESS_SAMPLE",
    "ParameterSensitivity",
    "RobustnessResult",
    "RobustnessTester",
]
