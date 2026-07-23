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
from agx_research.events.service import EventPlatform
from agx_research.horizons.base import Prediction
from agx_research.horizons.knowledge_weighted import KnowledgeWeightedHorizonModel
from agx_research.knowledge.store import KnowledgeStore
from agx_research.meta.decision_engine import MetaDecisionEngine, Recommendation


class RecommendationService:
    def __init__(
        self,
        knowledge_store: KnowledgeStore,
        *,
        event_platform: EventPlatform | None = None,
        engine: MetaDecisionEngine | None = None,
    ):
        self.knowledge_store = knowledge_store
        self.engine = engine or MetaDecisionEngine()
        self.models = {
            horizon: KnowledgeWeightedHorizonModel(horizon, event_platform=event_platform)
            for horizon in Horizon
        }

    def recommend(self, tickers: list[str], as_of: date) -> list[Recommendation]:
        knowledge = self.knowledge_store.all_latest()
        recommendations: list[Recommendation] = []
        for ticker in sorted(tickers):
            predictions: dict[Horizon, Prediction] = {}
            for horizon, model in self.models.items():
                prediction = model.predict(ticker, as_of, knowledge)
                if prediction is not None:
                    predictions[horizon] = prediction
            recommendation = self.engine.decide(ticker, as_of, predictions)
            if recommendation is not None:
                recommendations.append(recommendation)
        return recommendations
