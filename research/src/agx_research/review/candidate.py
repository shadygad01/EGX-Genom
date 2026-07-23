"""What a Reviewer evaluates: the fields `KnowledgeStore.promote()` would need,
bundled before promotion actually happens.

The Review Board runs *before* `KnowledgeStore.promote()` in the intended
production flow (see `board.py`), so there is no `KnowledgeObject` yet to
review — only the candidate values that would become one.
"""

from __future__ import annotations

from pydantic import BaseModel, Field

from agx_research.validation.statistical import StatisticalEvidence


class PromotionCandidate(BaseModel):
    confidence: float
    statistical_evidence: StatisticalEvidence
    economic_explanation: str
    expected_return: float
    expected_risk: float
    supporting_evidence: list[str] = Field(default_factory=list)
