"""Historical Patterns agent: matches current market conditions against
similar historical episodes (feeding the "what historical cases are
similar?" explainability requirement). Not yet implemented — needs a
similarity/analog-matching methodology over historical regimes.
"""

from __future__ import annotations

from agx_research.agents.base import ResearchAgent, ResearchFinding
from agx_research.data.snapshot import DatasetSnapshot


class HistoricalPatternsAgent(ResearchAgent):
    name = "historical_patterns_agent"

    def research(self, snapshot: DatasetSnapshot) -> list[ResearchFinding]:
        raise NotImplementedError("HistoricalPatternsAgent research logic is not yet implemented")
