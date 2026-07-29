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


def test_empty_persisted_file_degrades_to_cold_start_instead_of_crashing(tmp_path):
    """Regression test for a real failure: a CI restore step that redirects
    `git show <ref>:<path>` straight to `> <path>` truncates the
    destination to 0 bytes even when `<path>` doesn't exist yet at `<ref>`
    and the command fails (`.github/workflows/discovery.yml`'s first live
    run against a brand-new tracked file crashed exactly this way --
    `json.JSONDecodeError: Expecting value: line 1 column 1`).
    """
    persist_path = tmp_path / "empty.json"
    persist_path.write_text("")

    repo = JsonFileRepository(DummyEntity, persist_path=persist_path)
    assert repo.all_latest() == []
    assert repo.latest("a") is None

    repo.add(DummyEntity(id="a", version=1, label="first"))
    assert JsonFileRepository(DummyEntity, persist_path=persist_path).latest("a").label == "first"


def test_whitespace_only_persisted_file_also_degrades_to_cold_start(tmp_path):
    persist_path = tmp_path / "whitespace.json"
    persist_path.write_text("   \n")

    repo = JsonFileRepository(DummyEntity, persist_path=persist_path)
    assert repo.all_latest() == []
