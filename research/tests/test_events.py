from datetime import date
from pathlib import Path

from agx_research.data.mock_provider import MockDataProvider
from agx_research.data.schemas import NewsItem
from agx_research.data.snapshot import build_snapshot
from agx_research.events.adapters import derive_events_from_snapshot, events_from_price_moves
from agx_research.events.entity import EntityKind
from agx_research.events.event import EventType
from agx_research.events.repository import EventRepository

MOCK_ROOT = Path(__file__).resolve().parents[1] / "data" / "mock"


def snapshot():
    provider = MockDataProvider(MOCK_ROOT)
    return build_snapshot(
        provider,
        tickers=["COMI", "MFPC"],
        macro_series_ids=["BRENT_USD", "EGP_USD"],
        as_of=date(2026, 6, 14),
        lookback_days=30,
    )


def test_derives_corporate_macro_and_news_events():
    snap = snapshot()
    events = derive_events_from_snapshot(snap)

    types_present = {e.event_type for e in events}
    assert EventType.CORPORATE in types_present
    assert EventType.MACROECONOMIC in types_present
    assert EventType.NEWS in types_present


def test_every_event_carries_provenance_back_to_the_snapshot():
    snap = snapshot()
    events = derive_events_from_snapshot(snap)

    assert all(e.provenance.inputs[0].ref_id == snap.id for e in events)


def test_untagged_news_is_explicitly_market_wide_not_company_guessed():
    snap = snapshot()
    snap = snap.model_copy(
        update={
            "news": [
                *snap.news,
                NewsItem(
                    published_at=date(2026, 6, 14),
                    source="alborsa",
                    headline="Market-wide Egyptian economic headline",
                ),
            ]
        }
    )
    events = derive_events_from_snapshot(snap)
    market_news = [
        event
        for event in events
        if event.event_type == EventType.NEWS
        and any(entity.kind == EntityKind.MARKET for entity in event.entities)
    ]

    assert market_news
    assert all(event.entities[0].canonical_id == "EGX" for event in market_news)


def test_no_market_events_below_threshold():
    snap = snapshot()
    events = events_from_price_moves(snap, move_threshold=0.03)
    assert events == []


def test_market_events_fire_above_threshold():
    snap = snapshot()
    events = events_from_price_moves(snap, move_threshold=0.01)
    assert len(events) > 0
    assert all(e.event_type == EventType.MARKET for e in events)
    assert all(abs(e.metadata["pct_move"]) >= 0.01 for e in events)


def test_event_repository_persists_and_versions():
    snap = snapshot()
    events = derive_events_from_snapshot(snap)
    repo = EventRepository()
    for event in events:
        repo.add(event)

    assert len(repo.all_latest()) == len(events)
