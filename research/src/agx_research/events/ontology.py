"""Impact horizon classification: which research horizon(s) an event
subtype is relevant to investigate.

This is a triage/categorization decision, not a prediction of price impact
or direction — the same kind of judgment `MarketStructureAgent` already
makes when it proposes `Horizon.MICRO` for a candidate hypothesis. It says
"a dividend is worth investigating for short-horizon effects," not "this
dividend will move the price by X%." The mapping is an explicit, documented
engineering default and should be revisited once real research validates
(or contradicts) it — it is not itself a validated market claim.
"""

from __future__ import annotations

from agx_research.config import Horizon
from agx_research.events.taxonomy import EventSubtype

DEFAULT_IMPACT_HORIZONS: dict[EventSubtype, list[Horizon]] = {
    EventSubtype.EARNINGS: [Horizon.MICRO, Horizon.SWING],
    EventSubtype.DIVIDEND: [Horizon.MICRO],
    EventSubtype.STOCK_SPLIT: [Horizon.MICRO],
    EventSubtype.MERGER_ACQUISITION: [Horizon.SWING, Horizon.INVESTMENT],
    EventSubtype.CAPITAL_INCREASE: [Horizon.SWING, Horizon.INVESTMENT],
    EventSubtype.MANAGEMENT_CHANGE: [Horizon.SWING, Horizon.INVESTMENT],
    EventSubtype.GUIDANCE_UPDATE: [Horizon.SWING, Horizon.INVESTMENT],
    EventSubtype.SHARE_BUYBACK: [Horizon.SWING, Horizon.INVESTMENT],
    EventSubtype.DELISTING: [Horizon.INVESTMENT],
    EventSubtype.INTEREST_RATE_DECISION: [Horizon.SWING, Horizon.INVESTMENT],
    EventSubtype.INFLATION_RELEASE: [Horizon.SWING, Horizon.INVESTMENT],
    EventSubtype.GDP_RELEASE: [Horizon.INVESTMENT],
    EventSubtype.CURRENCY_MOVE: [Horizon.MICRO, Horizon.SWING],
    EventSubtype.TRADE_BALANCE: [Horizon.INVESTMENT],
    EventSubtype.COMMODITY_PRICE_MOVE: [Horizon.SWING, Horizon.INVESTMENT],
    EventSubtype.ELECTION: [Horizon.INVESTMENT],
    EventSubtype.POLICY_CHANGE: [Horizon.SWING, Horizon.INVESTMENT],
    EventSubtype.SANCTION: [Horizon.SWING, Horizon.INVESTMENT],
    EventSubtype.REGULATORY_CHANGE: [Horizon.SWING, Horizon.INVESTMENT],
    EventSubtype.GEOPOLITICAL_TENSION: [Horizon.MICRO, Horizon.SWING],
    EventSubtype.LARGE_PRICE_MOVE: [Horizon.MICRO],
    EventSubtype.VOLUME_SPIKE: [Horizon.MICRO],
    EventSubtype.CIRCUIT_BREAKER: [Horizon.MICRO],
    EventSubtype.INDEX_REBALANCE: [Horizon.SWING],
    EventSubtype.SUPPORT_BREAK: [Horizon.MICRO, Horizon.SWING],
    EventSubtype.RESISTANCE_BREAK: [Horizon.MICRO, Horizon.SWING],
    EventSubtype.MOVING_AVERAGE_CROSS: [Horizon.SWING],
    EventSubtype.TREND_REVERSAL: [Horizon.SWING, Horizon.INVESTMENT],
    EventSubtype.COMPANY_NEWS: [Horizon.MICRO, Horizon.SWING],
    EventSubtype.SECTOR_NEWS: [Horizon.SWING],
    EventSubtype.MACRO_NEWS: [Horizon.SWING, Horizon.INVESTMENT],
    EventSubtype.RUMOR: [Horizon.MICRO],
    EventSubtype.UNKNOWN: [],
}


def classify_impact_horizons(subtype: EventSubtype) -> list[Horizon]:
    return list(DEFAULT_IMPACT_HORIZONS.get(subtype, []))
