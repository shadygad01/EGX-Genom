"""Regime discovery (mission Phase 11) and failure-pattern
characterization (mission Phase 13) coverage for `patterns.regimes`."""

from __future__ import annotations

from datetime import date

from agx_research.patterns.control_suite import build_lead_lag_panel, build_momentum_panel
from agx_research.patterns.regimes import (
    BUCKET_COUNT_SENSITIVITY_GRID,
    DEFAULT_BUCKET_COUNT,
    PatternRegimeTag,
    RegimeDimension,
    RegimeSeries,
    analyze_pattern_failure_conditions,
    build_regime_series,
    bucket_count_sensitivity,
)
from agx_research.patterns.candidates import CandidateGeneratorConfig
from agx_research.patterns.engine import PatternDiscoveryEngine, PatternDiscoveryEngineConfig
from agx_research.patterns.multiple_testing import TestingLedgerRepository
from agx_research.patterns.registry import PatternRegistry, PatternStatus
from agx_research.patterns.validation import WalkForwardValidatorConfig


def _validated_momentum_pattern(seed: int = 1):
    panel = build_momentum_panel(seed)
    registry = PatternRegistry()
    engine = PatternDiscoveryEngine(
        pattern_registry=registry,
        testing_ledger_repository=TestingLedgerRepository(),
        config=PatternDiscoveryEngineConfig(
            candidate_config=CandidateGeneratorConfig(
                min_sample_size=15, correlation_prune_threshold=0.8, max_candidates_per_ticker=40,
                enable_three_feature=False, enable_regime_conditioning=False,
            ),
            walk_forward_config=WalkForwardValidatorConfig(n_folds=3, min_train_size=40, min_oos_sample_size=8, embargo_days=2),
            fdr_alpha=0.10, run_robustness=True, require_beats_baseline=True, horizons=(5,),
            enable_barrier_targets=False, enable_lead_lag=True,
        ),
    )
    engine.discover(panel)
    engine.validate(panel)
    engine.final_holdout(panel)
    validated = registry.by_status(PatternStatus.VALIDATED)
    return validated[0], panel


def test_regime_series_bucket_at_is_point_in_time_safe_and_forward_fills():
    series = RegimeSeries(
        dimension=RegimeDimension.VOLATILITY, k=3,
        dates=[date(2020, 1, 2), date(2020, 1, 3), date(2020, 1, 6)],
        buckets=[None, 1, 2],
    )
    assert series.bucket_at(date(2020, 1, 2)) is None
    assert series.bucket_at(date(2020, 1, 3)) == 1
    assert series.bucket_at(date(2020, 1, 4)) == 1  # forward-fills to the most recent known bucket
    assert series.bucket_at(date(2020, 1, 6)) == 2
    assert series.bucket_at(date(2019, 1, 1)) is None  # strictly before any data


def test_build_regime_series_covers_every_dimension_without_crashing():
    panel = build_momentum_panel(1)
    for dimension in RegimeDimension:
        series = build_regime_series(panel, dimension, k=DEFAULT_BUCKET_COUNT)
        assert series.dimension is dimension
        assert series.k == DEFAULT_BUCKET_COUNT
        assert len(series.dates) == len(series.buckets)
        # Every non-null bucket must be a valid index into [0, k).
        assert all(b is None or 0 <= b < DEFAULT_BUCKET_COUNT for b in series.buckets)


def test_build_regime_series_never_reads_data_after_the_bucketed_date():
    """Point-in-time safety proof: truncating the panel's tail must not
    change any bucket assigned to an earlier date -- a real look-ahead
    leak would let a later value influence an earlier bucket."""
    panel = build_momentum_panel(1)
    full = build_regime_series(panel, RegimeDimension.VOLATILITY, k=3)

    ticker = "A"
    series = panel.series[ticker]
    truncated_series = series.model_copy(
        update={
            "dates": series.dates[:-20], "open": series.open[:-20], "high": series.high[:-20],
            "low": series.low[:-20], "close": series.close[:-20],
            "adjusted_close": series.adjusted_close[:-20], "volume": series.volume[:-20],
        }
    )
    truncated_panel = panel.model_copy(
        update={
            "series": {**panel.series, ticker: truncated_series},
            "as_of": truncated_series.dates[-1],
        }
    )
    truncated = build_regime_series(truncated_panel, RegimeDimension.VOLATILITY, k=3)

    # Only dates still present in A's own (truncated) series are a fair
    # comparison -- a date inside the removed tail legitimately forward-
    # fills to A's last real value in the truncated version, which is not
    # a look-ahead leak, just a different (and correct) input.
    still_present = set(truncated_series.dates)
    full_by_date = dict(zip(full.dates, full.buckets))
    truncated_by_date = dict(zip(truncated.dates, truncated.buckets))
    checked = 0
    for d in still_present:
        if d in full_by_date and d in truncated_by_date:
            checked += 1
            assert full_by_date[d] == truncated_by_date[d], f"bucket for {d} changed after truncating the future"
    assert checked > 50  # sanity: the comparison actually exercised a real, sizeable date range


def test_analyze_pattern_failure_conditions_tags_a_real_unconditional_momentum_pattern():
    pattern, panel = _validated_momentum_pattern(seed=1)
    profile = analyze_pattern_failure_conditions(pattern, panel)
    assert profile.pattern_id == pattern.id
    assert len(profile.per_dimension) == len(RegimeDimension)
    assert len(profile.bucket_count_sensitivity) == len(RegimeDimension)
    # A clean, planted, unconditional momentum relationship should not be
    # tagged UNSTABLE (sign flipping across regimes) -- it's the same
    # relationship regardless of market backdrop by construction.
    assert profile.overall_tag != PatternRegimeTag.UNSTABLE


def test_analyze_pattern_failure_conditions_handles_a_lead_lag_pattern():
    lead_lag_panel = build_lead_lag_panel(1)
    registry = PatternRegistry()
    engine = PatternDiscoveryEngine(
        pattern_registry=registry,
        testing_ledger_repository=TestingLedgerRepository(),
        config=PatternDiscoveryEngineConfig(
            candidate_config=CandidateGeneratorConfig(
                min_sample_size=15, correlation_prune_threshold=0.999, max_candidates_per_ticker=60,
                enable_two_feature=False, enable_three_feature=False, enable_regime_conditioning=False,
            ),
            walk_forward_config=WalkForwardValidatorConfig(n_folds=3, min_train_size=40, min_oos_sample_size=8, embargo_days=2),
            fdr_alpha=0.10, run_robustness=True, require_beats_baseline=True, horizons=(5,),
            enable_barrier_targets=False, enable_lead_lag=True,
        ),
    )
    engine.discover(lead_lag_panel)
    engine.validate(lead_lag_panel)
    engine.final_holdout(lead_lag_panel)
    validated = [p for p in registry.by_status(PatternStatus.VALIDATED) if p.is_lead_lag]
    assert validated
    profile = analyze_pattern_failure_conditions(validated[0], lead_lag_panel)
    assert profile.pattern_id == validated[0].id
    assert profile.overall_tag in set(PatternRegimeTag)


def test_bucket_count_sensitivity_grid_matches_declared_constant():
    pattern, panel = _validated_momentum_pattern(seed=1)
    from agx_research.patterns.regimes import _reconstruct_matched_outcomes

    matched = _reconstruct_matched_outcomes(pattern, panel)
    results = bucket_count_sensitivity(pattern, panel, matched)
    assert len(results) == len(RegimeDimension)
    for r in results:
        assert set(r.signs_by_k.keys()) == set(BUCKET_COUNT_SENSITIVITY_GRID)


def test_analyze_pattern_failure_conditions_returns_insufficient_data_when_pattern_ticker_is_absent():
    pattern, panel = _validated_momentum_pattern(seed=1)
    empty_panel = panel.model_copy(update={"series": {}, "tickers": []})
    profile = analyze_pattern_failure_conditions(pattern, empty_panel)
    assert profile.overall_tag == PatternRegimeTag.INSUFFICIENT_DATA
    assert all(not n.bucket_outcomes for n in profile.per_dimension)
