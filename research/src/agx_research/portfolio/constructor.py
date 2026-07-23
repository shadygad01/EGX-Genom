"""Portfolio Intelligence: cross-ticker construction from recommendations.

Transparent, deterministic scoring and allocation — not portfolio
optimization (a real optimizer needs a covariance estimate that ten mock
days can't honestly support; named in TECHNICAL_DEBT):

- score(ticker) = confidence * expected_return / (expected_risk + eps),
  a risk-adjusted, confidence-discounted expectancy;
- only positive-score recommendations receive weight;
- weights are proportional to score, capped per position, remainder cash.

Every number in a PortfolioRecommendation traces to the underlying
Recommendations (and through them to knowledge, experiments, and data).
"""

from __future__ import annotations

from datetime import date, datetime

from pydantic import BaseModel, Field

from agx_research.domain.identifiers import new_id
from agx_research.domain.provenance import Provenance, ProvenanceRef
from agx_research.explainability import Explanation
from agx_research.meta.decision_engine import Recommendation

_EPS = 1e-9


class PortfolioPosition(BaseModel):
    ticker: str
    weight: float
    score: float
    expected_return: float
    expected_risk: float
    confidence: float
    supporting_knowledge_ids: list[str] = Field(default_factory=list)


class PortfolioRecommendation(BaseModel):
    id: str
    version: int = 1
    as_of: date
    positions: list[PortfolioPosition] = Field(default_factory=list)
    cash_weight: float
    explanation: Explanation
    provenance: Provenance


class PortfolioConstructor:
    def __init__(self, *, max_position_weight: float = 0.25):
        if not 0 < max_position_weight <= 1:
            raise ValueError("max_position_weight must be in (0, 1]")
        self.max_position_weight = max_position_weight

    def construct(
        self, recommendations: list[Recommendation], as_of: date
    ) -> PortfolioRecommendation:
        scored = []
        for rec in recommendations:
            score = (
                rec.confidence
                * rec.combined_expected_return
                / (rec.combined_expected_risk + _EPS)
            )
            if score > 0:
                scored.append((score, rec))
        scored.sort(key=lambda pair: (-pair[0], pair[1].ticker))

        total_score = sum(score for score, _ in scored)
        positions: list[PortfolioPosition] = []
        if total_score > 0:
            for score, rec in scored:
                weight = min(score / total_score, self.max_position_weight)
                positions.append(
                    PortfolioPosition(
                        ticker=rec.ticker,
                        weight=weight,
                        score=score,
                        expected_return=rec.combined_expected_return,
                        expected_risk=rec.combined_expected_risk,
                        confidence=rec.confidence,
                        supporting_knowledge_ids=rec.supporting_knowledge_ids,
                    )
                )
        cash_weight = max(0.0, 1.0 - sum(p.weight for p in positions))

        explanation = Explanation(
            why_this_stock=(
                f"{len(positions)} of {len(recommendations)} recommended tickers carry "
                "positive risk-adjusted, confidence-discounted expectancy."
                if positions
                else "No recommendation carried positive risk-adjusted expectancy; "
                "the portfolio holds cash rather than forcing positions."
            ),
            why_now=f"Constructed from recommendations as of {as_of.isoformat()}.",
            why_not_others=(
                "Tickers absent here either produced no evidence-backed recommendation "
                "at all, or scored non-positive after risk and confidence discounting."
            ),
            supporting_evidence=[
                f"{p.ticker}: score={p.score:.4f}, weight={p.weight:.3f}" for p in positions
            ],
            evidence_refs=[
                ProvenanceRef(kind="knowledge", ref_id=kid)
                for p in positions
                for kid in p.supporting_knowledge_ids
            ],
            invalidation_conditions=[
                "Any underlying recommendation's knowledge is retired or degrades.",
            ],
        )
        return PortfolioRecommendation(
            id=new_id("portfolio"),
            as_of=as_of,
            positions=positions,
            cash_weight=cash_weight,
            explanation=explanation,
            provenance=Provenance(
                produced_by="portfolio_constructor@1.0.0",
                produced_at=datetime.now(),
                inputs=[
                    ProvenanceRef(kind="recommendation", ref_id=rec.ticker)
                    for _, rec in scored
                ],
            ),
        )
