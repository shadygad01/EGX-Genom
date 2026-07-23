"""The KnowledgeObject schema.

Per Principle 5 ("Everything is versioned"), a KnowledgeObject is never
mutated in place beyond appending to its performance history and advancing
its status — `version` increments whenever `KnowledgeStore` writes a new
revision, so every past state remains reconstructable.
"""

from __future__ import annotations

from datetime import date

from pydantic import BaseModel, Field

from agx_research.config import Horizon
from agx_research.knowledge.lifecycle import KnowledgeStatus


class PerformanceRecord(BaseModel):
    """One monitored outcome of a promoted piece of knowledge."""

    as_of: date
    realized_return: float
    notes: str = ""


class KnowledgeObject(BaseModel):
    """A validated, promoted piece of research knowledge.

    Fields mirror the vision document's knowledge philosophy exactly: unique
    ID, discovery date, creator agent, supporting evidence, confidence,
    statistical strength, economic explanation, affected assets, applicable
    time horizon, expected return, expected risk, current status,
    performance history, and retirement status.
    """

    id: str
    version: int = 1
    discovery_date: date
    creator_agent: str
    supporting_evidence: list[str]
    confidence: float = Field(ge=0.0, le=1.0)
    statistical_strength: float  # e.g. the experiment's p-value or test statistic
    economic_explanation: str
    affected_assets: list[str]
    horizon: Horizon
    expected_return: float
    expected_risk: float
    status: KnowledgeStatus = KnowledgeStatus.PROMOTED
    performance_history: list[PerformanceRecord] = Field(default_factory=list)
    retired_at: date | None = None
    retirement_reason: str | None = None
