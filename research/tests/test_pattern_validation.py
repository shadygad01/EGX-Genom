"""Walk-forward splits, purging, and embargo for `patterns.validation`."""

from __future__ import annotations

from datetime import date, timedelta

from agx_research.patterns.candidates import ConditionOperator, FeatureCondition, PatternCandidate
from agx_research.patterns.features import FeatureCategory, FeatureSpec, FeatureSeries
from agx_research.patterns.targets import TargetKind, TargetSeries, TargetSpec
from agx_research.patterns.validation import (
    WalkForwardValidator,
    WalkForwardValidatorConfig,
    chronological_split,
    purge_and_embargo,
    walk_forward_index_folds,
)


def test_chronological_split_is_never_random():
    dates = [date(2024, 1, 1) + timedelta(days=i) for i in range(10)]
    train_a, test_a = chronological_split(dates, train_fraction=0.7)
    train_b, test_b = chronological_split(dates, train_fraction=0.7)
    assert train_a == train_b and test_a == test_b  # deterministic, not shuffled
    assert train_a == dates[:7]
    assert test_a == dates[7:]


def test_walk_forward_folds_are_expanding_and_chronological():
    folds = walk_forward_index_folds(100, n_folds=4, min_train_size=20)
    assert len(folds) == 4
    for i in range(1, len(folds)):
        # each fold's test period starts exactly where the previous one's ended
        assert folds[i][2] == folds[i - 1][3]
        # training start is always 0 (expanding window), never later
        assert folds[i][0] == 0
        assert folds[i][1] == folds[i][2]  # train_end == test_start


def test_walk_forward_folds_empty_when_not_enough_data():
    assert walk_forward_index_folds(10, n_folds=4, min_train_size=20) == []


def test_purge_and_embargo_shrinks_train_end_by_horizon_plus_embargo():
    # test starts at index 50; a target with a 5-day horizon plus a 2-day
    # embargo must purge any training index whose own forward window
    # could reach into [50-5-2, ...] = up to index 43.
    adjusted = purge_and_embargo(train_end_idx=48, test_start_idx=50, horizon_days=5, embargo_days=2)
    assert adjusted == 43


def test_purge_and_embargo_never_goes_negative():
    adjusted = purge_and_embargo(train_end_idx=10, test_start_idx=5, horizon_days=20, embargo_days=10)
    assert adjusted == 0


def _make_feature(dates: list[date], values: list[float | None]) -> FeatureSeries:
    return FeatureSeries(
        id="f:T", spec=FeatureSpec(id="f", category=FeatureCategory.PRICE, name="f", description="d"),
        ticker="T", dates=dates, values=values,
    )


def _make_target(dates: list[date], values: list[float | None]) -> TargetSeries:
    return TargetSeries(
        id="forward_return_5d:T",
        spec=TargetSpec(id="forward_return_5d", kind=TargetKind.FORWARD_RETURN, horizon_days=5),
        ticker="T", dates=dates, values=values,
    )


def test_walk_forward_validator_reports_not_enough_data_honestly():
    dates = [date(2024, 1, 1) + timedelta(days=i) for i in range(10)]
    feature = _make_feature(dates, [1.0] * 10)
    target = _make_target(dates, [0.01] * 10)
    candidate = PatternCandidate(
        id="c1", ticker="T", conditions=[FeatureCondition(feature_id="f:T", operator=ConditionOperator.GT, threshold=0.5)],
        target_id=target.id, complexity=1,
    )
    result = WalkForwardValidator(WalkForwardValidatorConfig(n_folds=4, min_train_size=30)).validate(
        candidate, anchor_dates=dates, feature_lookup={"f:T": feature}, target=target
    )
    assert result.survived is False
    assert result.n_folds_valid == 0
    assert "not enough" in result.reasons[0].lower()


def test_walk_forward_validator_survives_a_consistent_signal():
    n = 120
    dates = [date(2020, 1, 1) + timedelta(days=i) for i in range(n)]
    # Feature and target both alternate in lockstep every 10 days, a
    # perfectly consistent (noise-free) relationship across the whole run.
    values = [1.0 if (i // 10) % 2 == 0 else -1.0 for i in range(n)]
    feature = _make_feature(dates, values)
    target = _make_target(dates, [0.02 if v > 0 else -0.02 for v in values])
    candidate = PatternCandidate(
        id="c2", ticker="T", conditions=[FeatureCondition(feature_id="f:T", operator=ConditionOperator.GT, threshold=0.0)],
        target_id=target.id, complexity=1,
    )
    result = WalkForwardValidator(
        WalkForwardValidatorConfig(n_folds=4, min_train_size=20, min_oos_sample_size=5, embargo_days=1)
    ).validate(candidate, anchor_dates=dates, feature_lookup={"f:T": feature}, target=target)
    assert result.n_folds_valid > 0
    assert result.survived is True
    assert result.oos_distribution is not None
    assert result.oos_distribution.expectancy > 0


def test_walk_forward_validator_rejects_a_sign_flipping_relationship():
    """A relationship whose full-sample (discovery) mean is positive only
    because a strong early period dominates, while every genuinely
    out-of-sample fold (everything past `min_train_size=20`, where no
    fold ever tests) is consistently negative, must not survive -- the
    exact "worked on the full historical dataset but not out of sample"
    case the mission calls out by name."""
    n = 100
    dates = [date(2020, 1, 1) + timedelta(days=i) for i in range(n)]
    values = [1.0] * n
    # A large positive run confined to the pre-min_train_size period (never
    # tested out-of-sample) followed by a consistently negative regime for
    # the entire remainder (100% of every walk-forward test fold).
    outcomes = [0.10 if i < 20 else -0.02 for i in range(n)]
    feature = _make_feature(dates, values)
    target = _make_target(dates, outcomes)
    candidate = PatternCandidate(
        id="c3", ticker="T", conditions=[FeatureCondition(feature_id="f:T", operator=ConditionOperator.GT, threshold=0.5)],
        target_id=target.id, complexity=1,
    )
    result = WalkForwardValidator(
        WalkForwardValidatorConfig(n_folds=4, min_train_size=20, min_oos_sample_size=5, embargo_days=0)
    ).validate(candidate, anchor_dates=dates, feature_lookup={"f:T": feature}, target=target)
    assert result.survived is False
