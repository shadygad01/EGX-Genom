"""The scientific-method lifecycle every hypothesis moves through before it
can become knowledge.

A hypothesis walks its `pipeline` (see `hypotheses/pipeline.py`) one named
gate at a time, in order; gates cannot be skipped or evaluated out of turn.
A hypothesis that reaches its pipeline's final gate with a passing result is
eligible for promotion into a `KnowledgeObject` (see `agx_research.knowledge`).
Promotion, monitoring, and retirement are knowledge-level lifecycle stages,
not hypothesis stages, and live in `agx_research.knowledge.lifecycle`.

`Hypothesis` is immutable: `advance()` returns a new revision rather than
mutating in place, consistent with how `KnowledgeObject` revisions work —
callers persist whichever revision they want via `HypothesisRepository`.
"""

from __future__ import annotations

from datetime import date, datetime
from typing import TYPE_CHECKING

from pydantic import BaseModel, Field

from agx_research.config import Horizon
from agx_research.domain.identifiers import new_id
from agx_research.domain.provenance import Provenance, ProvenanceRef
from agx_research.hypotheses.pipeline import DEFAULT_PIPELINE, GateSpec

if TYPE_CHECKING:
    from agx_research.agents.base import ResearchFinding


class StageResult(BaseModel):
    """The outcome recorded when a hypothesis is evaluated at its current gate."""

    stage_name: str
    passed: bool
    evaluated_at: datetime
    notes: str = ""
    metrics: dict[str, float] = Field(default_factory=dict)


class Hypothesis(BaseModel):
    """A proposed, falsifiable relationship, moving through its validation pipeline."""

    id: str
    version: int = 1
    statement: str
    created_by: str  # agent name that produced the originating ResearchFinding
    created_at: date
    horizon: Horizon
    affected_assets: list[str]
    provenance: Provenance
    pipeline: list[GateSpec] = Field(default_factory=lambda: list(DEFAULT_PIPELINE))
    stage_index: int = 0
    stage_history: list[StageResult] = Field(default_factory=list)

    @classmethod
    def from_finding(
        cls,
        finding: "ResearchFinding",
        *,
        hypothesis_id: str | None = None,
        pipeline: list[GateSpec] | None = None,
    ) -> "Hypothesis":
        return cls(
            id=hypothesis_id or new_id("hyp"),
            statement=finding.proposed_hypothesis_statement,
            created_by=finding.agent_name,
            created_at=finding.observed_at,
            horizon=finding.horizon,
            affected_assets=finding.affected_assets,
            provenance=Provenance(
                produced_by=f"{finding.agent_name}@{finding.agent_version}",
                produced_at=datetime.now(),
                inputs=[ProvenanceRef(kind="research_finding", ref_id=finding.id)],
            ),
            pipeline=pipeline or list(DEFAULT_PIPELINE),
        )

    @property
    def current_stage_name(self) -> str:
        return self.pipeline[self.stage_index].name

    def advance(self, result: StageResult) -> "Hypothesis":
        """Return a new revision recording the outcome of evaluating the current gate.

        A failing result does not advance the pipeline index (it is the
        caller's responsibility to stop pursuing a hypothesis that keeps
        failing its current gate). A passing result moves to the next gate
        in `pipeline`, in order; gates cannot be skipped.
        """
        if result.stage_name != self.current_stage_name:
            raise ValueError(
                f"Cannot record a {result.stage_name} result while hypothesis "
                f"{self.id} is at gate {self.current_stage_name}"
            )
        next_stage_index = self.stage_index
        if result.passed and self.stage_index < len(self.pipeline) - 1:
            next_stage_index = self.stage_index + 1
        return self.model_copy(
            update={
                "version": self.version + 1,
                "stage_index": next_stage_index,
                "stage_history": [*self.stage_history, result],
            }
        )

    @property
    def is_ready_for_promotion(self) -> bool:
        return (
            self.stage_index == len(self.pipeline) - 1
            and bool(self.stage_history)
            and self.stage_history[-1].stage_name == self.current_stage_name
            and self.stage_history[-1].passed
        )
