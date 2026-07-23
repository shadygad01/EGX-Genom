from agx_research.acquisition_intelligence.domain_resolution import ProbeResult
from agx_research.acquisition_intelligence.stability import assess_stability


def test_no_probes_is_insufficient_data_but_still_scores_url_shape():
    result = assess_stability("https://example.com/feed.rss")
    assert result.insufficient_data is True
    assert result.score > 0.5  # canonical extension bonus


def test_session_token_in_url_lowers_score():
    clean = assess_stability("https://example.com/data.csv")
    tokened = assess_stability("https://example.com/data.csv?sessionid=abc123")
    assert tokened.score < clean.score


def test_opaque_long_identifier_lowers_score():
    plain = assess_stability("https://example.com/report.pdf")
    opaque_id = "a" * 30
    opaque = assess_stability(f"https://example.com/report/{opaque_id}.pdf")
    assert opaque.score < plain.score


def test_consistent_repeated_probes_raise_score():
    probes = [ProbeResult(url="https://x", reachable=True, status_code=200) for _ in range(5)]
    result = assess_stability("https://x", probes)
    assert result.insufficient_data is False
    assert any("5/5 probes returned the same status code" in e for e in result.evidence)


def test_inconsistent_probes_lower_score():
    probes = [
        ProbeResult(url="https://x", reachable=True, status_code=200),
        ProbeResult(url="https://x", reachable=True, status_code=404),
        ProbeResult(url="https://x", reachable=True, status_code=500),
    ]
    result = assess_stability("https://x", probes)
    assert result.score < 0.5


def test_all_failed_probes_scores_zero():
    probes = [ProbeResult(url="https://x", reachable=False) for _ in range(3)]
    result = assess_stability("https://x", probes)
    assert result.score == 0.0
