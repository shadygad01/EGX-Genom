"""Derive candidate Events from a DatasetSnapshot's raw records.

This is the seam between the raw data schemas (`CorporateEvent`,
`NewsItem`, `MacroObservation`, `PriceBar`) and the Event Platform.
Adapters only *propose* candidate events — persisting them (with
deduplication, conflict resolution, and lifecycle management) is
exclusively `EventPlatform.register()`'s job. A future real data provider
plugs in exactly the same way: turn its payload into candidates via
`build_candidate_event()`, then register them — no architectural change.

Covers four of the six `EventType`s from data actually present in a
snapshot (Corporate, Macroeconomic, News, Market). Political and Technical
events need data sources this scaffold doesn't have yet (a political news
feed; computed technical indicators) — see `docs/EVENT_PLATFORM_DESIGN.md`
for that as a named gap rather than a fabricated adapter.
"""

from __future__ import annotations

from datetime import datetime

from agx_research.data.snapshot import DatasetSnapshot
from agx_research.domain.provenance import Provenance, ProvenanceRef
from agx_research.events.entity import EntityKind
from agx_research.events.entity_resolver import EntityResolver
from agx_research.events.event import Event, EventSeverity, EventType
from agx_research.events.service import build_candidate_event
from agx_research.events.taxonomy import EventSubtype
from agx_research.universe.sector import StaticSectorProvider
from agx_research.universe.static import StaticUniverseProvider

_ADAPTER_NAME = "events.adapters"

# Raw corporate-event type strings (as they appear in provider data) mapped
# into the controlled taxonomy. Unrecognized strings become UNKNOWN rather
# than being guessed at — the raw string is preserved in metadata either way.
_CORPORATE_SUBTYPES: dict[str, EventSubtype] = {
    "EARNINGS": EventSubtype.EARNINGS,
    "DIVIDEND": EventSubtype.DIVIDEND,
    "SPLIT": EventSubtype.STOCK_SPLIT,
    "STOCK_SPLIT": EventSubtype.STOCK_SPLIT,
    "MERGER": EventSubtype.MERGER_ACQUISITION,
    "ACQUISITION": EventSubtype.MERGER_ACQUISITION,
    "CAPITAL_INCREASE": EventSubtype.CAPITAL_INCREASE,
    "MANAGEMENT_CHANGE": EventSubtype.MANAGEMENT_CHANGE,
    "GUIDANCE": EventSubtype.GUIDANCE_UPDATE,
    "BUYBACK": EventSubtype.SHARE_BUYBACK,
    "DELISTING": EventSubtype.DELISTING,
}

# Known macro series mapped to the subtype their significant moves represent.
_MACRO_SERIES_SUBTYPES: dict[str, EventSubtype] = {
    "EGP_USD": EventSubtype.CURRENCY_MOVE,
    "BRENT_USD": EventSubtype.COMMODITY_PRICE_MOVE,
}


def default_resolver(snapshot: DatasetSnapshot) -> EntityResolver:
    return EntityResolver(
        StaticUniverseProvider(),
        StaticSectorProvider(),
        as_of=snapshot.as_of,
        known_macro_series_ids=snapshot.macro_series_ids,
    )


def _provenance(snapshot: DatasetSnapshot, produced_by: str) -> Provenance:
    return Provenance(
        produced_by=produced_by,
        produced_at=datetime.now(),
        inputs=[ProvenanceRef(kind="dataset_snapshot", ref_id=snapshot.id)],
    )


def events_from_corporate_events(
    snapshot: DatasetSnapshot, resolver: EntityResolver | None = None
) -> list[Event]:
    resolver = resolver or default_resolver(snapshot)
    events: list[Event] = []
    for ticker, corporate_events in snapshot.corporate_events.items():
        for corporate_event in corporate_events:
            subtype = _CORPORATE_SUBTYPES.get(
                corporate_event.event_type.upper(), EventSubtype.UNKNOWN
            )
            events.append(
                build_candidate_event(
                    event_type=EventType.CORPORATE,
                    subtype=subtype,
                    entities=[resolver.resolve(ticker)],
                    event_date=corporate_event.event_date,
                    source="dataset_snapshot.corporate_events",
                    confidence=1.0,  # an observed disclosure, not an inference
                    severity=EventSeverity.MEDIUM,
                    metadata={
                        "event_type_raw": corporate_event.event_type,
                        "description": corporate_event.description,
                        **corporate_event.details,
                    },
                    provenance=_provenance(
                        snapshot, f"{_ADAPTER_NAME}.events_from_corporate_events"
                    ),
                )
            )
    return events


def events_from_macro_series(
    snapshot: DatasetSnapshot,
    resolver: EntityResolver | None = None,
    *,
    move_threshold: float = 0.01,
) -> list[Event]:
    """A MACROECONOMIC event for any day-over-day series move at or beyond
    `move_threshold`.

    Deliberately a change from Epoch II's behavior, which emitted one event
    per raw observation: a daily reading is *data* (it stays in the
    snapshot); an *event* is a notable change. One-event-per-observation
    buried real events in noise and made severity meaningless.
    """
    resolver = resolver or default_resolver(snapshot)
    events: list[Event] = []
    for series_id, observations in snapshot.macro_series.items():
        subtype = _MACRO_SERIES_SUBTYPES.get(series_id, EventSubtype.UNKNOWN)
        for previous, current in zip(observations, observations[1:]):
            if previous.value == 0:
                continue
            pct_move = (current.value - previous.value) / previous.value
            if abs(pct_move) < move_threshold:
                continue
            events.append(
                build_candidate_event(
                    event_type=EventType.MACROECONOMIC,
                    subtype=subtype,
                    entities=[resolver.resolve(series_id)],
                    event_date=current.observation_date,
                    source="dataset_snapshot.macro_series",
                    confidence=1.0,
                    severity=(
                        EventSeverity.HIGH
                        if abs(pct_move) >= 2 * move_threshold
                        else EventSeverity.MEDIUM
                    ),
                    metadata={
                        "series_id": series_id,
                        "value": current.value,
                        "previous_value": previous.value,
                        "pct_move": pct_move,
                    },
                    provenance=_provenance(snapshot, f"{_ADAPTER_NAME}.events_from_macro_series"),
                )
            )
    return events


def events_from_news(snapshot: DatasetSnapshot, resolver: EntityResolver | None = None) -> list[Event]:
    resolver = resolver or default_resolver(snapshot)
    events: list[Event] = []
    for item in snapshot.news:
        entities = resolver.resolve_many(item.tickers)
        has_company = any(entity.kind == EntityKind.COMPANY for entity in entities)
        events.append(
            build_candidate_event(
                event_type=EventType.NEWS,
                subtype=EventSubtype.COMPANY_NEWS if has_company else EventSubtype.MACRO_NEWS,
                entities=entities,
                event_date=item.published_at,
                source=item.source,
                confidence=0.6,  # unverified until corroborated by another source
                severity=EventSeverity.LOW,
                metadata={"headline": item.headline},
                provenance=_provenance(snapshot, f"{_ADAPTER_NAME}.events_from_news"),
                # Two different stories about the same company on the same
                # day are two events; the headline is the discriminator.
                discriminator=item.headline,
            )
        )
    return events


def events_from_price_moves(
    snapshot: DatasetSnapshot,
    resolver: EntityResolver | None = None,
    *,
    move_threshold: float = 0.03,
) -> list[Event]:
    """A MARKET event for any single-day close-to-close move at or beyond `move_threshold`."""
    resolver = resolver or default_resolver(snapshot)
    events: list[Event] = []
    for ticker, bars in snapshot.price_history.items():
        for previous, current in zip(bars, bars[1:]):
            if previous.close == 0:
                continue
            pct_move = (current.close - previous.close) / previous.close
            if abs(pct_move) < move_threshold:
                continue
            events.append(
                build_candidate_event(
                    event_type=EventType.MARKET,
                    subtype=EventSubtype.LARGE_PRICE_MOVE,
                    entities=[resolver.resolve(ticker)],
                    event_date=current.trade_date,
                    source="dataset_snapshot.price_history",
                    confidence=1.0,
                    severity=(
                        EventSeverity.HIGH
                        if abs(pct_move) >= 2 * move_threshold
                        else EventSeverity.MEDIUM
                    ),
                    metadata={"pct_move": pct_move},
                    provenance=_provenance(snapshot, f"{_ADAPTER_NAME}.events_from_price_moves"),
                )
            )
    return events


def derive_events_from_snapshot(
    snapshot: DatasetSnapshot,
    resolver: EntityResolver | None = None,
    *,
    price_move_threshold: float = 0.03,
    macro_move_threshold: float = 0.01,
) -> list[Event]:
    resolver = resolver or default_resolver(snapshot)
    return [
        *events_from_corporate_events(snapshot, resolver),
        *events_from_macro_series(snapshot, resolver, move_threshold=macro_move_threshold),
        *events_from_news(snapshot, resolver),
        *events_from_price_moves(snapshot, resolver, move_threshold=price_move_threshold),
    ]
