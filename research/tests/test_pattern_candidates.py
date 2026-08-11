"""Candidate generation, eligibility, and sample-size floor for
`patterns.candidates`."""

from __future__ import annotations

from agx_research.patterns.candidates import (
    CandidateGeneratorConfig,
    ConditionOperator,
    FeatureCondition,
    PatternCandidateGenerator,
)
from agx_research.patterns.features import FeatureFactory
from agx_research.patterns.targets import TargetFactory
from tests.pattern_test_helpers import make_deterministic_ticker_series, make_panel


def _context(n_days=200, seed=1):
    series = make_deterministic_ticker_series("T", n_days=n_days, seed=seed)
    panel = make_panel(series={"T": series})
    features = FeatureFactory(panel).build_price_features("T")
    targets = TargetFactory(panel).build_forward_returns("T")
    return panel, series, features, targets


def test_eligible_features_drops_series_below_min_sample_size():
    _, _, features, _ = _context()
    generator = PatternCandidateGenerator(CandidateGeneratorConfig(min_sample_size=1_000_000))
    assert generator.eligible_features(features) == []


def test_eligible_features_prunes_highly_correlated_duplicates():
    _, _, features, _ = _context()
    generator = PatternCandidateGenerator(CandidateGeneratorConfig(min_sample_size=10, correlation_prune_threshold=0.99))
    eligible = generator.eligible_features(features)
    # return_1d and acceleration_1d are near-mechanical transforms of each
    # other over a smooth synthetic series -- pruning should leave fewer
    # series than went in.
    assert len(eligible) < len(features)


def test_generated_candidates_always_clear_min_sample_size_in_practice():
    _, series, features, targets = _context()
    generator = PatternCandidateGenerator(CandidateGeneratorConfig(min_sample_size=20, correlation_prune_threshold=0.999))
    candidates = generator.generate(
        ticker="T", anchor_dates=series.dates, features=features, targets=targets, market_features=[]
    )
    for candidate in candidates:
        matched = sum(
            1
            for d in series.dates
            if candidate.matches({f.id: f for f in features}, d) and any(t.value_at(d) is not None for t in targets)
        )
        assert matched >= 20


def test_no_candidates_when_no_feature_clears_the_floor():
    _, series, features, targets = _context(n_days=10)
    generator = PatternCandidateGenerator(CandidateGeneratorConfig(min_sample_size=30))
    candidates = generator.generate(
        ticker="T", anchor_dates=series.dates, features=features, targets=targets, market_features=[]
    )
    assert candidates == []


def test_three_feature_candidates_require_enough_headroom():
    _, series, features, targets = _context(n_days=300)
    generator = PatternCandidateGenerator(
        CandidateGeneratorConfig(
            min_sample_size=20, correlation_prune_threshold=0.999, three_feature_min_headroom=1000,
        )
    )
    candidates = generator.generate(
        ticker="T", anchor_dates=series.dates, features=features, targets=targets, market_features=[]
    )
    assert all(c.complexity <= 2 for c in candidates)  # impossible headroom means no 3-feature survivors


def test_regime_conditioned_candidate_has_a_regime_filter_and_higher_complexity():
    _, series, features, targets = _context(n_days=250)
    market_feature = next(f for f in features if f.spec.id == "return_5d")
    market_feature = market_feature.model_copy(update={"ticker": "", "id": "return_5d:MARKET"})
    generator = PatternCandidateGenerator(
        CandidateGeneratorConfig(
            min_sample_size=20, correlation_prune_threshold=0.999,
            regime_feature_ids=("return_5d:MARKET",), enable_two_feature=False, enable_three_feature=False,
        )
    )
    candidates = generator.generate(
        ticker="T", anchor_dates=series.dates, features=features, targets=targets, market_features=[market_feature]
    )
    regime_conditioned = [c for c in candidates if c.is_regime_conditioned]
    assert regime_conditioned
    for c in regime_conditioned:
        assert c.regime_filter is not None
        assert c.complexity == len(c.conditions) + 1


def test_candidate_matches_returns_none_when_a_feature_is_missing():
    condition = FeatureCondition(feature_id="does_not_exist:T", operator=ConditionOperator.GT, threshold=0.0)
    from agx_research.patterns.candidates import PatternCandidate

    candidate = PatternCandidate(id="c", ticker="T", conditions=[condition], target_id="t", complexity=1)
    anchor_date = make_deterministic_ticker_series("T", n_days=5).dates[0]
    assert candidate.matches({}, anchor_date) is None
