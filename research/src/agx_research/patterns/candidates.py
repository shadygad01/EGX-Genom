"""The Pattern Generation Engine: turns a `FeatureSeries`/`TargetSeries`
pool into candidate rules, without a developer hand-specifying the final
pattern.

Combinatorial explosion is controlled at every stage, per the mission's
explicit requirement ("do not blindly generate combinatorial explosions"):
`eligible_features()` drops anything below `min_sample_size` or too
correlated with an already-kept feature (`correlation_prune_threshold`);
single-feature conditions are built from a small declared quantile grid,
not every possible threshold; two/three-feature interactions only combine
each feature's *median*-quantile condition (not the full grid); a
candidate is only kept once its *actual* joint match count against real
panel dates clears `min_sample_size` (checked before it's added, not
after evaluation); and `max_candidates` is a hard stop.
"""

from __future__ import annotations

import itertools
from datetime import date
from enum import Enum

from pydantic import BaseModel, Field

from agx_research.domain.identifiers import new_id
from agx_research.features.correlation import pearson_correlation
from agx_research.patterns.features import FeatureCategory, FeatureSeries
from agx_research.patterns.targets import TargetSeries

DEFAULT_QUANTILE_THRESHOLDS: tuple[float, ...] = (0.3, 0.5, 0.7)
DEFAULT_REGIME_FEATURE_IDS: tuple[str, ...] = (
    "market_breadth:MARKET",
    "cross_sectional_dispersion_20d:MARKET",
)


class ConditionOperator(str, Enum):
    GT = "gt"
    LT = "lt"

    def evaluate(self, value: float, threshold: float) -> bool:
        return value > threshold if self is ConditionOperator.GT else value < threshold


class FeatureCondition(BaseModel):
    feature_id: str
    operator: ConditionOperator
    threshold: float

    def describe(self) -> str:
        symbol = ">" if self.operator is ConditionOperator.GT else "<"
        return f"{self.feature_id} {symbol} {self.threshold:.4f}"


class PatternCandidate(BaseModel):
    id: str
    ticker: str
    conditions: list[FeatureCondition] = Field(default_factory=list)
    regime_filter: FeatureCondition | None = None
    target_id: str
    complexity: int
    is_regime_conditioned: bool = False
    is_cross_sectional: bool = False

    def all_conditions(self) -> list[FeatureCondition]:
        return self.conditions + ([self.regime_filter] if self.regime_filter else [])

    def definition(self) -> str:
        parts = [c.describe() for c in self.conditions]
        if self.regime_filter:
            parts.append(f"[regime] {self.regime_filter.describe()}")
        return " AND ".join(parts) + f" -> {self.target_id}"

    def matches(self, feature_lookup: dict[str, FeatureSeries], as_of: date) -> bool | None:
        """None when any referenced feature is unavailable at `as_of` — an
        unknown match is never silently treated as a non-match."""
        for condition in self.all_conditions():
            series = feature_lookup.get(condition.feature_id)
            if series is None:
                return None
            value = series.as_of_value(as_of)
            if value is None:
                return None
            if not condition.operator.evaluate(value, condition.threshold):
                return False
        return True


class CandidateGeneratorConfig(BaseModel):
    quantile_thresholds: tuple[float, ...] = DEFAULT_QUANTILE_THRESHOLDS
    min_sample_size: int = 30
    # A deliberately conservative default: live testing against synthetic
    # pure-noise data (see docs/PATTERN_DISCOVERY_REPORT.md's limitations
    # section) showed 0.9 lets too many mechanically-correlated engineered
    # features (e.g. return_1d vs return_3d on the same ticker) survive as
    # if independent. 0.8 is still a declared, uncalibrated choice, not a
    # measured optimum -- it measurably helped, it does not make the
    # underlying data-mining-bias risk (see match_overlap_prune_threshold
    # below) go away.
    correlation_prune_threshold: float = 0.8
    # Feature-level correlation pruning (above) is necessary but not
    # sufficient: many mechanically-derived features (return_1d/3d/5d,
    # distance_from_high/low, ...) survive it while still keying off
    # nearly the same underlying date subset once thresholded. Left
    # unchecked, a single lucky coincidence in the data gets counted as
    # many independent "discoveries" -- exactly the data-mining-bias
    # failure mode multiple-testing control is supposed to catch (see
    # `docs/PATTERN_DISCOVERY_REPORT.md`'s limitations section for the
    # live-measured evidence that motivated this: pure-noise synthetic
    # data produced dozens of BH-surviving, walk-forward-surviving
    # "patterns" before this prune existed). A candidate whose matched
    # trigger-date set overlaps an already-kept one by at least this
    # Jaccard threshold is dropped as redundant, not independently novel.
    match_overlap_prune_threshold: float = 0.85
    max_candidates_per_ticker: int = 500
    enable_two_feature: bool = True
    enable_three_feature: bool = True
    three_feature_min_headroom: int = 2  # require >= headroom * min_sample_size before adding a 3rd condition
    enable_regime_conditioning: bool = True
    regime_feature_ids: tuple[str, ...] = DEFAULT_REGIME_FEATURE_IDS


def _quantile(sorted_values: list[float], q: float) -> float:
    if not sorted_values:
        raise ValueError("cannot take a quantile of an empty sequence")
    if len(sorted_values) == 1:
        return sorted_values[0]
    position = q * (len(sorted_values) - 1)
    lower = int(position)
    upper = min(lower + 1, len(sorted_values) - 1)
    fraction = position - lower
    return sorted_values[lower] + (sorted_values[upper] - sorted_values[lower]) * fraction


def _series_correlation(a: FeatureSeries, b: FeatureSeries) -> float | None:
    common = sorted(set(a.dates) & set(b.dates))
    pairs = [(a.as_of_value(d), b.as_of_value(d)) for d in common]
    clean = [(x, y) for x, y in pairs if x is not None and y is not None]
    if len(clean) < 5:
        return None
    xs, ys = zip(*clean)
    return pearson_correlation(list(xs), list(ys))


class PatternCandidateGenerator:
    def __init__(self, config: CandidateGeneratorConfig | None = None):
        self.config = config or CandidateGeneratorConfig()

    def eligible_features(self, features: list[FeatureSeries]) -> list[FeatureSeries]:
        eligible = [f for f in features if f.non_null_count() >= self.config.min_sample_size]
        pruned: list[FeatureSeries] = []
        for feature in eligible:
            duplicate = False
            for kept in pruned:
                correlation = _series_correlation(feature, kept)
                if correlation is not None and abs(correlation) >= self.config.correlation_prune_threshold:
                    duplicate = True
                    break
            if not duplicate:
                pruned.append(feature)
        return pruned

    def _single_conditions(self, feature: FeatureSeries) -> list[FeatureCondition]:
        values = sorted(v for v in feature.values if v is not None)
        if len(values) < self.config.min_sample_size:
            return []
        thresholds = sorted({round(_quantile(values, q), 6) for q in self.config.quantile_thresholds})
        return [
            FeatureCondition(feature_id=feature.id, operator=op, threshold=threshold)
            for threshold in thresholds
            for op in (ConditionOperator.GT, ConditionOperator.LT)
        ]

    def _median_condition(self, feature: FeatureSeries) -> FeatureCondition | None:
        values = sorted(v for v in feature.values if v is not None)
        if len(values) < self.config.min_sample_size:
            return None
        median = round(_quantile(values, 0.5), 6)
        return FeatureCondition(feature_id=feature.id, operator=ConditionOperator.GT, threshold=median)

    def _match_stats(
        self,
        conditions: list[FeatureCondition],
        anchor_dates: list[date],
        feature_lookup: dict[str, FeatureSeries],
        target: TargetSeries,
    ) -> tuple[int, frozenset[date]]:
        """Returns `(sample_count, trigger_dates)`: `sample_count` is how
        many anchors both satisfy every condition *and* have a non-null
        target (the real, usable discovery sample); `trigger_dates` is
        every anchor satisfying the conditions alone, independent of the
        target -- the basis `_is_redundant_match` compares against, since
        two conditions that fire on nearly the same dates are testing the
        same underlying coincidence regardless of which target they're
        paired with this iteration."""
        count = 0
        triggered: set[date] = set()
        for anchor in anchor_dates:
            ok = True
            for condition in conditions:
                series = feature_lookup.get(condition.feature_id)
                value = series.as_of_value(anchor) if series else None
                if value is None or not condition.operator.evaluate(value, condition.threshold):
                    ok = False
                    break
            if not ok:
                continue
            triggered.add(anchor)
            if target.value_at(anchor) is not None:
                count += 1
        return count, frozenset(triggered)

    def _is_redundant_match(self, trigger_dates: frozenset[date], kept: list[frozenset[date]]) -> bool:
        threshold = self.config.match_overlap_prune_threshold
        for other in kept:
            union = len(trigger_dates | other)
            if union == 0:
                continue
            if len(trigger_dates & other) / union >= threshold:
                return True
        return False

    def generate(
        self,
        *,
        ticker: str,
        anchor_dates: list[date],
        features: list[FeatureSeries],
        targets: list[TargetSeries],
        market_features: list[FeatureSeries] | None = None,
    ) -> list[PatternCandidate]:
        """`features` should be this ticker's own price/volume/cross-sectional/
        fundamental features; `market_features` (optional) supplies
        market-wide/macro features usable only as a `regime_filter`, never
        as a primary condition of a per-ticker pattern (that distinction is
        what keeps "regime-conditioned" a genuinely separate candidate
        class rather than duplicating ordinary two-feature interactions).
        """
        market_features = market_features or []
        eligible = self.eligible_features(features)
        feature_lookup = {f.id: f for f in [*eligible, *market_features]}
        candidates: list[PatternCandidate] = []

        for target in targets:
            if target.spec.threshold is not None and target.spec.kind.value == "prob_exceeds":
                pass  # still a valid target; no special handling needed beyond value_at()

            singles_by_feature: dict[str, list[FeatureCondition]] = {
                f.id: self._single_conditions(f) for f in eligible
            }

            # ---- single-feature ----
            single_survivors: list[list[FeatureCondition]] = []
            kept_single_triggers: list[frozenset[date]] = []
            for feature in eligible:
                for condition in singles_by_feature[feature.id]:
                    if len(candidates) >= self.config.max_candidates_per_ticker:
                        return candidates
                    count, trigger_dates = self._match_stats([condition], anchor_dates, feature_lookup, target)
                    if count < self.config.min_sample_size:
                        continue
                    if self._is_redundant_match(trigger_dates, kept_single_triggers):
                        continue
                    kept_single_triggers.append(trigger_dates)
                    single_survivors.append([condition])
                    candidates.append(
                        self._build(ticker, [condition], target.id, feature, None)
                    )

            # ---- two-feature interactions (median condition per feature only) ----
            two_feature_base: list[tuple[FeatureSeries, FeatureCondition]] = [
                (f, self._median_condition(f)) for f in eligible
            ]
            two_feature_base = [(f, c) for f, c in two_feature_base if c is not None]
            two_survivors: list[list[FeatureCondition]] = []
            kept_two_triggers: list[frozenset[date]] = []
            if self.config.enable_two_feature:
                for (fa, ca), (fb, cb) in itertools.combinations(two_feature_base, 2):
                    if len(candidates) >= self.config.max_candidates_per_ticker:
                        return candidates
                    conditions = [ca, cb]
                    count, trigger_dates = self._match_stats(conditions, anchor_dates, feature_lookup, target)
                    if count < self.config.min_sample_size:
                        continue
                    if self._is_redundant_match(trigger_dates, kept_two_triggers):
                        continue
                    kept_two_triggers.append(trigger_dates)
                    two_survivors.append(conditions)
                    candidates.append(self._build(ticker, conditions, target.id, fa, fb))

            # ---- three-feature interactions (only with ample headroom) ----
            if self.config.enable_three_feature and two_survivors:
                required = self.config.min_sample_size * self.config.three_feature_min_headroom
                kept_three_triggers: list[frozenset[date]] = []
                for conditions in two_survivors:
                    used_ids = {c.feature_id for c in conditions}
                    for feature, condition in two_feature_base:
                        if feature.id in used_ids:
                            continue
                        if len(candidates) >= self.config.max_candidates_per_ticker:
                            return candidates
                        base_count, _ = self._match_stats(conditions, anchor_dates, feature_lookup, target)
                        if base_count < required:
                            continue
                        extended = [*conditions, condition]
                        count, trigger_dates = self._match_stats(extended, anchor_dates, feature_lookup, target)
                        if count < self.config.min_sample_size:
                            continue
                        if self._is_redundant_match(trigger_dates, kept_three_triggers):
                            continue
                        kept_three_triggers.append(trigger_dates)
                        candidates.append(self._build(ticker, extended, target.id, feature, None))

            # ---- regime-conditioned variants of single-feature survivors ----
            if self.config.enable_regime_conditioning:
                for conditions in single_survivors:
                    for regime_id in self.config.regime_feature_ids:
                        regime_series = feature_lookup.get(regime_id)
                        if regime_series is None:
                            continue
                        regime_condition = self._median_condition(regime_series)
                        if regime_condition is None:
                            continue
                        if len(candidates) >= self.config.max_candidates_per_ticker:
                            return candidates
                        count, _ = self._match_stats(
                            [*conditions, regime_condition], anchor_dates, feature_lookup, target
                        )
                        if count < self.config.min_sample_size:
                            continue
                        candidate = self._build(
                            ticker, conditions, target.id,
                            feature_lookup.get(conditions[0].feature_id), None,
                        )
                        candidate.regime_filter = regime_condition
                        candidate.is_regime_conditioned = True
                        candidate.complexity += 1
                        candidate.id = new_id("pattern_candidate")
                        candidates.append(candidate)

        return candidates

    def _build(
        self,
        ticker: str,
        conditions: list[FeatureCondition],
        target_id: str,
        primary_feature: FeatureSeries | None,
        secondary_feature: FeatureSeries | None,
    ) -> PatternCandidate:
        involved = [f for f in (primary_feature, secondary_feature) if f is not None]
        is_cross_sectional = any(f.spec.category is FeatureCategory.CROSS_SECTIONAL for f in involved)
        return PatternCandidate(
            id=new_id("pattern_candidate"),
            ticker=ticker,
            conditions=conditions,
            target_id=target_id,
            complexity=len(conditions),
            is_cross_sectional=is_cross_sectional,
        )


__all__ = [
    "DEFAULT_QUANTILE_THRESHOLDS",
    "DEFAULT_REGIME_FEATURE_IDS",
    "CandidateGeneratorConfig",
    "ConditionOperator",
    "FeatureCondition",
    "PatternCandidate",
    "PatternCandidateGenerator",
]
