"""Stable, platform-wide domain constants.

Deliberately holds only concepts unlikely to change shape: the three time
horizons. Universe membership (which tickers count as EGX30) is volatile —
a real feed will replace today's static snapshot wholesale — and lives in
`agx_research.universe` instead, so that replacement doesn't touch this
module or anything that imports `Horizon` from it.
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
