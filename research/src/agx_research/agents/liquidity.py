"""Liquidity agent: studies volume, turnover, bid-ask spread proxies, and
foreign/local flow data (e.g. "do foreign inflows predict banking strength?").
Not yet implemented — needs a foreign/local flow data source.
"""

from __future__ import annotations

from datetime import date

from agx_research.agents.base import ResearchAgent, ResearchFinding
from agx_research.data.provider import DataProvider


class LiquidityAgent(ResearchAgent):
    name = "liquidity_agent"

    def research(self, data_provider: DataProvider, as_of: date) -> list[ResearchFinding]:
        raise NotImplementedError("LiquidityAgent research logic is not yet implemented")
