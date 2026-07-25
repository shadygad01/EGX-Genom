"""Backup/restore for the platform's JSON repository stores.

Creates a tar.gz of every .json store under a data directory plus a
sha256 manifest; restore verifies every hash before writing anything, and
refuses a partial/corrupted archive outright — a backup that can't prove
its integrity is treated as no backup at all.

Cloud object storage, retention policies, and scheduled backup execution
are deployment configuration (business-blocked: provider choice/payment);
this module is what such configuration invokes.
"""

from __future__ import annotations

import hashlib
import json
import tarfile
from datetime import datetime
from pathlib import Path

_MANIFEST_NAME = "MANIFEST.json"


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def create_backup(data_dir: Path | str, backup_path: Path | str) -> dict:
    """Archive every .json store under `data_dir` into `backup_path` (tar.gz)."""
    data_dir = Path(data_dir)
    backup_path = Path(backup_path)
    if not data_dir.is_dir():
        raise FileNotFoundError(f"Data directory {data_dir} does not exist")

    files = sorted(p for p in data_dir.rglob("*.json") if p.is_file())
    manifest = {
        "created_at": datetime.now().isoformat(),
        "data_dir": str(data_dir),
        # Tar member names are POSIX paths on every platform. Keeping the
        # manifest in that same canonical form makes Windows backups
        # verifiable and portable to Linux runners (and vice versa).
        "files": {p.relative_to(data_dir).as_posix(): _sha256(p) for p in files},
    }
    backup_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_bytes = json.dumps(manifest, indent=2, sort_keys=True).encode()

    with tarfile.open(backup_path, "w:gz") as tar:
        for p in files:
            tar.add(p, arcname=p.relative_to(data_dir).as_posix())
        info = tarfile.TarInfo(_MANIFEST_NAME)
        info.size = len(manifest_bytes)
        import io

        tar.addfile(info, io.BytesIO(manifest_bytes))
    return manifest


def verify_backup(backup_path: Path | str) -> dict:
    """Check every archived file against the manifest; raise on any mismatch."""
    backup_path = Path(backup_path)
    with tarfile.open(backup_path, "r:gz") as tar:
        manifest_member = tar.extractfile(_MANIFEST_NAME)
        if manifest_member is None:
            raise ValueError(f"{backup_path} has no {_MANIFEST_NAME}")
        manifest = json.loads(manifest_member.read())
        for rel_path, expected_hash in manifest["files"].items():
            member = tar.extractfile(rel_path)
            if member is None:
                raise ValueError(f"{backup_path} is missing {rel_path} listed in its manifest")
            actual = hashlib.sha256(member.read()).hexdigest()
            if actual != expected_hash:
                raise ValueError(
                    f"Integrity failure in {backup_path}: {rel_path} hash mismatch "
                    f"(expected {expected_hash}, got {actual})"
                )
    return manifest


def restore_backup(backup_path: Path | str, target_dir: Path | str) -> dict:
    """Verify then extract a backup into `target_dir`. Never partially restores."""
    backup_path = Path(backup_path)
    target_dir = Path(target_dir)
    manifest = verify_backup(backup_path)  # raises before anything is written

    target_dir.mkdir(parents=True, exist_ok=True)
    with tarfile.open(backup_path, "r:gz") as tar:
        for rel_path in manifest["files"]:
            destination = target_dir / rel_path
            destination.parent.mkdir(parents=True, exist_ok=True)
            member = tar.extractfile(rel_path)
            if member is None:  # verify_backup already checked; defensive against archive mutation
                raise ValueError(f"{backup_path} is missing {rel_path}")
            destination.write_bytes(member.read())
    return manifest
