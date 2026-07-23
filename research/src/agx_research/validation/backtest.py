"""The Backtest gate: does the hypothesis produce excess return historically?

`NaiveDirectionalBacktester` is the concrete implementation: the simplest
honest trading translation of each hypothesis type, evaluated on
split/dividend-adjusted returns with no free parameters to overfit —

- pair hypothesis (co-movement claim): hold asset A on day t in the
  direction of asset B's day t-1 return (a lead-lag reading of the claim);
- single-asset hypothesis (drift claim): hold the asset in the direction
  of its own day t-1 return (momentum reading).

It reports hit rate and an annualized Sharpe ratio and passes only when
both clear their thresholds. It deliberately ignores transaction costs and
position sizing — those belong to a portfolio-level simulation harness
(system 15+) — and says so in its notes rather than pretending otherwise.
"""

from __future__ import annotations

import statistics
from abc import ABC, abstractmethod

from pydantic import BaseModel

from agx_research.data.snapshot import DatasetSnapshot
from agx_research.hypotheses.hypothesis import Hypothesis
from agx_research.hypotheses.statistic import series_for_hypothesis

_TRADING_DAYS_PER_YEAR = 250


class BacktestResult(BaseModel):
    passed: bool
    sharpe_ratio: float | None = None
    hit_rate: float | None = None
    notes: str = ""


class Backtester(ABC):
    """Simulates trading a hypothesis historically and scores the result."""

    @abstractmethod
    def run(self, hypothesis: Hypothesis, snapshot: DatasetSnapshot) -> BacktestResult:
        """Run the backtest and return performance metrics."""


class NaiveDirectionalBacktester(Backtester):
    def __init__(self, *, min_hit_rate: float = 0.5, min_sharpe: float = 0.0):
        self.min_hit_rate = min_hit_rate
        self.min_sharpe = min_sharpe

    def run(self, hypothesis: Hypothesis, snapshot: DatasetSnapshot) -> BacktestResult:
        series = series_for_hypothesis(hypothesis, snapshot)
        target = series[0]  # the asset actually held
        signal_source = series[1] if len(series) == 2 else series[0]
        if len(target) < 4:
            raise ValueError(
                f"Not enough data ({len(target)} observations) to backtest {hypothesis.id}"
            )

        # Position on day t is the sign of the signal source's day t-1 return.
        strategy_returns = [
            (1.0 if signal_source[t - 1] > 0 else -1.0 if signal_source[t - 1] < 0 else 0.0)
            * target[t]
            for t in range(1, len(target))
        ]
        active = [r for r, s in zip(strategy_returns, signal_source) if s != 0]
        if not active:
            return BacktestResult(
                passed=False,
                notes="Signal was flat for the whole window; nothing to evaluate.",
            )

        hits = sum(1 for r in active if r > 0)
        hit_rate = hits / len(active)
        mean_return = statistics.fmean(strategy_returns)
        std_return = statistics.pstdev(strategy_returns)
        sharpe = (
            (mean_return / std_return) * _TRADING_DAYS_PER_YEAR**0.5 if std_return > 0 else 0.0
        )

        passed = hit_rate >= self.min_hit_rate and sharpe >= self.min_sharpe
        return BacktestResult(
            passed=passed,
            sharpe_ratio=sharpe,
            hit_rate=hit_rate,
            notes=(
                f"Naive directional backtest over {len(strategy_returns)} days; "
                f"hit_rate={hit_rate:.3f} (min {self.min_hit_rate}), "
                f"annualized_sharpe={sharpe:.3f} (min {self.min_sharpe}). "
                "Ignores transaction costs and position sizing by design."
            ),
        )
