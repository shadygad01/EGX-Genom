"""Live pattern activation for `patterns.live`."""

from __future__ import annotations

from datetime import date

from agx_research.patterns.candidates import ConditionOperator, FeatureCondition, PatternCandidate
from agx_research.patterns.evaluation import evaluate_outcomes
from agx_research.patterns.features import FeatureCategory, FeatureSeries, FeatureSpec
from agx_research.patterns.live import LiveActivationEngine, RegimeCompatibility
from agx_research.patterns.registry import Pattern, PatternRegistry, PatternStatus, build_pattern
from agx_research.patterns.validation import WalkForwardResult


def _feature(as_of: date, value: float) -> FeatureSeries:
    return FeatureSeries(
        id="return_5d:COMI",
        spec=FeatureSpec(id="return_5d", category=FeatureCategory.PRICE, name="return_5d", description="d"),
        ticker="COMI", dates=[date(2024, 1, 1), as_of], values=[0.0, value],
    )


def _validated_pattern(*, threshold: float = 0.01, regime_filter: FeatureCondition | None = None) -> Pattern:
    candidate = PatternCandidate(
        id="c1", ticker="COMI",
        conditions=[FeatureCondition(feature_id="return_5d:COMI", operator=ConditionOperator.GT, threshold=threshold)],
        regime_filter=regime_filter,
        target_id="forward_return_5d:COMI", complexity=1,
    )
    distribution = evaluate_outcomes([0.01, 0.02, 0.015, 0.03, 0.02, -0.01, 0.01, 0.02, 0.01, 0.015])
    wf_result = WalkForwardResult(
        candidate_id=candidate.id, n_folds_attempted=2, n_folds_valid=2,
        discovery_distribution=distribution, oos_distribution=distribution, oos_sample_size=10,
        survived=True, reasons=["ok"],
    )
    return build_pattern(
        pattern_id="pattern_live_1", candidate=candidate, horizon_days=5, walk_forward=wf_result, robustness=None,
        discovery_period=(date(2024, 1, 1), date(2024, 6, 1)), validation_period=(date(2024, 6, 1), date(2024, 9, 1)),
        number_of_tests=50, status=PatternStatus.VALIDATED, produced_by="test@1.0.0",
    )


def test_activation_fires_when_conditions_are_met():
    registry = PatternRegistry()
    registry.add(_validated_pattern(threshold=0.01))
    feature_lookup = {"return_5d:COMI": _feature(date(2024, 1, 5), 0.05)}  # 0.05 > 0.01

    activations = LiveActivationEngine(registry).evaluate(as_of=date(2024, 1, 5), feature_lookup=feature_lookup)
    assert len(activations) == 1
    assert activations[0].label == "ACTIVE_PATTERN"
    assert activations[0].current_match is True
    assert activations[0].pattern_id == "pattern_live_1"
    assert activations[0].historical_expectancy > 0


def test_no_activation_when_condition_is_not_met():
    registry = PatternRegistry()
    registry.add(_validated_pattern(threshold=0.10))
    feature_lookup = {"return_5d:COMI": _feature(date(2024, 1, 5), 0.05)}  # 0.05 < 0.10

    activations = LiveActivationEngine(registry).evaluate(as_of=date(2024, 1, 5), feature_lookup=feature_lookup)
    assert activations == []


def test_no_activation_when_feature_is_unavailable():
    registry = PatternRegistry()
    registry.add(_validated_pattern())
    activations = LiveActivationEngine(registry).evaluate(as_of=date(2024, 1, 5), feature_lookup={})
    assert activations == []


def test_discovered_and_rejected_patterns_are_never_activated():
    registry = PatternRegistry()
    discovered = _validated_pattern()
    registry.add(discovered)
    registry.transition(discovered.id, PatternStatus.REJECTED, reason="test")
    feature_lookup = {"return_5d:COMI": _feature(date(2024, 1, 5), 0.05)}
    activations = LiveActivationEngine(registry).evaluate(as_of=date(2024, 1, 5), feature_lookup=feature_lookup)
    assert activations == []


def test_regime_filter_present_reports_compatible_not_unknown():
    regime_condition = FeatureCondition(feature_id="market_breadth:MARKET", operator=ConditionOperator.GT, threshold=0.5)
    registry = PatternRegistry()
    registry.add(_validated_pattern(regime_filter=regime_condition))
    feature_lookup = {
        "return_5d:COMI": _feature(date(2024, 1, 5), 0.05),
        "market_breadth:MARKET": FeatureSeries(
            id="market_breadth:MARKET",
            spec=FeatureSpec(id="market_breadth", category=FeatureCategory.CROSS_SECTIONAL, name="b", description="d"),
            ticker="", dates=[date(2024, 1, 5)], values=[0.7],
        ),
    }
    activations = LiveActivationEngine(registry).evaluate(as_of=date(2024, 1, 5), feature_lookup=feature_lookup)
    assert len(activations) == 1
    assert activations[0].regime_compatibility is RegimeCompatibility.COMPATIBLE
    assert any("[regime]" in e for e in activations[0].evidence)


def test_activation_evidence_and_invalidation_conditions_are_populated():
    registry = PatternRegistry()
    registry.add(_validated_pattern(threshold=0.01))
    feature_lookup = {"return_5d:COMI": _feature(date(2024, 1, 5), 0.05)}
    activations = LiveActivationEngine(registry).evaluate(as_of=date(2024, 1, 5), feature_lookup=feature_lookup)
    assert activations[0].evidence
    assert activations[0].invalidation_conditions
