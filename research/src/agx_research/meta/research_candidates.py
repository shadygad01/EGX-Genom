"""Quantitative research candidates that are not yet executable decisions.

A fair-value gap is useful to an investment manager even when macro, FX,
liquidity, freshness, or evidence gates prevent a buy decision. This module
makes that distinction explicit instead of hiding the candidate behind an
empty recommendations artifact.
"""

from __future__ import annotations

from datetime import date

from pydantic import BaseModel, Field

from agx_research.meta.readiness import DecisionReadiness


class ResearchCandidate(BaseModel):
    ticker: str
    as_of: date
    latest_price_date: date | None = None
    current_price: float
    target_price: float
    expected_return: float
    discount_pct: float
    time_to_target_days: int = 252
    confidence: float = 0.0
    decision: str = "watchlist"
    status: str = "research_candidate"
    included_models: list[str] = Field(default_factory=list)
    market_pe: float | None = None
    price_to_book: float | None = None
    dcf_per_share: float | None = None
    price_observations: int = 0
    financial_periods: int = 0
    macro_series: int = 0
    primary_blockers: list[str] = Field(default_factory=list)
    next_actions: list[str] = Field(default_factory=list)


def _confidence(row: DecisionReadiness) -> float:
    """Report evidence completeness; never convert it into a buy signal."""
    valuation = row.valuation
    model_score = min(len(valuation.included_models) / 3, 1.0) if valuation else 0.0
    price_score = min(row.price_observations / 252, 1.0)
    macro_score = min(row.macro_series / 3, 1.0)
    financial_score = min(row.financial_periods / 3, 1.0)
    return round(0.50 * model_score + 0.20 * price_score + 0.15 * macro_score + 0.15 * financial_score, 4)


def build_research_candidates(rows: list[DecisionReadiness]) -> list[ResearchCandidate]:
    """Build ranked undervaluation candidates while preserving execution gates.

    A candidate requires a current price and a multi-model fair value below
    which the market price trades. It is explicitly a watchlist item when the
    readiness gate is not executable; no blocker is discarded or weakened.
    """
    candidates: list[ResearchCandidate] = []
    for row in rows:
        valuation = row.valuation
        if (
            valuation is None
            or valuation.current_price is None
            or valuation.weighted_fair_value is None
            or row.price_vs_fair_value_pct is None
            or row.price_vs_fair_value_pct >= 0
        ):
            continue
        candidates.append(
            ResearchCandidate(
                ticker=row.ticker,
                as_of=row.as_of,
                latest_price_date=row.latest_price_date,
                current_price=valuation.current_price,
                target_price=valuation.weighted_fair_value,
                expected_return=round(valuation.weighted_fair_value / valuation.current_price - 1, 4),
                discount_pct=round(-row.price_vs_fair_value_pct, 4),
                confidence=_confidence(row),
                included_models=valuation.included_models,
                market_pe=valuation.market_pe,
                price_to_book=valuation.price_to_book,
                dcf_per_share=valuation.dcf_per_share,
                price_observations=row.price_observations,
                financial_periods=row.financial_periods,
                macro_series=row.macro_series,
                primary_blockers=row.blockers,
                next_actions=row.next_actions,
            )
        )
    return sorted(candidates, key=lambda candidate: (candidate.expected_return, candidate.confidence), reverse=True)
