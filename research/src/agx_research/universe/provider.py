"""The sole contract for point-in-time investable-universe membership.

Callers depend on this interface, never on a parallel ticker list. Production
uses dated collected membership; the mapping implementation is only for
explicit tests or caller-supplied snapshots and has no built-in constituents.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import date

from pydantic import BaseModel, Field, model_validator


class UniverseArtifact(BaseModel):
    as_of: date
    count: int = Field(ge=0)
    tickers: list[str]
    constituents: dict[str, str]

    @model_validator(mode="after")
    def membership_is_consistent(self):
        expected = sorted(self.constituents)
        if self.count != len(expected) or self.tickers != expected:
            raise ValueError("count and tickers must exactly match constituents")
        return self


class UniverseProvider(ABC):
    @abstractmethod
    def constituents(self, as_of: date) -> dict[str, str]:
        """Return {ticker: company_name} for index constituents as of `as_of`."""


class MappingUniverseProvider(UniverseProvider):
    """Explicit in-memory provider for tests and caller-supplied snapshots.

    It deliberately has no default membership: production must use a collected,
    dated provider and tests must state their universe explicitly.
    """

    def __init__(self, constituents: dict[str, str]):
        self._constituents = dict(constituents)

    def constituents(self, as_of: date) -> dict[str, str]:
        return dict(self._constituents)
