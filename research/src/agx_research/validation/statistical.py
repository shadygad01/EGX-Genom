"""The Statistical Validation gate.

`SignificanceThresholdValidator` is a real (if deliberately simple)
implementation — a p-value threshold check — included so the pipeline has
at least one working gate to run end to end. It is not a substitute for
more rigorous validation (multiple-testing correction, out-of-sample
checks, etc.); treat it as a floor, not the final word.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from pydantic import BaseModel

from agx_research.hypotheses.experiment import ExperimentResult


class ValidationResult(BaseModel):
    passed: bool
    p_value: float
    alpha: float
    notes: str = ""


class StatisticalValidator(ABC):
    """Turns raw experiment output into a pass/fail statistical judgment."""

    @abstractmethod
    def validate(self, experiment_result: ExperimentResult) -> ValidationResult:
        """Judge whether `experiment_result` clears this validator's bar."""


class SignificanceThresholdValidator(StatisticalValidator):
    """Passes an experiment result whose p-value is below `alpha`."""

    def __init__(self, alpha: float = 0.05):
        self.alpha = alpha

    def validate(self, experiment_result: ExperimentResult) -> ValidationResult:
        passed = experiment_result.p_value < self.alpha
        return ValidationResult(
            passed=passed,
            p_value=experiment_result.p_value,
            alpha=self.alpha,
            notes=(
                f"p={experiment_result.p_value:.4g} "
                f"{'<' if passed else '>='} alpha={self.alpha}"
            ),
        )
