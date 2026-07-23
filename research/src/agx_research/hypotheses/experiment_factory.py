"""The Experiment Factory: every hypothesis generates multiple experiments.

Each class here satisfies the existing `Experiment` ABC unchanged — no
interface change was needed. Four are genuinely real, if deliberately
simple, statistics over the one feature this scaffold has
(`pairwise_return_correlation`): cross-validation, bootstrap, walk-forward,
and an in-sample/out-of-sample split. `StressTestExperiment` adapts the
existing `StressTester` interface. `SensitivityAnalysisExperiment` and
`MonteCarloExperiment` are real interfaces that raise `NotImplementedError`
— both need a defined parameter/scenario space that's a research decision,
not scaffolding (the brief itself calls Monte Carlo out as a placeholder).

Callers that want each `ExperimentResult` recorded as a versioned Artifact
should wrap it via `orchestration.artifacts.ArtifactRepository.store()` —
that mechanism already exists generically, so nothing here needs to import
the orchestration layer.
"""

from __future__ import annotations

import random
import statistics

from scipy import stats as scipy_stats

from agx_research.data.adjustments import adjusted_returns_for_ticker
from agx_research.data.snapshot import DatasetSnapshot
from agx_research.features.correlation import pearson_correlation
from agx_research.hypotheses.experiment import Experiment, ExperimentResult
from agx_research.hypotheses.hypothesis import Hypothesis
from agx_research.validation.stress_test import StressTester


def _tickers_from_hypothesis(hypothesis: Hypothesis) -> tuple[str, str]:
    if len(hypothesis.affected_assets) < 2:
        raise ValueError(
            f"{hypothesis.id}: pairwise experiments need at least two affected_assets, "
            f"got {hypothesis.affected_assets}"
        )
    return hypothesis.affected_assets[0], hypothesis.affected_assets[1]


def _returns_for(snapshot: DatasetSnapshot, ticker: str) -> list[float]:
    return adjusted_returns_for_ticker(snapshot, ticker)


def _aligned_returns(
    snapshot: DatasetSnapshot, ticker_a: str, ticker_b: str
) -> tuple[list[float], list[float]]:
    returns_a = _returns_for(snapshot, ticker_a)
    returns_b = _returns_for(snapshot, ticker_b)
    n = min(len(returns_a), len(returns_b))
    return returns_a[-n:], returns_b[-n:]


class CrossValidationExperiment(Experiment):
    """k-fold cross-validation of the pairwise correlation statistic."""

    def __init__(self, folds: int = 3):
        self.folds = folds

    def run(self, hypothesis: Hypothesis, snapshot: DatasetSnapshot) -> ExperimentResult:
        ticker_a, ticker_b = _tickers_from_hypothesis(hypothesis)
        returns_a, returns_b = _aligned_returns(snapshot, ticker_a, ticker_b)
        n = len(returns_a)
        if n < self.folds * 2:
            raise ValueError(
                f"Not enough data ({n} observations) for {self.folds}-fold cross-validation"
            )

        fold_size = n // self.folds
        fold_correlations = []
        for i in range(self.folds):
            start = i * fold_size
            end = n if i == self.folds - 1 else start + fold_size
            r = pearson_correlation(returns_a[start:end], returns_b[start:end])
            if r is not None:
                fold_correlations.append(r)
        if len(fold_correlations) < 2:
            raise ValueError("Not enough folds produced a valid correlation")

        statistic, p_value = scipy_stats.ttest_1samp(fold_correlations, popmean=0.0)
        return ExperimentResult(
            statistic=float(statistic),
            p_value=float(p_value),
            sample_size=n,
            details={"fold_correlations": fold_correlations, "folds": self.folds},
        )


class BootstrapExperiment(Experiment):
    """Resamples daily returns with replacement to bootstrap a confidence interval."""

    def __init__(self, iterations: int = 500, seed: int = 42):
        self.iterations = iterations
        self.seed = seed

    def run(self, hypothesis: Hypothesis, snapshot: DatasetSnapshot) -> ExperimentResult:
        ticker_a, ticker_b = _tickers_from_hypothesis(hypothesis)
        returns_a, returns_b = _aligned_returns(snapshot, ticker_a, ticker_b)
        n = len(returns_a)
        if n < 5:
            raise ValueError(f"Not enough data ({n} observations) to bootstrap")

        rng = random.Random(self.seed)
        bootstrap_correlations = []
        for _ in range(self.iterations):
            indices = [rng.randrange(n) for _ in range(n)]
            sample_a = [returns_a[i] for i in indices]
            sample_b = [returns_b[i] for i in indices]
            r = pearson_correlation(sample_a, sample_b)
            if r is not None:
                bootstrap_correlations.append(r)
        if len(bootstrap_correlations) < 2:
            raise ValueError("Bootstrap resampling did not produce enough valid correlations")

        mean_r = statistics.fmean(bootstrap_correlations)
        opposite_side = sum(
            1 for r in bootstrap_correlations if (r <= 0) != (mean_r <= 0)
        )
        total = len(bootstrap_correlations)
        p_value = min(1.0, 2 * min(opposite_side, total - opposite_side) / total)

        return ExperimentResult(
            statistic=mean_r,
            p_value=p_value,
            sample_size=n,
            details={
                "iterations": total,
                "bootstrap_std": statistics.pstdev(bootstrap_correlations),
            },
        )


class WalkForwardExperiment(Experiment):
    """Rolling-window re-evaluation of the correlation statistic across time."""

    def __init__(self, window: int = 5, step: int = 1):
        self.window = window
        self.step = step

    def run(self, hypothesis: Hypothesis, snapshot: DatasetSnapshot) -> ExperimentResult:
        ticker_a, ticker_b = _tickers_from_hypothesis(hypothesis)
        returns_a, returns_b = _aligned_returns(snapshot, ticker_a, ticker_b)
        n = len(returns_a)
        if n < self.window + self.step:
            raise ValueError(
                f"Not enough data ({n} observations) for a walk-forward window of {self.window}"
            )

        window_correlations = []
        start = 0
        while start + self.window <= n:
            r = pearson_correlation(
                returns_a[start : start + self.window], returns_b[start : start + self.window]
            )
            if r is not None:
                window_correlations.append(r)
            start += self.step
        if len(window_correlations) < 2:
            raise ValueError("Not enough walk-forward windows produced a valid correlation")

        statistic, p_value = scipy_stats.ttest_1samp(window_correlations, popmean=0.0)
        return ExperimentResult(
            statistic=float(statistic),
            p_value=float(p_value),
            sample_size=n,
            details={
                "window_correlations": window_correlations,
                "window": self.window,
                "step": self.step,
            },
        )


class OutOfSampleExperiment(Experiment):
    """Splits the snapshot's window in two; reports whether the statistic holds out of sample."""

    def run(self, hypothesis: Hypothesis, snapshot: DatasetSnapshot) -> ExperimentResult:
        ticker_a, ticker_b = _tickers_from_hypothesis(hypothesis)
        returns_a, returns_b = _aligned_returns(snapshot, ticker_a, ticker_b)
        n = len(returns_a)
        if n < 6:
            raise ValueError(f"Not enough data ({n} observations) for an in/out-of-sample split")

        midpoint = n // 2
        in_sample_r = pearson_correlation(returns_a[:midpoint], returns_b[:midpoint])
        out_a, out_b = returns_a[midpoint:], returns_b[midpoint:]
        try:
            out_r, out_p = scipy_stats.pearsonr(out_a, out_b)
            out_r, out_p = float(out_r), float(out_p)
        except Exception:
            out_r, out_p = 0.0, 1.0

        return ExperimentResult(
            statistic=out_r,
            p_value=out_p,
            sample_size=len(out_a),
            details={
                "in_sample_correlation": in_sample_r,
                "out_of_sample_correlation": out_r,
                "same_sign_as_in_sample": (
                    in_sample_r is not None and (in_sample_r <= 0) == (out_r <= 0)
                ),
            },
        )


class StressTestExperiment(Experiment):
    """Adapts an Epoch I `StressTester` into a versioned Experiment/artifact."""

    def __init__(self, stress_tester: StressTester):
        self.stress_tester = stress_tester

    def run(self, hypothesis: Hypothesis, snapshot: DatasetSnapshot) -> ExperimentResult:
        result = self.stress_tester.run(hypothesis, snapshot)
        return ExperimentResult(
            statistic=1.0 if result.passed else 0.0,
            p_value=0.0 if result.passed else 1.0,
            sample_size=len(result.scenario_results),
            details={
                "scenario_results": result.scenario_results,
                "notes": result.notes,
                "passed": result.passed,
            },
        )


class SensitivityAnalysisExperiment(Experiment):
    """Needs a defined parameter space per hypothesis type — a research decision, not scaffolding."""

    def run(self, hypothesis: Hypothesis, snapshot: DatasetSnapshot) -> ExperimentResult:
        raise NotImplementedError("SensitivityAnalysisExperiment is not yet implemented")


class MonteCarloExperiment(Experiment):
    """Explicit placeholder interface per the brief — no simulator exists yet."""

    def run(self, hypothesis: Hypothesis, snapshot: DatasetSnapshot) -> ExperimentResult:
        raise NotImplementedError(
            "MonteCarloExperiment is a placeholder interface; no simulator is implemented yet"
        )


class ExperimentFactory:
    """Given a hypothesis, produces every experiment type applicable to it."""

    def __init__(self, stress_tester: StressTester | None = None):
        self.stress_tester = stress_tester

    def build(self, hypothesis: Hypothesis) -> list[Experiment]:
        experiments: list[Experiment] = [
            CrossValidationExperiment(),
            BootstrapExperiment(),
            WalkForwardExperiment(),
            OutOfSampleExperiment(),
            SensitivityAnalysisExperiment(),
            MonteCarloExperiment(),
        ]
        if self.stress_tester is not None:
            experiments.append(StressTestExperiment(self.stress_tester))
        return experiments

    def run_all(
        self, hypothesis: Hypothesis, snapshot: DatasetSnapshot
    ) -> dict[str, ExperimentResult]:
        """Run every experiment this factory can produce.

        Experiments that are still `NotImplementedError` placeholders are
        skipped rather than treated as failures; a real experiment raising
        `ValueError` (e.g. not enough data) propagates, since that's a
        genuine problem with running it against this hypothesis/snapshot.
        """
        results: dict[str, ExperimentResult] = {}
        for experiment in self.build(hypothesis):
            name = type(experiment).__name__
            try:
                results[name] = experiment.run(hypothesis, snapshot)
            except NotImplementedError:
                continue
        return results
