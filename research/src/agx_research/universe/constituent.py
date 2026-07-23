"""IndexConstituent: a single (index, ticker) membership fact as of a date.

Carrying `as_of_date` per row (rather than overwriting a single current
snapshot) lets `CollectedUniverseProvider` answer "who was in EGX30 on
date X" without look-ahead bias, the same guarantee every other point-in-
time query in this platform (`DatasetSnapshot`, adjusted returns) already
gives -- a constituent added or dropped after `as_of` must not silently
change what research run against an earlier date sees.
"""

from __future__ import annotations

from datetime import date

from pydantic import BaseModel


class IndexConstituent(BaseModel):
    index: str  # e.g. "EGX30", "EGX70"
    ticker: str
    company_name: str
    as_of_date: date
