"""SourceCandidate: what the Discovery Engine is allowed to produce.

Deliberately a much smaller, looser shape than `SourceSpec` -- a discovery
heuristic can observe a URL and a hint about what kind of thing it is, but it
cannot know a license, a reliability prior, or a category with any
confidence. Turning a candidate into a real `SourceSpec` (`qualification.
register_candidate`) always requires those to be supplied explicitly by
whoever reviews the candidate; nothing about the shape of `SourceCandidate`
itself allows a discovery run to mint a trusted source.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field

from agx_research.sources.spec import AccessMethod


class DiscoveryMethod(str, Enum):
    RSS_AUTODISCOVERY = "rss_autodiscovery"  # <link rel=alternate type=rss/atom>
    SITEMAP_SCAN = "sitemap_scan"
    PDF_REPOSITORY_SCAN = "pdf_repository_scan"  # a page linking many PDFs (IR/regulatory)
    STRUCTURED_DATASET_SCAN = "structured_dataset_scan"  # CSV/XLS/JSON/XML download links
    API_DOCUMENTATION_SCAN = "api_documentation_scan"
    FINANCIAL_DOCUMENT_SCAN = "financial_document_scan"  # keyword-matched IR/report links
    MANUAL = "manual"


class SourceCandidate(BaseModel):
    discovered_url: str
    origin_page_url: str
    discovery_method: DiscoveryMethod
    access_method_guess: AccessMethod
    title_hint: str = ""
    evidence: str = ""  # the literal tag/link/text that triggered the finding
    discovered_at: datetime = Field(default_factory=datetime.now)
    notes: str = ""

    def fingerprint(self) -> str:
        """Stable identity for dedup -- same URL discovered twice is one candidate."""
        return self.discovered_url.strip().rstrip("/").lower()
