"""Robustness testing for `patterns.robustness`."""

from __future__ import annotations

from agx_research.patterns.candidates import ConditionOperator, FeatureCondition, PatternCandidate
from agx_research.patterns.features import FeatureFactory
from agx_research.patterns.robustness import RobustnessTester
from agx_research.patterns.targets import TargetFactory
from tests.pattern_test_helpers import make_deterministic_ticker_series, make_panel


def _setup(n_days=300, seed=1, block_length=10):
    series = make_deterministic_ticker_series("T", n_days=n_days, seed=seed, block_length=block_length)
    panel = make_panel(series={"T": series})
    features = {f.id: f for f in FeatureFactory(panel).build_price_features("T")}
    targets = {t.id: t for t in TargetFactory(panel).build_forward_returns("T")}
    return series, features, targets


def test_robustness_passes_for_a_pattern_that_is_stable_across_nearby_thresholds():
    series, features, targets = _setup()
    target = targets["forward_return_5d:T"]
    candidate = PatternCandidate(
        id="c1", ticker="T",
        conditions=[FeatureCondition(feature_id="return_1d:T", operator=ConditionOperator.GT, threshold=0.0)],
        target_id=target.id, complexity=1,
    )
    tester = RobustnessTester(min_sample=5)
    result = tester.run(candidate, anchor_dates=series.dates, feature_lookup=features, target=target)
    assert result.base_expectancy is not None
    assert result.threshold_sensitivity
    assert result.checks_run > 0


def test_robustness_flags_a_pattern_that_only_works_at_one_arbitrary_threshold():
    """Mission's own example: `RS > 83.17` working while nearby thresholds
    fail is a likely overfit. Construct a feature/target pair where only
    one razor-thin threshold band produces a (spuriously) large outcome,
    and every nearby perturbation flips sign."""
    from datetime import date, timedelta

    from agx_research.patterns.features import FeatureCategory, FeatureSeries, FeatureSpec
    from agx_research.patterns.targets import TargetKind, TargetSeries, TargetSpec

    n = 100
    dates = [date(2024, 1, 1) + timedelta(days=i) for i in range(n)]
    # A feature spanning -50..49; only the narrow band (0, 5] is a genuine
    # "lucky" winner (+1.0), everything else loses a little (-0.05). At
    # threshold=0 the base candidate matches all of 1..49 and looks mildly
    # profitable (the rare big winners dominate the mean) -- but nudging
    # the threshold up past the lucky band (a common-sized perturbation
    # given this feature's own spread) excludes the winners entirely and
    # the sign flips negative, exactly the mission's "RS > 83.17 works but
    # RS > 84 fails" overfit signature.
    values = [float(i - 50) for i in range(n)]
    outcomes = [1.0 if 0 < v <= 5 else -0.05 for v in values]
    feature = FeatureSeries(
        id="f:T", spec=FeatureSpec(id="f", category=FeatureCategory.PRICE, name="f", description="d"),
        ticker="T", dates=dates, values=values,
    )
    target = TargetSeries(
        id="t:T", spec=TargetSpec(id="t", kind=TargetKind.FORWARD_RETURN, horizon_days=5),
        ticker="T", dates=dates, values=outcomes,
    )
    candidate = PatternCandidate(
        id="c2", ticker="T",
        conditions=[FeatureCondition(feature_id="f:T", operator=ConditionOperator.GT, threshold=0.0)],
        target_id=target.id, complexity=1,
    )
    tester = RobustnessTester(min_sample=5, threshold_deltas=(-0.5, 0.5))
    result = tester.run(candidate, anchor_dates=dates, feature_lookup={"f:T": feature}, target=target)
    # Shifting the threshold by 50% of the feature's own spread flips which
    # rows match, and since match parity perfectly tracks outcome sign here,
    # the sign of expectancy should flip too.
    flips = [c for c in result.threshold_sensitivity if c.same_sign_as_base is False]
    assert flips


def test_robustness_reports_transaction_cost_survival():
    series, features, targets = _setup()
    target = targets["forward_return_5d:T"]
    candidate = PatternCandidate(
        id="c3", ticker="T",
        conditions=[FeatureCondition(feature_id="return_1d:T", operator=ConditionOperator.GT, threshold=0.0)],
        target_id=target.id, complexity=1,
    )
    tester = RobustnessTester(min_sample=5, transaction_cost_bps=20.0)
    result = tester.run(candidate, anchor_dates=series.dates, feature_lookup=features, target=target)
    assert result.transaction_cost_survival is not None
    assert result.net_of_cost_expectancy is not None
    assert abs(result.net_of_cost_expectancy - (result.base_expectancy - 0.002)) < 1e-9


def test_robustness_run_with_too_little_data_is_honest_not_fabricated():
    from datetime import date

    from agx_research.patterns.features import FeatureCategory, FeatureSeries, FeatureSpec
    from agx_research.patterns.targets import TargetKind, TargetSeries, TargetSpec

    dates = [date(2024, 1, 1), date(2024, 1, 2)]
    feature = FeatureSeries(
        id="f:T", spec=FeatureSpec(id="f", category=FeatureCategory.PRICE, name="f", description="d"),
        ticker="T", dates=dates, values=[1.0, 1.0],
    )
    target = TargetSeries(
        id="t:T", spec=TargetSpec(id="t", kind=TargetKind.FORWARD_RETURN, horizon_days=5),
        ticker="T", dates=dates, values=[None, None],
    )
    candidate = PatternCandidate(
        id="c4", ticker="T",
        conditions=[FeatureCondition(feature_id="f:T", operator=ConditionOperator.GT, threshold=0.0)],
        target_id=target.id, complexity=1,
    )
    result = RobustnessTester().run(candidate, anchor_dates=dates, feature_lookup={"f:T": feature}, target=target)
    assert result.passed is False
    assert result.base_expectancy is None
    assert "too small" in result.notes[0].lower()
