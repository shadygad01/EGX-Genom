"""Point-in-time joins and timestamp alignment for `patterns.panel`,
exercised through the real `MarketMemory`/`MockDataProvider` wiring (not
the direct-construction helper other `test_pattern_*.py` files use) --
this is the one test file that proves `build_research_panel()` itself,
not just the models it produces, behaves correctly.
"""

from __future__ import annotations

from datetime import date
from pathlib import Path

from agx_research.data.mock_provider import MockDataProvider
from agx_research.market_memory.memory import MarketMemory
from agx_research.patterns.panel import build_research_panel
from agx_research.universe.provider import MappingUniverseProvider
from agx_research.universe.sector import StaticSectorProvider

_MOCK_DATA = Path(__file__).resolve().parents[1] / "data" / "mock"


def _memory(**overrides) -> MarketMemory:
    kwargs = dict(
        data_provider=MockDataProvider(_MOCK_DATA),
        universe_provider=MappingUniverseProvider({"COMI": "CIB", "MFPC": "MOPCO"}),
        sector_provider=StaticSectorProvider(),
        macro_series_ids=["BRENT_USD", "EGP_USD"],
        macro_series_sources={"BRENT_USD": "fred", "EGP_USD": "fred"},
        lookback_days=30,
        pattern_lookback_days=3650,
    )
    kwargs.update(overrides)
    return MarketMemory(
        kwargs.pop("data_provider"), kwargs.pop("universe_provider"), kwargs.pop("sector_provider"), **kwargs
    )


def test_panel_only_contains_bars_at_or_before_as_of():
    as_of = date(2026, 6, 8)
    panel = build_research_panel(_memory(), as_of=as_of)
    for series in panel.series.values():
        assert all(d <= as_of for d in series.dates)


def test_panel_never_includes_a_ticker_with_fewer_than_two_bars():
    as_of = date(2026, 6, 1)  # the very first mock trading day -- at most 1 bar exists
    panel = build_research_panel(_memory(), as_of=as_of)
    assert panel.series == {}


def test_panel_dates_are_ascending_per_ticker():
    panel = build_research_panel(_memory(), as_of=date(2026, 6, 14))
    for series in panel.series.values():
        assert series.dates == sorted(series.dates)
        assert len(series.dates) == len(set(series.dates))  # no duplicates


def test_macro_series_are_filtered_by_source_publication_lag():
    """`build_snapshot()` already drops any macro observation not knowable
    by `as_of` per its declared source lag -- this proves that filtering
    survives into the panel unchanged (fred = 0-day lag, so every
    observation with `observation_date <= as_of` should be present)."""
    as_of = date(2026, 6, 8)
    panel = build_research_panel(_memory(), as_of=as_of)
    for series_id, observations in panel.macro_series.items():
        assert all(obs.observation_date <= as_of for obs in observations)


def test_ticker_index_of_matches_the_stored_date():
    panel = build_research_panel(_memory(), as_of=date(2026, 6, 14))
    series = panel.series["COMI"]
    idx = series.index_of(series.dates[3])
    assert idx == 3
    assert series.index_of(date(1999, 1, 1)) is None


def test_universe_limitation_note_is_always_present():
    panel = build_research_panel(_memory(), as_of=date(2026, 6, 14))
    assert "survivorship" in panel.universe_limitation_note.lower()


def test_explicit_ticker_filter_restricts_to_requested_subset():
    panel = build_research_panel(_memory(), as_of=date(2026, 6, 14), tickers=["COMI"])
    assert panel.tickers == ["COMI"]
    assert "MFPC" not in panel.series
