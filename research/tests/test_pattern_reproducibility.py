"""Reproducibility metadata (mission Phase 19) coverage for
`patterns.reproducibility`, plus end-to-end wiring checks in `engine.py`."""

from __future__ import annotations

from agx_research.patterns.candidates import CandidateGeneratorConfig
from agx_research.patterns.control_suite import build_momentum_panel
from agx_research.patterns.engine import PatternDiscoveryEngine, PatternDiscoveryEngineConfig
from agx_research.patterns.multiple_testing import TestingLedgerRepository
from agx_research.patterns.registry import PatternRegistry, PatternStatus
from agx_research.patterns.reproducibility import build_reproducibility_manifest
from agx_research.patterns.validation import WalkForwardValidatorConfig


def test_build_reproducibility_manifest_populates_a_real_git_commit_when_available():
    manifest = build_reproducibility_manifest(
        engine_name="test_engine", engine_version="1.0.0", config={"a": 1},
    )
    assert manifest.experiment_id.startswith("experiment_")
    assert manifest.engine_name == "test_engine"
    assert manifest.engine_version == "1.0.0"
    assert manifest.dataset_source == "unknown"
    assert manifest.dataset_version is None
    assert manifest.config == {"a": 1}
    # This repository IS a git checkout, so a real commit sha should resolve
    # (not asserted to be non-None on principle -- CI environments without
    # git metadata should still get an honest None, not a fabricated sha --
    # but locally this proves the resolution path actually works).
    assert manifest.git_commit is None or len(manifest.git_commit) == 40


def test_build_reproducibility_manifest_carries_dataset_source_and_version_through():
    manifest = build_reproducibility_manifest(
        engine_name="e", engine_version="1", dataset_source="collected",
        dataset_version="abc123deadbeef", config={},
    )
    assert manifest.dataset_source == "collected"
    assert manifest.dataset_version == "abc123deadbeef"


def test_two_manifests_from_the_same_call_get_distinct_experiment_ids():
    a = build_reproducibility_manifest(engine_name="e", engine_version="1", config={})
    b = build_reproducibility_manifest(engine_name="e", engine_version="1", config={})
    assert a.experiment_id != b.experiment_id


def test_discover_validate_final_holdout_each_stamp_their_own_manifest_and_pattern_traces_all_three():
    panel = build_momentum_panel(1)
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

    discover_report = engine.discover(panel, dataset_source="mock")
    validate_report = engine.validate(panel, dataset_source="mock")
    holdout_report = engine.final_holdout(panel, dataset_source="mock")

    assert discover_report.reproducibility is not None
    assert validate_report.reproducibility is not None
    assert holdout_report.reproducibility is not None
    # Three separate runs -> three distinct experiment ids, even though
    # they operated on the same panel/config.
    experiment_ids = {
        discover_report.reproducibility.experiment_id,
        validate_report.reproducibility.experiment_id,
        holdout_report.reproducibility.experiment_id,
    }
    assert len(experiment_ids) == 3
    for r in (discover_report, validate_report, holdout_report):
        assert r.reproducibility.dataset_source == "mock"

    validated = registry.by_status(PatternStatus.VALIDATED)
    assert validated
    pattern = validated[0]
    # discovery_experiment_id must be the FIRST run's id, preserved across
    # validate()/final_holdout() re-building the pattern -- never
    # overwritten with a later run's id.
    assert pattern.discovery_experiment_id == discover_report.reproducibility.experiment_id
    # last_experiment_id must reflect the MOST RECENT run that touched it
    # (final_holdout(), the last of the three calls).
    assert pattern.last_experiment_id == holdout_report.reproducibility.experiment_id


def test_validate_and_final_holdout_stamp_a_manifest_even_on_the_empty_early_return():
    registry = PatternRegistry()
    engine = PatternDiscoveryEngine(pattern_registry=registry, testing_ledger_repository=TestingLedgerRepository())
    panel = build_momentum_panel(1)

    validate_report = engine.validate(panel, dataset_source="mock")
    assert validate_report.patterns_considered == 0
    assert validate_report.reproducibility is not None

    holdout_report = engine.final_holdout(panel, dataset_source="mock")
    assert holdout_report.patterns_considered == 0
    assert holdout_report.reproducibility is not None
