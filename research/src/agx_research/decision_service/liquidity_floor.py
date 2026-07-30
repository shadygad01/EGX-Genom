"""Liquidity/tradability hard floor.

`docs/ARCHITECTURE_ADVERSARIAL_REVIEW.md` R4: a ticker below this floor
caps out at target weight zero regardless of how strong its thesis reads
-- illiquidity is a hard constraint on executability (you cannot buy or
sell meaningful size in a thin EGX name without moving the price against
yourself), not merely weighted evidence. This earns the same override-
class treatment the country-risk crisis rung already gets (Section 1.1/
1.6 of that review named this gap: the Evidence Matrix folded liquidity
into Q6 as ordinary weighted evidence, when it is structurally more like
Q9's override).
"""

from __future__ import annotations

import statistics

from agx_research.data.snapshot import DatasetSnapshot

# Declared, uncalibrated floor (EGP average daily traded value) -- same
# posture as `docs/TECHNICAL_DEBT.md`'s TD-6/TD-17/TD-20/TD-33 (see TD-46).
# A single named constant so every caller (`meta.readiness`, `cli.py`'s
# `decide` subcommand) shares one number instead of each declaring its own
# copy that could silently drift.
DEFAULT_MIN_AVERAGE_TRADED_VALUE = 1_000_000.0


def compute_illiquid_tickers(
    snapshot: DatasetSnapshot,
    *,
    min_average_traded_value: float = DEFAULT_MIN_AVERAGE_TRADED_VALUE,
) -> set[str]:
    """A ticker whose average `close * volume` over the snapshot's price
    history falls below `min_average_traded_value` is illiquid.

    Declared, uncalibrated floor -- same posture as
    `docs/TECHNICAL_DEBT.md`'s TD-6/TD-17/TD-20/TD-33: no real multi-year
    EGX liquidity history exists in this platform yet to calibrate a real
    threshold against. A ticker with no price history at all is treated
    as illiquid -- never assumed tradable from an absence of data.
    """
    illiquid: set[str] = set()
    for ticker in snapshot.tickers:
        bars = snapshot.price_history.get(ticker, [])
        if not bars:
            illiquid.add(ticker)
            continue
        traded_values = [bar.close * bar.volume for bar in bars]
        if statistics.fmean(traded_values) < min_average_traded_value:
            illiquid.add(ticker)
    return illiquid
