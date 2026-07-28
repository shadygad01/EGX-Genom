from datetime import date
from pathlib import Path

from agx_research.data.mock_provider import MockDataProvider
from agx_research.market_memory.memory import MarketMemory, is_egx_trading_day
from agx_research.universe.provider import MappingUniverseProvider
from agx_research.universe.sector import StaticSectorProvider

MOCK_ROOT = Path(__file__).resolve().parents[1] / "data" / "mock"


def make_memory() -> MarketMemory:
    return MarketMemory(
        MockDataProvider(MOCK_ROOT),
        MappingUniverseProvider({"COMI": "COMI", "MFPC": "MFPC"}),
        StaticSectorProvider(),
        macro_series_ids=["BRENT_USD"],
        lookback_days=30,
    )


def test_egx_weekend_is_friday_saturday():
    assert is_egx_trading_day(date(2026, 6, 4)) is True  # Thursday
    assert is_egx_trading_day(date(2026, 6, 5)) is False  # Friday
    assert is_egx_trading_day(date(2026, 6, 6)) is False  # Saturday
    assert is_egx_trading_day(date(2026, 6, 7)) is True  # Sunday


def test_reconstruct_bundles_snapshot_universe_and_sectors():
    state = make_memory().reconstruct(date(2026, 6, 14))

    assert state.as_of == date(2026, 6, 14)
    assert "COMI" in state.constituents
    assert state.sectors["COMI"] == "Banks"
    assert state.trading_session.is_trading_day is True


def test_reconstruct_never_sees_data_after_as_of():
    state = make_memory().reconstruct(date(2026, 6, 9))
    assert all(
        bar.trade_date <= date(2026, 6, 9) for bar in state.dataset_snapshot.price_history["COMI"]
    )


def test_reconstruct_is_deterministic():
    memory = make_memory()
    state_a = memory.reconstruct(date(2026, 6, 14))
    state_b = memory.reconstruct(date(2026, 6, 14))
    assert state_a.dataset_snapshot.id == state_b.dataset_snapshot.id


def test_calendar_fixed_holiday_is_not_a_trading_day():
    from agx_research.market_memory.calendar import StaticEGXCalendar

    calendar = StaticEGXCalendar()
    assert calendar.is_trading_day(date(2026, 10, 6)) is False  # Armed Forces Day (Tuesday)
    assert calendar.holiday_name(date(2026, 10, 6)) == "Armed Forces Day"


def test_calendar_movable_holiday_table_is_respected():
    from agx_research.market_memory.calendar import StaticEGXCalendar

    calendar = StaticEGXCalendar(movable_holidays={date(2026, 6, 9): "Test Eid"})
    assert calendar.is_trading_day(date(2026, 6, 9)) is False
    # And with an empty table the same Tuesday is a normal trading day.
    assert StaticEGXCalendar(movable_holidays={}).is_trading_day(date(2026, 6, 9)) is True


def test_reconstruct_populates_canonical_events():
    state = make_memory().reconstruct(date(2026, 6, 14))
    assert state.events, "expected registered events for the mock window"
    # Events come through the platform: fingerprint ids, resolved entities.
    assert all(e.id.startswith("event_") for e in state.events)


def test_macro_lookback_days_is_passed_through_to_the_snapshot():
    memory = MarketMemory(
        MockDataProvider(MOCK_ROOT),
        MappingUniverseProvider({"COMI": "COMI", "MFPC": "MFPC"}),
        StaticSectorProvider(),
        macro_series_ids=["BRENT_USD"],
        lookback_days=5,
        macro_lookback_days=30,
    )
    state = memory.reconstruct(date(2026, 6, 14))
    assert state.dataset_snapshot.macro_lookback_days == 30
    assert all(
        bar.trade_date >= date(2026, 6, 9) for bar in state.dataset_snapshot.price_history["COMI"]
    )
    assert any(
        obs.observation_date < date(2026, 6, 9)
        for obs in state.dataset_snapshot.macro_series["BRENT_USD"]
    )
