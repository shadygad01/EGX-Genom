"""Transparent market-wide macro overlay for portfolio exposure."""

from __future__ import annotations

from datetime import date
from typing import Literal

from pydantic import BaseModel, Field

from agx_research.data.schemas import MacroObservation


class MacroContribution(BaseModel):
    factor: str
    series_id: str
    importance_weight: float
    effective_weight: float
    signal: Literal[-1, 0, 1]
    latest_value: float
    previous_value: float
    latest_date: date
    change_pct: float
    impact: Literal["supportive", "neutral", "adverse"]


class MacroDecisionOverlay(BaseModel):
    as_of: date
    decision: Literal["supportive", "cautious", "defensive", "insufficient_data"]
    score: float
    exposure_multiplier: float
    available_weight: float
    contributions: list[MacroContribution] = Field(default_factory=list)
    rationale: str


FACTOR_SPECS = [
    ("currency", ("egypt_official_fx_egp_per_usd", "EGP_USD"), 0.20, -1),
    ("inflation", ("egypt_total_cpi_yoy", "egypt_urban_cpi_yoy", "egypt_cpi_inflation"), 0.20, -1),
    ("interest_rates", ("egypt_lending_rate",), 0.15, -1),
    ("fx_reserves", ("egypt_net_international_reserves_usd", "egypt_total_reserves_usd"), 0.15, 1),
    ("external_debt", ("egypt_external_debt_usd",), 0.15, -1),
    ("current_account", ("egypt_current_account_pct_gdp",), 0.10, 1),
    ("real_growth", ("egypt_real_gdp_growth",), 0.05, 1),
]


def _observations_for(macro_series, aliases):
    for series_id in aliases:
        observations = sorted(macro_series.get(series_id, []), key=lambda row: row.observation_date)
        if len(observations) >= 2:
            return series_id, observations
    return None


def assess_macro_overlay(
    macro_series: dict[str, list[MacroObservation]], as_of: date
) -> MacroDecisionOverlay:
    contributions: list[MacroContribution] = []
    for factor, aliases, weight, favorable_direction in FACTOR_SPECS:
        resolved = _observations_for(macro_series, aliases)
        if resolved is None:
            continue
        series_id, observations = resolved
        previous, latest = observations[-2:]
        if previous.value == 0:
            continue
        change = (latest.value - previous.value) / abs(previous.value)
        raw_direction = 1 if change > 0 else -1 if change < 0 else 0
        signal = raw_direction * favorable_direction
        contributions.append(MacroContribution(
            factor=factor, series_id=series_id, importance_weight=weight,
            effective_weight=0.0, signal=signal, latest_value=latest.value,
            previous_value=previous.value, latest_date=latest.observation_date,
            change_pct=change,
            impact="supportive" if signal > 0 else "adverse" if signal < 0 else "neutral",
        ))
    available_weight = sum(row.importance_weight for row in contributions)
    if available_weight == 0:
        return MacroDecisionOverlay(
            as_of=as_of, decision="insufficient_data", score=0.0,
            exposure_multiplier=1.0, available_weight=0.0,
            rationale="No factor had two comparable observations; portfolio exposure was not adjusted.",
        )
    for row in contributions:
        row.effective_weight = row.importance_weight / available_weight
    score = sum(row.effective_weight * row.signal for row in contributions)
    if score > 0.25:
        decision, multiplier = "supportive", 1.0
    elif score >= -0.25:
        decision, multiplier = "cautious", 0.75
    else:
        decision, multiplier = "defensive", 0.50
    return MacroDecisionOverlay(
        as_of=as_of, decision=decision, score=score,
        exposure_multiplier=multiplier, available_weight=available_weight,
        contributions=contributions,
        rationale=f"Macro score {score:+.2f}; equity exposure is capped at {multiplier:.0%} and the remainder stays cash.",
    )
