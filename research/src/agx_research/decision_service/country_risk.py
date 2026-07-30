"""Country & Macro Risk severity classification.

Merges what the Decision Evidence Matrix originally treated as two
questions (Q5 macro/FX backdrop, Q9 sovereign/country risk) into one
graduated axis, per `docs/ARCHITECTURE_ADVERSARIAL_REVIEW.md` R3: a CBE
reserve/currency drawdown is simultaneously a Q5 signal and a leading
indicator of a future Q9 rating action, so a hard boundary between "feeds
in normally" and "can override everything" was an artifact of the
write-up, not of the underlying evidence.

`CRISIS` requires a real, discrete sovereign rating action -- it is never
inferred from a currency/macro move alone. A currency move of any single
declared threshold is exactly the kind of number this platform's own
no-fabrication discipline says shouldn't be asserted as "crisis" without
corroborating discrete evidence (the same reasoning
`data.adjustments.py`'s split/dividend handling already applies: act on a
real, dated event, not an inferred one). `DETERIORATING` is reachable
from macro data alone, and from a rating outlook change short of an
actual downgrade.

No collector for `SovereignRatingAction` exists yet (`moodys_ratings`/
`sp_global_ratings`/`fitch_ratings` are `PLANNED` in `sources/catalog.py`
-- see `docs/ARCHITECTURE_ADVERSARIAL_REVIEW.md` roadmap step 5). Until
one does, `rating_actions` is always empty in a real run, so `CRISIS` is
honestly unreachable today -- a genuine capability gap, not a silently
lowered bar.
"""

from __future__ import annotations

from datetime import date, timedelta
from enum import Enum

from pydantic import BaseModel, Field

from agx_research.data.schemas import MacroObservation

# Named, shared constants -- `meta.readiness`'s country-risk-data-presence
# pre-check reuses these exact values rather than declaring its own copy
# that could silently drift from what `assess_country_risk` actually uses.
DEFAULT_CURRENCY_SERIES_ID = "EGP_USD"
MIN_OBSERVATIONS_FOR_CHANGE = 2


class CountryRiskSeverity(str, Enum):
    NORMAL = "normal"
    DETERIORATING = "deteriorating"
    CRISIS = "crisis"


class SovereignRatingAction(BaseModel):
    """One discrete rating-agency action. No real collector exists yet for
    this -- see this module's docstring; the shape is declared now so the
    Decision Service's override logic has something concrete to consume
    the moment `moodys_ratings`/`sp_global_ratings`/`fitch_ratings` go
    IMPLEMENTED, rather than inventing this contract later under time
    pressure."""

    agency: str
    action: str  # "downgrade" | "upgrade" | "affirm"
    outlook: str | None = None  # e.g. "negative" | "stable" | "positive"
    announced_at: date


class CountryRiskAssessment(BaseModel):
    as_of: date
    severity: CountryRiskSeverity
    reasons: list[str] = Field(default_factory=list)


def assess_country_risk(
    macro_series: dict[str, list[MacroObservation]],
    as_of: date,
    *,
    currency_series_id: str = DEFAULT_CURRENCY_SERIES_ID,
    deterioration_threshold: float = 0.05,
    rating_actions: list[SovereignRatingAction] | None = None,
    rating_action_lookback_days: int = 180,
) -> CountryRiskAssessment:
    """Classify country-risk severity as of `as_of`.

    `deterioration_threshold` (default 5%) applies to the cumulative
    percentage change of `currency_series_id` (EGP/USD by default -- the
    same series `agents.macro.MacroAgent` already names as a currency-
    exposure mechanism) across whatever observations are given; it is a
    declared, uncalibrated floor (new debt, same posture as
    `docs/TECHNICAL_DEBT.md`'s TD-6/TD-17/TD-20/TD-33 -- no real multi-year
    EGP crisis history exists in this platform yet to calibrate against).
    """
    reasons: list[str] = []
    severity = CountryRiskSeverity.NORMAL

    observations = sorted(
        macro_series.get(currency_series_id, []), key=lambda o: o.observation_date
    )
    if len(observations) >= MIN_OBSERVATIONS_FOR_CHANGE and observations[0].value != 0:
        change = (observations[-1].value - observations[0].value) / abs(observations[0].value)
        if abs(change) >= deterioration_threshold:
            severity = CountryRiskSeverity.DETERIORATING
            reasons.append(
                f"{currency_series_id} moved {change:+.2%} over the available window "
                f"(floor {deterioration_threshold:.0%})"
            )

    cutoff = as_of - timedelta(days=rating_action_lookback_days)
    recent_actions = [
        action
        for action in (rating_actions or [])
        if cutoff <= action.announced_at <= as_of
    ]
    for action in recent_actions:
        if action.action == "downgrade":
            severity = CountryRiskSeverity.CRISIS
            reasons.append(f"{action.agency} downgrade announced {action.announced_at.isoformat()}")
        elif action.outlook == "negative" and severity == CountryRiskSeverity.NORMAL:
            severity = CountryRiskSeverity.DETERIORATING
            reasons.append(
                f"{action.agency} negative outlook announced {action.announced_at.isoformat()}"
            )

    return CountryRiskAssessment(as_of=as_of, severity=severity, reasons=reasons)
