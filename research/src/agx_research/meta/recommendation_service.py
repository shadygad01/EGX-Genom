"""Assembles the daily answer to the Core Mission question:
which tickers currently carry evidence-backed opportunity, and why.

For every ticker in the universe, each horizon's knowledge-weighted model
predicts (or abstains); the Meta Decision Engine combines whatever
predictions exist into one explainable Recommendation. Tickers with no
surviving knowledge simply produce no recommendation — absence of
evidence is an answer, not a gap to fill.
"""

from __future__ import annotations

from datetime import date

from agx_research.config import Horizon
from agx_research.domain.provenance import ProvenanceRef
from agx_research.events.service import EventPlatform
from agx_research.horizons.base import Prediction
from agx_research.horizons.knowledge_weighted import KnowledgeWeightedHorizonModel
from agx_research.knowledge.store import KnowledgeStore
from agx_research.meta.decision_engine import MetaDecisionEngine, Recommendation
from agx_research.valuation import FairValueEngine

FAIR_VALUE_INVESTMENT_WEIGHT = 0.20


class RecommendationService:
    def __init__(
        self,
        knowledge_store: KnowledgeStore,
        *,
        event_platform: EventPlatform | None = None,
        engine: MetaDecisionEngine | None = None,
        fair_value_engine: FairValueEngine | None = None,
    ):
        self.knowledge_store = knowledge_store
        self.engine = engine or MetaDecisionEngine()
        self.fair_value_engine = fair_value_engine
        self.models = {
            horizon: KnowledgeWeightedHorizonModel(horizon, event_platform=event_platform)
            for horizon in Horizon
        }

    def recommend(
        self,
        tickers: list[str],
        as_of: date,
        *,
        ready_horizons_by_ticker: dict[str, set[Horizon]] | None = None,
        latest_prices: dict[str, float] | None = None,
    ) -> list[Recommendation]:
        knowledge = self.knowledge_store.all_latest()
        recommendations: list[Recommendation] = []
        for ticker in sorted(tickers):
            predictions: dict[Horizon, Prediction] = {}
            for horizon, model in self.models.items():
                if (
                    ready_horizons_by_ticker is not None
                    and horizon not in ready_horizons_by_ticker.get(ticker, set())
                ):
                    continue
                prediction = model.predict(ticker, as_of, knowledge)
                if prediction is not None:
                    reference_price = (latest_prices or {}).get(ticker)
                    if reference_price is not None and reference_price > 0:
                        prediction = prediction.model_copy(
                            update={"reference_price": reference_price}
                        )
                    if horizon == Horizon.INVESTMENT and self.fair_value_engine and reference_price:
                        valuation = self.fair_value_engine.value(ticker, as_of)
                        if valuation is not None:
                            implied = max(-1.0, min(2.0, valuation.weighted_fair_value / reference_price - 1))
                            price_vs_fair_value = reference_price / valuation.weighted_fair_value - 1
                            ref = ProvenanceRef(kind="calculated_fair_value", ref_id=f"{ticker}:{as_of}:{valuation.assumptions_version}")
                            prediction = prediction.model_copy(update={
                                "expected_return": (1 - FAIR_VALUE_INVESTMENT_WEIGHT) * prediction.expected_return + FAIR_VALUE_INVESTMENT_WEIGHT * implied,
                                "explanation": prediction.explanation.model_copy(update={
                                    "supporting_evidence": [*prediction.explanation.supporting_evidence, f"Calculated fair value={valuation.weighted_fair_value:.2f} (avg. of {len(valuation.included_models)} models: {','.join(valuation.included_models)}); current price={reference_price:.2f} is {price_vs_fair_value:+.1%} vs. fair value; fair-value weight in expected return={FAIR_VALUE_INVESTMENT_WEIGHT:.0%}"],
                                    "evidence_refs": [*prediction.explanation.evidence_refs, ref],
                                }),
                                "provenance": prediction.provenance.model_copy(update={"inputs": [*prediction.provenance.inputs, ref]}),
                            })
                    predictions[horizon] = prediction
            recommendation = self.engine.decide(ticker, as_of, predictions)
            if recommendation is not None:
                recommendations.append(recommendation)
        return recommendations
