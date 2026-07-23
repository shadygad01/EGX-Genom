"""The UniverseProvider contract: source of index constituent membership.

Mirrors `agx_research.data.provider.DataProvider` deliberately — depend on
this interface, not on a specific static list or vendor feed. The only
implementation today (`StaticUniverseProvider`) wraps a fixed snapshot;
a live EGX30 membership feed is future work and should be added as a new
class implementing this same interface.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import date


class UniverseProvider(ABC):
    @abstractmethod
    def constituents(self, as_of: date) -> dict[str, str]:
        """Return {ticker: company_name} for index constituents as of `as_of`."""
