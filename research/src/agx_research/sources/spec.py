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
    access_method: AccessMethod
    status: SourceStatus
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
    supported_entities: list[str] = Field(default_factory=list)
    supported_event_types: list[str] = Field(default_factory=list)
    supported_languages: list[str] = Field(default_factory=lambda: ["en"])
    data_quality_score: float | None = Field(
        default=None, description="Measured only; never declared."
    )
    notes: str = ""
