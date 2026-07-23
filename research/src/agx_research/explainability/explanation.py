"""The Explanation object required on every prediction and recommendation.

Principle 3 forbids black-box predictions. Concretely, that means nothing in
`horizons/` or `meta/` may return a prediction or recommendation without one
of these attached, and every field must answer one of the six questions the
vision document requires explainability to cover.
"""

from __future__ import annotations

from pydantic import BaseModel, Field


class Explanation(BaseModel):
    """Answers to the questions every recommendation must be able to answer."""

    why_this_stock: str
    why_now: str
    why_not_others: str
    supporting_evidence: list[str] = Field(default_factory=list)
    similar_historical_cases: list[str] = Field(default_factory=list)
    invalidation_conditions: list[str] = Field(default_factory=list)
