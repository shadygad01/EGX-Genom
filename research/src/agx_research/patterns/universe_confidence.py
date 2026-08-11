"""Point-in-time universe confidence: makes the honest limitation
`panel.UNIVERSE_LIMITATION_NOTE` already states machine-readable, and
gives every discovery run an explicit, never-silent choice between a
study universe and a deliberately-biased current-constituents control.

No free/public source of historical EGX30/EGX70 reconstitution history
was found (`docs/EGX30_DATA_SOURCE_QUALIFICATION.md`, category 2) — this
module does not pretend otherwise. What it does instead, per the
mission's explicit fallback instructions: (1) tag every panel with a
`UniverseConfidence` so no caller can mistake "the only membership data
that exists" for "verified point-in-time truth", and (2) support running
the same discovery pipeline over two distinct baskets — the real price
dataset's own full coverage (`STUDY`, no membership claim beyond "these
tickers have real price history"), and the current, single-snapshot
EGX30 list applied across the whole history (`CURRENT_CONTROL`, a
known-biased survivorship control, never promoted past a comparison) —
so a reader can see whether a discovered relationship is an artifact of
which basket was searched.
"""

from __future__ import annotations

from datetime import date
from enum import Enum

# The one real, dated EGX30/EGX70 snapshot this repository has
# (`research/data/universe/EGX30.csv`/`EGX70.csv`, `as_of_date` column).
CURRENT_UNIVERSE_SNAPSHOT_DATE = date(2026, 7, 26)


class UniverseConfidence(str, Enum):
    NONE = "none"
    CURRENT_SNAPSHOT_ONLY = "current_snapshot_only"
    HISTORICAL = "historical"


def assess_universe_confidence(
    as_of: date, *, snapshot_date: date = CURRENT_UNIVERSE_SNAPSHOT_DATE
) -> UniverseConfidence:
    """`HISTORICAL` is declared but never actually returned today — no
    source that would justify it exists (see module docstring). Kept as
    a real enum member, not omitted, so a future real reconstitution-
    history source has somewhere honest to report into without a schema
    change, the same "reserved, not fabricated" posture
    `discovery.resolution_memory.ClaimAttribute.BRAND_NAME`/
    `PARENT_COMPANY` already use in this codebase for the identical
    reason."""
    if as_of >= snapshot_date:
        return UniverseConfidence.CURRENT_SNAPSHOT_ONLY
    return UniverseConfidence.NONE


class StudyUniverseMode(str, Enum):
    STUDY = "study"
    CURRENT_CONTROL = "current_control"


def split_study_and_control_tickers(
    available_tickers: list[str], real_egx30_tickers: set[str]
) -> dict[StudyUniverseMode, list[str]]:
    """`available_tickers`: whatever a real price source actually covers
    (no membership claim). `real_egx30_tickers`: the current, single-
    snapshot EGX30 list. The control is deliberately the *intersection*
    — every ticker in it both has real price history AND is a current
    EGX30 member, applied across the whole study period regardless of
    whether it was really a constituent then. Never used to validate a
    pattern, only to compare against the unrestricted study basket."""
    available = sorted(set(available_tickers))
    control = sorted(set(available_tickers) & real_egx30_tickers)
    return {
        StudyUniverseMode.STUDY: available,
        StudyUniverseMode.CURRENT_CONTROL: control,
    }


__all__ = [
    "CURRENT_UNIVERSE_SNAPSHOT_DATE",
    "StudyUniverseMode",
    "UniverseConfidence",
    "assess_universe_confidence",
    "split_study_and_control_tickers",
]
