"""Outcome tracking: every live activation is followed forward so the
platform can eventually measure whether a validated pattern keeps working
after deployment — the whole point of separating `VALIDATED` from
`ACTIVE`/`WEAKENING` in the registry's lifecycle.

`update_outcomes()` fills in `actual_Nd`/`mfe`/`mae` incrementally as more
of a ticker's own subsequent bars become available in the panel — it never
back-fills a value using data the activation date itself couldn't have
seen (each horizon strictly reads `entry_idx+1 : entry_idx+1+horizon`,
the same forward-only slicing `targets.py` uses).
"""

from __future__ import annotations

from datetime import date
from pathlib import Path

from pydantic import BaseModel, Field

from agx_research.domain.identifiers import new_id
from agx_research.patterns.live import PatternActivation
from agx_research.patterns.panel import ResearchPanel
from agx_research.patterns.registry import Pattern
from agx_research.storage.repository import JsonFileRepository

OUTCOME_HORIZONS: tuple[tuple[int, str], ...] = (
    (5, "actual_5d"),
    (10, "actual_10d"),
    (20, "actual_20d"),
    (60, "actual_60d"),
)


class ActivationOutcome(BaseModel):
    id: str
    version: int = 1
    activation_id: str
    pattern_id: str
    ticker: str
    activation_time: date
    features_at_activation: dict[str, float] = Field(default_factory=dict)
    predicted_expectancy: float
    predicted_hit_rate: float
    actual_5d: float | None = None
    actual_10d: float | None = None
    actual_20d: float | None = None
    actual_60d: float | None = None
    mfe: float | None = None
    mae: float | None = None


class OutcomeRepository(JsonFileRepository[ActivationOutcome]):
    def __init__(self, persist_path: Path | str | None = None):
        super().__init__(ActivationOutcome, persist_path)


class OutcomeTracker:
    def __init__(self, repository: OutcomeRepository):
        self.repository = repository

    def record_activation(
        self,
        activation: PatternActivation,
        pattern: Pattern,
        *,
        features_at_activation: dict[str, float],
    ) -> ActivationOutcome:
        outcome = ActivationOutcome(
            id=new_id("activation_outcome"),
            activation_id=activation.id,
            pattern_id=activation.pattern_id,
            ticker=activation.ticker,
            activation_time=activation.as_of,
            features_at_activation=features_at_activation,
            predicted_expectancy=pattern.expectancy,
            predicted_hit_rate=pattern.hit_rate,
        )
        return self.repository.add(outcome)

    def update_outcomes(self, panel: ResearchPanel) -> list[ActivationOutcome]:
        updated: list[ActivationOutcome] = []
        for outcome in self.repository.all_latest():
            series = panel.series.get(outcome.ticker)
            if series is None:
                continue
            entry_idx = series.index_of(outcome.activation_time)
            if entry_idx is None:
                continue
            entry_price = series.adjusted_close[entry_idx]
            if entry_price == 0:
                continue

            changed: dict[str, float] = {}
            for horizon, field_name in OUTCOME_HORIZONS:
                if getattr(outcome, field_name) is not None:
                    continue
                if entry_idx + horizon < len(series.adjusted_close):
                    exit_price = series.adjusted_close[entry_idx + horizon]
                    changed[field_name] = (exit_price - entry_price) / entry_price

            available_horizon = len(series.adjusted_close) - 1 - entry_idx
            if available_horizon > 0:
                capped = min(60, available_horizon)
                window_highs = series.high[entry_idx + 1 : entry_idx + 1 + capped]
                window_lows = series.low[entry_idx + 1 : entry_idx + 1 + capped]
                if window_highs and window_lows:
                    changed["mfe"] = (max(window_highs) - entry_price) / entry_price
                    changed["mae"] = (min(window_lows) - entry_price) / entry_price

            if changed:
                revised = outcome.model_copy(update={**changed, "version": outcome.version + 1})
                self.repository.add(revised)
                updated.append(revised)
        return updated


__all__ = ["ActivationOutcome", "OUTCOME_HORIZONS", "OutcomeRepository", "OutcomeTracker"]
