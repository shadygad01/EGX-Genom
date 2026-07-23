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
