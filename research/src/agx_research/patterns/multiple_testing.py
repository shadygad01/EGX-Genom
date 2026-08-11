"""Multiple-testing control: this engine can generate thousands of
candidates per run, so a few statistically impressive results are expected
by chance alone. `benjamini_hochberg()` is the false-discovery-rate control
the mission requires; `TestingLedger` is the persisted, per-run record of
exactly how many hypotheses were tested and over what sample, so that
burden is never silently forgotten between runs — a pattern's
`Pattern.number_of_tests` field (see `registry.py`) always cites the
ledger it competed inside, not a bare, unexplained p-value.
"""

from __future__ import annotations

from datetime import date, datetime
from pathlib import Path

from pydantic import BaseModel, Field

from agx_research.storage.repository import JsonFileRepository


def benjamini_hochberg(p_values: list[float], *, fdr_alpha: float = 0.10) -> list[bool]:
    """Standard BH step-up procedure. Returns per-index accept/reject
    booleans in the *original* order of `p_values` (True = survives FDR
    control at `fdr_alpha`)."""
    n = len(p_values)
    if n == 0:
        return []
    ranked = sorted(range(n), key=lambda i: p_values[i])
    largest_accepted_rank = 0
    for rank, idx in enumerate(ranked, start=1):
        if p_values[idx] <= (rank / n) * fdr_alpha:
            largest_accepted_rank = rank
    accept = [False] * n
    for rank, idx in enumerate(ranked, start=1):
        if rank <= largest_accepted_rank:
            accept[idx] = True
    return accept


def complexity_penalty(p_value: float, complexity: int) -> float:
    """A conservative Bonferroni-style extra penalty scaled by a
    candidate's own condition count, on top of (never instead of) BH
    control across the whole candidate pool — discourages a 3-feature
    interaction from surviving on a raw p-value alone just because BH's
    pooled threshold happened to be generous that run. `complexity` is
    `PatternCandidate.complexity`; a single-feature candidate (complexity
    1) is unpenalized."""
    return min(1.0, p_value * complexity)


class TestingLedger(BaseModel):
    id: str
    version: int = 1
    run_id: str
    as_of: date
    hypotheses_tested: int
    discovery_sample_size: int
    validation_sample_size: int
    alpha: float = 0.05
    fdr_alpha: float = 0.10
    surviving_after_fdr: int = 0
    created_at: datetime = Field(default_factory=datetime.now)


class TestingLedgerRepository(JsonFileRepository[TestingLedger]):
    def __init__(self, persist_path: Path | str | None = None):
        super().__init__(TestingLedger, persist_path)


__all__ = [
    "TestingLedger",
    "TestingLedgerRepository",
    "benjamini_hochberg",
    "complexity_penalty",
]
