from __future__ import annotations

from pathlib import Path

from agx_research.papers.paper import ResearchPaper
from agx_research.storage.repository import JsonFileRepository


class PaperRepository(JsonFileRepository[ResearchPaper]):
    def __init__(self, persist_path: Path | str | None = None):
        super().__init__(ResearchPaper, persist_path)
