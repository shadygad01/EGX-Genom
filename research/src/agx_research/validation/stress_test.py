"""The Stress Test gate: does the hypothesis hold up under adverse scenarios?

No concrete implementation yet — scenario design (rate shocks, EGP
devaluation, sector-specific shocks, liquidity crunches, etc.) is a research
decision, not scaffolding. Implement `StressTester` subclasses once specific
scenarios are defined.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from pydantic import BaseModel, Field

from agx_research.data.provider import DataProvider
from agx_research.hypotheses.hypothesis import Hypothesis


class StressTestResult(BaseModel):
    passed: bool
    scenario_results: dict[str, float] = Field(default_factory=dict)
    notes: str = ""


class StressTester(ABC):
    """Evaluates a hypothesis against adverse market scenarios."""

    @abstractmethod
    def run(self, hypothesis: Hypothesis, data_provider: DataProvider) -> StressTestResult:
        """Run the configured stress scenarios and return the aggregate result."""
