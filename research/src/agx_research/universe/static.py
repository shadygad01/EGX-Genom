"""A fixed-snapshot UniverseProvider, standing in for a live EGX30 feed.

The constituent list below is a placeholder for scaffolding and tests. It
is NOT a live feed and must not be treated as authoritative market data —
replace `StaticUniverseProvider`'s default with a real, dated source before
any research conclusion depends on universe membership.
"""

from __future__ import annotations

from datetime import date

from agx_research.universe.provider import UniverseProvider

EGX30_UNIVERSE_PLACEHOLDER: dict[str, str] = {
    "COMI": "Commercial International Bank",
    "HRHO": "EFG Hermes Holding",
    "TMGH": "Talaat Moustafa Group",
    "SWDY": "Elsewedy Electric",
    "EAST": "Eastern Company",
    "ETEL": "Telecom Egypt",
    "ABUK": "Abu Qir Fertilizers",
    "ORWE": "Oriental Weavers",
    "EFIH": "e-Finance",
    "MFPC": "Misr Fertilizers Production Company (MOPCO)",
}


class StaticUniverseProvider(UniverseProvider):
    def __init__(self, constituents: dict[str, str] | None = None):
        self._constituents = dict(constituents or EGX30_UNIVERSE_PLACEHOLDER)

    def constituents(self, as_of: date) -> dict[str, str]:
        return dict(self._constituents)
