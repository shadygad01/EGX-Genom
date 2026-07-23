"""News Intelligence agent: extracts sentiment and event signals from news
flow and relates them to subsequent price behavior. Not yet implemented —
needs an NLP/sentiment pipeline over `NewsItem` data.
"""

from __future__ import annotations

from agx_research.agents.base import ResearchAgent, ResearchFinding
from agx_research.data.snapshot import DatasetSnapshot


class NewsIntelligenceAgent(ResearchAgent):
    name = "news_intelligence_agent"

    def research(self, snapshot: DatasetSnapshot) -> list[ResearchFinding]:
        raise NotImplementedError("NewsIntelligenceAgent research logic is not yet implemented")
