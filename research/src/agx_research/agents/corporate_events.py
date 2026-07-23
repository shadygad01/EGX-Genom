"""Corporate Events agent: studies reactions to earnings, dividends, capital
changes, and other disclosures (e.g. "do positive earnings create delayed
reactions?"). Not yet implemented — needs an event-study methodology.
"""

from __future__ import annotations

from datetime import date

from agx_research.agents.base import ResearchAgent, ResearchFinding
from agx_research.data.provider import DataProvider


class CorporateEventsAgent(ResearchAgent):
    name = "corporate_events_agent"

    def research(self, data_provider: DataProvider, as_of: date) -> list[ResearchFinding]:
        raise NotImplementedError("CorporateEventsAgent research logic is not yet implemented")
