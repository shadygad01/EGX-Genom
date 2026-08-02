import json
import io
import sys
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

    # This is a CLI-plumbing test (run/status/backup), not a live-collection
    # test -- unit tests never touch the network (see docs/DATA_ACQUISITION.md),
    # so it must pass an explicit testing-only mode rather than rely on the
    # CLI's production default (`--mode live`, which needs real egress).
    assert main([*base, "run", "--date", date(2026, 6, 14).isoformat(), "--mode", "mock"]) == 0
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


def test_cli_publication_status_reports_early_maturity_with_no_history(tmp_path, capsys):
    # Reports System Maturity (project owner direction, 2026-08-02):
    # informational only, always exits 0 -- nothing left to "fail closed"
    # on, since publishing is governed per-decision by meta.decision_quality,
    # not by this command.
    data_dir = tmp_path / "empty_production_data"

    assert main([
        "--data-dir",
        str(data_dir),
        "publication-status",
        "--date",
        "2026-07-28",
    ]) == 0

    report = json.loads(capsys.readouterr().out)
    assert report["level"] == "early"
    assert report["governance_reviewed"] is False
    assert not data_dir.exists(), "publication-status must not mutate the inspected directory"


def test_cli_publication_status_ignores_malformed_governance_review(tmp_path, capsys):
    # An optional legal_publication_approval.json can only ever raise the
    # reported level -- a malformed one is treated the same as a missing
    # one (no real track record exists here either way, so this must
    # still report "early", never error out or block).
    data_dir = tmp_path / "invalid_production_data"
    data_dir.mkdir()
    (data_dir / "legal_publication_approval.json").write_text("{}", encoding="utf-8")

    assert main([
        "--data-dir",
        str(data_dir),
        "publication-status",
        "--date",
        "2026-07-28",
    ]) == 0

    report = json.loads(capsys.readouterr().out)
    assert report["level"] == "early"
    assert report["governance_reviewed"] is False


def test_cli_publication_status_writes_utf8_on_windows_code_page(tmp_path, monkeypatch):
    raw_output = io.BytesIO()
    windows_stdout = io.TextIOWrapper(raw_output, encoding="cp1252")
    monkeypatch.setattr(sys, "stdout", windows_stdout)

    assert main([
        "--data-dir",
        str(tmp_path / "empty_data"),
        "publication-status",
        "--date",
        "2026-07-28",
    ]) == 0

    windows_stdout.flush()
    report = json.loads(raw_output.getvalue().decode("utf-8"))
    assert report["level"] == "early"
