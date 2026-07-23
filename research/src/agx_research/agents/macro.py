"""Macro agent: relates macroeconomic series (oil, EGP/USD, CBE rate, inflation)
to sector/stock performance (e.g. "does higher oil price improve fertilizer
sector performance?"). Not yet implemented — needs a defined macro series
catalog and sector mapping before it can propose findings.
"""

from __future__ import annotations

from datetime import date

from agx_research.agents.base import ResearchAgent, ResearchFinding
from agx_research.data.provider import DataProvider


class MacroAgent(ResearchAgent):
    name = "macro_agent"

    def research(self, data_provider: DataProvider, as_of: date) -> list[ResearchFinding]:
        raise NotImplementedError("MacroAgent research logic is not yet implemented")
