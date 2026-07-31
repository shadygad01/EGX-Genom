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
    # MACROECONOMIC absorbs the former ECONOMIC_RELEASES capability
    # (Architecture Adversarial Review, 2026-07-30): both drew on the
    # exact same source pool (trading_economics/cbe/capmas/mof_egypt) with
    # no independent consumer distinguishing them -- one label, not two,
    # per the review's "what could be merged" finding.
    MACROECONOMIC = "macroeconomic"
    MARKET_BREADTH = "market_breadth"
    TRADING_CALENDAR = "trading_calendar"
    INDEX_CONSTITUENTS = "index_constituents"
    SECTOR_MEMBERSHIP = "sector_membership"
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
    Capability.FINANCIAL_STATEMENTS: [
        "egid_financial_filings",
        "telecom_egypt_ir",
        "orascom_ir",
        "company_ir",
    ],
    Capability.INVESTOR_RELATIONS: [
        "egid_financial_filings",
        "telecom_egypt_ir",
        "orascom_ir",
        "company_ir",
    ],
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
        "amwal_alghad",
    ],
    # Merged with the former ECONOMIC_RELEASES pool (trading_economics/cbe/
    # capmas/mof_egypt -- already present here) plus the new Sovereign &
    # Credit Context sources feeding the Country & Macro Risk severity
    # classification's crisis rung (Architecture Adversarial Review R3/R8).
    Capability.MACROECONOMIC: [
        "worldbank",
        # "fred" deliberately excluded from live ranking (project owner
        # direction, 2026-07-31): 3 consecutive real `deploy-pages.yml` LIVE
        # runs all timed out fetching it, so it was never actually a working
        # live dependency despite being catalogued `IMPLEMENTED` -- see
        # docs/TECHNICAL_DEBT.md TD-50. `FredCsvCollector` and its own unit
        # tests stay real/working code; only this live capability pool
        # stopped depending on it. Re-add here once a real live fetch
        # succeeds again (e.g. a mirror endpoint, or the original recovers).
        "imf",
        "oecd",
        "undata",
        "trading_economics",
        "cbe",
        "mof_egypt",
        "capmas",
        "moodys_ratings",
        "sp_global_ratings",
        "fitch_ratings",
        # Added during the Mission Completion Review's final-consistency
        # pass (2026-07-30): both catalogued but previously had zero
        # capability mapping at all, despite being real, named macro/
        # external-sector candidates in docs/FREE_DECISION_DATA_BLUEPRINT.md
        # (Egypt Open Data, §1.1; Suez Canal Authority, §7) --
        # egypt_open_data as further macro context, suez_canal_stats as the
        # External-Sector/FX-driver candidate the Adversarial Review's R11
        # deliberately scoped down to "low-priority, validation-only"
        # rather than a whole new capability -- this gives it a real, if
        # low-ranked, path to collection instead of a dangling catalog row.
        "egypt_open_data",
        "suez_canal_stats",
    ],
    Capability.MARKET_BREADTH: [],
    Capability.TRADING_CALENDAR: ["egx_official"],
    Capability.INDEX_CONSTITUENTS: ["egx_universe_seed", "egx_official"],
    Capability.SECTOR_MEMBERSHIP: ["egx_official"],
    Capability.RESEARCH_PAPERS: ["arxiv", "ssrn", "nber"],
}
