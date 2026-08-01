"""Persistence for the Shadow Fund: one continuously-versioned entity.

Every trading day's `ShadowFundSnapshot` is a new *version* of the single
`"shadow_fund"` entity, not a new entity keyed by date -- so `history()`
is already the complete daily NAV/state time series for free, and
`latest()` is always today's current portfolio state. Follows the same
`storage.JsonFileRepository` composition every other versioned store in
this codebase uses (`knowledge/store.py`, `hypotheses/repository.py`,
`meta/decision_ledger.py`)."""

from __future__ import annotations

from pathlib import Path

from agx_research.shadow_fund.models import ShadowFundSnapshot
from agx_research.storage.repository import JsonFileRepository

SHADOW_FUND_ENTITY_ID = "shadow_fund"


class ShadowFundLedger(JsonFileRepository[ShadowFundSnapshot]):
    def __init__(self, persist_path: Path | str | None = None):
        super().__init__(ShadowFundSnapshot, persist_path)

    def latest_snapshot(self) -> ShadowFundSnapshot | None:
        return self.latest(SHADOW_FUND_ENTITY_ID)

    def daily_history(self) -> list[ShadowFundSnapshot]:
        """Every trading day's snapshot, oldest first."""
        return self.history(SHADOW_FUND_ENTITY_ID)

    def record(self, snapshot: ShadowFundSnapshot) -> ShadowFundSnapshot:
        previous = self.latest_snapshot()
        if previous is not None and snapshot.date <= previous.date:
            # A retry, manual rerun, or dashboard rebuild re-calling this
            # for a date already recorded must never insert a duplicate
            # NAV point -- `daily_history()` is the NAV time series, and a
            # duplicate would double-count that day's return everywhere it
            # feeds forward (risk metrics, attribution, the next day's
            # `prior_daily_returns`/`prior_nav_series`).
            raise ValueError(
                f"Shadow Fund snapshots must have strictly increasing dates "
                f"(latest is {previous.date}, got {snapshot.date})"
            )
        snapshot.version = (previous.version + 1) if previous is not None else 1
        return self.add(snapshot)
