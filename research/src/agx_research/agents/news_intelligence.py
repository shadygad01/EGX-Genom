"""News Intelligence agent: extracts sentiment and event signals from news
flow and relates them to subsequent price behavior. Not yet implemented —
needs an NLP/sentiment pipeline over `NewsItem` data.
"""

from __future__ import annotations

from datetime import date

from agx_research.agents.base import ResearchAgent, ResearchFinding
from agx_research.data.provider import DataProvider


class NewsIntelligenceAgent(ResearchAgent):
    name = "news_intelligence_agent"

    def research(self, data_provider: DataProvider, as_of: date) -> list[ResearchFinding]:
        raise NotImplementedError("NewsIntelligenceAgent research logic is not yet implemented")
