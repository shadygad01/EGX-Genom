"""Tests for the dashboard artifact export + validate layer: every
export_* function is a thin model_dump over an existing repository/service,
and validate_dashboard_artifacts must catch a corrupted or schema-drifted
file rather than let it reach the published site.
"""

from datetime import date, datetime
from pathlib import Path

import pytest
from pydantic import ValidationError

from agx_research.dashboard.export import (
    ARTIFACT_FILENAMES,
    export_events,
    export_knowledge,
    export_market_state,
    export_patterns,
    export_recommendations,
    export_runtime_metrics,
    export_source_registry,
    export_system_status,
    write_dashboard_artifacts,
)
from agx_research.dashboard.validate import DashboardArtifactError, validate_dashboard_artifacts
from agx_research.data.mock_provider import MockDataProvider
from agx_research.domain.provenance import Provenance
from agx_research.events.entity import EntityKind, EntityRef
from agx_research.events.event import EventSeverity, EventType
from agx_research.events.repository import EventRepository
from agx_research.events.service import EventPlatform, build_candidate_event
from agx_research.events.taxonomy import EventSubtype
from agx_research.knowledge.schema import KnowledgeObject, StatisticalEvidence
from agx_research.knowledge.store import KnowledgeStore
from agx_research.market_memory.memory import MarketMemory
from agx_research.runtime.engine import RunRecord, RunRecordRepository, RunStatus
from agx_research.universe.sector import StaticSectorProvider
from agx_research.universe.static import StaticUniverseProvider

MOCK_ROOT = Path(__file__).resolve().parents[1] / "data" / "mock"


def _knowledge(ticker: str = "COMI") -> KnowledgeObject:
    return KnowledgeObject(
        id="know-test",
        discovery_date=date(2026, 5, 1),
        creator_agent="test",
        supporting_evidence=[],
        confidence=0.7,
        statistical_evidence=StatisticalEvidence(
            method="test", statistic=2.0, p_value=0.01, sample_size=40
        ),
        economic_explanation="test",
        affected_assets=[ticker],
        horizon="swing",
        expected_return=0.03,
        expected_risk=0.02,
        provenance=Provenance(produced_by="test", produced_at=datetime.now()),
    )


def _memory(event_platform: EventPlatform | None = None) -> MarketMemory:
    return MarketMemory(
        MockDataProvider(MOCK_ROOT),
        StaticUniverseProvider(),
        StaticSectorProvider(),
        tickers=["COMI", "MFPC"],
        macro_series_ids=["BRENT_USD"],
        lookback_days=30,
        event_platform=event_platform or EventPlatform(),
    )


# --- individual export_* functions ---


def test_export_knowledge_empty_store():
    assert export_knowledge(KnowledgeStore()) == []


def test_export_knowledge_returns_latest_revision_only():
    store = KnowledgeStore()
    original = _knowledge()
    store._repo.add(original)
    store._repo.add(original.model_copy(update={"version": 2, "confidence": 0.9}))

    exported = export_knowledge(store)
    assert len(exported) == 1
    assert exported[0]["version"] == 2
    assert exported[0]["confidence"] == 0.9


def test_export_events_returns_registered_events():
    repo = EventRepository()
    platform = EventPlatform(repository=repo)
    candidate = build_candidate_event(
        event_type=EventType.CORPORATE,
        subtype=EventSubtype.DIVIDEND,
        entities=[EntityRef(kind=EntityKind.COMPANY, canonical_id="COMI", raw_mention="COMI")],
        event_date=date(2026, 6, 1),
        source="test",
        confidence=0.8,
        severity=EventSeverity.MEDIUM,
        provenance=Provenance(produced_by="test", produced_at=datetime.now()),
    )
    platform.register(candidate)

    exported = export_events(repo)
    assert len(exported) == 1
    assert exported[0]["event_type"] == "corporate"


def test_export_patterns_is_always_empty():
    assert export_patterns() == []


def test_export_recommendations_empty_when_as_of_is_none():
    store = KnowledgeStore()
    platform = EventPlatform()
    assert export_recommendations(store, platform, tickers=["COMI"], as_of=None) == []


def test_export_recommendations_from_promoted_knowledge():
    store = KnowledgeStore()
    store._repo.add(_knowledge("COMI"))
    platform = EventPlatform()

    exported = export_recommendations(
        store, platform, tickers=["COMI", "MFPC"], as_of=date(2026, 6, 14)
    )
    assert {r["ticker"] for r in exported} == {"COMI"}
    assert exported[0]["explanation"]["evidence_refs"]


def test_export_market_state_none_when_as_of_is_none():
    assert export_market_state(_memory(), None) is None


def test_export_market_state_reconstructs_real_state():
    state = export_market_state(_memory(), date(2026, 6, 14))
    assert state is not None
    assert state["as_of"] == "2026-06-14"
    assert "COMI" in state["dataset_snapshot"]["price_history"]


def test_export_runtime_metrics():
    runs = RunRecordRepository()
    runs.add(
        RunRecord(
            id="run-1",
            run_date=date(2026, 6, 14),
            status=RunStatus.SUCCEEDED,
            started_at=datetime.now(),
            completed_at=datetime.now(),
        )
    )
    exported = export_runtime_metrics(runs)
    assert len(exported) == 1
    assert exported[0]["status"] == "succeeded"


def test_export_system_status_counts():
    runs = RunRecordRepository()
    runs.add(
        RunRecord(
            id="run-1",
            run_date=date(2026, 6, 14),
            status=RunStatus.SUCCEEDED,
            started_at=datetime.now(),
            completed_at=datetime.now(),
        )
    )
    store = KnowledgeStore()
    store._repo.add(_knowledge())

    status = export_system_status(runs, store, pipeline_run_date=date(2026, 6, 14))
    assert status["runs"] == 1
    assert status["succeeded"] == 1
    assert status["knowledge_objects"] == 1
    assert status["by_status"] == {"promoted": 1}
    assert status["pipeline_run_date"] == "2026-06-14"


def test_export_source_registry_matches_catalog_size():
    from agx_research.sources.catalog import seed_sources

    exported = export_source_registry()
    assert len(exported) == len(seed_sources())
    assert any(s["id"] == "stooq" for s in exported)


# --- write_dashboard_artifacts + validate_dashboard_artifacts round trip ---


def test_write_and_validate_round_trip(tmp_path):
    store = KnowledgeStore()
    store._repo.add(_knowledge())
    event_repo = EventRepository()
    runs = RunRecordRepository()
    runs.add(
        RunRecord(
            id="run-1",
            run_date=date(2026, 6, 14),
            status=RunStatus.SUCCEEDED,
            started_at=datetime.now(),
            completed_at=datetime.now(),
        )
    )

    counts = write_dashboard_artifacts(
        knowledge_store=store,
        event_repository=event_repo,
        runs=runs,
        memory=_memory(EventPlatform(repository=event_repo)),
        tickers=["COMI", "MFPC"],
        as_of=date(2026, 6, 14),
        out_dir=tmp_path,
    )

    for filename in ARTIFACT_FILENAMES:
        assert (tmp_path / filename).exists()

    validated = validate_dashboard_artifacts(tmp_path)
    assert validated == counts


def test_validate_missing_file_raises(tmp_path):
    with pytest.raises(DashboardArtifactError, match="missing"):
        validate_dashboard_artifacts(tmp_path)


def _write_valid_empty_artifacts(directory: Path) -> None:
    for filename in ARTIFACT_FILENAMES:
        if filename == "market_state.json":
            directory.joinpath(filename).write_text("null")
        elif filename == "system_status.json":
            directory.joinpath(filename).write_text('{"generated_at": "2026-06-14T00:00:00"}')
        else:
            directory.joinpath(filename).write_text("[]")


def test_validate_malformed_json_raises(tmp_path):
    _write_valid_empty_artifacts(tmp_path)
    (tmp_path / "knowledge.json").write_text("{not valid json")

    with pytest.raises(DashboardArtifactError, match="invalid JSON"):
        validate_dashboard_artifacts(tmp_path)


def test_validate_rejects_non_empty_patterns(tmp_path):
    _write_valid_empty_artifacts(tmp_path)
    (tmp_path / "patterns.json").write_text('[{"id": "fabricated"}]')

    with pytest.raises(DashboardArtifactError, match="expected empty"):
        validate_dashboard_artifacts(tmp_path)


def test_validate_rejects_schema_violation(tmp_path):
    _write_valid_empty_artifacts(tmp_path)
    # Missing every required KnowledgeObject field.
    (tmp_path / "knowledge.json").write_text('[{"id": "bad"}]')

    with pytest.raises(DashboardArtifactError):
        validate_dashboard_artifacts(tmp_path)


def test_pydantic_still_rejects_bad_knowledge_object_directly():
    with pytest.raises(ValidationError):
        KnowledgeObject.model_validate({"id": "bad"})
