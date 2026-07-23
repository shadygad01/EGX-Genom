from datetime import date
from pathlib import Path

from agx_research.data.mock_provider import MockDataProvider
from agx_research.data.snapshot import build_snapshot
from agx_research.data.snapshot_repository import DatasetSnapshotRepository

MOCK_ROOT = Path(__file__).resolve().parents[1] / "data" / "mock"


def test_persists_and_retrieves_a_snapshot():
    provider = MockDataProvider(MOCK_ROOT)
    snapshot = build_snapshot(
        provider, tickers=["COMI"], macro_series_ids=[], as_of=date(2026, 6, 14), lookback_days=30
    )
    repo = DatasetSnapshotRepository()
    repo.add(snapshot)

    assert repo.latest(snapshot.id) == snapshot


def test_persistence_roundtrip(tmp_path):
    persist_path = tmp_path / "snapshots.json"
    provider = MockDataProvider(MOCK_ROOT)
    snapshot = build_snapshot(
        provider, tickers=["COMI"], macro_series_ids=[], as_of=date(2026, 6, 14), lookback_days=30
    )
    repo = DatasetSnapshotRepository(persist_path=persist_path)
    repo.add(snapshot)

    reloaded = DatasetSnapshotRepository(persist_path=persist_path)
    assert reloaded.latest(snapshot.id).id == snapshot.id
    assert reloaded.latest(snapshot.id).price_history.keys() == snapshot.price_history.keys()
