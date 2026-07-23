"""RawArchive: content-addressed, write-once storage for binary payloads
(PDF, Excel, images) that don't fit `RawDocument.content_text` (which holds
text formats -- CSV/JSON/XML/RSS -- directly).

Every artifact is stored forever, keyed by its own sha256, under
`<archive_dir>/<hash[:2]>/<hash>.bin`. Storing identical bytes twice is a
no-op (the file already exists at that path) -- this *is* the "never
overwrite" rule, enforced by construction rather than by convention: there is
no code path in this class that opens an existing archived file for writing.
`RawDocument.is_binary` + `content_hash` (already the sha256 the document
carries) is the pointer from a document's metadata back into this store, so
no third id scheme is needed.
"""

from __future__ import annotations

import hashlib
from pathlib import Path


class RawArchive:
    def __init__(self, archive_dir: Path | str = "research/data/raw_archive"):
        self.archive_dir = Path(archive_dir)

    def store(self, content: bytes) -> str:
        digest = hashlib.sha256(content).hexdigest()
        path = self._path_for(digest)
        if not path.exists():
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(content)
        return digest

    def retrieve(self, digest: str) -> bytes:
        path = self._path_for(digest)
        if not path.exists():
            raise KeyError(f"No archived content for hash {digest}")
        return path.read_bytes()

    def contains(self, digest: str) -> bool:
        return self._path_for(digest).exists()

    def _path_for(self, digest: str) -> Path:
        return self.archive_dir / digest[:2] / f"{digest}.bin"
