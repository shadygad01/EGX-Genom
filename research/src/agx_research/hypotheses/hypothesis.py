"""The scientific-method lifecycle every hypothesis moves through before it
can become knowledge.

Stages are strictly ordered and cannot be skipped:

    OBSERVATION -> HYPOTHESIS -> DATA_COLLECTION -> EXPERIMENT
    -> STATISTICAL_VALIDATION -> STRESS_TEST -> BACKTEST -> PEER_VALIDATION

A hypothesis that reaches PEER_VALIDATION with a passing result is eligible
for promotion into a `KnowledgeObject` (see `agx_research.knowledge`).
Promotion, monitoring, and retirement are knowledge-level lifecycle stages,
not hypothesis stages, and live in `agx_research.knowledge.lifecycle`.
"""

from __future__ import annotations

from datetime import date, datetime
from enum import IntEnum

from pydantic import BaseModel, Field

from agx_research.config import Horizon


class HypothesisStage(IntEnum):
    OBSERVATION = 0
    HYPOTHESIS = 1
    DATA_COLLECTION = 2
    EXPERIMENT = 3
    STATISTICAL_VALIDATION = 4
    STRESS_TEST = 5
    BACKTEST = 6
    PEER_VALIDATION = 7


class StageResult(BaseModel):
    """The outcome recorded when a hypothesis is evaluated at a given stage."""

    stage: HypothesisStage
    passed: bool
    evaluated_at: datetime
    notes: str = ""
    metrics: dict[str, float] = Field(default_factory=dict)


class Hypothesis(BaseModel):
    """A proposed, falsifiable relationship, moving through the scientific method."""

    id: str
    statement: str
    created_by: str  # agent name that produced the originating ResearchFinding
    created_at: date
    horizon: Horizon
    affected_assets: list[str]
    stage: HypothesisStage = HypothesisStage.OBSERVATION
    stage_history: list[StageResult] = Field(default_factory=list)

    def advance(self, result: StageResult) -> None:
        """Record the outcome of evaluating the hypothesis at its current stage.

        A failing result retires the hypothesis in place (it does not advance,
        and it is the caller's responsibility to stop pursuing it). A passing
        result moves the hypothesis to the next stage in the fixed order
        above. Stages cannot be skipped or evaluated out of order.
        """
        if result.stage != self.stage:
            raise ValueError(
                f"Cannot record a {result.stage.name} result while hypothesis "
                f"{self.id} is at stage {self.stage.name}"
            )
        self.stage_history.append(result)
        if result.passed and self.stage != HypothesisStage.PEER_VALIDATION:
            self.stage = HypothesisStage(self.stage + 1)

    @property
    def is_ready_for_promotion(self) -> bool:
        return (
            self.stage == HypothesisStage.PEER_VALIDATION
            and bool(self.stage_history)
            and self.stage_history[-1].stage == HypothesisStage.PEER_VALIDATION
            and self.stage_history[-1].passed
        )
