"""The Runtime Engine: scheduled execution of the daily research pipeline.

In-process, deterministic, replayable. `run_range()` walks a date span in
order with per-day failure isolation: one day's exception is recorded as a
FAILED RunRecord and the range continues — a bad data day must never halt
the research organization. Non-trading days are recorded as SKIPPED (with
the holiday name when known) rather than silently absent, so a replayed
range always produces the same, complete run ledger.

An OS-level scheduler (cron/systemd/cloud) triggering `run_day` is
deployment configuration (System 18 / a business-infrastructure decision),
not engineering logic — the engine is what such a trigger calls.
"""

from __future__ import annotations

from datetime import date, datetime, timedelta
from enum import Enum
from pathlib import Path

from pydantic import BaseModel

from agx_research.domain.identifiers import new_id
from agx_research.market_memory.calendar import StaticEGXCalendar, TradingCalendar
from agx_research.orchestration.pipeline import DailyResearchPipeline, PipelineResult
from agx_research.storage.repository import JsonFileRepository


class RunStatus(str, Enum):
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    SKIPPED_NON_TRADING = "skipped_non_trading"


class RunRecord(BaseModel):
    id: str
    version: int = 1
    run_date: date
    status: RunStatus
    session_id: str | None = None
    hypotheses: int = 0
    promoted: int = 0
    error: str | None = None
    notes: str = ""
    started_at: datetime
    completed_at: datetime


class RunRecordRepository(JsonFileRepository[RunRecord]):
    def __init__(self, persist_path: Path | str | None = None):
        super().__init__(RunRecord, persist_path)


class RuntimeEngine:
    def __init__(
        self,
        pipeline: DailyResearchPipeline,
        *,
        calendar: TradingCalendar | None = None,
        run_records: RunRecordRepository | None = None,
    ):
        self.pipeline = pipeline
        self.calendar = calendar or StaticEGXCalendar()
        self.run_records = run_records or RunRecordRepository()

    def run_day(self, as_of: date) -> RunRecord:
        started_at = datetime.now()
        if not self.calendar.is_trading_day(as_of):
            holiday = self.calendar.holiday_name(as_of)
            record = RunRecord(
                id=new_id("run"),
                run_date=as_of,
                status=RunStatus.SKIPPED_NON_TRADING,
                notes=f"Non-trading day{f' ({holiday})' if holiday else ' (weekend)'}",
                started_at=started_at,
                completed_at=datetime.now(),
            )
            return self.run_records.add(record)

        try:
            result: PipelineResult = self.pipeline.run(as_of)
        except Exception as exc:  # per-day failure isolation, recorded not raised
            record = RunRecord(
                id=new_id("run"),
                run_date=as_of,
                status=RunStatus.FAILED,
                error=f"{type(exc).__name__}: {exc}",
                started_at=started_at,
                completed_at=datetime.now(),
            )
            return self.run_records.add(record)

        record = RunRecord(
            id=new_id("run"),
            run_date=as_of,
            status=RunStatus.SUCCEEDED,
            session_id=result.session.id,
            hypotheses=len(result.outcomes),
            promoted=sum(1 for o in result.outcomes if o.promoted),
            started_at=started_at,
            completed_at=datetime.now(),
        )
        return self.run_records.add(record)

    def run_range(self, start: date, end: date) -> list[RunRecord]:
        if end < start:
            raise ValueError("end must be on or after start")
        records = []
        current = start
        while current <= end:
            records.append(self.run_day(current))
            current += timedelta(days=1)
        return records
