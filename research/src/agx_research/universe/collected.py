"""A UniverseProvider backed by collected data, mirroring
`data.mock_provider.LocalCsvDataProvider`'s "collected data reads through
the same interface as everything else" pattern.

Reads `<data_dir>/universe/<INDEX>.csv` (columns: ticker,company_name,
as_of_date) -- the layout `collectors.service.CollectionService` writes
whenever a batch carries `IndexConstituent`s. Point-in-time correct: for a
given `as_of` date, returns the constituent set from the latest collected
snapshot at or before that date, never a later one -- the same no-look-
ahead guarantee every other point-in-time query in this platform gives.

Empty (never fabricated) when nothing has been collected yet, or when every
collected snapshot postdates `as_of`.
"""

from __future__ import annotations

import csv
from datetime import date
from pathlib import Path

from agx_research.universe.provider import UniverseProvider


class CollectedUniverseProvider(UniverseProvider):
    def __init__(self, data_dir: Path | str, *, index: str | None = None):
        self.data_dir = Path(data_dir)
        self.index = index

    def constituents(self, as_of: date) -> dict[str, str]:
        universe_dir = self.data_dir / "universe"
        paths = (
            [universe_dir / f"{self.index}.csv"]
            if self.index is not None
            else sorted(universe_dir.glob("*.csv"))
        )
        combined: dict[str, str] = {}
        for path in paths:
            if not path.exists():
                continue
            by_date: dict[date, dict[str, str]] = {}
            with path.open(newline="") as f:
                for row in csv.DictReader(f):
                    snapshot_date = date.fromisoformat(row["as_of_date"])
                    by_date.setdefault(snapshot_date, {})[row["ticker"]] = row["company_name"]
            eligible_dates = [d for d in by_date if d <= as_of]
            if eligible_dates:
                combined.update(by_date[max(eligible_dates)])
        return combined
