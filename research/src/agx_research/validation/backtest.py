"""The Backtest gate: does the hypothesis produce excess return historically?

`NaiveDirectionalBacktester` is the concrete implementation: the simplest
honest trading translation of each hypothesis type, evaluated on
split/dividend-adjusted returns with no free parameters to overfit —

- pair hypothesis (co-movement claim): hold asset A on day t in the
  direction of asset B's day t-1 return (a lead-lag reading of the claim);
- single-asset hypothesis (drift claim): hold the asset in the direction
  of its own day t-1 return (momentum reading).

It reports net mean return, hit rate, and annualized Sharpe on a held-out
tail sample after an explicit turnover-based transaction-cost assumption.
It passes only when hit rate and Sharpe clear their thresholds. Portfolio
position sizing remains outside this deliberately small validation gate.
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
    net_mean_return: float | None = None
    observations: int = 0
    transaction_cost_bps: float = 0.0
    out_of_sample_fraction: float = 0.0
    notes: str = ""


class Backtester(ABC):
    """Simulates trading a hypothesis historically and scores the result."""

    @abstractmethod
    def run(self, hypothesis: Hypothesis, snapshot: DatasetSnapshot) -> BacktestResult:
        """Run the backtest and return performance metrics."""


class NaiveDirectionalBacktester(Backtester):
    def __init__(
        self, *, min_hit_rate: float = 0.5, min_sharpe: float = 0.0,
        transaction_cost_bps: float = 20.0, out_of_sample_fraction: float = 0.30,
    ):
        self.min_hit_rate = min_hit_rate
        self.min_sharpe = min_sharpe
        self.transaction_cost_bps = transaction_cost_bps
        self.out_of_sample_fraction = out_of_sample_fraction

    def run(self, hypothesis: Hypothesis, snapshot: DatasetSnapshot) -> BacktestResult:
        series = series_for_hypothesis(hypothesis, snapshot)
        target = series[0]  # the asset actually held
        signal_source = series[1] if len(series) == 2 else series[0]
        if len(target) < 4:
            raise ValueError(
                f"Not enough data ({len(target)} observations) to backtest {hypothesis.id}"
            )

        # Position on day t is the sign of the signal source's day t-1 return.
        positions = [
            1.0 if signal_source[t - 1] > 0 else -1.0 if signal_source[t - 1] < 0 else 0.0
            for t in range(1, len(target))
        ]
        gross_returns = [position * target[t] for t, position in enumerate(positions, start=1)]
        cost_rate = self.transaction_cost_bps / 10_000
        previous = 0.0
        net_returns = []
        for gross, position in zip(gross_returns, positions):
            turnover = abs(position - previous)
            net_returns.append(gross - turnover * cost_rate)
            previous = position
        oos_size = max(3, int(len(net_returns) * self.out_of_sample_fraction))
        strategy_returns = net_returns[-oos_size:]
        oos_positions = positions[-oos_size:]
        active = [r for r, position in zip(strategy_returns, oos_positions) if position != 0]
        if not active:
            return BacktestResult(
                passed=False,
                observations=len(strategy_returns),
                transaction_cost_bps=self.transaction_cost_bps,
                out_of_sample_fraction=self.out_of_sample_fraction,
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
            net_mean_return=mean_return,
            observations=len(strategy_returns),
            transaction_cost_bps=self.transaction_cost_bps,
            out_of_sample_fraction=self.out_of_sample_fraction,
            notes=(
                f"Out-of-sample directional backtest over {len(strategy_returns)} days; "
                f"hit_rate={hit_rate:.3f} (min {self.min_hit_rate}), "
                f"annualized_sharpe={sharpe:.3f} (min {self.min_sharpe}). "
                f"Includes {self.transaction_cost_bps:.1f} bps transaction costs per unit turnover; "
                "position sizing remains fixed at one unit."
            ),
        )
