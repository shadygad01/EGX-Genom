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
from agx_research.discovery.gleif_lookup import GleifLegalEntityClient
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


_WIKIDATA_MAX_429_RETRIES = 4
_WIKIDATA_DEFAULT_RETRY_AFTER_SECONDS = 5.0
# A real live run hung for 9+ minutes on a single company before this cap
# existed: Wikidata's own `Retry-After` value is honored, but nothing
# upstream bounds how large it can be, and un-capped it turns "back off
# and retry" into "block this whole sprint run for however long a
# rate-limiter feels like." Capping is what keeps a large-but-honest
# `Retry-After` from becoming an effectively unbounded wait.
_WIKIDATA_MAX_RETRY_DELAY_SECONDS = 15.0


def build_live_wikidata_client(
    *, timeout_seconds: float = 30.0, min_seconds_between_requests: float = 0.3,
) -> WikidataOfficialWebsiteClient:
    """`WikidataOfficialWebsiteClient.lookup` calls this up to twice per
    company (a name search, then a claims read for whatever entity
    matched) -- `min_seconds_between_requests` paces that loop so a
    ~100-company sprint run stays a reasonable, well-behaved client rather
    than a request burst, matching the spirit (not the exact mechanism) of
    `collectors.fetcher.HttpFetcher`'s per-source rate limiting.

    Live-verified failure mode this retries: a shared GitHub Actions
    runner IP hitting Wikidata's action API got a real `HTTP 429 Too Many
    Requests` ("You are making too many requests to the API") on the very
    first call, despite `min_seconds_between_requests` already pacing this
    client's own calls -- the contention is from *other* traffic sharing
    that IP range, not this client's own request rate, so only backing off
    and retrying (honoring a `Retry-After` header when the response
    supplies one, capped at `_WIKIDATA_MAX_RETRY_DELAY_SECONDS`) can
    recover from it.
    """
    last_request_at = 0.0

    def fetch_json(url: str):
        nonlocal last_request_at
        for attempt in range(_WIKIDATA_MAX_429_RETRIES + 1):
            elapsed = time.monotonic() - last_request_at
            if elapsed < min_seconds_between_requests:
                time.sleep(min_seconds_between_requests - elapsed)
            last_request_at = time.monotonic()

            request = urllib.request.Request(url, headers={"User-Agent": _USER_AGENT})
            try:
                with urllib.request.urlopen(request, timeout=timeout_seconds) as response:
                    return json.loads(response.read().decode("utf-8", errors="replace"))
            except urllib.error.HTTPError as exc:
                body = exc.read().decode("utf-8", errors="replace")[:300]
                if exc.code == 429 and attempt < _WIKIDATA_MAX_429_RETRIES:
                    retry_after = exc.headers.get("Retry-After") if exc.headers else None
                    try:
                        delay = float(retry_after) if retry_after else _WIKIDATA_DEFAULT_RETRY_AFTER_SECONDS
                    except ValueError:
                        delay = _WIKIDATA_DEFAULT_RETRY_AFTER_SECONDS
                    delay = min(delay, _WIKIDATA_MAX_RETRY_DELAY_SECONDS)
                    print(
                        f"Wikidata API rate-limited (attempt {attempt + 1}/"
                        f"{_WIKIDATA_MAX_429_RETRIES + 1}); retrying in {delay:.1f}s.",
                        file=sys.stderr,
                    )
                    time.sleep(delay)
                    continue
                # Diagnostic only: `WikidataOfficialWebsiteClient.lookup`
                # still degrades to "no hint" on any failure either way
                # (never raises to the caller) -- this is purely so a live
                # run's logs can distinguish "the endpoint rejected/
                # rate-limited the request" from "no matching entity/claim
                # exists" (see AD-33/AD-34's follow-up).
                print(
                    f"Wikidata API request failed: HTTP {exc.code} {exc.reason}: {body}",
                    file=sys.stderr,
                )
                return {}
            except (urllib.error.URLError, OSError, TimeoutError, json.JSONDecodeError) as exc:
                print(f"Wikidata API request failed: {exc!r}", file=sys.stderr)
                return {}
        return {}

    return WikidataOfficialWebsiteClient(fetch_json)


_GLEIF_MAX_429_RETRIES = 3
_GLEIF_DEFAULT_RETRY_AFTER_SECONDS = 5.0
_GLEIF_MAX_RETRY_DELAY_SECONDS = 15.0


def build_live_gleif_client(
    *, timeout_seconds: float = 30.0, min_seconds_between_requests: float = 0.3,
) -> GleifLegalEntityClient:
    """Same pacing/429-backoff shape as `build_live_wikidata_client` above,
    applied preemptively rather than reactively: unlike Wikidata's client,
    this one has not yet been exercised against the real GLEIF API from a
    live-egress environment, so there is no confirmed real rate-limit
    incident to calibrate against (the honest state is "defensively
    built, not yet live-verified" -- see `discovery.gleif_lookup`'s module
    docstring). `GleifLegalEntityClient.lookup` still degrades every
    per-company failure to "no match" and never raises to the caller,
    the same honest fallback every other live adapter here uses.
    """
    last_request_at = 0.0

    def fetch_json(url: str):
        nonlocal last_request_at
        for attempt in range(_GLEIF_MAX_429_RETRIES + 1):
            elapsed = time.monotonic() - last_request_at
            if elapsed < min_seconds_between_requests:
                time.sleep(min_seconds_between_requests - elapsed)
            last_request_at = time.monotonic()

            request = urllib.request.Request(url, headers={"User-Agent": _USER_AGENT})
            try:
                with urllib.request.urlopen(request, timeout=timeout_seconds) as response:
                    return json.loads(response.read().decode("utf-8", errors="replace"))
            except urllib.error.HTTPError as exc:
                body = exc.read().decode("utf-8", errors="replace")[:300]
                if exc.code == 429 and attempt < _GLEIF_MAX_429_RETRIES:
                    retry_after = exc.headers.get("Retry-After") if exc.headers else None
                    try:
                        delay = float(retry_after) if retry_after else _GLEIF_DEFAULT_RETRY_AFTER_SECONDS
                    except ValueError:
                        delay = _GLEIF_DEFAULT_RETRY_AFTER_SECONDS
                    delay = min(delay, _GLEIF_MAX_RETRY_DELAY_SECONDS)
                    print(
                        f"GLEIF API rate-limited (attempt {attempt + 1}/"
                        f"{_GLEIF_MAX_429_RETRIES + 1}); retrying in {delay:.1f}s.",
                        file=sys.stderr,
                    )
                    time.sleep(delay)
                    continue
                # Diagnostic only, same posture as build_live_wikidata_client:
                # GleifLegalEntityClient.lookup degrades to "no match" either
                # way -- this just lets a live run's logs distinguish
                # "the endpoint rejected/rate-limited the request" from
                # "no matching entity/record exists".
                print(f"GLEIF API request failed: HTTP {exc.code} {exc.reason}: {body}", file=sys.stderr)
                return {}
            except (urllib.error.URLError, OSError, TimeoutError, json.JSONDecodeError) as exc:
                print(f"GLEIF API request failed: {exc!r}", file=sys.stderr)
                return {}
        return {}

    return GleifLegalEntityClient(fetch_json)
