from datetime import date, datetime
from pathlib import Path

import pytest

from agx_research.config import Horizon
from agx_research.data.mock_provider import MockDataProvider
from agx_research.data.snapshot import build_snapshot
from agx_research.domain.provenance import Provenance
from agx_research.hypotheses.experiment_factory import (
    BootstrapExperiment,
    CrossValidationExperiment,
    ExperimentFactory,
    MonteCarloExperiment,
    OutOfSampleExperiment,
    SensitivityAnalysisExperiment,
    WalkForwardExperiment,
)
from agx_research.hypotheses.hypothesis import Hypothesis

MOCK_ROOT = Path(__file__).resolve().parents[1] / "data" / "mock"


def snapshot():
    provider = MockDataProvider(MOCK_ROOT)
    return build_snapshot(
        provider, tickers=["COMI", "MFPC"], macro_series_ids=[], as_of=date(2026, 6, 14), lookback_days=30
    )


def hypothesis(affected_assets=("COMI", "MFPC")) -> Hypothesis:
    return Hypothesis(
        id="hyp-experiments",
        statement="test",
        created_by="agent",
        created_at=date(2026, 6, 1),
        horizon=Horizon.MICRO,
        affected_assets=list(affected_assets),
        provenance=Provenance(produced_by="agent@0.1.0", produced_at=datetime.now()),
    )


def test_cross_validation_produces_a_significance_test_across_folds():
    result = CrossValidationExperiment(folds=3).run(hypothesis(), snapshot())
    assert result.sample_size == 9
    assert len(result.details["fold_statistics"]) == 3
    assert 0.0 <= result.p_value <= 1.0


def test_bootstrap_is_deterministic_given_a_seed():
    result_a = BootstrapExperiment(iterations=200, seed=7).run(hypothesis(), snapshot())
    result_b = BootstrapExperiment(iterations=200, seed=7).run(hypothesis(), snapshot())
    assert result_a.statistic == result_b.statistic
    assert result_a.p_value == result_b.p_value


def test_walk_forward_produces_a_rolling_window_series():
    result = WalkForwardExperiment(window=5, step=1).run(hypothesis(), snapshot())
    assert len(result.details["window_statistics"]) == 5  # 9 obs, window 5, step 1 -> 5 windows


def test_out_of_sample_reports_both_halves():
    result = OutOfSampleExperiment().run(hypothesis(), snapshot())
    assert "in_sample_statistic" in result.details
    assert "out_of_sample_statistic" in result.details


def test_single_asset_hypothesis_uses_mean_return_statistic():
    """One affected asset -> the claim statistic is the mean adjusted daily return."""
    result = CrossValidationExperiment(folds=3).run(hypothesis(affected_assets=("COMI",)), snapshot())
    assert len(result.details["fold_statistics"]) == 3

    oos = OutOfSampleExperiment().run(hypothesis(affected_assets=("COMI",)), snapshot())
    assert 0.0 <= oos.p_value <= 1.0


def test_three_asset_hypothesis_is_rejected_not_guessed():
    with pytest.raises(ValueError):
        CrossValidationExperiment().run(
            hypothesis(affected_assets=("COMI", "MFPC", "SWDY")), snapshot()
        )


def test_sensitivity_analysis_reports_sign_stability_across_windows():
    result = SensitivityAnalysisExperiment().run(hypothesis(), snapshot())
    assert result.details["settings"] >= 2
    assert 0.0 <= result.p_value <= 1.0
    assert result.p_value == result.details["sign_flips"] / result.details["settings"]


def test_monte_carlo_is_an_explicit_placeholder():
    with pytest.raises(NotImplementedError):
        MonteCarloExperiment().run(hypothesis(), snapshot())


def test_factory_run_all_skips_placeholders_and_returns_real_results():
    factory = ExperimentFactory()
    results = factory.run_all(hypothesis(), snapshot())

    assert "MonteCarloExperiment" not in results
    for name in (
        "CrossValidationExperiment",
        "BootstrapExperiment",
        "WalkForwardExperiment",
        "OutOfSampleExperiment",
        "SensitivityAnalysisExperiment",
    ):
        assert name in results


def test_experiment_results_can_be_stored_as_versioned_artifacts():
    from agx_research.orchestration.artifacts import ArtifactKind, ArtifactRepository

    factory = ExperimentFactory()
    results = factory.run_all(hypothesis(), snapshot())
    repo = ArtifactRepository()

    for name, result in results.items():
        artifact = repo.store(
            kind=ArtifactKind.EXPERIMENT_RESULT,
            payload=result,
            provenance=Provenance(produced_by=name, produced_at=datetime.now()),
        )
        assert artifact.version == 1

    assert len(repo.all_latest()) == len(results)
