"""Macro agent: relates macroeconomic series (oil, EGP/USD, CBE rate, inflation)
to sector/stock performance (e.g. "does higher oil price improve fertilizer
sector performance?"). Not yet implemented — needs a defined macro series
catalog and sector mapping before it can propose findings.
"""

from __future__ import annotations

from agx_research.agents.base import ResearchAgent, ResearchFinding
from agx_research.data.snapshot import DatasetSnapshot


class MacroAgent(ResearchAgent):
    name = "macro_agent"

    def research(self, snapshot: DatasetSnapshot) -> list[ResearchFinding]:
        raise NotImplementedError("MacroAgent research logic is not yet implemented")
