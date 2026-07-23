from datetime import date
from pathlib import Path

from agx_research.agents.market_structure import MarketStructureAgent
from agx_research.data.mock_provider import MockDataProvider
from agx_research.orchestration.orchestrator import ResearchOrchestrator

MOCK_ROOT = Path(__file__).resolve().parents[1] / "data" / "mock"


def test_orchestrator_runs_agents_against_one_snapshot_and_records_lineage():
    provider = MockDataProvider(MOCK_ROOT)
    agent = MarketStructureAgent(ticker_pairs=[("COMI", "MFPC")], correlation_threshold=0.0)
    orchestrator = ResearchOrchestrator(
        agents=[agent],
        data_provider=provider,
        tickers=["COMI", "MFPC"],
        macro_series_ids=["BRENT_USD"],
        lookback_days=30,
    )

    cycle = orchestrator.run(date(2026, 6, 14))

    assert cycle.run_date == date(2026, 6, 14)
    assert cycle.agent_versions == {"market_structure_agent": "0.1.0"}
    assert len(cycle.findings) == 1

    finding = cycle.findings[0]
    # The finding's own provenance points back at exactly the snapshot the cycle built --
    # this is the walkable chain: cycle -> dataset_snapshot_id -> finding.provenance ref.
    assert finding.provenance.inputs[0].ref_id == cycle.dataset_snapshot_id
    assert cycle.completed_at is not None
    assert cycle.completed_at >= cycle.started_at


def test_orchestrator_with_no_agents_produces_empty_findings():
    provider = MockDataProvider(MOCK_ROOT)
    orchestrator = ResearchOrchestrator(
        agents=[], data_provider=provider, tickers=["COMI"], macro_series_ids=[]
    )

    cycle = orchestrator.run(date(2026, 6, 14))

    assert cycle.findings == []
    assert cycle.agent_versions == {}


def test_run_session_builds_an_explicit_task_graph_and_persists_snapshot_artifact():
    from agx_research.orchestration.artifacts import ArtifactKind
    from agx_research.orchestration.task_graph import TaskStatus

    provider = MockDataProvider(MOCK_ROOT)
    agent = MarketStructureAgent(ticker_pairs=[("COMI", "MFPC")], correlation_threshold=0.0)
    orchestrator = ResearchOrchestrator(
        agents=[agent],
        data_provider=provider,
        tickers=["COMI", "MFPC"],
        macro_series_ids=["BRENT_USD"],
        lookback_days=30,
    )

    session = orchestrator.run_session(date(2026, 6, 14))

    assert session.run_date == date(2026, 6, 14)
    assert len(session.tasks) == 2
    assert all(t.status == TaskStatus.SUCCEEDED for t in session.tasks)
    assert session.tasks[1].dependencies == [session.tasks[0].id]
    assert len(session.findings) == 1
    assert len(session.artifact_ids) == 1

    artifact = orchestrator.artifact_repository.latest(session.artifact_ids[0])
    assert artifact.kind == ArtifactKind.DATASET_SNAPSHOT
    assert artifact.payload["id"] == session.dataset_snapshot_id
