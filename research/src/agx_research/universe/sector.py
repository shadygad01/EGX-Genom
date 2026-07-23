"""Sector classification, mirroring UniverseProvider's shape and caveats.

The placeholder mapping below is scaffolding, not authoritative EGX sector
data — replace `StaticSectorProvider`'s default before any research
conclusion depends on sector membership, same caveat as
`universe.static.EGX30_UNIVERSE_PLACEHOLDER`.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import date


class SectorProvider(ABC):
    @abstractmethod
    def sector_of(self, ticker: str, as_of: date) -> str | None:
        """Return the sector classification for `ticker` as of `as_of`, or None if unknown."""


EGX_SECTOR_PLACEHOLDER: dict[str, str] = {
    "COMI": "Banks",
    "HRHO": "Financial Services",
    "TMGH": "Real Estate",
    "SWDY": "Industrial Goods",
    "EAST": "Consumer Goods",
    "ETEL": "Telecommunications",
    "ABUK": "Basic Resources",
    "ORWE": "Consumer Goods",
    "EFIH": "Financial Services",
    "MFPC": "Basic Resources",
}


class StaticSectorProvider(SectorProvider):
    def __init__(self, sectors: dict[str, str] | None = None):
        self._sectors = dict(sectors or EGX_SECTOR_PLACEHOLDER)

    def sector_of(self, ticker: str, as_of: date) -> str | None:
        return self._sectors.get(ticker)
