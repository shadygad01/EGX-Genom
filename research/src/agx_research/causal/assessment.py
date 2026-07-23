"""The Causal Engine's evidence shapes.

Per the brief, this epoch builds the architecture, not full causal
inference. `CausalAssessment` is what a `CausalReasoner` (see
`reasoner.py`) produces: candidate causes, confounders, alternative
explanations, confidence, and economic rationale — every field the vision
document requires an explanation to cover, structured rather than prose.
"""

from __future__ import annotations

from pydantic import BaseModel, Field

from agx_research.domain.provenance import Provenance


class CandidateCause(BaseModel):
    description: str
    mechanism: str
    supporting_evidence: list[str] = Field(default_factory=list)


class Confounder(BaseModel):
    description: str
    plausibility: float = Field(ge=0.0, le=1.0)


class AlternativeExplanation(BaseModel):
    description: str
    plausibility: float = Field(ge=0.0, le=1.0)


class CausalAssessment(BaseModel):
    hypothesis_id: str
    candidate_causes: list[CandidateCause] = Field(default_factory=list)
    confounders: list[Confounder] = Field(default_factory=list)
    alternative_explanations: list[AlternativeExplanation] = Field(default_factory=list)
    confidence: float = Field(ge=0.0, le=1.0)
    economic_rationale: str
    notes: str = ""
    provenance: Provenance
