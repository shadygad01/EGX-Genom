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
    registry.transition(pattern.id, PatternStatus.VALIDATING)
    registry.transition(pattern.id, PatternStatus.VALIDATED)
    registry.transition(pattern.id, PatternStatus.ACTIVE)
    registry.transition(pattern.id, PatternStatus.WEAKENING, reason="live decay")
    latest = registry.latest(pattern.id)
    assert latest.version == 5
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
    registry.transition("pattern_a", PatternStatus.VALIDATING)
    registry.transition("pattern_a", PatternStatus.VALIDATED)

    validated = registry.by_status(PatternStatus.VALIDATED)
    discovered = registry.by_status(PatternStatus.DISCOVERED)
    assert [p.id for p in validated] == ["pattern_a"]
    assert [p.id for p in discovered] == ["pattern_b"]


def test_transition_rejects_a_discovered_pattern_jumping_straight_to_validated():
    """Mission Phase 17 (registry lifecycle tightening): a pattern must
    clear VALIDATING (purged walk-forward + robustness + baseline) before
    it can ever become VALIDATED -- `transition()` must refuse the
    shortcut, not just leave it undocumented."""
    registry = PatternRegistry()
    pattern = _make_pattern()
    registry.add(pattern)
    with pytest.raises(ValueError, match="Illegal transition"):
        registry.transition(pattern.id, PatternStatus.VALIDATED)
    # The illegal attempt must not have mutated anything.
    assert registry.latest(pattern.id).validation_status is PatternStatus.DISCOVERED
    assert registry.latest(pattern.id).version == 1


def test_transition_rejects_reviving_a_rejected_pattern():
    registry = PatternRegistry()
    pattern = _make_pattern()
    registry.add(pattern)
    registry.transition(pattern.id, PatternStatus.REJECTED, reason="failed OOS validation")
    with pytest.raises(ValueError, match="Illegal transition"):
        registry.transition(pattern.id, PatternStatus.VALIDATING)
    with pytest.raises(ValueError, match="Illegal transition"):
        registry.transition(pattern.id, PatternStatus.VALIDATED)


def test_transition_allows_weakening_to_return_to_validated_for_revalidation():
    registry = PatternRegistry()
    pattern = _make_pattern()
    registry.add(pattern)
    registry.transition(pattern.id, PatternStatus.VALIDATING)
    registry.transition(pattern.id, PatternStatus.VALIDATED)
    registry.transition(pattern.id, PatternStatus.WEAKENING, reason="live decay")
    registry.transition(pattern.id, PatternStatus.VALIDATED)  # revalidation succeeded
    assert registry.latest(pattern.id).validation_status is PatternStatus.VALIDATED


def test_build_pattern_experiment_id_fields_default_to_none_and_thread_through():
    pattern = _make_pattern()
    assert pattern.discovery_experiment_id is None
    assert pattern.last_experiment_id is None

    with_ids = build_pattern(
        pattern_id="p2",
        candidate=PatternCandidate(
            id="c2", ticker="COMI",
            conditions=[FeatureCondition(feature_id="return_5d:COMI", operator=ConditionOperator.GT, threshold=0.01)],
            target_id="forward_return_5d:COMI", complexity=1,
        ),
        horizon_days=5,
        walk_forward=WalkForwardResult(
            candidate_id="c2", n_folds_attempted=0, n_folds_valid=0,
            discovery_distribution=evaluate_outcomes([0.01, 0.02, -0.01, 0.03, 0.015]),
            survived=False, reasons=["not yet validated"],
        ),
        robustness=None, discovery_period=(date(2024, 1, 1), date(2024, 6, 1)), validation_period=None,
        number_of_tests=100, status=PatternStatus.DISCOVERED, produced_by="test@1.0.0",
        discovery_experiment_id="experiment_abc123", last_experiment_id="experiment_abc123",
    )
    assert with_ids.discovery_experiment_id == "experiment_abc123"
    assert with_ids.last_experiment_id == "experiment_abc123"
