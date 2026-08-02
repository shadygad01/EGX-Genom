"""Sector classification, mirroring UniverseProvider's shape and caveats.

`EGX_SECTOR_PLACEHOLDER` is scaffolding (10 hand-picked tickers only) --
prefer `CollectedSectorProvider`, which reads real, collected sector data
(`ChiefFinancialsCollector` derives it from Chief Capital's own site
category, e.g. ".../egx-egyptian-stock-exchange/banks/...") and falls back
to the placeholder only for a ticker nothing has ever collected. This
matters beyond display: `valuation.engine.FairValueEngine` uses `sector`
to decide sector-specific multiples and, more importantly, to exclude
DCF/EPV/EV-EBITDA models for banks (`_is_bank()`) -- a ticker with no
sector data silently skips that exclusion, which is exactly the kind of
real decision-quality gap this module's docstring used to warn about.
"""

from __future__ import annotations

import csv
from abc import ABC, abstractmethod
from datetime import date
from pathlib import Path

from pydantic import BaseModel


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


class SectorClassification(BaseModel):
    """One collector's real, evidenced sector classification for one
    ticker -- e.g. derived from Chief Capital's own site category, never
    guessed. `observed_date` is when the classification was collected
    (a sector rarely changes, but this keeps the record versioned/dated
    like every other collected fact in this platform)."""

    ticker: str
    sector: str
    source_id: str
    observed_date: date


class StaticSectorProvider(SectorProvider):
    def __init__(self, sectors: dict[str, str] | None = None):
        self._sectors = dict(sectors or EGX_SECTOR_PLACEHOLDER)

    def sector_of(self, ticker: str, as_of: date) -> str | None:
        return self._sectors.get(ticker)


class CollectedSectorProvider(SectorProvider):
    """Reads `<data_dir>/sectors/sector_membership.csv` (the layout
    `collectors.service.CollectionService` writes whenever a batch carries
    `SectorClassification`s), falling back to `fallback` (the static
    placeholder by default) for any ticker nothing has collected yet --
    never worse coverage than `StaticSectorProvider` alone, only better.

    Deliberately its own top-level directory, not `<data_dir>/universe/`:
    `universe.collected.CollectedUniverseProvider.constituents()` globs
    *every* CSV under `universe/` and requires each one to have an
    `as_of_date` column (the index-constituent format) -- a real, live-
    evidenced incident (2026-08-02 production run) confirmed this file
    sitting in `universe/` crashes every pipeline stage with
    `KeyError: 'as_of_date'` the moment `CollectedUniverseProvider` scans
    the directory. Never place a differently-shaped CSV inside
    `universe/` again."""

    def __init__(self, data_dir: Path | str, *, fallback: dict[str, str] | None = None):
        self.data_dir = Path(data_dir)
        self._fallback = dict(fallback if fallback is not None else EGX_SECTOR_PLACEHOLDER)
        self._sectors = self._load()

    def _load(self) -> dict[str, str]:
        path = self.data_dir / "sectors" / "sector_membership.csv"
        if not path.exists():
            return {}
        sectors: dict[str, str] = {}
        with path.open(newline="") as f:
            for row in csv.DictReader(f):
                sectors[row["ticker"]] = row["sector"]
        return sectors

    def sector_of(self, ticker: str, as_of: date) -> str | None:
        return self._sectors.get(ticker, self._fallback.get(ticker))
