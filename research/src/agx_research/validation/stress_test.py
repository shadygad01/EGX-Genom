"""The Stress Test gate: does the hypothesis hold up under adverse scenarios?

`HistoricalWorstWindowStressTester` is the concrete implementation: the
adverse scenario is not simulated (that would be fabricating market data)
but *located* — the worst k-day cumulative-return window for the
hypothesis's primary asset within the snapshot. The hypothesis's claim
statistic is recomputed inside that stressed window and must keep the same
sign as the full-window statistic. This is a real, mechanical check that
the claimed relationship didn't exist only in calm conditions.

Hypothetical scenario design (rate shocks, EGP devaluation paths) remains
future work requiring either a simulator or scenario-calibrated data —
add further `StressTester` subclasses for those, don't extend this one.
"""

from __future__ import annotations

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
