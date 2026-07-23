"""Derive canonical Events from a DatasetSnapshot's raw records.

This is the seam between Epoch I's raw data schemas (`CorporateEvent`,
`NewsItem`, `MacroObservation`, `PriceBar`) and the Event Engine: existing
`DatasetSnapshot` fields and existing agents are untouched, but any new
consumer should read `Event`s produced here rather than the raw records
directly.

Covers four of the six `EventType`s from data actually present in a
snapshot (Corporate, Macroeconomic, News, Market). Political and Technical
events need data sources this scaffold doesn't have yet (a political news
feed; computed technical indicators) — see `docs/EPOCH_II_DESIGN.md` for
that as a named gap rather than a fabricated adapter.
"""

from __future__ import annotations

from datetime import datetime

from agx_research.data.snapshot import DatasetSnapshot
from agx_research.domain.identifiers import new_id
from agx_research.domain.provenance import Provenance, ProvenanceRef
from agx_research.events.event import Event, EventSeverity, EventType

_ADAPTER_NAME = "events.adapters"


def _provenance(snapshot: DatasetSnapshot, produced_by: str) -> Provenance:
    return Provenance(
        produced_by=produced_by,
        produced_at=datetime.now(),
        inputs=[ProvenanceRef(kind="dataset_snapshot", ref_id=snapshot.id)],
    )


def events_from_corporate_events(snapshot: DatasetSnapshot) -> list[Event]:
    events: list[Event] = []
    for ticker, corporate_events in snapshot.corporate_events.items():
        for corporate_event in corporate_events:
            events.append(
                Event(
                    id=new_id("event"),
                    event_type=EventType.CORPORATE,
                    entities=[ticker],
                    timestamp=datetime.combine(corporate_event.event_date, datetime.min.time()),
                    source="dataset_snapshot.corporate_events",
                    confidence=1.0,  # an observed disclosure, not an inference
                    severity=EventSeverity.MEDIUM,
                    metadata={
                        "event_type_raw": corporate_event.event_type,
                        "description": corporate_event.description,
                    },
                    provenance=_provenance(snapshot, f"{_ADAPTER_NAME}.events_from_corporate_events"),
                )
            )
    return events


def events_from_macro_series(snapshot: DatasetSnapshot) -> list[Event]:
    events: list[Event] = []
    for series_id, observations in snapshot.macro_series.items():
        for observation in observations:
            events.append(
                Event(
                    id=new_id("event"),
                    event_type=EventType.MACROECONOMIC,
                    entities=[series_id],
                    timestamp=datetime.combine(observation.observation_date, datetime.min.time()),
                    source="dataset_snapshot.macro_series",
                    confidence=1.0,
                    severity=EventSeverity.LOW,
                    metadata={"value": observation.value},
                    provenance=_provenance(snapshot, f"{_ADAPTER_NAME}.events_from_macro_series"),
                )
            )
    return events


def events_from_news(snapshot: DatasetSnapshot) -> list[Event]:
    events: list[Event] = []
    for item in snapshot.news:
        events.append(
            Event(
                id=new_id("event"),
                event_type=EventType.NEWS,
                entities=list(item.tickers),
                timestamp=datetime.combine(item.published_at, datetime.min.time()),
                source=item.source,
                confidence=0.6,  # unverified until corroborated by another source/event
                severity=EventSeverity.LOW,
                metadata={"headline": item.headline},
                provenance=_provenance(snapshot, f"{_ADAPTER_NAME}.events_from_news"),
            )
        )
    return events


def events_from_price_moves(snapshot: DatasetSnapshot, *, move_threshold: float = 0.03) -> list[Event]:
    """A MARKET event for any single-day close-to-close move at or beyond `move_threshold`."""
    events: list[Event] = []
    for ticker, bars in snapshot.price_history.items():
        for previous, current in zip(bars, bars[1:]):
            if previous.close == 0:
                continue
            pct_move = (current.close - previous.close) / previous.close
            if abs(pct_move) < move_threshold:
                continue
            events.append(
                Event(
                    id=new_id("event"),
                    event_type=EventType.MARKET,
                    entities=[ticker],
                    timestamp=datetime.combine(current.trade_date, datetime.min.time()),
                    source="dataset_snapshot.price_history",
                    confidence=1.0,
                    severity=(
                        EventSeverity.HIGH if abs(pct_move) >= 2 * move_threshold else EventSeverity.MEDIUM
                    ),
                    metadata={"pct_move": pct_move},
                    provenance=_provenance(snapshot, f"{_ADAPTER_NAME}.events_from_price_moves"),
                )
            )
    return events


def derive_events_from_snapshot(
    snapshot: DatasetSnapshot, *, price_move_threshold: float = 0.03
) -> list[Event]:
    return [
        *events_from_corporate_events(snapshot),
        *events_from_macro_series(snapshot),
        *events_from_news(snapshot),
        *events_from_price_moves(snapshot, move_threshold=price_move_threshold),
    ]
