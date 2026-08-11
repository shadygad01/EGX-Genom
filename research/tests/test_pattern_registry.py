"""Registry persistence and lifecycle transitions for `patterns.registry`."""

from __future__ import annotations

from datetime import date

import pytest

from agx_research.patterns.candidates import ConditionOperator, FeatureCondition, PatternCandidate
from agx_research.patterns.evaluation import evaluate_outcomes
from agx_research.patterns.registry import Pattern, PatternRegistry, PatternStatus, build_pattern
from agx_research.patterns.validation import WalkForwardResult


def _make_pattern(pattern_id: str = "pattern_1", status: PatternStatus = PatternStatus.DISCOVERED) -> Pattern:
    candidate = PatternCandidate(
        id="c1", ticker="COMI",
        conditions=[FeatureCondition(feature_id="return_5d:COMI", operator=ConditionOperator.GT, threshold=0.01)],
        target_id="forward_return_5d:COMI", complexity=1,
    )
    distribution = evaluate_outcomes([0.01, 0.02, -0.01, 0.03, 0.015, 0.02, -0.005, 0.01, 0.02, 0.01])
    wf_result = WalkForwardResult(
        candidate_id=candidate.id, n_folds_attempted=0, n_folds_valid=0,
        discovery_distribution=distribution, survived=False, reasons=["not yet validated"],
    )
    return build_pattern(
        pattern_id=pattern_id, candidate=candidate, horizon_days=5, walk_forward=wf_result, robustness=None,
        discovery_period=(date(2024, 1, 1), date(2024, 6, 1)), validation_period=None,
        number_of_tests=100, status=status, produced_by="test@1.0.0",
    )


def test_registry_persists_and_reloads(tmp_path):
    path = tmp_path / "registry.json"
    registry = PatternRegistry(path)
    pattern = _make_pattern()
    registry.add(pattern)
    assert path.exists()

    reloaded = PatternRegistry(path)
    fetched = reloaded.latest(pattern.id)
    assert fetched is not None
    assert fetched.definition == pattern.definition
    assert fetched.validation_status is PatternStatus.DISCOVERED


def test_a_rejected_pattern_is_never_deleted_only_transitioned():
    registry = PatternRegistry()
    pattern = _make_pattern()
    registry.add(pattern)
    registry.transition(pattern.id, PatternStatus.REJECTED, reason="failed OOS validation")

    history = registry.history(pattern.id)
    assert len(history) == 2  # the original DISCOVERED revision is still there
    assert history[0].validation_status is PatternStatus.DISCOVERED
    assert history[1].validation_status is PatternStatus.REJECTED
    assert history[1].rejection_reason == "failed OOS validation"
    latest = registry.latest(pattern.id)
    assert latest.validation_status is PatternStatus.REJECTED
    assert latest.version == 2


def test_transition_increments_version_every_time():
    registry = PatternRegistry()
    pattern = _make_pattern()
    registry.add(pattern)
    registry.transition(pattern.id, PatternStatus.VALIDATED)
    registry.transition(pattern.id, PatternStatus.ACTIVE)
    registry.transition(pattern.id, PatternStatus.WEAKENING, reason="live decay")
    latest = registry.latest(pattern.id)
    assert latest.version == 4
    assert latest.validation_status is PatternStatus.WEAKENING


def test_transition_unknown_pattern_raises():
    registry = PatternRegistry()
    with pytest.raises(KeyError):
        registry.transition("does_not_exist", PatternStatus.REJECTED)


def test_by_status_filters_to_latest_revision_only():
    registry = PatternRegistry()
    a = _make_pattern("pattern_a")
    b = _make_pattern("pattern_b")
    registry.add(a)
    registry.add(b)
    registry.transition("pattern_a", PatternStatus.VALIDATED)

    validated = registry.by_status(PatternStatus.VALIDATED)
    discovered = registry.by_status(PatternStatus.DISCOVERED)
    assert [p.id for p in validated] == ["pattern_a"]
    assert [p.id for p in discovered] == ["pattern_b"]
