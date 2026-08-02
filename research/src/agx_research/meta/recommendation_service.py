"""Assembles the daily answer to the Core Mission question:
which tickers currently carry evidence-backed opportunity, and why.

For every ticker in the universe, each horizon's knowledge-weighted model
predicts (or abstains); the Meta Decision Engine combines whatever
predictions exist into one explainable Recommendation. Tickers with no
surviving knowledge simply produce no recommendation — absence of
evidence is an answer, not a gap to fill.
"""

from __future__ import annotations

from datetime import date, datetime

from agx_research.config import Horizon
from agx_research.domain.provenance import Provenance, ProvenanceRef
from agx_research.events.service import EventPlatform
from agx_research.explainability import Explanation
from agx_research.horizons.base import Prediction
from agx_research.horizons.knowledge_weighted import KnowledgeWeightedHorizonModel
from agx_research.knowledge.store import KnowledgeStore
from agx_research.meta.decision_engine import MetaDecisionEngine, Recommendation
from agx_research.valuation import FairValueEngine, compute_valuation_metrics

FAIR_VALUE_INVESTMENT_WEIGHT = 0.20
MARKET_MULTIPLE_INVESTMENT_WEIGHT = 0.10
VALUATION_ONLY_MODEL_ID = "multi_model_fair_value"


def _valuation_prediction(ticker, as_of, reference_price, valuation) -> Prediction:
    implied = max(-1.0, min(2.0, valuation.weighted_fair_value / reference_price - 1))
    scenario_risk = max(
        0.05,
        (valuation.bull_case - valuation.bear_case) / (2 * valuation.weighted_fair_value),
    )
    confidence = min(0.85, 0.55 + 0.05 * len(valuation.included_models))
    ref = ProvenanceRef(
        kind="calculated_fair_value",
        ref_id=f"{ticker}:{as_of}:{valuation.assumptions_version}",
    )
    return Prediction(
        ticker=ticker,
        horizon=Horizon.INVESTMENT,
        as_of=as_of,
        model_id=VALUATION_ONLY_MODEL_ID,
        model_version=valuation.assumptions_version,
        expected_return=implied,
        expected_risk=scenario_risk,
        confidence=confidence,
        reference_price=reference_price,
        explanation=Explanation(
            why_this_stock=(
                f"{ticker} has a point-in-time fair value supported by "
                f"{len(valuation.included_models)} mutually checked models."
            ),
            why_now=(
                f"Current price {reference_price:.2f} can be compared with fair value "
                f"{valuation.weighted_fair_value:.2f}."
            ),
            why_not_others=(
                "Tickers without at least three valid valuation models are withheld."
            ),
            supporting_evidence=[
                f"fair_value={valuation.weighted_fair_value:.4f}",
                f"bear_case={valuation.bear_case:.4f}",
                f"bull_case={valuation.bull_case:.4f}",
                f"models={','.join(valuation.included_models)}",
            ],
            evidence_refs=[ref],
            invalidation_conditions=[
                "A new filing changes the reported cash flow, earnings, equity, debt, or share count."
            ],
        ),
        provenance=Provenance(
            produced_by=f"{VALUATION_ONLY_MODEL_ID}@{valuation.assumptions_version}",
            produced_at=datetime.now().astimezone(),
            inputs=[ref],
        ),
    )


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
        sectors_by_ticker: dict[str, str] | None = None,
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
                reference_price = (latest_prices or {}).get(ticker)
                if (
                    prediction is None
                    and horizon == Horizon.INVESTMENT
                    and self.fair_value_engine
                    and reference_price
                ):
                    fair = self.fair_value_engine.value(
                        ticker, as_of, sector=(sectors_by_ticker or {}).get(ticker)
                    )
                    if fair is not None:
                        prediction = _valuation_prediction(ticker, as_of, reference_price, fair)
                if prediction is not None:
                    if reference_price is not None and reference_price > 0:
                        prediction = prediction.model_copy(
                            update={"reference_price": reference_price}
                        )
                    if horizon == Horizon.INVESTMENT and self.fair_value_engine and reference_price:
                        valuation = self.fair_value_engine.value(
                            ticker, as_of, sector=(sectors_by_ticker or {}).get(ticker)
                        )
                        if valuation is not None and prediction.model_id != VALUATION_ONLY_MODEL_ID:
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
                        metrics = compute_valuation_metrics(
                            ticker,
                            as_of,
                            reference_price,
                            self.fair_value_engine.provider,
                            self.fair_value_engine,
                            sector=(sectors_by_ticker or {}).get(ticker),
                        )
                        if metrics.market_pe is not None and metrics.market_pe > 0:
                            # Earnings yield minus the valuation engine's declared risk-free
                            # rate is a transparent valuation-carry input, not the provider's
                            # opaque Buy/Sell label. Bound it before blending so one anomalous
                            # multiple cannot dominate validated AGX knowledge.
                            carry = max(
                                -0.50,
                                min(
                                    0.50,
                                    (1 / metrics.market_pe)
                                    - self.fair_value_engine.assumptions.risk_free_rate,
                                ),
                            )
                            market_ref = ProvenanceRef(
                                kind="market_fundamental_snapshot",
                                ref_id=f"{ticker}:{as_of}:market_pe",
                            )
                            prediction = prediction.model_copy(update={
                                "expected_return": (
                                    (1 - MARKET_MULTIPLE_INVESTMENT_WEIGHT)
                                    * prediction.expected_return
                                    + MARKET_MULTIPLE_INVESTMENT_WEIGHT * carry
                                ),
                                "explanation": prediction.explanation.model_copy(update={
                                    "supporting_evidence": [
                                        *prediction.explanation.supporting_evidence,
                                        f"Market P/E={metrics.market_pe:.2f}; earnings-yield spread={carry:+.1%}; market-multiple weight in expected return={MARKET_MULTIPLE_INVESTMENT_WEIGHT:.0%}",
                                    ],
                                    "evidence_refs": [
                                        *prediction.explanation.evidence_refs,
                                        market_ref,
                                    ],
                                }),
                                "provenance": prediction.provenance.model_copy(update={
                                    "inputs": [*prediction.provenance.inputs, market_ref]
                                }),
                            })
                    predictions[horizon] = prediction
            recommendation = self.engine.decide(ticker, as_of, predictions)
            if recommendation is not None:
                recommendations.append(recommendation)
        return recommendations
