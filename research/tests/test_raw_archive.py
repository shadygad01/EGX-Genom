import pytest

from agx_research.collectors.archive import RawArchive


def test_store_and_retrieve_roundtrip(tmp_path):
    archive = RawArchive(tmp_path)
    digest = archive.store(b"hello world")
    assert archive.retrieve(digest) == b"hello world"


def test_storing_identical_bytes_twice_is_a_noop(tmp_path):
    archive = RawArchive(tmp_path)
    d1 = archive.store(b"same content")
    path = archive._path_for(d1)
    mtime_before = path.stat().st_mtime_ns
    d2 = archive.store(b"same content")
    assert d1 == d2
    assert path.stat().st_mtime_ns == mtime_before  # never rewritten


def test_retrieve_unknown_hash_raises_keyerror(tmp_path):
    archive = RawArchive(tmp_path)
    with pytest.raises(KeyError):
        archive.retrieve("deadbeef")


def test_contains(tmp_path):
    archive = RawArchive(tmp_path)
    digest = archive.store(b"content")
    assert archive.contains(digest)
    assert not archive.contains("0" * 64)
