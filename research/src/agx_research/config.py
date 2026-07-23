"""Platform-wide constants: time horizons and the EGX30 universe.

The EGX30 constituent list below is a placeholder snapshot for scaffolding
and tests. It is NOT a live feed and must not be treated as authoritative
market data — replace with a real, dated source before any research
conclusion depends on universe membership.
"""

from __future__ import annotations

from enum import Enum


class Horizon(str, Enum):
    """The three independent time horizons the platform optimizes simultaneously."""

    MICRO = "micro"  # 1-3 trading days
    SWING = "swing"  # 1-4 weeks
    INVESTMENT = "investment"  # 1-6 months


HORIZON_WINDOWS = {
    Horizon.MICRO: "1-3 trading days",
    Horizon.SWING: "1-4 weeks",
    Horizon.INVESTMENT: "1-6 months",
}

# Placeholder EGX30 snapshot (ticker -> company name). Update from an
# authoritative, dated EGX source before relying on this for real research.
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
