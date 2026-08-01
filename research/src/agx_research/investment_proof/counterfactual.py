"""Phase 4: Counterfactual Analysis.

"What changes if Macro disappears? If Value disappears? ..." -- answered
by real ablation, not a sensitivity estimate: remove every knowledge
object belonging to one category and literally recompute the prediction
and decision with the exact same real code
(`KnowledgeWeightedHorizonModel.predict()` + `MetaDecisionEngine.decide()`)
the platform already uses for a real decision. Whichever category's
removal actually flips the action is the evidence that truly drives the
decision -- not a coefficient or an assumption about importance.
"""

from __future__ import annotations

from datetime import date

from pydantic import BaseModel, Field

from agx_research.config import Horizon
from agx_research.horizons.knowledge_weighted import KnowledgeWeightedHorizonModel
from agx_research.investment_proof.categories import Category, category_for_agent
from agx_research.knowledge.schema import KnowledgeObject
from agx_research.meta.decision_engine import DecisionAction, MetaDecisionEngine


class CounterfactualScenario(BaseModel):
    category_removed: Category
    knowledge_ids_removed: list[str]
    counterfactual_action: DecisionAction | None
    counterfactual_expected_return: float | None
    decision_changed: bool
    expected_return_delta: float | None = None


class CounterfactualResult(BaseModel):
    ticker: str
    as_of: date
    baseline_action: DecisionAction | None
    baseline_expected_return: float | None
    categories_present: list[Category]
    scenarios: list[CounterfactualScenario] = Field(default_factory=list)
    decisive_categories: list[Category] = Field(default_factory=list)


class CounterfactualEngine:
    def __init__(self):
        self._model = KnowledgeWeightedHorizonModel(Horizon.INVESTMENT)
        self._engine = MetaDecisionEngine()

    def analyze(
        self, ticker: str, as_of: date, knowledge: list[KnowledgeObject], *, reference_price: float | None = None
    ) -> CounterfactualResult:
        baseline_action, baseline_return = self._decide(ticker, as_of, knowledge, reference_price)
        by_category: dict[Category, list[str]] = {}
        for k in knowledge:
            category = category_for_agent(k.creator_agent)
            if category is not None:
                by_category.setdefault(category, []).append(k.id)

        result = CounterfactualResult(
            ticker=ticker,
            as_of=as_of,
            baseline_action=baseline_action,
            baseline_expected_return=baseline_return,
            categories_present=sorted(by_category, key=lambda c: c.value),
        )
        for category, ids in sorted(by_category.items(), key=lambda item: item[0].value):
            ablated = [k for k in knowledge if k.id not in ids]
            action, expected_return = self._decide(ticker, as_of, ablated, reference_price)
            changed = action != baseline_action
            result.scenarios.append(
                CounterfactualScenario(
                    category_removed=category,
                    knowledge_ids_removed=ids,
                    counterfactual_action=action,
                    counterfactual_expected_return=expected_return,
                    decision_changed=changed,
                    expected_return_delta=(
                        expected_return - baseline_return
                        if expected_return is not None and baseline_return is not None
                        else None
                    ),
                )
            )
            if changed:
                result.decisive_categories.append(category)
        return result

    def _decide(
        self, ticker: str, as_of: date, knowledge: list[KnowledgeObject], reference_price: float | None
    ) -> tuple[DecisionAction | None, float | None]:
        prediction = self._model.predict(ticker, as_of, knowledge)
        if prediction is None:
            return None, None
        if reference_price is not None and reference_price > 0:
            prediction = prediction.model_copy(update={"reference_price": reference_price})
        recommendation = self._engine.decide(ticker, as_of, {Horizon.INVESTMENT: prediction})
        if recommendation is None:
            return None, None
        decision = recommendation.horizon_decisions[Horizon.INVESTMENT]
        return decision.action, decision.expected_return


__all__ = ["CounterfactualEngine", "CounterfactualResult", "CounterfactualScenario"]
