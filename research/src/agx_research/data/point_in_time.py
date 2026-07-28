"""Point-in-time availability: when a macro observation actually became
knowable, not just the period it describes.

`MacroObservation.observation_date` is the period a value covers (a
World Bank annual indicator is normalized to Dec 31 of its year --
`collectors/worldbank.py`; a FRED series carries its own real
observation date; CAPMAS/UN SDG likewise) -- never when it was actually
published. Treating a value as usable starting on its own period date is
real look-ahead bias: an annual figure is not knowable to a market
participant the moment the year ends, and `docs/PHASE_STATUS.md` already
documents the concrete case this closes -- "World Bank/UN SDG report
annually (often with a 1-2 year publication lag) and CAPMAS monthly."

`ASSUMED_PUBLICATION_LAG_DAYS` is a declared, source-*class* default lag,
not measured from real per-series publication metadata (this codebase has
never collected any, and no verified citation exists for a precise
per-source figure -- see TD-37). Values here are deliberately a
conservative *floor*, not a best guess at the real average: a national
statistics office cannot compile, review, and publish a release the
instant its reporting period ends, so a small non-zero floor is a safer
default than treating a period-end date as already-public knowledge --
but it is picked low enough to never contradict this codebase's own
already-live-verified evidence (a real World Bank observation was
confirmed collected and usable ~165 days after its period end during the
"Egyptian Live Data Sprint" phase; see `docs/PHASE_STATUS.md`). A source
with no declared lag defaults to 0 days (no assumed delay), which is also
correct for same-day/near-real-time sources like prices and daily FRED
series -- this function only ever *removes* not-yet-knowable observations
from a snapshot, it never adds fabricated ones.
"""

from __future__ import annotations

from datetime import date, timedelta

DEFAULT_PUBLICATION_LAG_DAYS = 0

ASSUMED_PUBLICATION_LAG_DAYS: dict[str, int] = {
    # Annual/periodic national-accounts releases: a conservative floor
    # (compilation/review takes at least this long), well under the
    # ~165-day-old point this codebase has already live-verified as
    # collectible from World Bank -- not a claim about the real average lag.
    "worldbank": 30,
    "undata": 30,
    "capmas": 30,
    # FRED series used here (oil, FX, yields, VIX) are same-day/next-day;
    # no assumed delay.
    "fred": 0,
}


def known_as_of(observation_date: date, *, source: str | None = None) -> date:
    """The earliest date a value describing `observation_date` could
    plausibly have been known, given `source`'s declared publication lag
    (0 days -- no assumed delay -- for an undeclared or `None` source)."""
    lag_days = ASSUMED_PUBLICATION_LAG_DAYS.get(source or "", DEFAULT_PUBLICATION_LAG_DAYS)
    return observation_date + timedelta(days=lag_days)


def is_knowable(observation_date: date, as_of: date, *, source: str | None = None) -> bool:
    """Whether a value describing `observation_date` was already knowable
    as of `as_of`, given `source`'s declared publication lag."""
    return known_as_of(observation_date, source=source) <= as_of
