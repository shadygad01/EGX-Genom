"""Financial Performance agent: relates fundamentals (earnings growth, margins,
leverage, ROE) to forward returns. Not yet implemented — needs a financial
statement data source and a defined fundamental factor set.
"""

from __future__ import annotations

from datetime import date

from agx_research.agents.base import ResearchAgent, ResearchFinding
from agx_research.data.provider import DataProvider


class FinancialPerformanceAgent(ResearchAgent):
    name = "financial_performance_agent"

    def research(self, data_provider: DataProvider, as_of: date) -> list[ResearchFinding]:
        raise NotImplementedError("FinancialPerformanceAgent research logic is not yet implemented")
