"""HttpFetcher tests. No live network calls: urlopen/time.sleep are
monkeypatched, and robots.txt behavior is exercised via injected responses.
"""

from __future__ import annotations

import urllib.error
import urllib.request

import pytest

from agx_research.collectors.fetcher import FetchDisallowed, FetchError, HttpFetcher
from agx_research.sources.spec import AccessMethod, RateLimit, RetryPolicy, SourceCategory, SourceSpec, SourceStatus


def make_spec(**overrides) -> SourceSpec:
    defaults = dict(
        id="test_source",
        name="Test Source",
        category=SourceCategory.MARKET_DATA,
        access_method=AccessMethod.CSV_DOWNLOAD,
        status=SourceStatus.IMPLEMENTED,
        base_url="https://example.test/data",
        reliability_score=0.8,
        freshness_score=0.9,
        retry_policy=RetryPolicy(max_attempts=3, backoff_seconds=0.01, backoff_multiplier=2.0),
        rate_limit=RateLimit(requests_per_minute=60, min_seconds_between_requests=0.01),
    )
    defaults.update(overrides)
    return SourceSpec(**defaults)


class _FakeResponse:
    def __init__(self, text: str):
        self._text = text

    def read(self):
        return self._text.encode()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False


def test_robots_disallowed_raises_without_network(monkeypatch):
    fetcher = HttpFetcher()
    monkeypatch.setattr(HttpFetcher, "_robots_allows", lambda self, url: False)
    with pytest.raises(FetchDisallowed):
        fetcher.fetch_text("https://example.test/data", make_spec())


def test_robots_allowed_permits_fetch(monkeypatch):
    fetcher = HttpFetcher()
    monkeypatch.setattr(HttpFetcher, "_robots_allows", lambda self, url: True)
    monkeypatch.setattr(urllib.request, "urlopen", lambda request, timeout: _FakeResponse("ok"))
    result = fetcher.fetch_text("https://example.test/data", make_spec())
    assert result == "ok"


def test_respect_robots_false_skips_robots_check_entirely(monkeypatch):
    fetcher = HttpFetcher(respect_robots=False)

    def _boom(self, url):
        raise AssertionError("robots.txt should not be checked when respect_robots=False")

    monkeypatch.setattr(HttpFetcher, "_robots_allows", _boom)
    monkeypatch.setattr(urllib.request, "urlopen", lambda request, timeout: _FakeResponse("ok"))
    assert fetcher.fetch_text("https://example.test/data", make_spec()) == "ok"


def test_retries_then_succeeds(monkeypatch):
    fetcher = HttpFetcher(respect_robots=False)
    sleeps: list[float] = []
    monkeypatch.setattr("time.sleep", lambda seconds: sleeps.append(seconds))

    attempts = {"count": 0}

    def flaky_urlopen(request, timeout):
        attempts["count"] += 1
        if attempts["count"] < 3:
            raise urllib.error.URLError("connection refused")
        return _FakeResponse("finally")

    monkeypatch.setattr(urllib.request, "urlopen", flaky_urlopen)
    result = fetcher.fetch_text("https://example.test/data", make_spec())
    assert result == "finally"
    assert attempts["count"] == 3
    # two retry sleeps with exponential backoff (0.01, then 0.02)
    assert sleeps == [0.01, 0.02]


def test_exhausted_retries_raise_fetch_error(monkeypatch):
    fetcher = HttpFetcher(respect_robots=False)
    monkeypatch.setattr("time.sleep", lambda seconds: None)

    def always_fails(request, timeout):
        raise urllib.error.URLError("connection refused")

    monkeypatch.setattr(urllib.request, "urlopen", always_fails)
    with pytest.raises(FetchError):
        fetcher.fetch_text("https://example.test/data", make_spec(retry_policy=RetryPolicy(
            max_attempts=2, backoff_seconds=0.01, backoff_multiplier=2.0
        )))


def test_a_malformed_hostname_fails_the_fetch_instead_of_crashing_the_caller(monkeypatch):
    """Regression test for a real production incident (2026-07-31): a full
    ~101-company acquisition sweep crashed outright, losing all prior
    progress, when one company's name-derived guessed domain produced an
    empty/too-long IDNA label. `socket.getaddrinfo` raises `UnicodeError`
    directly (not an `OSError` subclass), so it previously propagated
    straight past every retry/backoff path here -- one bad hostname must
    report as an ordinary fetch failure, never crash the whole caller.
    """
    fetcher = HttpFetcher(respect_robots=False)
    monkeypatch.setattr("time.sleep", lambda seconds: None)

    def bad_hostname(request, timeout):
        raise UnicodeError("label empty or too long")

    monkeypatch.setattr(urllib.request, "urlopen", bad_hostname)
    with pytest.raises(FetchError):
        fetcher.fetch_text("https://.example.test/", make_spec(retry_policy=RetryPolicy(
            max_attempts=2, backoff_seconds=0.01, backoff_multiplier=2.0
        )))


def test_successful_fetch_records_real_request_latency(monkeypatch):
    fetcher = HttpFetcher(respect_robots=False)
    monkeypatch.setattr("time.sleep", lambda seconds: None)

    clock = {"t": 0.0}

    def fake_monotonic():
        clock["t"] += 0.5
        return clock["t"]

    monkeypatch.setattr("time.monotonic", fake_monotonic)
    monkeypatch.setattr(urllib.request, "urlopen", lambda request, timeout: _FakeResponse("ok"))

    fetcher.fetch_text("https://example.test/data", make_spec())

    assert fetcher.request_latencies == [0.5]


def test_latency_not_recorded_for_a_failed_fetch(monkeypatch):
    fetcher = HttpFetcher(respect_robots=False)
    monkeypatch.setattr("time.sleep", lambda seconds: None)

    def always_fails(request, timeout):
        raise urllib.error.URLError("connection refused")

    monkeypatch.setattr(urllib.request, "urlopen", always_fails)
    with pytest.raises(FetchError):
        fetcher.fetch_text("https://example.test/data", make_spec(retry_policy=RetryPolicy(
            max_attempts=2, backoff_seconds=0.01, backoff_multiplier=2.0
        )))

    assert fetcher.request_latencies == []


def test_fetch_handles_url_with_raw_non_ascii_characters(monkeypatch):
    """Regression test for a real production crash: a live Zawya sitemap
    <loc> entry contained literal (non-percent-encoded) non-ASCII
    characters in its path. `urllib.request.Request` passed that straight
    to `http.client`, which raised `UnicodeEncodeError` deep inside
    `_encode_request` (`str.encode('ascii')` on the request line) -- an
    unhandled crash, not a normal HTTP error, so it wasn't even reported as
    a `FetchError`. `fetch_bytes` must percent-encode the URL first.
    """
    fetcher = HttpFetcher(respect_robots=False)
    seen_urls: list[str] = []

    def _capture_urlopen(request, timeout):
        seen_urls.append(request.full_url)
        # The exact failure this reproduces: building the real HTTP
        # request line must not raise UnicodeEncodeError.
        request.full_url.encode("ascii")
        return _FakeResponse("ok")

    monkeypatch.setattr(urllib.request, "urlopen", _capture_urlopen)
    result = fetcher.fetch_text("https://example.test/أخبار/مقال", make_spec())

    assert result == "ok"
    assert seen_urls == ["https://example.test/%D8%A3%D8%AE%D8%A8%D8%A7%D8%B1/%D9%85%D9%82%D8%A7%D9%84"]


def test_fetch_does_not_double_encode_an_already_percent_encoded_url(monkeypatch):
    fetcher = HttpFetcher(respect_robots=False)
    seen_urls: list[str] = []

    def _capture_urlopen(request, timeout):
        seen_urls.append(request.full_url)
        return _FakeResponse("ok")

    monkeypatch.setattr(urllib.request, "urlopen", _capture_urlopen)
    fetcher.fetch_text("https://example.test/data?s=comi.eg&i=d#ticker=COMI", make_spec())

    assert seen_urls == ["https://example.test/data?s=comi.eg&i=d#ticker=COMI"]


def test_robots_txt_fetch_is_timeout_bounded_not_a_hang(monkeypatch):
    """Regression test for a real production hang: stdlib
    `RobotFileParser.read()` calls `urlopen()` with no timeout at all, so a
    host that accepts the TCP connection but never responds hangs that call
    -- and the whole sequential discovery run behind it -- indefinitely (a
    live run was cancelled after 90+ minutes stuck here). Fetching
    robots.txt through the same timeout-bounded path every other request
    uses must degrade to allow-all on timeout, not hang or raise.
    """
    fetcher = HttpFetcher(timeout_seconds=5.0)
    seen_timeouts: list[float] = []

    def _times_out(request, timeout):
        seen_timeouts.append(timeout)
        raise TimeoutError("simulated: connection accepted, server never responded")

    monkeypatch.setattr(urllib.request, "urlopen", _times_out)

    assert fetcher._robots_allows("https://example.test/data") is True
    assert seen_timeouts == [5.0]


def test_robots_txt_real_disallow_rule_is_still_respected(monkeypatch):
    """The timeout-bounded refetch (`parser.parse()` on our own fetched
    lines) must produce the same result `RobotFileParser.read()` would --
    this isn't just a graceful-degrade path, real Disallow rules still work.
    """
    fetcher = HttpFetcher()
    robots_txt = "User-agent: *\nDisallow: /private\n"

    monkeypatch.setattr(
        urllib.request, "urlopen", lambda request, timeout: _FakeResponse(robots_txt)
    )

    assert fetcher._robots_allows("https://example.test/private/page") is False
    assert fetcher._robots_allows("https://example.test/public/page") is True


def test_robots_status_degrades_instead_of_crashing_on_a_malformed_url():
    """Regression test for a real production crash: a discovered candidate
    with no scheme+netloc (e.g. from a non-compliant sitemap <loc> entry)
    made `urllib.request.Request(f"{base}/robots.txt")` raise
    `ValueError: unknown url type` -- not `URLError`/`OSError`, so it wasn't
    caught, and took down the whole discovery_engine pipeline stage. A
    malformed URL must degrade the same way a genuinely unreachable host
    does (robots_status returns None -- unknown, not confirmed-allowed).
    """
    fetcher = HttpFetcher()
    assert fetcher.robots_status(":///not-a-real-url") is None
    assert fetcher.robots_status("javascript:void(0)") is None


def test_rate_limit_sleeps_between_requests_to_same_source(monkeypatch):
    fetcher = HttpFetcher(respect_robots=False)
    sleeps: list[float] = []
    monkeypatch.setattr("time.sleep", lambda seconds: sleeps.append(seconds))
    monkeypatch.setattr(urllib.request, "urlopen", lambda request, timeout: _FakeResponse("ok"))

    clock = {"t": 0.0}
    monkeypatch.setattr("time.monotonic", lambda: clock["t"])

    spec = make_spec(rate_limit=RateLimit(requests_per_minute=60, min_seconds_between_requests=5.0))
    fetcher.fetch_text("https://example.test/data", spec)
    clock["t"] += 1.0  # only 1s elapsed, less than the 5s minimum interval
    fetcher.fetch_text("https://example.test/data", spec)

    assert sleeps == [4.0]
