"""Capability: the acquisition program's primary object.

Root-principle correction (see `docs/ACQUISITION_STRATEGY.md`): a homepage
is not a data source, and a company website is not a capability. AGX needs
independent kinds of data -- Price Data, Corporate Disclosures, Corporate
Actions, Financial Statements, Investor Relations, News, Macroeconomic
Data, Market Breadth, Trading Calendar, Index Constituents, Sector
Membership, Economic Releases, Research Papers -- and each one may have
more than one legal acquisition strategy. This module is that mapping
turned into runtime data, not narrative: `CAPABILITY_STRATEGIES` is a
declared, ranked pool of *catalogued* `SourceSpec` ids per capability
(never a fabricated or guessed source), which `capability_engine.py` then
ranks with live registry/reputation data and executes with automatic
fallback.

A capability with only one candidate today (e.g. Trading Calendar) is
honestly not yet diversified, not silently padded with an invented
alternative -- diversification happens by cataloguing a second legal
strategy (see `docs/ACQUISITION_STRATEGY.md`'s per-capability analysis),
never by adding a placeholder id here.
"""

from __future__ import annotations

from enum import Enum


class Capability(str, Enum):
    PRICE_DATA = "price_data"
    CORPORATE_DISCLOSURES = "corporate_disclosures"
    CORPORATE_ACTIONS = "corporate_actions"
    FINANCIAL_STATEMENTS = "financial_statements"
    INVESTOR_RELATIONS = "investor_relations"
    NEWS = "news"
    MACROECONOMIC = "macroeconomic"
    MARKET_BREADTH = "market_breadth"
    TRADING_CALENDAR = "trading_calendar"
    INDEX_CONSTITUENTS = "index_constituents"
    SECTOR_MEMBERSHIP = "sector_membership"
    ECONOMIC_RELEASES = "economic_releases"
    RESEARCH_PAPERS = "research_papers"


# Declared candidate pools per capability -- every id here is a real
# `SourceSpec` id from `sources/catalog.py`'s seed catalog (verified to
# exist, never invented for this mapping). Order is the starting prior
# `docs/ACQUISITION_STRATEGY.md` Step 5 chose; `rank_capability_strategies`
# (capability_engine.py) recomputes the actual order from registry state
# and measured reputation, so this list is a candidate *set*, not a
# hardcoded final answer.
#
# Market Breadth is deliberately absent as an independent entry: it is
# computed from Price Data already collected, not fetched from a separate
# feed (see docs/ACQUISITION_STRATEGY.md capability 8) -- listing the same
# ids here would double-attempt price collectors for no new information.
CAPABILITY_STRATEGIES: dict[Capability, list[str]] = {
    Capability.PRICE_DATA: [
        "egx_price_composite",
        "stooq",
        "fmp",
        "alphavantage",
        "polygon",
        "tiingo",
        "egx_official",
        "company_ir",
    ],
    Capability.CORPORATE_DISCLOSURES: [
        "egx_official",
        "fra_egypt",
        "company_ir",
        "enterprise_press",
        "mubasher",
        "zawya",
    ],
    Capability.CORPORATE_ACTIONS: [
        "egx_official",
        "company_ir",
        "reuters",
        "enterprise_press",
        "mubasher",
        "zawya",
    ],
    Capability.FINANCIAL_STATEMENTS: ["company_ir", "fmp"],
    Capability.INVESTOR_RELATIONS: ["company_ir"],
    Capability.NEWS: [
        "reuters",
        "enterprise_press",
        "gdelt",
        "mubasher",
        "zawya",
        "asharq_business",
        "cnbc_arabia",
        "alarabiya_business",
        "marketscreener",
        "investing_news",
        "almal",
        "alborsa",
        "masrawy_economy",
        "youm7_economy",
        "skynews_arabia_economy",
        "asharq_economy",
    ],
    Capability.MACROECONOMIC: [
        "worldbank",
        "fred",
        "imf",
        "oecd",
        "undata",
        "trading_economics",
        "cbe",
        "mof_egypt",
        "capmas",
    ],
    Capability.MARKET_BREADTH: [],
    Capability.TRADING_CALENDAR: ["egx_official"],
    Capability.INDEX_CONSTITUENTS: ["egx_universe_seed", "egx_official"],
    Capability.SECTOR_MEMBERSHIP: ["egx_official"],
    Capability.ECONOMIC_RELEASES: ["trading_economics", "cbe", "capmas", "mof_egypt"],
    Capability.RESEARCH_PAPERS: ["arxiv", "ssrn", "nber"],
}
