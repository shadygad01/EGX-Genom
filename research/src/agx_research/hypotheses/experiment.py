"""The Experiment stage of the hypothesis lifecycle.

An Experiment is the concrete, repeatable procedure that produces the
evidence a hypothesis is judged on. Statistical Validation, Stress Test, and
Backtest (see `agx_research.validation`) are subsequent, distinct gates that
consume an ExperimentResult rather than being part of the experiment itself.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from pydantic import BaseModel, Field

from agx_research.data.snapshot import DatasetSnapshot
from agx_research.hypotheses.hypothesis import Hypothesis


class ExperimentResult(BaseModel):
    """Raw output of running an experiment against a hypothesis."""

    statistic: float
    p_value: float
    sample_size: int
    details: dict = Field(default_factory=dict)


class Experiment(ABC):
    """A repeatable procedure that produces evidence for or against a hypothesis."""

    @abstractmethod
    def run(self, hypothesis: Hypothesis, snapshot: DatasetSnapshot) -> ExperimentResult:
        """Execute the experiment and return its raw result.

        Implementations must be deterministic given the same data so that
        results are reproducible and versionable.
        """
