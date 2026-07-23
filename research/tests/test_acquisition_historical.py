from datetime import date

from agx_research.acquisition_intelligence.historical import (
    WaybackAvailabilityClient,
    assess_historical_availability,
    parse_cdx_timestamps,
    parse_closest_snapshot,
)


def test_parse_closest_snapshot_present():
    payload = {
        "url": "example.com",
        "archived_snapshots": {
            "closest": {
                "status": "200", "available": True,
                "url": "http://web.archive.org/web/20250615000000/http://example.com/",
                "timestamp": "20250615000000",
            }
        },
    }
    assert parse_closest_snapshot(payload) == date(2025, 6, 15)


def test_parse_closest_snapshot_absent():
    assert parse_closest_snapshot({"url": "example.com", "archived_snapshots": {}}) is None


def test_parse_closest_snapshot_unavailable_flag():
    payload = {"archived_snapshots": {"closest": {"available": False, "timestamp": "20250101000000"}}}
    assert parse_closest_snapshot(payload) is None


def test_parse_cdx_timestamps_skips_header_row():
    rows = [["timestamp"], ["20200101000000"], ["20210601000000"], ["20220615000000"]]
    result = parse_cdx_timestamps(rows)
    assert result == [date(2020, 1, 1), date(2021, 6, 1), date(2022, 6, 15)]


def test_parse_cdx_timestamps_empty_input():
    assert parse_cdx_timestamps([]) == []
    assert parse_cdx_timestamps([["timestamp"]]) == []


def test_assess_no_snapshot_at_all_scores_zero():
    result = assess_historical_availability(closest_snapshot=None, cdx_timestamps=[])
    assert result.score == 0.0
    assert result.has_any_snapshot is False


def test_assess_with_full_year_span_scores_near_max():
    timestamps = [date(2024, 1, 1), date(2025, 1, 1)]
    result = assess_historical_availability(closest_snapshot=date(2025, 1, 1), cdx_timestamps=timestamps)
    assert result.score == 1.0
    assert result.snapshot_count == 2


def test_assess_with_short_span_scores_partial():
    timestamps = [date(2025, 1, 1), date(2025, 1, 31)]  # 30-day span
    result = assess_historical_availability(closest_snapshot=None, cdx_timestamps=timestamps)
    assert 0.0 < result.score < 0.2


def test_assess_single_availability_hit_with_no_cdx_scores_modest_default():
    result = assess_historical_availability(closest_snapshot=date(2025, 1, 1), cdx_timestamps=None)
    assert result.has_any_snapshot is True
    assert result.score == 0.4


def test_wayback_client_builds_expected_urls():
    calls = []

    def fetch_json(url):
        calls.append(url)
        return {}

    client = WaybackAvailabilityClient(fetch_json)
    client.check_availability("https://example.com/feed")
    client.cdx_snapshots("https://example.com/feed")

    assert "archive.org/wayback/available" in calls[0]
    assert "example.com" in calls[0]
    assert "web.archive.org/cdx/search/cdx" in calls[1]
    assert "output=json" in calls[1]
