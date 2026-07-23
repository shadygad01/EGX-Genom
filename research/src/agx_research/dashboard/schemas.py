"""Schemas owned by the dashboard export layer itself.

Every other dashboard artifact (knowledge, events, recommendations,
market state, runtime metrics, source registry) reuses an existing
domain model verbatim -- this module exists only for the one artifact
that has no natural home elsewhere: a small computed summary of overall
platform health, mirroring what `cli.py`'s `status` subcommand already
prints.
"""

from __future__ import annotations

from datetime import date, datetime

from pydantic import BaseModel, Field


class DashboardSystemStatus(BaseModel):
    generated_at: datetime
    pipeline_run_date: date | None = None
    runs: int = 0
    succeeded: int = 0
    failed: int = 0
    knowledge_objects: int = 0
    by_status: dict[str, int] = Field(default_factory=dict)
