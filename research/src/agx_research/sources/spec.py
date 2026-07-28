"""SourceSpec: the full declarative description of one data source.

Every source is independently replaceable because everything a collector
needs to know about it — access, limits, licensing, validation and
normalization rules, conflict priority — lives here as data, versioned in
the `SourceRegistry`, not in code. The only code per source family is its
collector, and generic collectors (RSS, CSV endpoints) serve many specs.

Honesty conventions:
- `reliability_score`/`freshness_score` are *declared priors* (documented
  in the seed catalog), replaced by measured values as history accumulates.
- `data_quality_score` starts None: it is only ever measured, never
  declared.
- `status` states plainly whether the source is collectable today and, if
  not, exactly what blocks it (user API key, ToS review).
"""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, Field


class SourceCategory(str, Enum):
    OFFICIAL = "official"
    COMPANY = "company"
    MARKET_DATA = "market_data"
    NEWS = "news"
    ARABIC_NEWS = "arabic_news"
    MACROECONOMIC = "macroeconomic"
    GLOBAL_MARKETS = "global_markets"
    ALTERNATIVE = "alternative"
    RESEARCH = "research"


class AccessMethod(str, Enum):
    CSV_DOWNLOAD = "csv_download"
    JSON_API = "json_api"
    RSS_FEED = "rss_feed"
    XBRL = "xbrl"
    PDF_DOWNLOAD = "pdf_download"
    HTML_SCRAPE = "html_scrape"  # last resort only, per program rules
    MANUAL = "manual"


class SourceStatus(str, Enum):
    IMPLEMENTED = "implemented"  # a real collector exists and is tested
    PLANNED = "planned"  # catalogued; collector/config pending
    NEEDS_KEY = "needs_key"  # free tier requires a user-registered API key
    TOS_REVIEW = "tos_review"  # terms ambiguity blocks collection until reviewed
    DISABLED = "disabled"


class LegalUseStatus(str, Enum):
    """Independent legal-review state; implementation is never legal clearance."""

    CLEARED = "cleared"
    RESEARCH_ONLY = "research_only"
    REVIEW_REQUIRED = "review_required"
    BLOCKED = "blocked"


class LifecycleState(str, Enum):
    """Where a source sits in the qualification pipeline (`sources.qualification`).

    Distinct from `SourceStatus`: `status` gates *whether a collector may run
    at all* (auth/ToS/config); `lifecycle_state` gates *how much the rest of
    the platform trusts it* once it can run. A source can be IMPLEMENTED and
    still only CANDIDATE/QUARANTINE if it hasn't accumulated evidence yet.
    Promotion only ever moves forward one stage at a time and only on
    evidence (see `qualification.evaluate_promotion`) — never assigned by
    fiat, never skipped.
    """

    CANDIDATE = "candidate"  # discovered, nothing about it verified yet
    QUARANTINE = "quarantine"  # verified reachable; collecting but unscored
    EVALUATION = "evaluation"  # enough runs to score reputation, still probationary
    TRUSTED = "trusted"  # reputation cleared the bar; feeds the platform normally
    CORE = "core"  # long-running, high-reputation; a load-bearing source


class HealthStatus(str, Enum):
    """Current operational health, maintained by `sources.health`."""

    UNKNOWN = "unknown"  # never run, or no recent run to judge by
    HEALTHY = "healthy"
    DEGRADED = "degraded"  # elevated failures/staleness but still producing data
    DOWN = "down"  # consecutive failures past the alert threshold


class ActivationStatus(str, Enum):
    """Whether this source is switched on for scheduled collection."""

    ACTIVE = "active"
    PAUSED = "paused"  # held pending an external unblock (health alert, key, ToS review)
    RETIRED = "retired"  # permanently withdrawn (superseded, dead, ToS revoked)


def default_lifecycle_for_status(status: SourceStatus) -> tuple[LifecycleState, ActivationStatus]:
    """The seed catalog's one honest mapping from access status to platform trust.

    IMPLEMENTED sources were engineering-verified (endpoint confirmed, collector
    tested against recorded fixtures) rather than autonomously discovered, so
    they start at TRUSTED rather than walking the CANDIDATE/QUARANTINE stages
    meant for the discovery engine's output — but never CORE, which is reserved
    for sources with actual measured run history (`reputation.py`).
    PLANNED sources are catalogued but nothing about them is verified yet, so
    they stay CANDIDATE and ACTIVE (engineering work to verify them continues).
    NEEDS_KEY/TOS_REVIEW are CANDIDATE and PAUSED — genuinely blocked on a
    credential or legal review, not a collection failure.
    DISABLED is RETIRED outright.
    """

    if status == SourceStatus.IMPLEMENTED:
        return LifecycleState.TRUSTED, ActivationStatus.ACTIVE
    if status == SourceStatus.DISABLED:
        return LifecycleState.CANDIDATE, ActivationStatus.RETIRED
    if status in (SourceStatus.NEEDS_KEY, SourceStatus.TOS_REVIEW):
        return LifecycleState.CANDIDATE, ActivationStatus.PAUSED
    return LifecycleState.CANDIDATE, ActivationStatus.ACTIVE


class RetryPolicy(BaseModel):
    max_attempts: int = 3
    backoff_seconds: float = 2.0
    backoff_multiplier: float = 2.0


class RateLimit(BaseModel):
    requests_per_minute: int = 10
    min_seconds_between_requests: float = 1.0


class SourceSpec(BaseModel):
    id: str
    version: int = 1
    name: str
    category: SourceCategory
    country: str = "EG"
    access_method: AccessMethod
    status: SourceStatus
    legal_use_status: LegalUseStatus = LegalUseStatus.REVIEW_REQUIRED
    lifecycle_state: LifecycleState = LifecycleState.CANDIDATE
    health_status: HealthStatus = HealthStatus.UNKNOWN
    activation_status: ActivationStatus = ActivationStatus.ACTIVE
    base_url: str | None = None
    authentication: str = "none"  # "none" | "api_key(user-supplied)" | description
    reliability_score: float = Field(ge=0.0, le=1.0, description="Declared prior until measured")
    freshness_score: float = Field(ge=0.0, le=1.0, description="Declared prior until measured")
    historical_coverage: str = "unknown"
    expected_latency: str = "unknown"
    update_frequency: str = "unknown"
    schema_version: str = "1.0"
    collector: str | None = None  # collector class name serving this spec
    collector_version: str | None = None
    integrated_via: str | None = Field(
        default=None,
        description="Source is an operational provider leg inside this parent collector.",
    )
    integrated_capabilities: list[str] = Field(default_factory=list)
    retry_policy: RetryPolicy = Field(default_factory=RetryPolicy)
    rate_limit: RateLimit = Field(default_factory=RateLimit)
    license: str = "unknown"
    terms_of_use_url: str | None = None
    provenance_policy: str = "raw_document_envelope"  # every payload wrapped as RawDocument
    validation_rules: list[str] = Field(default_factory=list)
    normalization_rules: list[str] = Field(default_factory=list)
    conflict_priority: int = Field(
        default=50,
        description="Higher wins ties in cross-source conflict resolution (0-100).",
    )
    priority: int = Field(
        default=50,
        description="Collection scheduling priority (0-100, higher collected/discovered first). "
        "Distinct from conflict_priority, which only matters at resolution time.",
    )
    supported_entities: list[str] = Field(default_factory=list)
    supported_event_types: list[str] = Field(default_factory=list)
    supported_languages: list[str] = Field(default_factory=lambda: ["en"])
    data_quality_score: float | None = Field(
        default=None, description="Measured only; never declared."
    )
    reputation_score: float | None = Field(
        default=None,
        description="Composite score from sources.reputation; measured only, never declared.",
    )
    notes: str = ""
