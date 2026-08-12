"""Coverage for `patterns.universe_confidence` -- the point-in-time
universe-confidence tagging and study/control basket split."""

from __future__ import annotations

from datetime import date, timedelta

from agx_research.patterns.universe_confidence import (
    CURRENT_UNIVERSE_SNAPSHOT_DATE,
    StudyUniverseMode,
    UniverseConfidence,
    assess_universe_confidence,
    split_study_and_control_tickers,
)


def test_as_of_on_the_snapshot_date_is_current_snapshot_only():
    assert assess_universe_confidence(CURRENT_UNIVERSE_SNAPSHOT_DATE) is UniverseConfidence.CURRENT_SNAPSHOT_ONLY


def test_as_of_after_the_snapshot_date_is_current_snapshot_only():
    after = CURRENT_UNIVERSE_SNAPSHOT_DATE + timedelta(days=30)
    assert assess_universe_confidence(after) is UniverseConfidence.CURRENT_SNAPSHOT_ONLY


def test_as_of_before_the_snapshot_date_is_none():
    before = CURRENT_UNIVERSE_SNAPSHOT_DATE - timedelta(days=1)
    assert assess_universe_confidence(before) is UniverseConfidence.NONE


def test_historical_is_never_returned_by_the_default_assessment():
    # Declared but unreachable today (module docstring) -- no real
    # reconstitution-history source exists yet to justify it.
    for offset_days in (-3650, -365, -1, 0, 1, 365, 3650):
        result = assess_universe_confidence(CURRENT_UNIVERSE_SNAPSHOT_DATE + timedelta(days=offset_days))
        assert result is not UniverseConfidence.HISTORICAL


def test_custom_snapshot_date_is_respected():
    custom = date(2020, 1, 1)
    assert assess_universe_confidence(date(2020, 1, 1), snapshot_date=custom) is UniverseConfidence.CURRENT_SNAPSHOT_ONLY
    assert assess_universe_confidence(date(2019, 12, 31), snapshot_date=custom) is UniverseConfidence.NONE


def test_split_study_and_control_is_the_intersection_for_control():
    available = ["A", "B", "C", "D"]
    real_egx30 = {"B", "D", "Z"}  # Z has no price history -- must not appear anywhere

    split = split_study_and_control_tickers(available, real_egx30)

    assert split[StudyUniverseMode.STUDY] == ["A", "B", "C", "D"]
    assert split[StudyUniverseMode.CURRENT_CONTROL] == ["B", "D"]


def test_split_deduplicates_and_sorts_both_baskets():
    split = split_study_and_control_tickers(["C", "A", "A", "B"], {"A", "C"})
    assert split[StudyUniverseMode.STUDY] == ["A", "B", "C"]
    assert split[StudyUniverseMode.CURRENT_CONTROL] == ["A", "C"]


def test_split_control_is_empty_when_no_available_ticker_is_a_real_egx30_member():
    split = split_study_and_control_tickers(["X", "Y"], {"A", "B"})
    assert split[StudyUniverseMode.CURRENT_CONTROL] == []
    assert split[StudyUniverseMode.STUDY] == ["X", "Y"]
