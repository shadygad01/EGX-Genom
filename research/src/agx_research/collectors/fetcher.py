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
from urllib.parse import quote, urlsplit, urlunsplit

from agx_research.sources.spec import SourceSpec

_USER_AGENT = "AGX-Research/1.0 (research data collection; contact via repository)"


class FetchDisallowed(Exception):
    """robots.txt (or source status) forbids this fetch."""


class FetchError(Exception):
    """All retry attempts failed."""


_URL_COMPONENT_SAFE_CHARS = "/:@!$&'()*+,;=~%"


def _encode_request_url(url: str) -> str:
    """Percent-encode a URL's path/query/fragment before handing it to
    `urllib.request.Request`. Some real sites publish links (a sitemap
    `<loc>` entry, an anchor href) with literal non-ASCII characters
    instead of percent-encoding them -- `http.client` cannot send that as
    a request line (`str.encode('ascii')` raises `UnicodeEncodeError`,
    crashing the fetch outright rather than returning a normal HTTP
    response). Every RFC 3986 sub-delim plus `%` is kept safe so an
    already correctly-encoded URL (e.g. Stooq's own `?s=...&i=d#ticker=...`
    query/fragment) is never double-encoded or mangled.
    """
    parts = urlsplit(url)
    return urlunsplit((
        parts.scheme, parts.netloc,
        quote(parts.path, safe=_URL_COMPONENT_SAFE_CHARS),
        quote(parts.query, safe=_URL_COMPONENT_SAFE_CHARS),
        quote(parts.fragment, safe=_URL_COMPONENT_SAFE_CHARS),
    ))


class HttpFetcher:
    def __init__(self, *, respect_robots: bool = True, timeout_seconds: float = 30.0):
        self.respect_robots = respect_robots
        self.timeout_seconds = timeout_seconds
        self._last_request_at: dict[str, float] = {}
        self._robots_cache: dict[str, urllib.robotparser.RobotFileParser] = {}
        self._robots_unreachable: dict[str, bool] = {}
        # Real network round-trip time per successful request (urlopen+read
        # only -- excludes rate-limit/backoff sleeps, which aren't the
        # source's latency). `CollectionService` reads new entries after
        # each `Collector.fetch()` call to feed `reputation.py`'s `latency`
        # dimension (see TD-16).
        self.request_latencies: list[float] = []

    def _get_robots_parser(self, base: str) -> urllib.robotparser.RobotFileParser:
        parser = self._robots_cache.get(base)
        if parser is None:
            parser = urllib.robotparser.RobotFileParser(f"{base}/robots.txt")
            try:
                # Not `parser.read()`: stdlib's `RobotFileParser.read()` calls
                # `urlopen()` with no timeout at all, so a host that accepts
                # the TCP connection but never responds (a real anti-bot
                # behavior, distinct from a fast connection-refused) hangs
                # this call -- and everything sequentially after it --
                # indefinitely. Fetching it ourselves through the same
                # timeout-bounded path every other request already uses, then
                # feeding the raw lines to `parser.parse()`, gets the same
                # parsed result without the unbounded wait.
                request = urllib.request.Request(
                    f"{base}/robots.txt", headers={"User-Agent": _USER_AGENT}
                )
                with urllib.request.urlopen(request, timeout=self.timeout_seconds) as response:
                    content = response.read()
                parser.parse(content.decode("utf-8", errors="replace").splitlines())
                self._robots_unreachable[base] = False
            except (urllib.error.URLError, OSError, TimeoutError):
                # Unreachable robots.txt: default-allow is the standard
                # convention; the failure is not treated as a prohibition.
                parser.allow_all = True
                self._robots_unreachable[base] = True
            self._robots_cache[base] = parser
        return parser

    def _robots_allows(self, url: str) -> bool:
        parts = urlsplit(url)
        base = f"{parts.scheme}://{parts.netloc}"
        parser = self._get_robots_parser(base)
        return parser.can_fetch(_USER_AGENT, url)

    def robots_status(self, url: str) -> bool | None:
        """Three-state robots.txt check for callers that need to distinguish
        "explicitly allowed" from "robots.txt unreachable, allowed only by
        the default-allow convention" -- unlike `_robots_allows` (used by
        `fetch_bytes`, which permissively proceeds either way, the standard
        compliant-crawler behavior), this returns `None` when robots.txt
        itself couldn't be fetched, so a stricter caller (e.g. the
        Acquisition Intelligence Engine's legality gate) can treat that as
        genuinely unknown rather than confirmed-allowed.
        """
        parts = urlsplit(url)
        base = f"{parts.scheme}://{parts.netloc}"
        parser = self._get_robots_parser(base)
        if self._robots_unreachable.get(base):
            return None
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
                request = urllib.request.Request(
                    _encode_request_url(url), headers={"User-Agent": _USER_AGENT}
                )
                request_started_at = time.monotonic()
                with urllib.request.urlopen(request, timeout=self.timeout_seconds) as response:
                    content = response.read()
                self.request_latencies.append(time.monotonic() - request_started_at)
                return content
            except (urllib.error.URLError, OSError, TimeoutError) as exc:
                last_error = exc
                if attempts < spec.retry_policy.max_attempts:
                    time.sleep(delay)
                    delay *= spec.retry_policy.backoff_multiplier
        raise FetchError(
            f"{spec.id}: {attempts} attempt(s) failed for {url}: {last_error}"
        ) from last_error
