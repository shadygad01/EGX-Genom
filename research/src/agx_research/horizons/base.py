"""The per-horizon model contract.

Micro, Swing, and Investment Alpha are independent models sharing this one
interface. Nothing outside `agx_research.meta` is allowed to combine their
outputs — see `docs/ARCHITECTURE.md`.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import date

from pydantic import BaseModel, Field

from agx_research.config import Horizon
from agx_research.domain.provenance import Provenance
from agx_research.explainability import Explanation
from agx_research.knowledge import KnowledgeObject


class Prediction(BaseModel):
    """A single-horizon prediction for one ticker. Never returned without an Explanation.

    `model_id`/`model_version` record exactly which model artifact produced
    this — necessary once a model is retrained, so a monitoring/retirement
    decision (Principle 4) can tell whether a degrading result came from the
    same model or a since-replaced one (Principle 5: models are versioned).
    """

    ticker: str
    horizon: Horizon
    as_of: date
    model_id: str
    model_version: str
    expected_return: float
    expected_risk: float
    confidence: float
    reference_price: float | None = Field(default=None, gt=0)
    explanation: Explanation
    supporting_knowledge_ids: list[str] = Field(default_factory=list)
    provenance: Provenance


class HorizonModel(ABC):
    """A model scoped to exactly one time horizon."""

    horizon: Horizon
    model_id: str
    model_version: str

    @abstractmethod
    def predict(
        self, ticker: str, as_of: date, knowledge: list[KnowledgeObject]
    ) -> Prediction | None:
        """Produce a prediction for `ticker` as of `as_of` using promoted `knowledge`
        relevant to this horizon, or None if there isn't enough evidence to predict.
        """
