"""HTTP fetching with the program's legal and robustness rules enforced in code.

- robots.txt is checked (stdlib urllib.robotparser) and a disallowed URL
  raises `FetchDisallowed` — compliance is not left to collector authors'
  discretion.
- Per-source rate limiting (min interval between requests) and bounded
  retries with exponential backoff come from the SourceSpec's declared
  policies.
- stdlib urllib honors HTTPS_PROXY; no extra dependencies.

Unit tests never hit the network: collectors accept injected fetch
callables and are tested against recorded-format fixtures. This module is
exercised live only in deployed environments with egress.
"""

from __future__ import annotations

import time
import urllib.error
import urllib.request
import urllib.robotparser
from urllib.parse import urlsplit

from agx_research.sources.spec import SourceSpec

_USER_AGENT = "AGX-Research/1.0 (research data collection; contact via repository)"


class FetchDisallowed(Exception):
    """robots.txt (or source status) forbids this fetch."""


class FetchError(Exception):
    """All retry attempts failed."""


class HttpFetcher:
    def __init__(self, *, respect_robots: bool = True, timeout_seconds: float = 30.0):
        self.respect_robots = respect_robots
        self.timeout_seconds = timeout_seconds
        self._last_request_at: dict[str, float] = {}
        self._robots_cache: dict[str, urllib.robotparser.RobotFileParser] = {}

    def _robots_allows(self, url: str) -> bool:
        parts = urlsplit(url)
        base = f"{parts.scheme}://{parts.netloc}"
        parser = self._robots_cache.get(base)
        if parser is None:
            parser = urllib.robotparser.RobotFileParser(f"{base}/robots.txt")
            try:
                parser.read()
            except (urllib.error.URLError, OSError):
                # Unreachable robots.txt: default-allow is the standard
                # convention; the failure is not treated as a prohibition.
                parser.allow_all = True
            self._robots_cache[base] = parser
        return parser.can_fetch(_USER_AGENT, url)

    def fetch_text(self, url: str, spec: SourceSpec) -> str:
        return self.fetch_bytes(url, spec).decode("utf-8", errors="replace")

    def fetch_bytes(self, url: str, spec: SourceSpec) -> bytes:
        if self.respect_robots and not self._robots_allows(url):
            raise FetchDisallowed(f"robots.txt disallows {url}")

        min_interval = spec.rate_limit.min_seconds_between_requests
        last = self._last_request_at.get(spec.id)
        if last is not None:
            elapsed = time.monotonic() - last
            if elapsed < min_interval:
                time.sleep(min_interval - elapsed)

        attempts = 0
        delay = spec.retry_policy.backoff_seconds
        last_error: Exception | None = None
        while attempts < spec.retry_policy.max_attempts:
            attempts += 1
            self._last_request_at[spec.id] = time.monotonic()
            try:
                request = urllib.request.Request(url, headers={"User-Agent": _USER_AGENT})
                with urllib.request.urlopen(request, timeout=self.timeout_seconds) as response:
                    return response.read()
            except (urllib.error.URLError, OSError, TimeoutError) as exc:
                last_error = exc
                if attempts < spec.retry_policy.max_attempts:
                    time.sleep(delay)
                    delay *= spec.retry_policy.backoff_multiplier
        raise FetchError(
            f"{spec.id}: {attempts} attempt(s) failed for {url}: {last_error}"
        ) from last_error
