"""Technical Structure agent: studies price/volume pattern regularities
(support/resistance, momentum, mean reversion) as candidate hypotheses, not
as encoded trading rules. Not yet implemented.
"""

from __future__ import annotations

from datetime import date

from agx_research.agents.base import ResearchAgent, ResearchFinding
from agx_research.data.provider import DataProvider


class TechnicalStructureAgent(ResearchAgent):
    name = "technical_structure_agent"

    def research(self, data_provider: DataProvider, as_of: date) -> list[ResearchFinding]:
        raise NotImplementedError("TechnicalStructureAgent research logic is not yet implemented")
