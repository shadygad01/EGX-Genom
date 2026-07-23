"""Financial Performance agent: relates fundamentals (earnings growth, margins,
leverage, ROE) to forward returns. Not yet implemented — needs a financial
statement data source and a defined fundamental factor set.
"""

from __future__ import annotations

from agx_research.agents.base import ResearchAgent, ResearchFinding
from agx_research.data.snapshot import DatasetSnapshot


class FinancialPerformanceAgent(ResearchAgent):
    name = "financial_performance_agent"

    def research(self, snapshot: DatasetSnapshot) -> list[ResearchFinding]:
        raise NotImplementedError("FinancialPerformanceAgent research logic is not yet implemented")
