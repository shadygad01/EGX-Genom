"""Regime discovery (mission Phase 11) and failure-pattern
characterization (mission Phase 13).

Six independent market-wide regime dimensions -- volatility, breadth,
dispersion, trend, correlation, turnover -- each classified into K
buckets (low..high) via the same trailing-percentile-rank primitive
`features.py`'s own `volatility_regime_pct` already uses
(`_percentile_rank` over a trailing lookback window, never the full
sample), so every regime label stays point-in-time safe by construction:
a bucket assigned to date `t` never depends on data dated after `t`.

`analyze_pattern_failure_conditions()` buckets an already-VALIDATED
pattern's own matched outcomes by regime label and classifies it
unconditional / regime_specific / sensitive / unstable / insufficient_data
from the real, measured per-bucket expectancy spread -- never a
fabricated label. This is a post-hoc, descriptive characterization of a
pattern the three-way split has already promoted, not a new discovery
decision, so it deliberately reads a pattern's FULL matched history
(research + holdout periods together) rather than restricting to the
research-only dates `discover()`/`validate()` use -- there is no
look-ahead risk in describing what already happened to an already-settled
pattern.

`bucket_count_sensitivity()` re-runs the same classification at several
different K values (the mission's "sensitivity to regime count"
requirement) and reports whether each dimension's qualitative read (which
sign the pattern shows) holds steady across K, or flips -- an unstable
read across K is itself informative, not swept under the rug.
"""

from __future__ import annotations

import statistics
from bisect import bisect_right
from datetime import date
from enum import Enum

from pydantic import BaseModel, Field

from agx_research.features.correlation import pearson_correlation
from agx_research.patterns.candidates import PatternCandidate
from agx_research.patterns.evaluation import OutcomeDistribution, evaluate_outcomes
from agx_research.patterns.features import FeatureFactory, _percentile_rank, _rolling_with_none
from agx_research.patterns.panel import ResearchPanel
from agx_research.patterns.registry import Pattern
from agx_research.patterns.targets import TargetFactory

DEFAULT_REGIME_LOOKBACK_DAYS = 120
CORRELATION_LOOKBACK_DAYS = 60
DEFAULT_BUCKET_COUNT = 3
# The mission's "sensitivity to regime count" requirement -- every
# dimension is re-classified at each of these and compared for a
# qualitative (sign) flip, not re-tuned to whichever K looks best.
BUCKET_COUNT_SENSITIVITY_GRID: tuple[int, ...] = (2, 3, 4)
MIN_BUCKET_SAMPLE = 5
REGIME_SPECIFIC_DOMINANCE_RATIO = 3.0
SENSITIVE_COEFFICIENT_OF_VARIATION = 0.5


class RegimeDimension(str, Enum):
    VOLATILITY = "volatility"
    BREADTH = "breadth"
    DISPERSION = "dispersion"
    TREND = "trend"
    CORRELATION = "correlation"
    TURNOVER = "turnover"


class PatternRegimeTag(str, Enum):
    UNCONDITIONAL = "unconditional"
    REGIME_SPECIFIC = "regime_specific"
    SENSITIVE = "sensitive"
    UNSTABLE = "unstable"
    INSUFFICIENT_DATA = "insufficient_data"


class RegimeSeries(BaseModel):
    dimension: RegimeDimension
    k: int
    dates: list[date] = Field(default_factory=list)
    buckets: list[int | None] = Field(default_factory=list)

    def bucket_at(self, t: date) -> int | None:
        """As-of lookup, same discipline as `FeatureSeries.as_of_value`:
        the most recent non-null bucket dated at or before `t`."""
        idx = bisect_right(self.dates, t) - 1
        while idx >= 0:
            if self.buckets[idx] is not None:
                return self.buckets[idx]
            idx -= 1
        return None


class RegimeBucketOutcome(BaseModel):
    dimension: RegimeDimension
    bucket: int
    k: int
    sample_size: int
    expectancy: float
    hit_rate: float


class DimensionFailureNote(BaseModel):
    dimension: RegimeDimension
    k: int
    bucket_outcomes: list[RegimeBucketOutcome]
    weakest_bucket: int | None
    weakest_bucket_expectancy: float | None
    sign_flip: bool
    note: str


class BucketCountSensitivityResult(BaseModel):
    dimension: RegimeDimension
    signs_by_k: dict[int, list[int]]  # k -> sign (+1/0/-1) per bucket, low to high
    stable_across_k: bool


class PatternFailureProfile(BaseModel):
    pattern_id: str
    overall_tag: PatternRegimeTag
    per_dimension: list[DimensionFailureNote]
    bucket_count_sensitivity: list[BucketCountSensitivityResult]
    weakest_conditions: list[str]


def _bucket_from_trailing_percentile(
    raw_values: list[float | None], *, lookback: int, k: int
) -> list[int | None]:
    pct = _rolling_with_none(raw_values, lookback, lambda v: _percentile_rank(v[-1], v[:-1]))
    return [min(k - 1, int(p * k)) if p is not None else None for p in pct]


def _market_average(panel: ResearchPanel, dates: list[date], per_ticker_values: dict[str, list[float | None]]) -> list[float | None]:
    """`per_ticker_values[ticker][i]` must already be aligned to `dates`
    (each ticker's own series is forward-filled onto the shared calendar
    via `as_of_value` by the caller). Averages only across tickers with a
    real observation at that date -- never imputes a missing ticker."""
    out: list[float | None] = []
    for i in range(len(dates)):
        values = [series[i] for series in per_ticker_values.values() if series[i] is not None]
        out.append(statistics.fmean(values) if values else None)
    return out


def _build_volatility_dimension(panel: ResearchPanel, calendar: list[date], k: int) -> RegimeSeries:
    per_ticker: dict[str, list[float | None]] = {}
    for ticker in panel.tickers:
        vol = next((f for f in FeatureFactory(panel).build_price_features(ticker) if f.spec.id == "volatility_20d"), None)
        per_ticker[ticker] = [vol.as_of_value(d) if vol else None for d in calendar]
    raw = _market_average(panel, calendar, per_ticker)
    buckets = _bucket_from_trailing_percentile(raw, lookback=DEFAULT_REGIME_LOOKBACK_DAYS, k=k)
    return RegimeSeries(dimension=RegimeDimension.VOLATILITY, k=k, dates=calendar, buckets=buckets)


def _build_trend_dimension(panel: ResearchPanel, calendar: list[date], k: int) -> RegimeSeries:
    per_ticker: dict[str, list[float | None]] = {}
    for ticker in panel.tickers:
        ret = next((f for f in FeatureFactory(panel).build_price_features(ticker) if f.spec.id == "return_20d"), None)
        per_ticker[ticker] = [ret.as_of_value(d) if ret else None for d in calendar]
    raw = _market_average(panel, calendar, per_ticker)
    buckets = _bucket_from_trailing_percentile(raw, lookback=DEFAULT_REGIME_LOOKBACK_DAYS, k=k)
    return RegimeSeries(dimension=RegimeDimension.TREND, k=k, dates=calendar, buckets=buckets)


def _build_turnover_dimension(panel: ResearchPanel, calendar: list[date], k: int) -> RegimeSeries:
    per_ticker: dict[str, list[float | None]] = {}
    for ticker in panel.tickers:
        rel_vol = next(
            (f for f in FeatureFactory(panel).build_volume_features(ticker) if f.spec.id == "relative_volume_20d"),
            None,
        )
        per_ticker[ticker] = [rel_vol.as_of_value(d) if rel_vol else None for d in calendar]
    raw = _market_average(panel, calendar, per_ticker)
    buckets = _bucket_from_trailing_percentile(raw, lookback=DEFAULT_REGIME_LOOKBACK_DAYS, k=k)
    return RegimeSeries(dimension=RegimeDimension.TURNOVER, k=k, dates=calendar, buckets=buckets)


def _build_market_feature_dimension(
    panel: ResearchPanel, calendar: list[date], k: int, dimension: RegimeDimension, feature_id: str
) -> RegimeSeries:
    market_features = [f for f in FeatureFactory(panel).build_all() if f.ticker == ""]
    feature = next((f for f in market_features if f.spec.id == feature_id), None)
    raw = [feature.as_of_value(d) if feature else None for d in calendar]
    buckets = _bucket_from_trailing_percentile(raw, lookback=DEFAULT_REGIME_LOOKBACK_DAYS, k=k)
    return RegimeSeries(dimension=dimension, k=k, dates=calendar, buckets=buckets)


def _build_correlation_dimension(panel: ResearchPanel, calendar: list[date], k: int) -> RegimeSeries:
    """Mean pairwise Pearson correlation of daily adjusted returns across
    every ticker pair in the panel, over a trailing `CORRELATION_LOOKBACK_
    DAYS` window ending at (and including) each date -- the only regime
    dimension with no existing `FeatureFactory` output to reuse, computed
    directly from `TickerSeries.adjusted_close` the same way every other
    return calculation in this codebase does."""
    daily_returns: dict[str, dict[date, float]] = {}
    for ticker, series in panel.series.items():
        closes = series.adjusted_close
        returns = {
            series.dates[i]: (closes[i] - closes[i - 1]) / closes[i - 1]
            for i in range(1, len(closes))
            if closes[i - 1] != 0
        }
        daily_returns[ticker] = returns

    tickers = list(panel.tickers)
    raw: list[float | None] = []
    for d in calendar:
        window_start_idx = bisect_right(calendar, d) - CORRELATION_LOOKBACK_DAYS
        if window_start_idx < 0:
            raw.append(None)
            continue
        window_dates = calendar[window_start_idx : bisect_right(calendar, d)]
        pair_correlations: list[float] = []
        for i in range(len(tickers)):
            for j in range(i + 1, len(tickers)):
                a = [daily_returns[tickers[i]][wd] for wd in window_dates if wd in daily_returns[tickers[i]]]
                b = [daily_returns[tickers[j]][wd] for wd in window_dates if wd in daily_returns[tickers[j]]]
                if len(a) < CORRELATION_LOOKBACK_DAYS // 2 or len(b) < CORRELATION_LOOKBACK_DAYS // 2:
                    continue
                corr = pearson_correlation(a, b)
                if corr is not None:
                    pair_correlations.append(corr)
        raw.append(statistics.fmean(pair_correlations) if pair_correlations else None)

    buckets = _bucket_from_trailing_percentile(raw, lookback=DEFAULT_REGIME_LOOKBACK_DAYS, k=k)
    return RegimeSeries(dimension=RegimeDimension.CORRELATION, k=k, dates=calendar, buckets=buckets)


def build_regime_series(panel: ResearchPanel, dimension: RegimeDimension, *, k: int = DEFAULT_BUCKET_COUNT) -> RegimeSeries:
    calendar = panel.all_dates()
    if dimension is RegimeDimension.VOLATILITY:
        return _build_volatility_dimension(panel, calendar, k)
    if dimension is RegimeDimension.TREND:
        return _build_trend_dimension(panel, calendar, k)
    if dimension is RegimeDimension.TURNOVER:
        return _build_turnover_dimension(panel, calendar, k)
    if dimension is RegimeDimension.BREADTH:
        return _build_market_feature_dimension(panel, calendar, k, dimension, "market_breadth")
    if dimension is RegimeDimension.DISPERSION:
        return _build_market_feature_dimension(panel, calendar, k, dimension, "cross_sectional_dispersion_20d")
    if dimension is RegimeDimension.CORRELATION:
        return _build_correlation_dimension(panel, calendar, k)
    raise ValueError(f"Unknown regime dimension: {dimension!r}")


def _reconstruct_matched_outcomes(pattern: Pattern, panel: ResearchPanel) -> list[tuple[date, float]]:
    """Mirrors `engine.py`'s own `validate()`/`final_holdout()` candidate
    reconstruction (including the lead/lag cross-ticker `feature_lookup`
    fix) -- kept as its own small copy here rather than importing engine
    internals, since failure analysis deliberately reads a pattern's FULL
    date range (see module docstring), not the research-only/holdout-only
    slice either engine phase restricts itself to."""
    if pattern.ticker not in panel.series:
        return []
    all_features = FeatureFactory(panel).build_all()
    market_features = [f for f in all_features if f.ticker == ""]
    ticker_features = [f for f in all_features if f.ticker == pattern.ticker]

    predictors = market_features
    if pattern.is_lead_lag:
        from agx_research.patterns.engine import _lead_lag_predictor_features, _sector_leaders

        sector_leaders = _sector_leaders(panel)
        predictors = _lead_lag_predictor_features(
            panel, all_features, market_features, pattern.ticker, sector_leaders,
            ("return_1d", "return_5d", "relative_volume_5d"),
        )
    feature_lookup = {f.id: f for f in [*ticker_features, *predictors]}

    targets = TargetFactory(panel).build_all(pattern.ticker)
    target = next((t for t in targets if t.id == pattern.target_id), None)
    if target is None:
        barrier_targets = TargetFactory(panel).build_barrier_targets(pattern.ticker)
        target = next((t for t in barrier_targets if t.id == pattern.target_id), None)
    if target is None:
        return []

    candidate = PatternCandidate(
        id=pattern.id, ticker=pattern.ticker, conditions=pattern.conditions,
        regime_filter=pattern.regime_filter, target_id=pattern.target_id, complexity=pattern.complexity,
        is_lead_lag=pattern.is_lead_lag,
    )
    outcomes: list[tuple[date, float]] = []
    for d in panel.series[pattern.ticker].dates:
        value = target.value_at(d)
        if value is None:
            continue
        if candidate.matches(feature_lookup, d):
            outcomes.append((d, value))
    return outcomes


def _sign(x: float) -> int:
    if x > 0:
        return 1
    if x < 0:
        return -1
    return 0


def _bucket_outcomes_for_dimension(
    matched: list[tuple[date, float]], regime: RegimeSeries
) -> list[RegimeBucketOutcome]:
    by_bucket: dict[int, list[float]] = {}
    for d, v in matched:
        b = regime.bucket_at(d)
        if b is None:
            continue
        by_bucket.setdefault(b, []).append(v)

    results: list[RegimeBucketOutcome] = []
    for bucket in range(regime.k):
        values = by_bucket.get(bucket, [])
        if len(values) < MIN_BUCKET_SAMPLE:
            continue
        distribution: OutcomeDistribution | None = evaluate_outcomes(values)
        if distribution is None:
            continue
        results.append(
            RegimeBucketOutcome(
                dimension=regime.dimension, bucket=bucket, k=regime.k,
                sample_size=distribution.sample_count, expectancy=distribution.expectancy,
                hit_rate=distribution.hit_rate,
            )
        )
    return results


def _dimension_note(dimension: RegimeDimension, k: int, bucket_outcomes: list[RegimeBucketOutcome]) -> DimensionFailureNote:
    if not bucket_outcomes:
        return DimensionFailureNote(
            dimension=dimension, k=k, bucket_outcomes=[], weakest_bucket=None, weakest_bucket_expectancy=None,
            sign_flip=False, note="No bucket cleared the minimum sample floor for this dimension.",
        )
    signs = {_sign(b.expectancy) for b in bucket_outcomes if b.expectancy != 0}
    sign_flip = len({s for s in signs if s != 0}) > 1
    weakest = min(bucket_outcomes, key=lambda b: b.expectancy)
    note = (
        f"Weakest in bucket {weakest.bucket}/{k - 1} "
        f"(expectancy {weakest.expectancy:+.4f}, n={weakest.sample_size})"
        + (" -- sign flips across buckets." if sign_flip else ".")
    )
    return DimensionFailureNote(
        dimension=dimension, k=k, bucket_outcomes=bucket_outcomes, weakest_bucket=weakest.bucket,
        weakest_bucket_expectancy=weakest.expectancy, sign_flip=sign_flip, note=note,
    )


def _classify_overall_tag(per_dimension: list[DimensionFailureNote]) -> PatternRegimeTag:
    with_data = [n for n in per_dimension if n.bucket_outcomes]
    if not with_data:
        return PatternRegimeTag.INSUFFICIENT_DATA
    if any(n.sign_flip for n in with_data):
        return PatternRegimeTag.UNSTABLE

    regime_specific = False
    sensitive = False
    for n in with_data:
        magnitudes = sorted((abs(b.expectancy) for b in n.bucket_outcomes), reverse=True)
        if len(magnitudes) >= 2 and magnitudes[1] > 0 and magnitudes[0] / magnitudes[1] >= REGIME_SPECIFIC_DOMINANCE_RATIO:
            regime_specific = True
        if len(magnitudes) >= 2:
            mean_mag = statistics.fmean(magnitudes)
            if mean_mag > 0:
                cv = statistics.pstdev(magnitudes) / mean_mag
                if cv >= SENSITIVE_COEFFICIENT_OF_VARIATION:
                    sensitive = True

    if regime_specific:
        return PatternRegimeTag.REGIME_SPECIFIC
    if sensitive:
        return PatternRegimeTag.SENSITIVE
    return PatternRegimeTag.UNCONDITIONAL


def bucket_count_sensitivity(
    pattern: Pattern, panel: ResearchPanel, matched: list[tuple[date, float]],
    *, bucket_counts: tuple[int, ...] = BUCKET_COUNT_SENSITIVITY_GRID,
) -> list[BucketCountSensitivityResult]:
    results: list[BucketCountSensitivityResult] = []
    for dimension in RegimeDimension:
        signs_by_k: dict[int, list[int]] = {}
        for k in bucket_counts:
            regime = build_regime_series(panel, dimension, k=k)
            bucket_outcomes = _bucket_outcomes_for_dimension(matched, regime)
            signs_by_k[k] = [_sign(b.expectancy) for b in bucket_outcomes]
        non_empty = [set(s) - {0} for s in signs_by_k.values() if s]
        stable = len(non_empty) <= 1 or all(s == non_empty[0] for s in non_empty[1:])
        results.append(BucketCountSensitivityResult(dimension=dimension, signs_by_k=signs_by_k, stable_across_k=stable))
    return results


def analyze_pattern_failure_conditions(pattern: Pattern, panel: ResearchPanel) -> PatternFailureProfile:
    """The Phase 13 entry point: `agx research failure-profile` and any
    future consumer call this once per already-VALIDATED pattern."""
    matched = _reconstruct_matched_outcomes(pattern, panel)

    per_dimension: list[DimensionFailureNote] = []
    for dimension in RegimeDimension:
        regime = build_regime_series(panel, dimension, k=DEFAULT_BUCKET_COUNT)
        bucket_outcomes = _bucket_outcomes_for_dimension(matched, regime)
        per_dimension.append(_dimension_note(dimension, DEFAULT_BUCKET_COUNT, bucket_outcomes))

    overall_tag = _classify_overall_tag(per_dimension)
    sensitivity = bucket_count_sensitivity(pattern, panel, matched)
    weakest_conditions = [n.note for n in per_dimension if n.bucket_outcomes]

    return PatternFailureProfile(
        pattern_id=pattern.id, overall_tag=overall_tag, per_dimension=per_dimension,
        bucket_count_sensitivity=sensitivity, weakest_conditions=weakest_conditions,
    )


__all__ = [
    "BUCKET_COUNT_SENSITIVITY_GRID",
    "BucketCountSensitivityResult",
    "DEFAULT_BUCKET_COUNT",
    "DimensionFailureNote",
    "MIN_BUCKET_SAMPLE",
    "PatternFailureProfile",
    "PatternRegimeTag",
    "RegimeBucketOutcome",
    "RegimeDimension",
    "RegimeSeries",
    "analyze_pattern_failure_conditions",
    "bucket_count_sensitivity",
    "build_regime_series",
]
