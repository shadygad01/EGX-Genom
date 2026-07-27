"""The Stress Test gate: does the hypothesis hold up under adverse scenarios?

`HistoricalWorstWindowStressTester` is the concrete implementation: the
adverse scenario is not simulated (that would be fabricating market data)
but *located* — the worst k-day cumulative-return window for the
hypothesis's primary asset within the snapshot. The hypothesis's claim
statistic is recomputed inside that stressed window and must keep the same
sign as the full-window statistic. This is a real, mechanical check that
the claimed relationship didn't exist only in calm conditions.

`MonteCarloBlockBootstrapStressTester` is the Monte Carlo simulator
`docs/PHASE_STATUS.md`/`NEXT_MISSIONS.md` named as the one Experiment
Factory gap that's a design decision, not a data blocker. It stays
faithful to the same "never fabricate market data" rule: every simulated
path is built by resampling *contiguous blocks* of the hypothesis's real
observed returns with replacement (a standard block bootstrap), never a
parametric/synthetic distribution — recombination of real data, not
invention of new data. Blocks (not single observations, unlike
`hypotheses.experiment_factory.BootstrapExperiment`, which exists to
estimate the statistic's general stability, not to stress-test a
worst case) preserve real short-run autocorrelation/volatility
clustering, the way actual adverse runs (several bad days in a row)
actually occur. The hypothesis's statistic is recomputed over many
simulated paths, and the tail percentile in the *adverse* direction (the
one that would falsify the claim) must keep the same sign as the
full-sample statistic.

Hypothetical, non-resampled scenario design (rate shocks, EGP devaluation
paths) remains future work requiring scenario-calibrated data this
codebase doesn't have — add further `StressTester` subclasses for those,
don't extend either of these two.
"""

from __future__ import annotations

import random
from abc import ABC, abstractmethod

from pydantic import BaseModel, Field

from agx_research.data.snapshot import DatasetSnapshot
from agx_research.hypotheses.hypothesis import Hypothesis
from agx_research.hypotheses.statistic import (
    hypothesis_statistic,
    series_for_hypothesis,
    slice_series,
)


class StressTestResult(BaseModel):
    passed: bool
    scenario_results: dict[str, float] = Field(default_factory=dict)
    notes: str = ""


class StressTester(ABC):
    """Evaluates a hypothesis against adverse market scenarios."""

    @abstractmethod
    def run(self, hypothesis: Hypothesis, snapshot: DatasetSnapshot) -> StressTestResult:
        """Run the configured stress scenarios and return the aggregate result."""


class HistoricalWorstWindowStressTester(StressTester):
    def __init__(self, window: int = 5):
        self.window = window

    def run(self, hypothesis: Hypothesis, snapshot: DatasetSnapshot) -> StressTestResult:
        series = series_for_hypothesis(hypothesis, snapshot)
        n = len(series[0])
        window = min(self.window, n)
        if n < 4 or window < 3:
            raise ValueError(
                f"Not enough data ({n} observations) to stress-test {hypothesis.id}"
            )

        # Locate the worst cumulative-return window for the primary asset.
        worst_start, worst_sum = 0, float("inf")
        for start in range(0, n - window + 1):
            window_sum = sum(series[0][start : start + window])
            if window_sum < worst_sum:
                worst_sum = window_sum
                worst_start = start

        full_value = hypothesis_statistic(series)
        stressed_value = hypothesis_statistic(
            slice_series(series, worst_start, worst_start + window)
        )

        if full_value is None or stressed_value is None:
            return StressTestResult(
                passed=False,
                scenario_results={"worst_window_cumulative_return": worst_sum},
                notes="Statistic undefined in the stressed window; treating as a failure.",
            )

        sign_holds = (full_value <= 0) == (stressed_value <= 0)
        return StressTestResult(
            passed=sign_holds,
            scenario_results={
                "worst_window_cumulative_return": worst_sum,
                "full_window_statistic": full_value,
                "stressed_window_statistic": stressed_value,
            },
            notes=(
                f"Worst {window}-day window starts at offset {worst_start} "
                f"(cumulative return {worst_sum:.4f}); statistic sign "
                f"{'holds' if sign_holds else 'flips'} under stress."
            ),
        )


def _block_bootstrap_resample(
    series: list[list[float]], n: int, block_size: int, rng: random.Random
) -> list[list[float]]:
    """Concatenate randomly-chosen contiguous blocks (sampled with
    replacement, same start index across every series so a pair
    hypothesis's cross-series alignment is preserved) until each resampled
    series reaches length `n`. Every value is a real observed return."""
    resampled: list[list[float]] = [[] for _ in series]
    max_start = n - block_size
    while len(resampled[0]) < n:
        start = rng.randint(0, max_start)
        take = min(block_size, n - len(resampled[0]))
        for i, s in enumerate(series):
            resampled[i].extend(s[start : start + take])
    return resampled


class MonteCarloBlockBootstrapStressTester(StressTester):
    """See this module's docstring for the block-bootstrap methodology.

    `block_size` defaults to 5 but shrinks to fit short series (mirroring
    `HistoricalWorstWindowStressTester`'s `window = min(self.window, n)`),
    so this never raises for any series length the DATA_COLLECTION gate
    (`orchestration.pipeline.PipelineConfig.min_observations`, default 6)
    already let through. `seed` makes every run deterministic and
    reproducible, the same convention `hypotheses.experiment_factory.
    BootstrapExperiment` already uses.
    """

    def __init__(
        self,
        iterations: int = 500,
        block_size: int = 5,
        worst_percentile: float = 0.05,
        seed: int = 42,
    ):
        if iterations < 1:
            raise ValueError("iterations must be at least 1")
        if block_size < 1:
            raise ValueError("block_size must be at least 1")
        if not 0 < worst_percentile < 1:
            raise ValueError("worst_percentile must be in (0, 1)")
        self.iterations = iterations
        self.block_size = block_size
        self.worst_percentile = worst_percentile
        self.seed = seed

    def run(self, hypothesis: Hypothesis, snapshot: DatasetSnapshot) -> StressTestResult:
        series = series_for_hypothesis(hypothesis, snapshot)
        n = len(series[0])
        if n < 4:
            raise ValueError(
                f"Not enough data ({n} observations) to stress-test {hypothesis.id}"
            )
        block_size = max(1, min(self.block_size, n // 2))

        full_value = hypothesis_statistic(series)
        if full_value is None:
            return StressTestResult(
                passed=False,
                notes="Statistic undefined over the full series; treating as a failure.",
            )

        rng = random.Random(self.seed)
        simulated: list[float] = []
        for _ in range(self.iterations):
            resampled = _block_bootstrap_resample(series, n, block_size, rng)
            value = hypothesis_statistic(resampled)
            if value is not None:
                simulated.append(value)
        if len(simulated) < 10:
            return StressTestResult(
                passed=False,
                scenario_results={"full_statistic": full_value},
                notes=(
                    f"Only {len(simulated)} of {self.iterations} simulated path(s) produced "
                    "a defined statistic; too few to assess."
                ),
            )

        simulated.sort()
        # The tail that would falsify the claim: below the full-sample
        # statistic when it's non-negative, above it when it's negative.
        tail_fraction = self.worst_percentile if full_value >= 0 else 1 - self.worst_percentile
        tail_index = min(len(simulated) - 1, max(0, round((len(simulated) - 1) * tail_fraction)))
        worst_percentile_value = simulated[tail_index]

        sign_holds = (full_value <= 0) == (worst_percentile_value <= 0)
        return StressTestResult(
            passed=sign_holds,
            scenario_results={
                "full_statistic": full_value,
                "worst_percentile_statistic": worst_percentile_value,
                "iterations": float(len(simulated)),
                "block_size": float(block_size),
            },
            notes=(
                f"{len(simulated)} block-bootstrap simulated path(s) (block size {block_size}); "
                f"the {self.worst_percentile:.0%} worst-case tail statistic "
                f"({worst_percentile_value:.4f}) {'keeps' if sign_holds else 'flips'} "
                f"the full-sample statistic's sign ({full_value:.4f})."
            ),
        )
