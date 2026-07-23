"""Persists every hypothesis, regardless of outcome.

Including hypotheses that failed a gate and were never promoted: Principle 7
("knowledge continuously evolves") requires the research organization to
remember what it already tried, not just what survived — otherwise the same
falsified idea can be silently rediscovered and re-spend research effort
indefinitely.
"""

from __future__ import annotations

from pathlib import Path

from agx_research.hypotheses.hypothesis import Hypothesis
from agx_research.storage.repository import JsonFileRepository


class HypothesisRepository(JsonFileRepository[Hypothesis]):
    def __init__(self, persist_path: Path | str | None = None):
        super().__init__(Hypothesis, persist_path)
