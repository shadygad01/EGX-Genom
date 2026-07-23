"""Investment Alpha model: 1-6 month horizon. Not yet implemented — needs a
trained model consuming knowledge promoted for `Horizon.INVESTMENT`.
"""

from __future__ import annotations

from datetime import date

from agx_research.config import Horizon
from agx_research.horizons.base import HorizonModel, Prediction
from agx_research.knowledge import KnowledgeObject


class InvestmentAlphaModel(HorizonModel):
    horizon = Horizon.INVESTMENT
    model_id = "investment_alpha"
    model_version = "0.1.0"

    def predict(
        self, ticker: str, as_of: date, knowledge: list[KnowledgeObject]
    ) -> Prediction | None:
        raise NotImplementedError("InvestmentAlphaModel prediction logic is not yet implemented")
