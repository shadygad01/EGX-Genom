"""Phase 8: Investment Committee Validation.

Each named category (Macro/Sector/Quality/Value/Catalyst/Technical --
`RETURN_CONTRIBUTING_CATEGORIES`) is treated as an independent "committee"
casting an opinion via its real knowledge-object evidence. This engine
measures, across a real batch of tickers:

- **Agreement**: does the committee's own directional signal (positive/
  negative contribution to expected_return) agree with the sign of the
  final blended expected_return?
- **Disagreement**: the opposite -- a committee whose evidence pointed one
  way while the platform's final answer went the other.
- **Influence**: how often (via real `CounterfactualEngine` ablation, not
  an assumption) removing this committee's evidence actually changed the
  decision.

**Historical usefulness is honestly `ready_for_data`, not fabricated**:
answering "does this committee's opinion correlate with later realized
outcomes" needs `DecisionRecord` to know which categories contributed to
each recorded decision, and it doesn't (a real, named schema gap -- see
`docs/TECHNICAL_DEBT.md`). No correlation is invented in its place.
"""

from __future__ import annotations

from datetime import date

from pydantic import BaseModel, Field

from agx_research.investment_proof.attribution import DecisionAttributionEngine
from agx_research.investment_proof.categories import RETURN_CONTRIBUTING_CATEGORIES, Category
from agx_research.investment_proof.counterfactual import CounterfactualEngine
from agx_research.knowledge.schema import KnowledgeObject


class CommitteeStats(BaseModel):
    category: Category
    tickers_present: int = 0
    agrees_with_final_direction: int = 0
    disagrees_with_final_direction: int = 0
    decisive_count: int = 0
    historical_usefulness_status: str = "ready_for_data"

    @property
    def agreement_rate(self) -> float | None:
        return self.agrees_with_final_direction / self.tickers_present if self.tickers_present else None

    @property
    def decisive_rate(self) -> float | None:
        return self.decisive_count / self.tickers_present if self.tickers_present else None


class CommitteeValidationResult(BaseModel):
    as_of: date
    tickers_evaluated: int
    committees: list[CommitteeStats] = Field(default_factory=list)


class CommitteeValidationEngine:
    def __init__(self):
        self._attribution = DecisionAttributionEngine()
        self._counterfactual = CounterfactualEngine()

    def validate(
        self,
        tickers: list[str],
        as_of: date,
        knowledge_by_ticker: dict[str, list[KnowledgeObject]],
        *,
        latest_prices: dict[str, float] | None = None,
    ) -> CommitteeValidationResult:
        latest_prices = latest_prices or {}
        stats = {category: CommitteeStats(category=category) for category in RETURN_CONTRIBUTING_CATEGORIES}
        evaluated = 0

        for ticker in tickers:
            knowledge = knowledge_by_ticker.get(ticker, [])
            if not knowledge:
                continue
            reference_price = latest_prices.get(ticker)
            attribution = self._attribution.attribute(ticker, as_of, knowledge, reference_price=reference_price)
            if attribution.final_expected_return is None:
                continue
            evaluated += 1
            final_positive = attribution.final_expected_return > 0

            counterfactual = self._counterfactual.analyze(ticker, as_of, knowledge, reference_price=reference_price)
            decisive = set(counterfactual.decisive_categories)

            for contribution in attribution.return_contributions:
                s = stats[contribution.category]
                s.tickers_present += 1
                contribution_positive = contribution.contribution_to_expected_return > 0
                if contribution_positive == final_positive:
                    s.agrees_with_final_direction += 1
                else:
                    s.disagrees_with_final_direction += 1
                if contribution.category in decisive:
                    s.decisive_count += 1

        return CommitteeValidationResult(
            as_of=as_of, tickers_evaluated=evaluated, committees=sorted(stats.values(), key=lambda s: s.category.value)
        )


__all__ = ["CommitteeStats", "CommitteeValidationEngine", "CommitteeValidationResult"]
