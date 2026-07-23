"""The Backtest gate: does the hypothesis produce excess return historically?

No concrete implementation yet — real backtesting requires a portfolio
simulation harness (position sizing, transaction costs, EGX trading
calendar/settlement rules) that doesn't exist yet in this scaffold.
Implement `Backtester` subclasses once that harness exists.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from pydantic import BaseModel

from agx_research.data.snapshot import DatasetSnapshot
from agx_research.hypotheses.hypothesis import Hypothesis


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
