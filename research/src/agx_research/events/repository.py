from __future__ import annotations

from pathlib import Path

from agx_research.events.event import Event
from agx_research.storage.repository import JsonFileRepository


class EventRepository(JsonFileRepository[Event]):
    def __init__(self, persist_path: Path | str | None = None):
        super().__init__(Event, persist_path)
