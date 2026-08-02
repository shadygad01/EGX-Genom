"""The investment claim is the atomic unit of learning.

Papers are source/evidence containers.  A claim owns its lifecycle and is
the only research entity that can become production-eligible.
"""

from __future__ import annotations

from datetime import date, datetime
from enum import Enum

from pydantic import BaseModel, Field, model_validator

from agx_research.config import Horizon
from agx_research.domain.provenance import Provenance
from agx_research.hypotheses.pipeline import GateSpec


class ClaimStage(str, Enum):
    HYPOTHESIS = "hypothesis"
    EXPERIMENT = "experiment"
    VALIDATION = "validation"
    SHADOW_FUND = "shadow_fund"
    INVESTMENT_PROOF = "investment_proof"
    PROMOTED = "promoted"
    REJECTED = "rejected"


TERMINAL_STAGES = {ClaimStage.PROMOTED, ClaimStage.REJECTED}
CLAIM_LIFECYCLE = (
    ClaimStage.HYPOTHESIS,
    ClaimStage.EXPERIMENT,
    ClaimStage.VALIDATION,
    ClaimStage.SHADOW_FUND,
    ClaimStage.INVESTMENT_PROOF,
    ClaimStage.PROMOTED,
)


class ClaimEvidence(BaseModel):
    stage: ClaimStage
    evidence_type: str
    ref_id: str
    recorded_at: datetime
    passed: bool
    notes: str = ""
    metrics: dict[str, float] = Field(default_factory=dict)


class Claim(BaseModel):
    id: str
    version: int = 1
    statement: str
    created_by: str
    created_at: date
    horizon: Horizon
    affected_assets: list[str]
    provenance: Provenance
    methodology_id: str
    methodology: list[GateSpec]
    source_paper_ids: list[str] = Field(default_factory=list)
    hypothesis_id: str
    knowledge_id: str | None = None
    stage: ClaimStage = ClaimStage.HYPOTHESIS
    evidence_history: list[ClaimEvidence] = Field(default_factory=list)
    rejection_reason: str | None = None

    @model_validator(mode="after")
    def validate_terminal_state(self) -> "Claim":
        if self.stage == ClaimStage.REJECTED and not self.rejection_reason:
            raise ValueError("A rejected claim must record a rejection reason")
        return self

    @property
    def is_experimentally_validated(self) -> bool:
        """The sole production-consumption gate."""
        validation = [e for e in self.evidence_history if e.stage == ClaimStage.VALIDATION]
        return bool(validation) and validation[-1].passed and self.stage != ClaimStage.REJECTED

    @property
    def is_ready_for_promotion(self) -> bool:
        """Compatibility with KnowledgeStore's structural evidence protocol.

        Knowledge promotion means eligibility for production knowledge; final
        claim promotion remains a later lifecycle stage after shadow proof.
        """
        return self.is_experimentally_validated

    @property
    def current_stage_name(self) -> str:
        return self.stage.value
