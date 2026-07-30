"""PositionState: a long-term investor's current holding in one ticker.

External, user-supplied data -- never fetched, inferred, or fabricated.
A real portfolio's holdings are inherently outside anything this platform
can autonomously discover (`docs/ARCHITECTURE_ADVERSARIAL_REVIEW.md`
Section 1.10 names this tension explicitly: full autonomy applies to
research generation, not to a decision that depends on the investor's own
position). Deliberately a single aggregate position per ticker, not a
multi-lot/cost-basis-aware model -- Section 1.6 of that review flagged
staged entries and tax-lot awareness as real simplifications, kept for v1
per this mission's "simplicity preferred over architectural complexity"
constraint; extend only once a real need is named, not speculatively.
"""

from __future__ import annotations

from pydantic import BaseModel, Field


class PositionState(BaseModel):
    ticker: str
    held: bool
    current_weight: float = Field(default=0.0, ge=0.0, le=1.0)
    average_cost: float | None = None
