"""ResearchPaper: every promoted discovery's paper trail, as typed sections.

Fields, not free-form markdown — every section is populated mechanically
from the actual evidence objects that produced it (`generator.py`), never
generated prose divorced from data.
"""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel

from agx_research.domain.provenance import Provenance


class ResearchPaper(BaseModel):
    id: str
    version: int = 1
    title: str
    gene_id: str
    knowledge_id: str
    hypothesis_id: str
    problem: str
    observation: str
    methodology: str
    dataset: str
    experiments: str
    evidence: str
    results: str
    limitations: str
    conclusion: str
    future_work: str
    published_at: datetime
    provenance: Provenance
