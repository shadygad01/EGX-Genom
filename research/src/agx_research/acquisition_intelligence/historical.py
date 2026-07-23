"""Historical availability verification via the Internet Archive's Wayback
Machine -- free, no-key, documented, decades-stable public APIs (same
confidence tier as FRED's/World Bank's endpoints already used for real
collectors):

- Availability API: `https://archive.org/wayback/available?url=...` --
  returns the closest archived snapshot, if any.
- CDX API: `https://web.archive.org/cdx/search/cdx?url=...&output=json&fl=timestamp`
  -- returns every snapshot timestamp on record, letting a real span (not
  just "it exists once") be measured.

Parsing is split from fetching (same pattern as every collector's
`parse()`): `parse_closest_snapshot`/`parse_cdx_timestamps` are pure
functions of an already-fetched payload, fully testable against a recorded
fixture with no network dependency. `WaybackAvailabilityClient` is the thin
live-fetch wrapper around an injected `fetch_json` callable.
"""

from __future__ import annotations

from datetime import date, datetime
from typing import Callable
from urllib.parse import quote

from pydantic import BaseModel, Field

_AVAILABLE_ENDPOINT = "https://archive.org/wayback/available"
_CDX_ENDPOINT = "https://web.archive.org/cdx/search/cdx"

FetchJson = Callable[[str], object]

# A source with archived history spanning at least this many days scores
# full marks; below that, score scales linearly. Declared policy, not a
# calibrated threshold -- no measured history exists yet to calibrate from.
_FULL_SCORE_SPAN_DAYS = 365


class HistoricalAvailabilityAssessment(BaseModel):
    score: float = Field(ge=0.0, le=1.0)
    has_any_snapshot: bool
    earliest_snapshot: date | None = None
    latest_snapshot: date | None = None
    snapshot_count: int = 0
    evidence: str = ""


def _parse_wayback_timestamp(raw: str) -> date:
    return datetime.strptime(raw[:8], "%Y%m%d").date()


def parse_closest_snapshot(payload: dict) -> date | None:
    closest = (payload.get("archived_snapshots") or {}).get("closest")
    if not closest or not closest.get("available"):
        return None
    timestamp = closest.get("timestamp")
    if not timestamp:
        return None
    return _parse_wayback_timestamp(timestamp)


def parse_cdx_timestamps(rows: list) -> list[date]:
    """`rows` is the CDX API's raw JSON array-of-arrays, header row included."""
    if not rows or len(rows) < 2:
        return []
    body = rows[1:]
    dates = []
    for row in body:
        if not row:
            continue
        try:
            dates.append(_parse_wayback_timestamp(row[0]))
        except (ValueError, IndexError):
            continue
    return sorted(dates)


def assess_historical_availability(
    *, closest_snapshot: date | None, cdx_timestamps: list[date] | None = None,
) -> HistoricalAvailabilityAssessment:
    cdx_timestamps = cdx_timestamps or []

    if not closest_snapshot and not cdx_timestamps:
        return HistoricalAvailabilityAssessment(
            score=0.0, has_any_snapshot=False,
            evidence="No archived snapshot found via the Wayback Machine.",
        )

    if cdx_timestamps:
        earliest, latest = cdx_timestamps[0], cdx_timestamps[-1]
        span_days = (latest - earliest).days
        score = min(1.0, span_days / _FULL_SCORE_SPAN_DAYS) if span_days > 0 else 0.2
        return HistoricalAvailabilityAssessment(
            score=score, has_any_snapshot=True, earliest_snapshot=earliest,
            latest_snapshot=latest, snapshot_count=len(cdx_timestamps),
            evidence=f"{len(cdx_timestamps)} snapshot(s) spanning {span_days} day(s).",
        )

    # Only the availability API answered (no CDX span data supplied) -- a
    # single confirmed snapshot exists, but coverage depth is unmeasured.
    return HistoricalAvailabilityAssessment(
        score=0.4, has_any_snapshot=True, earliest_snapshot=closest_snapshot,
        latest_snapshot=closest_snapshot, snapshot_count=1,
        evidence="A snapshot exists but only single-point availability was checked "
        "(no CDX span data supplied).",
    )


class WaybackAvailabilityClient:
    def __init__(self, fetch_json: FetchJson):
        self.fetch_json = fetch_json

    def check_availability(self, url: str) -> dict:
        return self.fetch_json(f"{_AVAILABLE_ENDPOINT}?url={quote(url, safe='')}")

    def cdx_snapshots(self, url: str, *, limit: int = 500) -> list:
        query = f"{_CDX_ENDPOINT}?url={quote(url, safe='')}&output=json&fl=timestamp&limit={limit}"
        return self.fetch_json(query)
