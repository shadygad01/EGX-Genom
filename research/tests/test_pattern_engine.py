"""End-to-end integration tests for `patterns.engine.PatternDiscoveryEngine`.

Two properties matter equally and both need direct proof, not just unit
coverage of their pieces in isolation:

1. The engine can actually validate a real, planted relationship when one
   genuinely exists (`test_engine_end_to_end_validates_a_real_planted_pattern`)
   -- without this, "the real run against today's data returns zero" would
   be unfalsifiable (an engine that always says zero regardless of input
   would trivially "pass" every honesty requirement while being useless).
2. With too little data to responsibly search at all, the engine refuses
   to generate a single candidate rather than fabricating one from noise
   (`test_engine_generates_nothing_below_the_sample_size_floor`) -- the
   same behavior the real `agx research discover` run against this
   repository's actual (thin) data exhibits today, see
   `docs/PATTERN_DISCOVERY_REPORT.md`.
"""

from __future__ import annotations

from agx_research.patterns.candidates import CandidateGeneratorConfig
from agx_research.patterns.engine import PatternDiscoveryEngine, PatternDiscoveryEngineConfig
from agx_research.patterns.multiple_testing import TestingLedgerRepository
from agx_research.patterns.registry import PatternRegistry, PatternStatus
from agx_research.patterns.validation import WalkForwardValidatorConfig
from tests.pattern_test_helpers import make_deterministic_ticker_series, make_panel


def test_engine_end_to_end_validates_a_real_planted_pattern():
    """A, B are deterministic (seeded), noise-small series with a genuine,
    strong, real periodic momentum relationship baked into their
    construction (see `pattern_test_helpers`'s module docstring). With a
    generous-but-real candidate/validation configuration, the full
    discover -> validate pipeline (candidate generation, discovery-sample
    screening, Benjamini-Hochberg FDR control, purged walk-forward
    out-of-sample validation, robustness testing, baseline comparison)
    must find and VALIDATE at least one of them.
    """
    a = make_deterministic_ticker_series(
        "A", n_days=200, seed=11, block_length=10, daily_drift=0.01, noise_stdev=0.0005, sector="Banks"
    )
    b = make_deterministic_ticker_series(
        "B", n_days=200, seed=22, block_length=13, daily_drift=0.008, noise_stdev=0.0006, sector="Banks"
    )
    panel = make_panel(series={"A": a, "B": b})

    registry = PatternRegistry()
    engine = PatternDiscoveryEngine(
        pattern_registry=registry,
        testing_ledger_repository=TestingLedgerRepository(),
        config=PatternDiscoveryEngineConfig(
            candidate_config=CandidateGeneratorConfig(
                min_sample_size=15,
                correlation_prune_threshold=0.8,
                max_candidates_per_ticker=40,
                enable_three_feature=False,
                enable_regime_conditioning=False,
            ),
            walk_forward_config=WalkForwardValidatorConfig(
                n_folds=3, min_train_size=40, min_oos_sample_size=8, embargo_days=2
            ),
            fdr_alpha=0.10,
            require_beats_baseline=True,
            horizons=(5,),
        ),
    )

    discover_report = engine.discover(panel)
    assert discover_report.candidates_generated > 0
    assert discover_report.patterns_discovered > 0

    validate_report = engine.validate(panel)
    assert validate_report.patterns_surviving_to_validating >= 1
    assert registry.by_status(PatternStatus.VALIDATED) == []  # not yet -- final holdout still pending

    holdout_report = engine.final_holdout(panel)
    assert holdout_report.patterns_validated >= 1

    validated = registry.by_status(PatternStatus.VALIDATED)
    assert validated
    pattern = validated[0]
    assert pattern.oos_sample_size >= 8
    assert pattern.sample_size >= 15
    assert pattern.hit_rate > 0.5
    assert pattern.expectancy > 0
    assert pattern.number_of_tests == discover_report.candidates_generated  # multiple-testing burden is honestly cited
    assert pattern.holdout_period is not None
    assert pattern.holdout_sample_size > 0


def test_engine_generates_nothing_below_the_sample_size_floor():
    """With production-realistic default thresholds (`min_sample_size=30`)
    and too little history to ever clear them, the engine must generate
    zero candidates -- never a fabricated one from an undersized sample."""
    a = make_deterministic_ticker_series("A", n_days=15, seed=1)
    panel = make_panel(series={"A": a})

    registry = PatternRegistry()
    engine = PatternDiscoveryEngine(
        pattern_registry=registry, testing_ledger_repository=TestingLedgerRepository()
    )
    report = engine.discover(panel)
    assert report.candidates_generated == 0
    assert report.patterns_discovered == 0
    assert registry.all_latest() == []
    assert any("no bug" in n.lower() or "sample-size floor" in n.lower() for n in report.notes)


def test_engine_records_a_testing_ledger_even_with_zero_candidates():
    a = make_deterministic_ticker_series("A", n_days=15, seed=1)
    panel = make_panel(series={"A": a})
    ledger_repo = TestingLedgerRepository()
    engine = PatternDiscoveryEngine(pattern_registry=PatternRegistry(), testing_ledger_repository=ledger_repo)
    report = engine.discover(panel)

    ledger = ledger_repo.latest(report.testing_ledger_id)
    assert ledger is not None
    assert ledger.hypotheses_tested == 0
    assert ledger.surviving_after_fdr == 0


def test_validate_with_no_discovered_patterns_is_a_clean_no_op():
    a = make_deterministic_ticker_series("A", n_days=15, seed=1)
    panel = make_panel(series={"A": a})
    engine = PatternDiscoveryEngine(pattern_registry=PatternRegistry(), testing_ledger_repository=TestingLedgerRepository())
    report = engine.validate(panel)
    assert report.patterns_considered == 0
    assert report.patterns_surviving_to_validating == 0
    assert "discover" in report.notes[0].lower()


def test_final_holdout_with_no_validating_patterns_is_a_clean_no_op():
    a = make_deterministic_ticker_series("A", n_days=15, seed=1)
    panel = make_panel(series={"A": a})
    engine = PatternDiscoveryEngine(pattern_registry=PatternRegistry(), testing_ledger_repository=TestingLedgerRepository())
    report = engine.final_holdout(panel)
    assert report.patterns_considered == 0
    assert report.patterns_validated == 0
    assert "validate" in report.notes[0].lower()


def test_activate_and_track_outcomes_after_validation():
    a = make_deterministic_ticker_series(
        "A", n_days=200, seed=11, block_length=10, daily_drift=0.01, noise_stdev=0.0005, sector="Banks"
    )
    b = make_deterministic_ticker_series(
        "B", n_days=200, seed=22, block_length=13, daily_drift=0.008, noise_stdev=0.0006, sector="Banks"
    )
    panel = make_panel(series={"A": a, "B": b})
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
            horizons=(5,),
        ),
    )
    engine.discover(panel)
    engine.validate(panel)
    engine.final_holdout(panel)
    assert registry.by_status(PatternStatus.VALIDATED)

    activations = engine.activate(panel)
    # A validated pattern may or may not currently match today's exact
    # feature values -- what matters is the call succeeds and never
    # fabricates a match (see test_pattern_live.py for match-detection
    # correctness); if any activation fires, it must carry evidence.
    for activation in activations:
        assert activation.evidence
        assert activation.label == "ACTIVE_PATTERN"
