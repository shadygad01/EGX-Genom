"""Historical Patterns agent: matches current market conditions against
similar historical episodes (feeding the "what historical cases are
similar?" explainability requirement). Not yet implemented — needs a
similarity/analog-matching methodology over historical regimes.
"""

from __future__ import annotations

from datetime import date

from agx_research.agents.base import ResearchAgent, ResearchFinding
from agx_research.data.provider import DataProvider


class HistoricalPatternsAgent(ResearchAgent):
    name = "historical_patterns_agent"

    def research(self, data_provider: DataProvider, as_of: date) -> list[ResearchFinding]:
        raise NotImplementedError("HistoricalPatternsAgent research logic is not yet implemented")
