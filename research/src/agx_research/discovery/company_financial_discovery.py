"""Orchestrates one company's financial-source discovery attempt: fetch its
homepage, scan for categorized IR/report links (`discovery.engine.
discover_financial_documents`), suggest a collector per document
(`acquisition_intelligence.config_generation.suggest_collector`, the same
function `AcquisitionIntelligenceEngine` already uses -- no duplicated
recommendation logic), and fold the result into a
`CompanyFinancialSourceRecord`. Every outcome (discovered, blocked, or
homepage unreachable) is evidenced by a real fetch attempt through the
platform's own `HttpFetcher` (robots.txt/rate-limit/retry policy already
enforced there) -- nothing here fabricates a document or a reachable page.

One-level Investor Relations traversal (`docs/COLLECTOR_TEMPLATE_TAXONOMY.md`'s
Gap 1, closed here): a company's homepage very often links only the IR
*section* itself, not the specific report pages beneath it -- real evidence
from the first live run showed 8 of 21 `discovered` companies with nothing
but a bare `investor_relations_home` link because the crawl never went past
the homepage. This module now follows every distinct, actually-navigable
`INVESTOR_RELATIONS_HOME` candidate the homepage scan finds -- once, never
recursively, and gracefully (a failed follow-up fetch does not blank out
the level-1 evidence already gathered) -- and folds in whatever that page's
own links classify as. Deliberately still one real fetch attempt per page,
matching the module's existing "no retry loop against a known-blocked
destination" posture.
"""

from __future__ import annotations

from urllib.parse import urlsplit

from agx_research.acquisition_intelligence.config_generation import suggest_collector
from agx_research.collectors.fetcher import FetchDisallowed, FetchError, HttpFetcher
from agx_research.discovery.candidate import SourceCandidate
from agx_research.discovery.company_financial_registry import (
    CompanyFinancialSourceRecord,
    CompanyRegistryStatus,
    FinancialDocumentEntry,
)
from agx_research.discovery.engine import discover_financial_documents
from agx_research.discovery.financial_document import FinancialDocumentCategory
from agx_research.sources.spec import (
    AccessMethod,
    RateLimit,
    RetryPolicy,
    SourceCategory,
    SourceSpec,
    SourceStatus,
)

# A single-attempt probe spec: real EGX company sites are frequently
# unreachable from a restricted-egress environment (see TD-39), and
# repeatedly retrying a host that has already failed policy/reachability
# checks would just be hammering a known-blocked destination -- one honest
# attempt per company per run is the right posture, not a retry loop.
_PROBE_SPEC = SourceSpec(
    id="__company_financial_discovery_probe__",
    name="Company financial-source discovery probe",
    category=SourceCategory.COMPANY,
    access_method=AccessMethod.HTML_SCRAPE,
    status=SourceStatus.PLANNED,
    reliability_score=0.3,
    freshness_score=0.3,
    rate_limit=RateLimit(requests_per_minute=6, min_seconds_between_requests=2.0),
    retry_policy=RetryPolicy(max_attempts=1),
)

_NO_DOCUMENTS_FOUND = (
    "Homepage fetched successfully but no financial-document links matched "
    "(annual report/quarterly report/financial statements/investor relations "
    "keywords) -- needs manual IR-page review."
)


def _navigable_ir_home_urls(
    found: list[tuple[SourceCandidate, FinancialDocumentCategory]], homepage_url: str
) -> list[str]:
    """Distinct `INVESTOR_RELATIONS_HOME` candidates worth a real follow-up
    fetch -- excludes `javascript:`/`mailto:`/bare-fragment anchors (e.g.
    `#`, `#tab-mega-...`) that resolve back to the homepage itself, since
    following those would just refetch the page already in hand and could
    never be an infinite loop risk anyway (this function is called once,
    never recursively, by `discover_company_financial_sources`).
    """
    homepage_no_fragment = homepage_url.split("#", 1)[0].rstrip("/")
    seen: set[str] = set()
    urls: list[str] = []
    for candidate, category in found:
        if category != FinancialDocumentCategory.INVESTOR_RELATIONS_HOME:
            continue
        url = candidate.discovered_url
        parts = urlsplit(url)
        if parts.scheme not in ("http", "https") or not parts.netloc:
            continue
        no_fragment = url.split("#", 1)[0].rstrip("/")
        if no_fragment == homepage_no_fragment or no_fragment in seen:
            continue
        seen.add(no_fragment)
        urls.append(url)
    return urls


def discover_company_financial_sources(
    fetcher: HttpFetcher,
    record: CompanyFinancialSourceRecord,
    homepage_url: str,
) -> CompanyFinancialSourceRecord:
    """Returns an updated copy of `record` -- never mutates it in place,
    matching this codebase's append-only versioning discipline.
    """
    robots_allowed = fetcher.robots_status(homepage_url)
    try:
        html = fetcher.fetch_text(homepage_url, _PROBE_SPEC)
    except (FetchDisallowed, FetchError) as exc:
        return record.model_copy(update={
            "status": CompanyRegistryStatus.BLOCKED,
            "homepage_url": homepage_url,
            "robots_allowed": robots_allowed,
            "blocked_reason": f"{type(exc).__name__}: {exc}",
        })

    found = discover_financial_documents(html, homepage_url)

    # One-level IR-link traversal (docs/COLLECTOR_TEMPLATE_TAXONOMY.md's Gap
    # 1): the homepage frequently links only the IR section itself, not the
    # report pages beneath it. A failed follow-up fetch is non-fatal -- the
    # level-1 evidence already gathered still stands.
    for ir_url in _navigable_ir_home_urls(found, homepage_url):
        try:
            ir_html = fetcher.fetch_text(ir_url, _PROBE_SPEC)
        except (FetchDisallowed, FetchError):
            continue
        found = found + discover_financial_documents(ir_html, ir_url)

    documents: list[FinancialDocumentEntry] = []
    seen_fingerprints: set[str] = set()
    for candidate, category in found:
        fingerprint = candidate.fingerprint()
        if fingerprint in seen_fingerprints:
            continue
        seen_fingerprints.add(fingerprint)
        documents.append(
            FinancialDocumentEntry(
                url=candidate.discovered_url,
                category=category,
                source_type=candidate.access_method_guess,
                collector_recommendation=suggest_collector(candidate),
                evidence=candidate.evidence,
            )
        )
    status = CompanyRegistryStatus.DISCOVERED if documents else CompanyRegistryStatus.BLOCKED
    return record.model_copy(update={
        "status": status,
        "homepage_url": homepage_url,
        "robots_allowed": robots_allowed,
        "documents": documents,
        "blocked_reason": None if documents else _NO_DOCUMENTS_FOUND,
    })
