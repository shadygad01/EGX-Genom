from __future__ import annotations

from pathlib import Path

from agx_research.genome.gene import Gene
from agx_research.storage.repository import JsonFileRepository


class GeneRepository(JsonFileRepository[Gene]):
    def __init__(self, persist_path: Path | str | None = None):
        super().__init__(Gene, persist_path)
