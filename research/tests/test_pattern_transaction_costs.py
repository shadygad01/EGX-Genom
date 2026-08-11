"""Transaction cost sensitivity sweep (mission Phase 15) coverage for
`patterns.transaction_costs`."""

from __future__ import annotations

from agx_research.patterns.candidates import CandidateGeneratorConfig
from agx_research.patterns.control_suite import build_momentum_panel
from agx_research.patterns.engine import PatternDiscoveryEngine, PatternDiscoveryEngineConfig
from agx_research.patterns.multiple_testing import TestingLedgerRepository
from agx_research.patterns.registry import Pattern, PatternRegistry, PatternStatus
from agx_research.patterns.robustness import DEFAULT_TRANSACTION_COST_BPS
from agx_research.patterns.transaction_costs import (
    DEFAULT_COST_GRID_BPS,
    analyze_transaction_cost_sensitivity,
)
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


def test_cost_grid_is_reported_in_ascending_order_with_monotonically_decreasing_net_expectancy():
    pattern, panel = _validated_momentum_pattern()
    result = analyze_transaction_cost_sensitivity(pattern, panel)
    assert [lvl.cost_bps for lvl in result.levels] == list(DEFAULT_COST_GRID_BPS)
    for a, b in zip(result.levels, result.levels[1:]):
        assert a.net_expectancy >= b.net_expectancy  # higher cost never helps


def test_zero_cost_level_net_expectancy_equals_gross_expectancy():
    pattern, panel = _validated_momentum_pattern()
    result = analyze_transaction_cost_sensitivity(pattern, panel)
    zero_cost = next(lvl for lvl in result.levels if lvl.cost_bps == 0.0)
    assert abs(zero_cost.net_expectancy - result.gross_expectancy) < 1e-12


def test_breakeven_cost_bps_is_where_net_expectancy_crosses_zero():
    pattern, panel = _validated_momentum_pattern()
    result = analyze_transaction_cost_sensitivity(pattern, panel)
    assert result.gross_expectancy > 0  # this pattern only reaches VALIDATED with a real edge
    assert result.breakeven_cost_bps is not None
    assert abs(result.breakeven_cost_bps - result.gross_expectancy * 10_000) < 1e-9
    # Below breakeven the pattern survives; at/above it, it does not.
    below = analyze_transaction_cost_sensitivity(pattern, panel, cost_grid_bps=(result.breakeven_cost_bps - 1.0,))
    above = analyze_transaction_cost_sensitivity(pattern, panel, cost_grid_bps=(result.breakeven_cost_bps + 1.0,))
    assert below.levels[0].survives
    assert not above.levels[0].survives


def test_survives_default_cost_matches_robustness_gate_convention():
    pattern, panel = _validated_momentum_pattern()
    result = analyze_transaction_cost_sensitivity(pattern, panel)
    default_level = next((lvl for lvl in result.levels if lvl.cost_bps == DEFAULT_TRANSACTION_COST_BPS), None)
    if default_level is not None:
        assert result.survives_default_cost == default_level.survives
    else:
        assert result.survives_default_cost == (
            (result.gross_expectancy - DEFAULT_TRANSACTION_COST_BPS / 10_000) > 0
        )


def test_a_pattern_with_no_matched_outcomes_returns_a_clean_empty_result():
    empty_panel_pattern = Pattern.model_construct(
        id="p1", version=1, definition="does not matter", ticker="MISSING", conditions=[], target_id="t",
        horizon_days=5, discovery_period=(build_momentum_panel(1).as_of, build_momentum_panel(1).as_of),
        sample_size=0, oos_sample_size=0, expectancy=0.0, median_outcome=0.0, hit_rate=0.0, complexity=1,
        number_of_tests=1, validation_status=PatternStatus.VALIDATED,
        provenance={"produced_by": "test", "produced_at": "2020-01-01T00:00:00", "inputs": []},
    )
    panel = build_momentum_panel(1)
    result = analyze_transaction_cost_sensitivity(empty_panel_pattern, panel)
    assert result.sample_size == 0
    assert result.levels == []
    assert result.breakeven_cost_bps is None
    assert result.survives_default_cost is False


def test_net_hit_rate_never_exceeds_gross_hit_rate_for_a_positive_cost():
    pattern, panel = _validated_momentum_pattern()
    result = analyze_transaction_cost_sensitivity(pattern, panel)
    for lvl in result.levels:
        if lvl.cost_bps > 0:
            assert lvl.net_hit_rate <= result.gross_hit_rate
