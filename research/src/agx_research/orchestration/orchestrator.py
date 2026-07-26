"""Runs every registered agent against one point-in-time dataset snapshot.

`run()` is the original, minimal entry point: it materializes a
`DatasetSnapshot` and produces a bare `ResearchCycle` for callers that only
need agent findings. `run_session()` is the Epoch II superset: it runs the
same work through an explicit `TaskGraph` and returns a `ResearchSession`
owning every artifact produced. Both are kept — `run()`'s contract is
unchanged for existing callers.
"""

from __future__ import annotations

from datetime import date, datetime

from agx_research.agents.base import ResearchAgent
from agx_research.data.provider import DataProvider
from agx_research.data.snapshot import DatasetSnapshot, build_snapshot
from agx_research.domain.identifiers import new_id
from agx_research.domain.provenance import Provenance
from agx_research.orchestration.artifacts import ArtifactKind, ArtifactRepository
from agx_research.orchestration.cycle import ResearchCycle
from agx_research.orchestration.session import ResearchSession
from agx_research.orchestration.task_graph import Task, TaskGraph
from agx_research.universe.provider import UniverseProvider


class ResearchOrchestrator:
    def __init__(
        self,
        agents: list[ResearchAgent],
        data_provider: DataProvider,
        universe_provider: UniverseProvider,
        *,
        macro_series_ids: list[str] | None = None,
        lookback_days: int = 30,
        artifact_repository: ArtifactRepository | None = None,
    ):
        self.agents = agents
        self.data_provider = data_provider
        self.universe_provider = universe_provider
        self.macro_series_ids = macro_series_ids or []
        self.lookback_days = lookback_days
        self.artifact_repository = artifact_repository or ArtifactRepository()

    def run(self, as_of: date) -> ResearchCycle:
        started_at = datetime.now()
        snapshot = build_snapshot(
            self.data_provider,
            tickers=sorted(self.universe_provider.constituents(as_of)),
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

    def run_session(self, as_of: date) -> ResearchSession:
        """The Research Operating System entry point: builds an explicit task
        graph (snapshot -> agents), records every task's status/timing, and
        persists the snapshot as a versioned Artifact.
        """
        started_at = datetime.now()
        graph = TaskGraph()

        snapshot_task = Task(id=new_id("task"), name="build_dataset_snapshot")

        def _build_snapshot(_deps: dict) -> DatasetSnapshot:
            return build_snapshot(
                self.data_provider,
                tickers=sorted(self.universe_provider.constituents(as_of)),
                macro_series_ids=self.macro_series_ids,
                as_of=as_of,
                lookback_days=self.lookback_days,
            )

        graph.add_task(snapshot_task, _build_snapshot)
        graph.run_task(snapshot_task.id)
        snapshot: DatasetSnapshot = graph.result(snapshot_task.id)

        agents_task = Task(
            id=new_id("task"), name="run_research_agents", dependencies=[snapshot_task.id]
        )

        def _run_agents(deps: dict) -> list:
            snap: DatasetSnapshot = deps[snapshot_task.id]
            findings = []
            for agent in self.agents:
                findings.extend(agent.research(snap))
            return findings

        graph.add_task(agents_task, _run_agents)
        graph.run_task(agents_task.id)
        findings = graph.result(agents_task.id)

        snapshot_artifact = self.artifact_repository.store(
            kind=ArtifactKind.DATASET_SNAPSHOT,
            payload=snapshot,
            produced_by_task_id=snapshot_task.id,
            provenance=Provenance(produced_by=snapshot_task.id, produced_at=datetime.now()),
        )

        return ResearchSession(
            id=new_id("session"),
            run_date=as_of,
            dataset_snapshot_id=snapshot.id,
            agent_versions={agent.name: agent.version for agent in self.agents},
            tasks=graph.tasks(),
            artifact_ids=[snapshot_artifact.id],
            findings=findings,
            started_at=started_at,
            completed_at=datetime.now(),
        )
