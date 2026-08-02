"""Publication Governance: an optional, explicitly decoupled human
sign-off record -- never a blocker on this platform's actual output.

Until 2026-08-02 this module's `evaluate_publication_gate()`/
`apply_publication_gate()` were a system-wide, all-or-nothing switch that
required a human-authored legal-approval file *and* 30+ historical
results outperforming EGX30 at 95% confidence before *any* decision, of
any quality, could size a position. Neither condition had ever been
satisfied once in this platform's history, so every decision stayed
`RESEARCH_ONLY` regardless of how complete or well-evidenced it was.

The project owner's explicit correction (2026-08-02): whether a decision
can publish should be governed by the decision's own quality (see
`meta.decision_quality`, evaluated per ticker per horizon), not by how
much track record has accumulated or whether a human has formally signed
off. Those remain real, separate concerns -- just no longer blockers on
this platform's research/personal-use output (its only mode today):

- Historical track record now only ever *labels* system credibility,
  never blocks anything -- see `meta.system_maturity`.
- `LegalPublicationApproval` (kept below, unchanged in shape) is an
  optional input to `system_maturity`'s highest ("verified") tier, and
  is reserved for a future regulated/officially-published distribution
  mode this platform does not operate in today. Nothing in the default
  `agx decide`/`agx run` path requires or reads one.
"""

from __future__ import annotations

from datetime import date, datetime

from pydantic import BaseModel, Field


class PublicationEvidenceRef(BaseModel):
    raw_document_id: str
    source_id: str
    content_hash: str = Field(pattern=r"^[0-9a-f]{64}$")
    fetched_at: datetime
    coverage_pct: float = Field(ge=0.0, le=1.0)
    independent_group: str


class LegalPublicationApproval(BaseModel):
    """A real human's sign-off record -- reviewer, scope, and disclosures
    -- for a future regulated/officially-published distribution mode.
    Purely optional and informational today: supplying one can only ever
    raise `meta.system_maturity`'s reported level, never gate whether a
    decision publishes."""

    reviewer: str
    scope: str
    approved_at: datetime
    expires_at: date
    conflicts_disclosed: bool = False
    methodology_approved: bool = False
    evidence: PublicationEvidenceRef
