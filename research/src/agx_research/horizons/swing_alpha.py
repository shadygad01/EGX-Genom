"""Swing Alpha model: 1-4 week horizon. Not yet implemented — needs a trained
model consuming knowledge promoted for `Horizon.SWING`.
"""

from __future__ import annotations

from datetime import date

from agx_research.config import Horizon
from agx_research.horizons.base import HorizonModel, Prediction
from agx_research.knowledge import KnowledgeObject


class SwingAlphaModel(HorizonModel):
    horizon = Horizon.SWING

    def predict(
        self, ticker: str, as_of: date, knowledge: list[KnowledgeObject]
    ) -> Prediction | None:
        raise NotImplementedError("SwingAlphaModel prediction logic is not yet implemented")
