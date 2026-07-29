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
"""

from __future__ import annotations

from agx_research.acquisition_intelligence.config_generation import suggest_collector
from agx_research.collectors.fetcher import FetchDisallowed, FetchError, HttpFetcher
from agx_research.discovery.company_financial_registry import (
    CompanyFinancialSourceRecord,
    CompanyRegistryStatus,
    FinancialDocumentEntry,
)
from agx_research.discovery.engine import discover_financial_documents
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
    documents = [
        FinancialDocumentEntry(
            url=candidate.discovered_url,
            category=category,
            source_type=candidate.access_method_guess,
            collector_recommendation=suggest_collector(candidate),
            evidence=candidate.evidence,
        )
        for candidate, category in found
    ]
    status = CompanyRegistryStatus.DISCOVERED if documents else CompanyRegistryStatus.BLOCKED
    return record.model_copy(update={
        "status": status,
        "homepage_url": homepage_url,
        "robots_allowed": robots_allowed,
        "documents": documents,
        "blocked_reason": None if documents else _NO_DOCUMENTS_FOUND,
    })
