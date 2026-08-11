"""Lead/lag discovery (mission Phase 10): `X(t-k) -> Y(t)` candidate
generation, the sector-leader predictor-feature plumbing, and the
regression this module exists to guard -- `validate()`/`final_holdout()`
reconstruct a `PatternCandidate` from a persisted `Pattern` and must look
up a lead/lag pattern's cross-ticker predictor feature correctly, or the
condition silently reads as "feature missing" and the pattern fails every
time regardless of whether the relationship is real.
"""

from __future__ import annotations

import random

from agx_research.patterns.candidates import (
    CandidateGeneratorConfig,
    ConditionOperator,
    FeatureCondition,
    PatternCandidateGenerator,
)
from agx_research.patterns.engine import (
    PatternDiscoveryEngine,
    PatternDiscoveryEngineConfig,
    _lead_lag_predictor_features,
    _sector_leaders,
)
from agx_research.patterns.features import FeatureFactory
from agx_research.patterns.multiple_testing import TestingLedgerRepository
from agx_research.patterns.panel import TickerSeries
from agx_research.patterns.registry import PatternRegistry, PatternStatus
from agx_research.patterns.targets import TargetFactory
from agx_research.patterns.validation import WalkForwardValidatorConfig
from tests.pattern_test_helpers import make_deterministic_ticker_series, make_panel


def _build_leader_follower_panel(*, lag: int, n_days: int, block_length: int = 10, sector: str = "Banks"):
    """LEADER is a real, deterministic momentum series (same construction
    `pattern_test_helpers` already uses as its positive control). FOLLOWER's
    own daily return at day `i` is deliberately built to equal LEADER's
    daily return at day `i - lag` (plus tiny noise) -- a genuine,
    real, planted `LEADER.return_1d(t-lag) -> FOLLOWER's forward return`
    relationship, not a coincidence. FOLLOWER's volume is kept well below
    LEADER's so LEADER is unambiguously the sector's volume leader."""
    leader = make_deterministic_ticker_series(
        "LEADER", n_days=n_days, seed=3, block_length=block_length,
        daily_drift=0.012, noise_stdev=0.0003, sector=sector,
    )
    leader_daily_returns = [
        0.0 if i == 0 else (leader.close[i] - leader.close[i - 1]) / leader.close[i - 1]
        for i in range(n_days)
    ]
    rng = random.Random(101)
    follower_closes = [100.0]
    for i in range(1, n_days):
        driver = leader_daily_returns[i - lag] if i - lag >= 0 else 0.0
        follower_closes.append(follower_closes[-1] * (1 + driver + rng.gauss(0, 0.00005)))
    follower = TickerSeries(
        ticker="FOLLOWER",
        dates=leader.dates,
        open=[follower_closes[0], *follower_closes[:-1]],
        high=[c * 1.002 for c in follower_closes],
        low=[c * 0.998 for c in follower_closes],
        close=follower_closes,
        adjusted_close=list(follower_closes),
        volume=[50_000] * n_days,
        sector=sector,
    )
    panel = make_panel(series={"LEADER": leader, "FOLLOWER": follower})
    return panel, leader, follower


def test_feature_condition_read_dispatches_on_lag_days():
    series = make_deterministic_ticker_series("T", n_days=30, seed=1)
    panel = make_panel(series={"T": series})
    feature = next(f for f in FeatureFactory(panel).build_price_features("T") if f.spec.id == "return_1d")
    anchor = series.dates[20]

    no_lag = FeatureCondition(feature_id=feature.id, operator=ConditionOperator.GT, threshold=0.0)
    assert no_lag.read(feature, anchor) == feature.as_of_value(anchor)

    lagged = FeatureCondition(feature_id=feature.id, operator=ConditionOperator.GT, threshold=0.0, lag_days=4)
    assert lagged.read(feature, anchor) == feature.lagged_as_of_value(anchor, 4)
    assert lagged.read(feature, anchor) != no_lag.read(feature, anchor)


def test_sector_leaders_picks_the_highest_total_volume_ticker_per_sector():
    panel, leader, follower = _build_leader_follower_panel(lag=3, n_days=100)
    leaders = _sector_leaders(panel)
    assert leaders == {"Banks": "LEADER"}
    assert sum(leader.volume) > sum(follower.volume)


def test_sector_leaders_ignores_tickers_with_no_sector_assigned():
    a = make_deterministic_ticker_series("A", n_days=50, seed=1, sector=None)
    panel = make_panel(series={"A": a})
    assert _sector_leaders(panel) == {}


def test_lead_lag_predictor_features_include_the_leaders_curated_features_but_not_the_leader_itself():
    panel, leader, follower = _build_leader_follower_panel(lag=3, n_days=100)
    all_features = FeatureFactory(panel).build_all()
    market_features = [f for f in all_features if f.ticker == ""]
    sector_leaders = _sector_leaders(panel)

    predictors = _lead_lag_predictor_features(
        panel, all_features, market_features, "FOLLOWER", sector_leaders,
        ("return_1d", "return_5d", "relative_volume_5d"),
    )
    predictor_ids = {f.id for f in predictors}
    assert "return_1d:LEADER" in predictor_ids
    assert "return_5d:LEADER" in predictor_ids
    assert not any(f.ticker == "FOLLOWER" for f in predictors)

    # The leader itself has no peer to borrow from (it IS the leader).
    leader_predictors = _lead_lag_predictor_features(
        panel, all_features, market_features, "LEADER", sector_leaders,
        ("return_1d", "return_5d", "relative_volume_5d"),
    )
    assert not any(f.ticker == "LEADER" for f in leader_predictors)


def test_generate_lead_lag_finds_the_planted_relationship():
    lag = 5
    panel, leader, follower = _build_leader_follower_panel(lag=lag, n_days=220, block_length=10)
    leader_features = FeatureFactory(panel).build_price_features("LEADER")
    predictor = next(f for f in leader_features if f.spec.id == "return_1d")
    target = next(
        t for t in TargetFactory(panel).build_forward_returns("FOLLOWER") if t.spec.horizon_days == 5
    )

    generator = PatternCandidateGenerator(
        CandidateGeneratorConfig(min_sample_size=15, correlation_prune_threshold=0.999)
    )
    candidates = generator.generate_lead_lag(
        ticker="FOLLOWER", anchor_dates=follower.dates, target=target, predictor_features=[predictor],
    )

    assert candidates
    assert all(c.is_lead_lag for c in candidates)
    assert all(c.ticker == "FOLLOWER" for c in candidates)
    assert all(c.conditions[0].feature_id == predictor.id for c in candidates)
    assert all(c.conditions[0].lag_days > 0 for c in candidates)


def test_generate_lead_lag_respects_the_minimum_sample_size_floor():
    panel, leader, follower = _build_leader_follower_panel(lag=3, n_days=60)
    leader_features = FeatureFactory(panel).build_price_features("LEADER")
    predictor = next(f for f in leader_features if f.spec.id == "return_1d")
    target = next(
        t for t in TargetFactory(panel).build_forward_returns("FOLLOWER") if t.spec.horizon_days == 5
    )

    generator = PatternCandidateGenerator(
        CandidateGeneratorConfig(min_sample_size=1_000_000, correlation_prune_threshold=0.999)
    )
    candidates = generator.generate_lead_lag(
        ticker="FOLLOWER", anchor_dates=follower.dates, target=target, predictor_features=[predictor],
    )
    assert candidates == []


def test_engine_carries_a_lead_lag_pattern_through_validate_and_final_holdout():
    """Regression test for the exact bug fixed in `validate()`/
    `final_holdout()`: reconstructing a lead/lag `PatternCandidate` from
    its persisted `Pattern` must rebuild a `feature_lookup` that includes
    the sector leader's predictor feature, not just the pattern's own
    ticker plus market-wide features -- otherwise `matches()` always
    reports the feature missing, every match count is zero, and a
    genuinely real lead/lag relationship can never survive validation or
    holdout no matter how strong it is.
    """
    panel, leader, follower = _build_leader_follower_panel(lag=3, n_days=260, block_length=10)
    registry = PatternRegistry()
    engine = PatternDiscoveryEngine(
        pattern_registry=registry,
        testing_ledger_repository=TestingLedgerRepository(),
        config=PatternDiscoveryEngineConfig(
            candidate_config=CandidateGeneratorConfig(
                min_sample_size=15,
                correlation_prune_threshold=0.999,
                max_candidates_per_ticker=60,
                enable_two_feature=False,
                enable_three_feature=False,
                enable_regime_conditioning=False,
            ),
            walk_forward_config=WalkForwardValidatorConfig(
                n_folds=3, min_train_size=40, min_oos_sample_size=8, embargo_days=2
            ),
            fdr_alpha=0.2,
            run_robustness=False,
            require_beats_baseline=False,
            horizons=(5,),
            enable_barrier_targets=False,
            enable_lead_lag=True,
        ),
    )

    engine.discover(panel)
    discovered_lead_lag = [
        p for p in registry.by_status(PatternStatus.DISCOVERED) if p.is_lead_lag and p.ticker == "FOLLOWER"
    ]
    assert discovered_lead_lag, "the planted LEADER -> FOLLOWER relationship should generate a lead/lag candidate"

    engine.validate(panel)
    validating_lead_lag = [p for p in registry.by_status(PatternStatus.VALIDATING) if p.is_lead_lag]
    assert validating_lead_lag, (
        "a genuinely planted lead/lag relationship should survive purged walk-forward validation "
        "when its cross-ticker feature_lookup is reconstructed correctly"
    )

    engine.final_holdout(panel)
    validated_lead_lag = [p for p in registry.by_status(PatternStatus.VALIDATED) if p.is_lead_lag]
    assert validated_lead_lag, (
        "final_holdout() must also find the leader's predictor feature -- a holdout_sample_size "
        "of 0 here means the cross-ticker feature_lookup regressed"
    )
    pattern = validated_lead_lag[0]
    assert pattern.holdout_sample_size > 0
    assert pattern.holdout_period is not None
