"""Data shapes shared by every DataProvider implementation.

These are the four data classes the vision document calls out as inputs the
system must model relationships across, rather than in isolation: prices,
corporate events, macro variables, and news.
"""

from __future__ import annotations

from datetime import date

from pydantic import BaseModel, Field


class PriceBar(BaseModel):
    """A single daily OHLCV observation for one ticker."""

    ticker: str
    trade_date: date
    open: float
    high: float
    low: float
    close: float
    volume: int


class CorporateEvent(BaseModel):
    """A corporate action or disclosure (earnings, dividend, capital change, etc.)."""

    ticker: str
    event_date: date
    event_type: str
    description: str
    details: dict = Field(default_factory=dict)


class MacroObservation(BaseModel):
    """A single macroeconomic series observation (e.g. EGP/USD, oil price, CBE rate)."""

    series_id: str
    observation_date: date
    value: float


class NewsItem(BaseModel):
    """A news/sentiment item, optionally linked to one or more tickers."""

    published_at: date
    source: str
    headline: str
    tickers: list[str] = Field(default_factory=list)
    body: str | None = None
