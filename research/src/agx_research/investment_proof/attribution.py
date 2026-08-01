"""Phase 3: Decision Attribution.

For one ticker's INVESTMENT-horizon decision, answers "how much did each
layer contribute?" -- using the exact same computation
`KnowledgeWeightedHorizonModel`/`RecommendationService` already do, never
an approximation. Two kinds of contribution are reported, because the
model genuinely has two kinds:

- `return_contributions`: categories whose evidence additively composes
  `expected_return` (Macro/Sector/Quality/Catalyst/Technical from
  knowledge objects, plus Value from the fair-value blend) -- these are
  reported in real return units (e.g. "+0.03" means 3 percentage points
  of the final expected return), and are checked to actually sum back to
  the final expected_return (a real consistency falsification, not
  assumed).
- `modifiers`: Risk/Liquidity/Portfolio/Execution act as gates or
  multipliers on the decision, not additive return contributors -- each
  is reported as a factual description plus whatever real magnitude the
  underlying mechanism already computes (event-driven risk inflation,
  a liquidity-floor override, joint-portfolio weight normalization,
  entry/invalidation executability).
"""

from __future__ import annotations

from datetime import date

from pydantic import BaseModel, Field

from agx_research.config import Horizon
from agx_research.decision_service.liquidity_floor import DEFAULT_MIN_AVERAGE_TRADED_VALUE
from agx_research.horizons.knowledge_weighted import KnowledgeWeightedHorizonModel
from agx_research.investment_proof.categories import Category, category_for_agent
from agx_research.knowledge.schema import KnowledgeObject
from agx_research.meta.recommendation_service import FAIR_VALUE_INVESTMENT_WEIGHT
from agx_research.valuation import FairValueEngine


class CategoryContribution(BaseModel):
    category: Category
    knowledge_ids: list[str] = Field(default_factory=list)
    contribution_to_expected_return: float
    detail: str


class Modifier(BaseModel):
    category: Category
    detail: str
    magnitude: float | None = None


class AttributionResult(BaseModel):
    ticker: str
    as_of: date
    horizon: Horizon
    pre_value_expected_return: float | None = None
    final_expected_return: float | None = None
    return_contributions: list[CategoryContribution] = Field(default_factory=list)
    unattributed_knowledge_ids: list[str] = Field(default_factory=list)
    #: Real consistency check: sum(return_contributions) should equal
    #: final_expected_return. A nonzero residual here means either an
    #: unmapped evidence source or an arithmetic drift worth investigating
    #: -- never silently absorbed.
    attribution_residual: float | None = None
    modifiers: list[Modifier] = Field(default_factory=list)


class DecisionAttributionEngine:
    def __init__(self, *, fair_value_engine: FairValueEngine | None = None):
        self.fair_value_engine = fair_value_engine
        self._model = KnowledgeWeightedHorizonModel(Horizon.INVESTMENT)

    def attribute(
        self,
        ticker: str,
        as_of: date,
        knowledge: list[KnowledgeObject],
        *,
        reference_price: float | None = None,
        sector: str | None = None,
        illiquid: bool = False,
        isolated_weight_share: float | None = None,
        final_target_weight: float | None = None,
    ) -> AttributionResult:
        prediction = self._model.predict(ticker, as_of, knowledge)
        result = AttributionResult(ticker=ticker, as_of=as_of, horizon=Horizon.INVESTMENT)
        if prediction is None:
            return result  # no evidence at all -- nothing to attribute, honestly

        result.pre_value_expected_return = prediction.expected_return
        relevant = {k.id: k for k in knowledge if k.id in prediction.supporting_knowledge_ids}
        total_weight = sum(k.confidence for k in relevant.values())

        by_category: dict[Category, list[KnowledgeObject]] = {}
        unattributed: list[str] = []
        for knowledge_id, k in relevant.items():
            category = category_for_agent(k.creator_agent)
            if category is None:
                unattributed.append(knowledge_id)
                continue
            by_category.setdefault(category, []).append(k)
        result.unattributed_knowledge_ids = unattributed

        knowledge_weight = 1.0
        value_return = None
        if self.fair_value_engine is not None and reference_price is not None and reference_price > 0:
            valuation = self.fair_value_engine.value(ticker, as_of, sector=sector)
            if valuation is not None:
                implied = max(-1.0, min(2.0, valuation.weighted_fair_value / reference_price - 1))
                value_return = FAIR_VALUE_INVESTMENT_WEIGHT * implied
                knowledge_weight = 1.0 - FAIR_VALUE_INVESTMENT_WEIGHT
                result.return_contributions.append(
                    CategoryContribution(
                        category=Category.VALUE,
                        contribution_to_expected_return=value_return,
                        detail=(
                            f"Fair value {valuation.weighted_fair_value:.2f} vs. reference price "
                            f"{reference_price:.2f} implies {implied:+.2%}; blended at "
                            f"{FAIR_VALUE_INVESTMENT_WEIGHT:.0%} weight."
                        ),
                    )
                )

        for category, objects in sorted(by_category.items(), key=lambda item: item[0].value):
            category_weight = sum(k.confidence for k in objects)
            raw_contribution = sum(k.confidence * k.expected_return for k in objects) / total_weight
            result.return_contributions.append(
                CategoryContribution(
                    category=category,
                    knowledge_ids=[k.id for k in objects],
                    contribution_to_expected_return=raw_contribution * knowledge_weight,
                    detail=(
                        f"{len(objects)} knowledge object(s), confidence-weighted share "
                        f"{category_weight / total_weight:.1%} of the pre-value prediction."
                    ),
                )
            )

        result.final_expected_return = (
            (knowledge_weight * prediction.expected_return) + (value_return or 0.0)
            if value_return is not None
            else prediction.expected_return
        )
        result.attribution_residual = result.final_expected_return - sum(
            c.contribution_to_expected_return for c in result.return_contributions
        )

        result.modifiers = self._modifiers(
            prediction.expected_risk,
            illiquid=illiquid,
            isolated_weight_share=isolated_weight_share,
            final_target_weight=final_target_weight,
            reference_price=reference_price,
        )
        return result

    @staticmethod
    def _modifiers(
        expected_risk: float,
        *,
        illiquid: bool,
        isolated_weight_share: float | None,
        final_target_weight: float | None,
        reference_price: float | None,
    ) -> list[Modifier]:
        modifiers = [
            Modifier(
                category=Category.RISK,
                detail=f"Model expected_risk for this horizon: {expected_risk:.2%}.",
                magnitude=expected_risk,
            ),
            Modifier(
                category=Category.LIQUIDITY,
                detail=(
                    "Below the liquidity floor "
                    f"(EGP {DEFAULT_MIN_AVERAGE_TRADED_VALUE:,.0f} average daily traded value) -- "
                    "target weight forced to zero regardless of thesis strength."
                    if illiquid
                    else "Above the liquidity floor -- no override applied."
                ),
                magnitude=1.0 if illiquid else 0.0,
            ),
            Modifier(
                category=Category.EXECUTION,
                detail=(
                    "A real reference price is available -- an executable entry level exists."
                    if reference_price is not None
                    else "No reference price available -- no executable entry level exists (forces ABSTAIN if BUY_CANDIDATE)."
                ),
                magnitude=1.0 if reference_price is not None else 0.0,
            ),
        ]
        if isolated_weight_share is not None and final_target_weight is not None:
            modifiers.append(
                Modifier(
                    category=Category.PORTFOLIO,
                    detail=(
                        f"Isolated proportional share {isolated_weight_share:.2%} normalized to final weight "
                        f"{final_target_weight:.2%} once every other position in the portfolio is considered "
                        "jointly."
                    ),
                    magnitude=final_target_weight - isolated_weight_share,
                )
            )
        else:
            modifiers.append(
                Modifier(
                    category=Category.PORTFOLIO,
                    detail="Not evaluated as part of a portfolio (isolated_weight_share/final_target_weight not supplied).",
                )
            )
        return modifiers


__all__ = ["AttributionResult", "CategoryContribution", "DecisionAttributionEngine", "Modifier"]
