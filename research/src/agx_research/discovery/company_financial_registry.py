"""CompanyFinancialSourceRegistry: one resumable, versioned record per
EGX30/EGX70 company, indexing whatever Investor Relations / financial
report sources have been discovered for it so far.

Same "index over evidence, not a parallel source of truth" discipline as
`graph.KnowledgeGraph`: every `FinancialDocumentEntry` traces back to a
real, actually-fetched page (`discovery.company_financial_discovery`) --
this module never asserts a document exists that a fetch didn't observe.

Resumability contract ("never restart completed work, resume from the
last validated company"): `is_resumable_skip()` is the single place that
decides a company can be skipped on a re-run, and it only returns True for
`VALIDATED` -- `BLOCKED`/`HOMEPAGE_UNRESOLVED`/`PENDING` are always
re-attempted, since a later run (e.g. with real network egress this
codebase's own sandbox may lack -- see TD-39) might succeed where an
earlier one couldn't. `VALIDATED` is deliberately never set automatically
by the discovery pipeline itself -- reaching it requires a human/engineer
review step confirming the discovered documents are real and correctly
categorized, the same "auto-discovery proposes, a review step confirms"
discipline `sources.qualification` already applies before anything reaches
`TRUSTED`.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from pathlib import Path

from pydantic import BaseModel, Field

from agx_research.discovery.financial_document import FinancialDocumentCategory
from agx_research.sources.spec import AccessMethod
from agx_research.storage.repository import JsonFileRepository


class CompanyRegistryStatus(str, Enum):
    PENDING = "pending"  # not yet attempted
    HOMEPAGE_UNRESOLVED = "homepage_unresolved"  # no evidenced homepage hint exists yet
    BLOCKED = "blocked"  # homepage known; fetch attempt failed or found nothing categorizable
    DISCOVERED = "discovered"  # homepage fetched; >=1 financial document found
    VALIDATED = "validated"  # DISCOVERED and human/engineer-reviewed


class FinancialDocumentEntry(BaseModel):
    url: str
    category: FinancialDocumentCategory
    source_type: AccessMethod
    collector_recommendation: str | None = None
    evidence: str
    discovered_at: datetime = Field(default_factory=datetime.now)


class CompanyFinancialSourceRecord(BaseModel):
    id: str  # ticker
    version: int = 1
    ticker: str
    company_name: str
    isin: str | None = None
    index_membership: list[str] = Field(default_factory=list)  # e.g. ["EGX30"]
    homepage_url: str | None = None
    homepage_hint_source: str | None = None  # e.g. "web_search", "wikidata"
    status: CompanyRegistryStatus = CompanyRegistryStatus.PENDING
    documents: list[FinancialDocumentEntry] = Field(default_factory=list)
    robots_allowed: bool | None = None  # None = robots.txt unreachable/unknown
    blocked_reason: str | None = None
    last_attempted_at: datetime = Field(default_factory=datetime.now)
    notes: str = ""


class CompanyFinancialSourceRegistry(JsonFileRepository[CompanyFinancialSourceRecord]):
    def __init__(self, persist_path: Path | str | None = None):
        super().__init__(CompanyFinancialSourceRecord, persist_path)

    def by_status(self, status: CompanyRegistryStatus) -> list[CompanyFinancialSourceRecord]:
        return [r for r in self.all_latest() if r.status == status]

    def is_resumable_skip(self, ticker: str) -> bool:
        current = self.latest(ticker)
        return current is not None and current.status == CompanyRegistryStatus.VALIDATED

    def record(self, entry: CompanyFinancialSourceRecord) -> CompanyFinancialSourceRecord:
        current = self.latest(entry.id)
        version = (current.version + 1) if current else 1
        return self.add(entry.model_copy(update={"version": version}))
