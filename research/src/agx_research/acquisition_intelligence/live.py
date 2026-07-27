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
import sys
import time
import urllib.error
import urllib.request

from agx_research.acquisition_intelligence.domain_resolution import ProbeResult
from agx_research.acquisition_intelligence.historical import WaybackAvailabilityClient
from agx_research.collectors.fetcher import FetchDisallowed, FetchError, HttpFetcher
from agx_research.discovery.wikidata_lookup import WikidataOfficialWebsiteClient
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


def build_live_wikidata_client(*, timeout_seconds: float = 55.0) -> WikidataOfficialWebsiteClient:
    """Wikidata's own SPARQL endpoint requires `Accept:
    application/sparql-results+json` (unlike Wayback's APIs, which are
    JSON by default) -- otherwise it may reply with an HTML results page
    instead. A longer default timeout than Wayback's, just under
    Wikidata's own ~60s public-endpoint server-side execution limit: a
    P17+P856 scan is still a heavier query than a single-URL lookup, and a
    client-side timeout shorter than the server's own limit would abort a
    query that was about to legitimately succeed.
    """
    def fetch_json(url: str):
        request = urllib.request.Request(
            url, headers={"User-Agent": _USER_AGENT, "Accept": "application/sparql-results+json"}
        )
        try:
            with urllib.request.urlopen(request, timeout=timeout_seconds) as response:
                payload = json.loads(response.read().decode("utf-8", errors="replace"))
        except urllib.error.HTTPError as exc:
            # Diagnostic only: `WikidataOfficialWebsiteClient.lookup` still
            # degrades to `{}` on any non-dict/malformed return either way
            # (never raises to the caller) -- this is purely so a live run's
            # logs can distinguish "the endpoint rejected/rate-limited the
            # request" from "the query legitimately returned zero matches",
            # which looked identical in a first live run (see AD-33's
            # follow-up: two real, well-documented EGX30 constituents both
            # came back with no hint, and this was the only way to tell why).
            body = exc.read().decode("utf-8", errors="replace")[:500]
            print(
                f"Wikidata SPARQL request failed: HTTP {exc.code} {exc.reason}: {body}",
                file=sys.stderr,
            )
            return {}
        except (urllib.error.URLError, OSError, TimeoutError, json.JSONDecodeError) as exc:
            print(f"Wikidata SPARQL request failed: {exc!r}", file=sys.stderr)
            return {}

        bindings = (payload.get("results") or {}).get("bindings", []) if isinstance(payload, dict) else []
        print(f"Wikidata SPARQL request succeeded: {len(bindings)} binding(s) returned.", file=sys.stderr)
        # Temporary extra diagnostic (AD-33 follow-up): the query itself
        # demonstrably works (2404 real bindings on a live run) yet
        # match_wikidata_websites_to_companies still found zero matches for
        # Telecom Egypt -- so the remaining question is what the raw labels
        # actually look like, not whether data exists. Printing every label
        # containing a fixed substring is a cheap way to see the real label
        # text/shape without dumping all ~2400 rows.
        sample = [
            (b.get("companyLabel", {}).get("value"), b.get("website", {}).get("value"))
            for b in bindings
            if "telecom" in (b.get("companyLabel", {}).get("value") or "").lower()
        ]
        print(f"Wikidata labels containing 'telecom': {sample}", file=sys.stderr)
        return payload

    return WikidataOfficialWebsiteClient(fetch_json)
