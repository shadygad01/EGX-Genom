"""The Event taxonomy: a controlled vocabulary underneath each EventType category.

Adapters previously wrote free-form strings into `metadata["event_type_raw"]`.
`EventSubtype` replaces that with a validated enum, so "what kind of event
is this, precisely" is a checkable fact rather than an arbitrary string a
future adapter might spell differently.
"""

from __future__ import annotations

from enum import Enum

from agx_research.events.event import EventType


class EventSubtype(str, Enum):
    # Corporate
    EARNINGS = "earnings"
    DIVIDEND = "dividend"
    STOCK_SPLIT = "stock_split"
    MERGER_ACQUISITION = "merger_acquisition"
    CAPITAL_INCREASE = "capital_increase"
    MANAGEMENT_CHANGE = "management_change"
    GUIDANCE_UPDATE = "guidance_update"
    SHARE_BUYBACK = "share_buyback"
    DELISTING = "delisting"

    # Macroeconomic
    INTEREST_RATE_DECISION = "interest_rate_decision"
    INFLATION_RELEASE = "inflation_release"
    GDP_RELEASE = "gdp_release"
    CURRENCY_MOVE = "currency_move"
    TRADE_BALANCE = "trade_balance"
    COMMODITY_PRICE_MOVE = "commodity_price_move"

    # Political
    ELECTION = "election"
    POLICY_CHANGE = "policy_change"
    SANCTION = "sanction"
    REGULATORY_CHANGE = "regulatory_change"
    GEOPOLITICAL_TENSION = "geopolitical_tension"

    # Market
    LARGE_PRICE_MOVE = "large_price_move"
    VOLUME_SPIKE = "volume_spike"
    CIRCUIT_BREAKER = "circuit_breaker"
    INDEX_REBALANCE = "index_rebalance"

    # Technical
    SUPPORT_BREAK = "support_break"
    RESISTANCE_BREAK = "resistance_break"
    MOVING_AVERAGE_CROSS = "moving_average_cross"
    TREND_REVERSAL = "trend_reversal"

    # News
    COMPANY_NEWS = "company_news"
    SECTOR_NEWS = "sector_news"
    MACRO_NEWS = "macro_news"
    RUMOR = "rumor"

    UNKNOWN = "unknown"


EVENT_TYPE_SUBTYPES: dict[EventType, set[EventSubtype]] = {
    EventType.CORPORATE: {
        EventSubtype.EARNINGS,
        EventSubtype.DIVIDEND,
        EventSubtype.STOCK_SPLIT,
        EventSubtype.MERGER_ACQUISITION,
        EventSubtype.CAPITAL_INCREASE,
        EventSubtype.MANAGEMENT_CHANGE,
        EventSubtype.GUIDANCE_UPDATE,
        EventSubtype.SHARE_BUYBACK,
        EventSubtype.DELISTING,
    },
    EventType.MACROECONOMIC: {
        EventSubtype.INTEREST_RATE_DECISION,
        EventSubtype.INFLATION_RELEASE,
        EventSubtype.GDP_RELEASE,
        EventSubtype.CURRENCY_MOVE,
        EventSubtype.TRADE_BALANCE,
        EventSubtype.COMMODITY_PRICE_MOVE,
    },
    EventType.POLITICAL: {
        EventSubtype.ELECTION,
        EventSubtype.POLICY_CHANGE,
        EventSubtype.SANCTION,
        EventSubtype.REGULATORY_CHANGE,
        EventSubtype.GEOPOLITICAL_TENSION,
    },
    EventType.MARKET: {
        EventSubtype.LARGE_PRICE_MOVE,
        EventSubtype.VOLUME_SPIKE,
        EventSubtype.CIRCUIT_BREAKER,
        EventSubtype.INDEX_REBALANCE,
    },
    EventType.TECHNICAL: {
        EventSubtype.SUPPORT_BREAK,
        EventSubtype.RESISTANCE_BREAK,
        EventSubtype.MOVING_AVERAGE_CROSS,
        EventSubtype.TREND_REVERSAL,
    },
    EventType.NEWS: {
        EventSubtype.COMPANY_NEWS,
        EventSubtype.SECTOR_NEWS,
        EventSubtype.MACRO_NEWS,
        EventSubtype.RUMOR,
    },
}


def validate_subtype(event_type: EventType, subtype: EventSubtype) -> None:
    if subtype == EventSubtype.UNKNOWN:
        return
    allowed = EVENT_TYPE_SUBTYPES.get(event_type, set())
    if subtype not in allowed:
        raise ValueError(
            f"{subtype.value!r} is not a valid subtype for event_type {event_type.value!r}"
        )
