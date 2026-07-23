import json
import tarfile
from datetime import date

import pytest

from agx_research.cli import main
from agx_research.infrastructure.backup import create_backup, restore_backup, verify_backup


def _make_data_dir(tmp_path):
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    (data_dir / "knowledge.json").write_text(json.dumps({"k": [{"id": "k", "version": 1}]}))
    (data_dir / "nested").mkdir()
    (data_dir / "nested" / "runs.json").write_text(json.dumps({}))
    return data_dir


def test_backup_verify_restore_roundtrip(tmp_path):
    data_dir = _make_data_dir(tmp_path)
    backup_path = tmp_path / "backup.tar.gz"

    manifest = create_backup(data_dir, backup_path)
    assert set(manifest["files"]) == {"knowledge.json", "nested/runs.json"}
    assert verify_backup(backup_path)["files"] == manifest["files"]

    target = tmp_path / "restored"
    restore_backup(backup_path, target)
    assert (target / "knowledge.json").read_text() == (data_dir / "knowledge.json").read_text()
    assert (target / "nested" / "runs.json").exists()


def test_verify_rejects_tampered_backup(tmp_path):
    data_dir = _make_data_dir(tmp_path)
    backup_path = tmp_path / "backup.tar.gz"
    create_backup(data_dir, backup_path)

    # Rebuild the archive with a corrupted file but the original manifest.
    tampered = tmp_path / "tampered.tar.gz"
    with tarfile.open(backup_path, "r:gz") as src, tarfile.open(tampered, "w:gz") as dst:
        for member in src.getmembers():
            payload = src.extractfile(member).read()
            if member.name == "knowledge.json":
                payload = b'{"k": "corrupted"}'
                member.size = len(payload)
            import io

            dst.addfile(member, io.BytesIO(payload))

    with pytest.raises(ValueError, match="hash mismatch"):
        verify_backup(tampered)
    # And restore refuses before writing anything.
    with pytest.raises(ValueError):
        restore_backup(tampered, tmp_path / "should_not_exist")
    assert not (tmp_path / "should_not_exist").exists()


def test_cli_run_and_status_and_backup(tmp_path, capsys):
    data_dir = tmp_path / "agx_data"
    base = ["--data-dir", str(data_dir)]

    assert main([*base, "run", "--date", date(2026, 6, 14).isoformat()]) == 0
    out = capsys.readouterr().out
    assert "2026-06-14 succeeded" in out

    assert main([*base, "status"]) == 0
    status = json.loads(capsys.readouterr().out)
    assert status["runs"] == 1 and status["succeeded"] == 1

    backup_path = tmp_path / "b.tar.gz"
    assert main([*base, "backup", "--output", str(backup_path)]) == 0
    capsys.readouterr()
    assert main([*base, "verify-backup", "--input", str(backup_path)]) == 0
    assert "OK" in capsys.readouterr().out
