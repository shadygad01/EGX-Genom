"""The shared category vocabulary Phase 3 (attribution), Phase 4
(counterfactual), and Phase 8 (committee validation) all use.

The mission named 9 categories (Macro/Sector/Quality/Value/Catalyst/Risk/
Liquidity/Portfolio/Execution). This module adds a 10th, `TECHNICAL`, for
a real reason rather than mismapping evidence to fit exactly 9: two real
Scientist Framework agents (`MarketStructureAgent`'s cross-ticker
correlation findings via co-movement, `TechnicalStructureAgent`'s
price-pattern findings, and `HistoricalPatternsAgent`'s analog-matching
findings) produce genuinely technical-pattern evidence that doesn't
honestly belong under Catalyst, Quality, or any of the other 9 without
mislabeling it. The mission's own charter authorizes exactly this
("redesign... whenever doing so improves... explainability").

`AGENT_CATEGORY_MAP` is the one place `KnowledgeObject.creator_agent`
strings get mapped to a category -- every attribution/counterfactual/
committee engine imports this rather than re-declaring its own mapping.
"""

from __future__ import annotations

from enum import Enum


class Category(str, Enum):
    MACRO = "macro"
    SECTOR = "sector"
    QUALITY = "quality"
    VALUE = "value"
    CATALYST = "catalyst"
    RISK = "risk"
    LIQUIDITY = "liquidity"
    PORTFOLIO = "portfolio"
    EXECUTION = "execution"
    TECHNICAL = "technical"


#: `KnowledgeObject.creator_agent` -> Category, covering all 8 real
#: Scientist Framework agents (see `docs/PHASE_STATUS.md` System 08). The
#: `synthetic-` prefix knowledge `institutional_validation/` produces is
#: deliberately absent here -- attribution over synthetic evidence should
#: report an explicit "unmapped" category, never guess a real one.
#:
#: `MarketStructureAgent` (cross-ticker co-movement/correlation) maps to
#: SECTOR: it is the only real signal in this codebase measuring how a
#: ticker moves relative to its peers, the closest honest proxy to a
#: "sector" committee opinion available today (no dedicated sector-peer-
#: average computation exists -- see TD entry this mission adds).
#: `NewsIntelligenceAgent` maps to CATALYST (event/headline-driven,
#: same as CorporateEventsAgent) rather than RISK, since its findings are
#: framed as directional sentiment events, not a risk measurement.
AGENT_CATEGORY_MAP: dict[str, Category] = {
    "market_structure_agent": Category.SECTOR,
    "macro_agent": Category.MACRO,
    "corporate_events_agent": Category.CATALYST,
    "liquidity_agent": Category.LIQUIDITY,
    "technical_structure_agent": Category.TECHNICAL,
    "news_intelligence_agent": Category.CATALYST,
    "historical_patterns_agent": Category.TECHNICAL,
    "financial_performance_agent": Category.QUALITY,
}

#: Categories whose evidence additively composes the model's
#: `expected_return` (via `KnowledgeObject`s consumed by
#: `KnowledgeWeightedHorizonModel`), plus VALUE (blended separately by
#: `RecommendationService`'s fair-value step). These are the categories
#: `DecisionAttributionEngine.return_contributions` covers.
RETURN_CONTRIBUTING_CATEGORIES = frozenset(AGENT_CATEGORY_MAP.values()) | {Category.VALUE}

#: Categories that act as gates/modifiers on the decision (risk inflation,
#: hard overrides, joint-portfolio normalization, executability) rather
#: than additive return contributors -- covered by
#: `DecisionAttributionEngine.modifiers` instead.
MODIFIER_CATEGORIES = frozenset({Category.RISK, Category.LIQUIDITY, Category.PORTFOLIO, Category.EXECUTION})


def category_for_agent(creator_agent: str) -> Category | None:
    """None means genuinely unmapped -- e.g. synthetic validation
    knowledge, or a future agent this map hasn't been updated for yet.
    Callers must treat None as "unattributed", never silently drop it."""
    return AGENT_CATEGORY_MAP.get(creator_agent)


__all__ = [
    "AGENT_CATEGORY_MAP",
    "MODIFIER_CATEGORIES",
    "RETURN_CONTRIBUTING_CATEGORIES",
    "Category",
    "category_for_agent",
]
