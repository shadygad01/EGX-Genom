"""The Experiment Factory: every hypothesis generates multiple experiments.

Each class satisfies the existing `Experiment` ABC unchanged. Five are
real, deliberately simple statistics over the hypothesis's claim statistic
(`hypotheses/statistic.py` — correlation for pairs, mean return for single
assets): cross-validation, bootstrap, walk-forward, in/out-of-sample, and
sensitivity analysis over the estimation window. `StressTestExperiment`
adapts the `StressTester` interface. `MonteCarloExperiment` remains an
explicit placeholder — a market simulator is a research decision, not
scaffolding.

Callers that want each `ExperimentResult` recorded as a versioned Artifact
should wrap it via `orchestration.artifacts.ArtifactRepository.store()`.
"""

from __future__ import annotations

import random
import statistics

from scipy import stats as scipy_stats

from agx_research.data.snapshot import DatasetSnapshot
from agx_research.hypotheses.experiment import Experiment, ExperimentResult
from agx_research.hypotheses.hypothesis import Hypothesis
from agx_research.hypotheses.statistic import (
    hypothesis_statistic,
    series_for_hypothesis,
    slice_series,
)
from agx_research.validation.stress_test import StressTester


class CrossValidationExperiment(Experiment):
    """k-fold cross-validation of the hypothesis statistic."""

    def __init__(self, folds: int = 3):
        self.folds = folds

    def run(self, hypothesis: Hypothesis, snapshot: DatasetSnapshot) -> ExperimentResult:
        series = series_for_hypothesis(hypothesis, snapshot)
        n = len(series[0])
        if n < self.folds * 2:
            raise ValueError(
                f"Not enough data ({n} observations) for {self.folds}-fold cross-validation"
            )

        fold_size = n // self.folds
        fold_statistics = []
        for i in range(self.folds):
            start = i * fold_size
            end = n if i == self.folds - 1 else start + fold_size
            value = hypothesis_statistic(slice_series(series, start, end))
            if value is not None:
                fold_statistics.append(value)
        if len(fold_statistics) < 2:
            raise ValueError("Not enough folds produced a valid statistic")

        statistic, p_value = scipy_stats.ttest_1samp(fold_statistics, popmean=0.0)
        return ExperimentResult(
            statistic=float(statistic),
            p_value=float(p_value),
            sample_size=n,
            details={"fold_statistics": fold_statistics, "folds": self.folds},
        )


class BootstrapExperiment(Experiment):
    """Moving-block bootstrap preserving local return dependence and volatility clusters."""

    def __init__(
        self, iterations: int = 500, seed: int = 42, block_size: int | None = None
    ):
        self.iterations = iterations
        self.seed = seed
        self.block_size = block_size

    def run(self, hypothesis: Hypothesis, snapshot: DatasetSnapshot) -> ExperimentResult:
        series = series_for_hypothesis(hypothesis, snapshot)
        n = len(series[0])
        if n < 5:
            raise ValueError(f"Not enough data ({n} observations) to bootstrap")

        rng = random.Random(self.seed)
        block_size = self.block_size or max(2, round(n ** (1 / 3)))
        block_size = min(block_size, n)
        bootstrap_statistics = []
        for _ in range(self.iterations):
            indices: list[int] = []
            while len(indices) < n:
                start = rng.randrange(n)
                indices.extend((start + offset) % n for offset in range(block_size))
            indices = indices[:n]
            resampled = [[s[i] for i in indices] for s in series]
            value = hypothesis_statistic(resampled)
            if value is not None:
                bootstrap_statistics.append(value)
        if len(bootstrap_statistics) < 2:
            raise ValueError("Bootstrap resampling did not produce enough valid statistics")

        mean_value = statistics.fmean(bootstrap_statistics)
        opposite_side = sum(1 for v in bootstrap_statistics if (v <= 0) != (mean_value <= 0))
        total = len(bootstrap_statistics)
        p_value = min(1.0, 2 * min(opposite_side, total - opposite_side) / total)

        return ExperimentResult(
            statistic=mean_value,
            p_value=p_value,
            sample_size=n,
            details={
                "iterations": total,
                "method": "moving_block_bootstrap",
                "block_size": block_size,
                "bootstrap_std": statistics.pstdev(bootstrap_statistics),
            },
        )


class WalkForwardExperiment(Experiment):
    """Rolling-window re-evaluation of the hypothesis statistic across time."""

    def __init__(self, window: int = 5, step: int = 1):
        self.window = window
        self.step = step

    def run(self, hypothesis: Hypothesis, snapshot: DatasetSnapshot) -> ExperimentResult:
        series = series_for_hypothesis(hypothesis, snapshot)
        n = len(series[0])
        if n < self.window + self.step:
            raise ValueError(
                f"Not enough data ({n} observations) for a walk-forward window of {self.window}"
            )

        window_statistics = []
        start = 0
        while start + self.window <= n:
            value = hypothesis_statistic(slice_series(series, start, start + self.window))
            if value is not None:
                window_statistics.append(value)
            start += self.step
        if len(window_statistics) < 2:
            raise ValueError("Not enough walk-forward windows produced a valid statistic")

        mean_value = statistics.fmean(window_statistics)
        lag = min(
            len(window_statistics) - 1,
            max(1, (self.window + self.step - 1) // self.step - 1),
        )
        centered = [value - mean_value for value in window_statistics]
        n_windows = len(window_statistics)
        long_run_variance = sum(value * value for value in centered) / n_windows
        for offset in range(1, lag + 1):
            covariance = sum(
                centered[index] * centered[index - offset]
                for index in range(offset, n_windows)
            ) / n_windows
            long_run_variance += 2 * (1 - offset / (lag + 1)) * covariance
        standard_error = (max(long_run_variance, 0.0) / n_windows) ** 0.5
        statistic = mean_value / standard_error if standard_error > 0 else 0.0
        p_value = float(2 * scipy_stats.norm.sf(abs(statistic)))
        return ExperimentResult(
            statistic=float(statistic),
            p_value=float(p_value),
            sample_size=n,
            details={
                "window_statistics": window_statistics,
                "window": self.window,
                "step": self.step,
                "inference": "newey_west_hac",
                "hac_lag": lag,
            },
        )


class OutOfSampleExperiment(Experiment):
    """Splits the window in two; reports whether the statistic holds out of sample."""

    def run(self, hypothesis: Hypothesis, snapshot: DatasetSnapshot) -> ExperimentResult:
        series = series_for_hypothesis(hypothesis, snapshot)
        n = len(series[0])
        if n < 6:
            raise ValueError(f"Not enough data ({n} observations) for an in/out-of-sample split")

        midpoint = n // 2
        in_sample = hypothesis_statistic(slice_series(series, 0, midpoint))
        out_series = slice_series(series, midpoint, n)
        out_value = hypothesis_statistic(out_series)

        if len(series) == 2:
            try:
                _, out_p = scipy_stats.pearsonr(out_series[0], out_series[1])
                out_p = float(out_p)
            except Exception:
                out_p = 1.0
        else:
            try:
                _, out_p = scipy_stats.ttest_1samp(out_series[0], popmean=0.0)
                out_p = float(out_p)
            except Exception:
                out_p = 1.0

        out_value = out_value if out_value is not None else 0.0
        return ExperimentResult(
            statistic=out_value,
            p_value=out_p,
            sample_size=len(out_series[0]),
            details={
                "in_sample_statistic": in_sample,
                "out_of_sample_statistic": out_value,
                "same_sign_as_in_sample": (
                    in_sample is not None and (in_sample <= 0) == (out_value <= 0)
                ),
            },
        )


class SensitivityAnalysisExperiment(Experiment):
    """How sensitive is the statistic to the estimation window?

    The parameter space is the trailing-window fraction (by default the
    last 50%, 75%, and 100% of observations). A robust claim keeps its
    sign across settings; `p_value` is the fraction of settings whose
    statistic flips sign against the full-window value — 0.0 when fully
    stable, 1.0 when every alternative setting disagrees.
    """

    def __init__(self, window_fractions: tuple[float, ...] = (0.5, 0.75, 1.0)):
        if not window_fractions or any(not 0 < f <= 1 for f in window_fractions):
            raise ValueError("window_fractions must be fractions in (0, 1]")
        self.window_fractions = window_fractions

    def run(self, hypothesis: Hypothesis, snapshot: DatasetSnapshot) -> ExperimentResult:
        series = series_for_hypothesis(hypothesis, snapshot)
        n = len(series[0])
        if n < 6:
            raise ValueError(f"Not enough data ({n} observations) for sensitivity analysis")

        full_value = hypothesis_statistic(series)
        if full_value is None:
            raise ValueError("Full-window statistic is undefined")

        setting_values: dict[str, float] = {}
        flips = 0
        for fraction in self.window_fractions:
            window = max(3, int(n * fraction))
            value = hypothesis_statistic(slice_series(series, n - window, n))
            if value is None:
                continue
            setting_values[f"last_{fraction:.2f}"] = value
            if (value <= 0) != (full_value <= 0):
                flips += 1

        if not setting_values:
            raise ValueError("No sensitivity setting produced a valid statistic")

        return ExperimentResult(
            statistic=full_value,
            p_value=flips / len(setting_values),
            sample_size=n,
            details={
                "setting_statistics": setting_values,
                "sign_flips": flips,
                "settings": len(setting_values),
            },
        )


class StressTestExperiment(Experiment):
    """Adapts a `StressTester` into a versioned Experiment/artifact."""

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


class MonteCarloExperiment(Experiment):
    """Explicit placeholder interface — no market simulator is implemented yet."""

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
