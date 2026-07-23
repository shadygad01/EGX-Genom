from pydantic import BaseModel

from agx_research.storage.repository import JsonFileRepository


class DummyEntity(BaseModel):
    id: str
    version: int = 1
    label: str


def test_add_and_latest():
    repo = JsonFileRepository(DummyEntity)
    repo.add(DummyEntity(id="a", version=1, label="first"))
    repo.add(DummyEntity(id="a", version=2, label="second"))

    assert repo.latest("a").label == "second"
    assert repo.latest("does-not-exist") is None


def test_history_preserves_every_revision():
    repo = JsonFileRepository(DummyEntity)
    repo.add(DummyEntity(id="a", version=1, label="first"))
    repo.add(DummyEntity(id="a", version=2, label="second"))

    history = repo.history("a")
    assert [e.label for e in history] == ["first", "second"]


def test_all_latest_returns_one_per_entity():
    repo = JsonFileRepository(DummyEntity)
    repo.add(DummyEntity(id="a", version=1, label="a1"))
    repo.add(DummyEntity(id="a", version=2, label="a2"))
    repo.add(DummyEntity(id="b", version=1, label="b1"))

    latest_labels = sorted(e.label for e in repo.all_latest())
    assert latest_labels == ["a2", "b1"]


def test_persistence_roundtrip(tmp_path):
    persist_path = tmp_path / "dummy.json"
    repo = JsonFileRepository(DummyEntity, persist_path=persist_path)
    repo.add(DummyEntity(id="a", version=1, label="first"))
    repo.add(DummyEntity(id="a", version=2, label="second"))

    reloaded = JsonFileRepository(DummyEntity, persist_path=persist_path)
    assert reloaded.latest("a").label == "second"
    assert len(reloaded.history("a")) == 2
