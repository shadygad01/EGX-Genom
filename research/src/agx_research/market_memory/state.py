"""MarketState: everything needed to reconstruct one historical trading day exactly."""

from __future__ import annotations

from datetime import date

from pydantic import BaseModel, Field

from agx_research.data.snapshot import DatasetSnapshot
from agx_research.events.event import Event


class TradingSession(BaseModel):
    session_date: date
    is_trading_day: bool
    holiday_name: str | None = None
    notes: str = ""


class MarketState(BaseModel):
    as_of: date
    dataset_snapshot: DatasetSnapshot
    constituents: dict[str, str] = Field(default_factory=dict)
    sectors: dict[str, str] = Field(default_factory=dict)
    trading_session: TradingSession
    # Canonical events registered for this day's window, via the Event
    # Platform (deduped, conflict-resolved) — never raw records.
    events: list[Event] = Field(default_factory=list)
