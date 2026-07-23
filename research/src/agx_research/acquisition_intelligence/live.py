"""Live network adapters for `AcquisitionIntelligenceEngine`.

Every other module in this package is deliberately network-free (fully
testable with fakes); this is the one file that imports `HttpFetcher`/
`urllib` to back the engine's injected `prober`/`fetch_text`/
`robots_checker`/`wayback` with the real internet, for a deployment that
has outbound egress. Not exercised by the test suite for the same reason
`collectors.fetcher` isn't: this development sandbox has no outbound
network egress to arbitrary hosts (see `docs/DATA_ACQUISITION.md`'s
deployment note) -- these adapters are wired and ready for wherever the
runtime is deployed with egress.
"""

from __future__ import annotations

import json
import time
import urllib.error
import urllib.request

from agx_research.acquisition_intelligence.domain_resolution import ProbeResult
from agx_research.acquisition_intelligence.historical import WaybackAvailabilityClient
from agx_research.collectors.fetcher import FetchDisallowed, FetchError, HttpFetcher
from agx_research.sources.spec import (
    AccessMethod,
    RateLimit,
    RetryPolicy,
    SourceCategory,
    SourceSpec,
    SourceStatus,
)

_USER_AGENT = "AGX-Research/1.0 (acquisition intelligence probe; contact via repository)"

# A throwaway spec purely to satisfy HttpFetcher's per-source rate-limit/
# retry-policy interface when probing a domain that isn't registered yet --
# never persisted, never registered, not a real source.
_PROBE_SPEC = SourceSpec(
    id="acquisition_intelligence_probe",
    name="Acquisition Intelligence probe (internal only, not a real source)",
    category=SourceCategory.RESEARCH,
    access_method=AccessMethod.HTML_SCRAPE,
    status=SourceStatus.IMPLEMENTED,
    reliability_score=0.0,
    freshness_score=0.0,
    retry_policy=RetryPolicy(max_attempts=1, backoff_seconds=0.5),
    rate_limit=RateLimit(requests_per_minute=20, min_seconds_between_requests=3.0),
)


def build_live_prober(fetcher: HttpFetcher):
    def prober(url: str) -> ProbeResult:
        start = time.monotonic()
        try:
            text = fetcher.fetch_text(url, _PROBE_SPEC)
            return ProbeResult(
                url=url, reachable=True, status_code=200,
                latency_seconds=time.monotonic() - start, body=text,
            )
        except FetchDisallowed as exc:
            return ProbeResult(url=url, reachable=False, error=f"robots.txt disallows: {exc}")
        except FetchError as exc:
            return ProbeResult(url=url, reachable=False, error=str(exc))

    return prober


def build_live_fetch_text(fetcher: HttpFetcher):
    def fetch_text(url: str) -> str | None:
        try:
            return fetcher.fetch_text(url, _PROBE_SPEC)
        except (FetchDisallowed, FetchError):
            return None

    return fetch_text


def build_live_robots_checker(fetcher: HttpFetcher):
    def robots_checker(url: str) -> bool | None:
        return fetcher.robots_status(url)

    return robots_checker


def build_live_wayback_client(*, timeout_seconds: float = 15.0) -> WaybackAvailabilityClient:
    def fetch_json(url: str):
        request = urllib.request.Request(url, headers={"User-Agent": _USER_AGENT})
        try:
            with urllib.request.urlopen(request, timeout=timeout_seconds) as response:
                return json.loads(response.read().decode("utf-8", errors="replace"))
        except (urllib.error.URLError, OSError, TimeoutError, json.JSONDecodeError):
            return {}

    return WaybackAvailabilityClient(fetch_json)
