from datetime import date, datetime

from agx_research.config import Horizon
from agx_research.data.schemas import PriceBar
from agx_research.data.snapshot import DatasetSnapshot
from agx_research.domain.provenance import Provenance
from agx_research.explainability import Explanation
from agx_research.horizons.base import Prediction
from agx_research.meta.decision_engine import MetaDecisionEngine
from agx_research.meta.decision_ledger import DecisionLedger, OutcomeStatus


def prediction() -> Prediction:
    return Prediction(
        ticker="COMI", horizon=Horizon.MICRO, as_of=date(2026, 7, 1),
        model_id="test", model_version="1", expected_return=0.02,
        expected_risk=0.01, confidence=0.8,
        reference_price=100.0,
        explanation=Explanation(
            why_this_stock="test", why_now="test", why_not_others="test",
            invalidation_conditions=["evidence expires"],
        ),
        provenance=Provenance(produced_by="test", produced_at=datetime.now()),
    )


def bar(day: date, close: float, ticker: str = "COMI") -> PriceBar:
    return PriceBar(
        ticker=ticker, trade_date=day, open=close, high=close,
        low=close, close=close, volume=1000,
    )


def test_ledger_records_once_and_evaluates_expired_decision(tmp_path):
    recommendation = MetaDecisionEngine().decide(
        "COMI", date(2026, 7, 1), {Horizon.MICRO: prediction()}
    )
    assert recommendation is not None
    ledger = DecisionLedger(tmp_path / "decisions.json")
    ledger.record_recommendations([recommendation])
    ledger.record_recommendations([recommendation])
    assert len(ledger.all_latest()) == 1

    snapshot = DatasetSnapshot(
        id="snapshot", as_of=date(2026, 7, 4), lookback_days=10,
        macro_lookback_days=10,
        tickers=["COMI"], macro_series_ids=[], price_history={
            "COMI": [bar(date(2026, 7, 1), 100), bar(date(2026, 7, 4), 103)],
            "EGX30": [
                bar(date(2026, 7, 1), 100, "EGX30"),
                bar(date(2026, 7, 4), 100, "EGX30"),
            ],
        },
    )
    ledger.evaluate_expired(snapshot)
    [record] = ledger.all_latest()
    assert record.outcome_status == OutcomeStatus.EVALUATED
    assert round(record.gross_asset_return or 0, 6) == 0.03
    assert round(record.realized_return or 0, 6) == 0.028
    assert round(record.excess_return or 0, 6) == 0.03
    assert record.hit is True
    assert len(ledger.history(record.id)) == 2


def test_performance_summary_never_claims_edge_on_tiny_sample(tmp_path):
    recommendation = MetaDecisionEngine().decide(
        "COMI", date(2026, 7, 1), {Horizon.MICRO: prediction()}
    )
    assert recommendation is not None
    ledger = DecisionLedger(tmp_path / "decisions.json")
    ledger.record_recommendations([recommendation])
    summary = next(row for row in ledger.performance_summary() if row.horizon == Horizon.MICRO)
    assert summary.decisions == 1
    assert summary.sample_status == "insufficient_sample"
    assert summary.hit_rate is None


def test_performance_cannot_be_sufficient_without_benchmark(tmp_path):
    recommendation = MetaDecisionEngine().decide(
        "COMI", date(2026, 7, 1), {Horizon.MICRO: prediction()}
    )
    assert recommendation is not None
    ledger = DecisionLedger(tmp_path / "decisions.json")
    ledger.record_recommendations([recommendation])
    snapshot = DatasetSnapshot(
        id="snapshot", as_of=date(2026, 7, 4), lookback_days=10,
        macro_lookback_days=10,
        tickers=["COMI"], macro_series_ids=[], price_history={"COMI": [
            bar(date(2026, 7, 1), 100), bar(date(2026, 7, 4), 103),
        ]},
    )
    ledger.evaluate_expired(snapshot)
    summary = next(
        row for row in ledger.performance_summary(min_sample=1)
        if row.horizon == Horizon.MICRO
    )
    assert summary.evaluated == 1
    assert summary.benchmark_evaluated == 0
    assert summary.sample_status == "insufficient_benchmark"
    assert summary.hit_rate is None


def test_watch_and_avoid_are_not_counted_as_executed_trades(tmp_path):
    recommendation = MetaDecisionEngine().decide(
        "COMI", date(2026, 7, 1), {Horizon.MICRO: prediction()}
    )
    assert recommendation is not None
    for action in ("watch", "avoid", "abstain"):
        decision = recommendation.horizon_decisions[Horizon.MICRO]
        decision.action = action
        ledger = DecisionLedger(tmp_path / f"{action}.json")
        ledger.record_recommendations([recommendation])
        snapshot = DatasetSnapshot(
            id="snapshot", as_of=date(2026, 7, 4), lookback_days=10,
            macro_lookback_days=10,
            tickers=["COMI"], macro_series_ids=[], price_history={
                "COMI": [bar(date(2026, 7, 1), 100), bar(date(2026, 7, 4), 90)],
                "EGX30": [
                    bar(date(2026, 7, 1), 100, "EGX30"),
                    bar(date(2026, 7, 4), 95, "EGX30"),
                ],
            },
        )
        ledger.evaluate_expired(snapshot)
        [record] = ledger.all_latest()
        assert record.gross_asset_return == -0.1
        assert record.realized_return is None
        assert record.excess_return is None
        summary = next(
            row for row in ledger.performance_summary(min_sample=1)
            if row.horizon == Horizon.MICRO
        )
        assert summary.evaluated == 0
        assert summary.benchmark_evaluated == 0
