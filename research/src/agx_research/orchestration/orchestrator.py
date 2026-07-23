"""Runs every registered agent against one point-in-time dataset snapshot.

This is the concrete answer to "every trading day the platform must answer
one question": `ResearchOrchestrator.run(as_of)` materializes a
`DatasetSnapshot` and produces the `ResearchCycle` for that day.
"""

from __future__ import annotations

from datetime import date, datetime

from agx_research.agents.base import ResearchAgent
from agx_research.data.provider import DataProvider
from agx_research.data.snapshot import build_snapshot
from agx_research.domain.identifiers import new_id
from agx_research.orchestration.cycle import ResearchCycle


class ResearchOrchestrator:
    def __init__(
        self,
        agents: list[ResearchAgent],
        data_provider: DataProvider,
        *,
        tickers: list[str],
        macro_series_ids: list[str] | None = None,
        lookback_days: int = 30,
    ):
        self.agents = agents
        self.data_provider = data_provider
        self.tickers = tickers
        self.macro_series_ids = macro_series_ids or []
        self.lookback_days = lookback_days

    def run(self, as_of: date) -> ResearchCycle:
        started_at = datetime.now()
        snapshot = build_snapshot(
            self.data_provider,
            tickers=self.tickers,
            macro_series_ids=self.macro_series_ids,
            as_of=as_of,
            lookback_days=self.lookback_days,
        )

        findings = []
        for agent in self.agents:
            findings.extend(agent.research(snapshot))

        return ResearchCycle(
            id=new_id("cycle"),
            run_date=as_of,
            dataset_snapshot_id=snapshot.id,
            agent_versions={agent.name: agent.version for agent in self.agents},
            findings=findings,
            started_at=started_at,
            completed_at=datetime.now(),
        )
