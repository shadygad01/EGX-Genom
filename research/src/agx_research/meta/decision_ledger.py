"""Append-only audit ledger for every horizon decision and its later outcome."""

from __future__ import annotations

from datetime import date, datetime
from enum import Enum
from pathlib import Path
import statistics

from pydantic import BaseModel

from agx_research.config import Horizon
from agx_research.data.adjustments import compute_adjusted_closes
from agx_research.data.snapshot import DatasetSnapshot
from agx_research.meta.decision_engine import DecisionAction, Recommendation
from agx_research.storage.repository import JsonFileRepository


#: Reused by `shadow_fund.engine` for the identical assumption -- one
#: declared transaction-cost figure, not two that could silently drift.
DEFAULT_TRANSACTION_COST_BPS = 20.0


class OutcomeStatus(str, Enum):
    PENDING = "pending"
    EVALUATED = "evaluated"
    INSUFFICIENT_DATA = "insufficient_data"


class DecisionRecord(BaseModel):
    id: str
    version: int = 1
    ticker: str
    horizon: Horizon
    as_of: date
    action: DecisionAction
    expected_return: float
    expected_risk: float
    confidence: float
    valid_until: date
    publication_status: str
    recorded_at: datetime
    outcome_status: OutcomeStatus = OutcomeStatus.PENDING
    entry_price: float | None = None
    exit_price: float | None = None
    gross_asset_return: float | None = None
    realized_return: float | None = None
    transaction_cost_bps: float | None = None
    benchmark_ticker: str | None = None
    benchmark_return: float | None = None
    excess_return: float | None = None
    hit: bool | None = None
    evaluated_at: datetime | None = None


class DecisionPerformanceSummary(BaseModel):
    horizon: Horizon
    decisions: int
    evaluated: int
    pending: int
    insufficient_data: int
    hit_rate: float | None = None
    mean_realized_return: float | None = None
    benchmark_evaluated: int = 0
    mean_benchmark_return: float | None = None
    mean_excess_return: float | None = None
    median_excess_return: float | None = None
    excess_return_lower_95: float | None = None
    max_drawdown: float | None = None
    mean_expected_return: float | None = None
    calibration_error: float | None = None
    sample_status: str


class DecisionLedger(JsonFileRepository[DecisionRecord]):
    def __init__(self, persist_path: Path | str | None = None):
        super().__init__(DecisionRecord, persist_path)

    @staticmethod
    def record_id(ticker: str, horizon: Horizon, as_of: date) -> str:
        return f"decision_{ticker}_{horizon.value}_{as_of.isoformat()}"

    def record_recommendations(self, recommendations: list[Recommendation]) -> None:
        changed = False
        for recommendation in recommendations:
            for horizon, decision in recommendation.horizon_decisions.items():
                record_id = self.record_id(recommendation.ticker, horizon, recommendation.as_of)
                if self.latest(record_id) is not None:
                    continue
                self.add(
                    DecisionRecord(
                        id=record_id,
                        ticker=recommendation.ticker,
                        horizon=horizon,
                        as_of=recommendation.as_of,
                        action=decision.action,
                        expected_return=decision.expected_return,
                        expected_risk=decision.expected_risk,
                        confidence=decision.confidence,
                        valid_until=decision.valid_until,
                        publication_status=decision.publication_status.value,
                        recorded_at=datetime.now(),
                    ),
                    persist=False,
                )
                changed = True
        if changed:
            self.flush()

    def evaluate_expired(
        self,
        snapshot: DatasetSnapshot,
        *,
        benchmark_ticker: str = "EGX30",
        transaction_cost_bps: float = DEFAULT_TRANSACTION_COST_BPS,
    ) -> None:
        changed = False
        for record in list(self.all_latest()):
            if record.outcome_status != OutcomeStatus.PENDING or snapshot.as_of < record.valid_until:
                continue
            bars = snapshot.price_history.get(record.ticker, [])
            adjusted = compute_adjusted_closes(
                bars, snapshot.corporate_events.get(record.ticker, [])
            )
            entry_dates = [day for day in adjusted if day >= record.as_of]
            exit_dates = [day for day in adjusted if day >= record.valid_until]
            update = record.model_copy(deep=True)
            update.version += 1
            update.evaluated_at = datetime.now()
            if not entry_dates or not exit_dates:
                update.outcome_status = OutcomeStatus.INSUFFICIENT_DATA
            else:
                entry = min(entry_dates)
                exit_day = min(exit_dates)
                update.entry_price = adjusted[entry]
                update.exit_price = adjusted[exit_day]
                update.gross_asset_return = (
                    (update.exit_price - update.entry_price) / update.entry_price
                    if update.entry_price
                    else None
                )
                update.transaction_cost_bps = transaction_cost_bps
                executed = update.action == DecisionAction.BUY_CANDIDATE
                update.realized_return = (
                    update.gross_asset_return - transaction_cost_bps / 10_000
                    if executed and update.gross_asset_return is not None
                    else None
                )
                benchmark = compute_adjusted_closes(
                    snapshot.price_history.get(benchmark_ticker, []),
                    snapshot.corporate_events.get(benchmark_ticker, []),
                )
                benchmark_entries = [day for day in benchmark if day >= record.as_of]
                benchmark_exits = [day for day in benchmark if day >= record.valid_until]
                update.benchmark_ticker = benchmark_ticker
                if executed and benchmark_entries and benchmark_exits:
                    benchmark_entry = benchmark[min(benchmark_entries)]
                    benchmark_exit = benchmark[min(benchmark_exits)]
                    if benchmark_entry:
                        update.benchmark_return = (
                            (benchmark_exit - benchmark_entry) / benchmark_entry
                            - transaction_cost_bps / 10_000
                        )
                        if update.realized_return is not None:
                            update.excess_return = update.realized_return - update.benchmark_return
                update.outcome_status = OutcomeStatus.EVALUATED
                if update.excess_return is not None:
                    update.hit = update.excess_return > 0
            self.add(update, persist=False)
            changed = True
        if changed:
            self.flush()

    def performance_summary(self, min_sample: int = 30) -> list[DecisionPerformanceSummary]:
        summaries: list[DecisionPerformanceSummary] = []
        records = self.all_latest()
        for horizon in Horizon:
            horizon_records = [record for record in records if record.horizon == horizon]
            evaluated = [
                record for record in horizon_records
                if record.outcome_status == OutcomeStatus.EVALUATED
                and record.realized_return is not None
            ]
            benchmark_evaluated = [
                record for record in evaluated if record.excess_return is not None
            ]
            hit_rate = (
                sum(1 for record in benchmark_evaluated if record.hit)
                / len(benchmark_evaluated)
                if benchmark_evaluated else None
            )
            mean_realized = (
                sum(record.realized_return for record in evaluated if record.realized_return is not None)
                / len(evaluated)
                if evaluated else None
            )
            mean_expected = (
                sum(record.expected_return for record in evaluated) / len(evaluated)
                if evaluated else None
            )
            mean_benchmark = (
                sum(record.benchmark_return for record in benchmark_evaluated if record.benchmark_return is not None)
                / len(benchmark_evaluated)
                if benchmark_evaluated else None
            )
            mean_excess = (
                sum(record.excess_return for record in benchmark_evaluated if record.excess_return is not None)
                / len(benchmark_evaluated)
                if benchmark_evaluated else None
            )
            excess_values = [
                record.excess_return for record in benchmark_evaluated
                if record.excess_return is not None
            ]
            lower_95 = None
            if len(excess_values) >= 2:
                lower_95 = (
                    statistics.fmean(excess_values)
                    - 1.645 * statistics.stdev(excess_values) / len(excess_values) ** 0.5
                )
            wealth = 1.0
            peak = 1.0
            max_drawdown = 0.0 if excess_values else None
            for record in sorted(benchmark_evaluated, key=lambda item: item.as_of):
                wealth *= 1.0 + (record.realized_return or 0.0)
                peak = max(peak, wealth)
                max_drawdown = min(max_drawdown or 0.0, wealth / peak - 1.0)
            summaries.append(
                DecisionPerformanceSummary(
                    horizon=horizon,
                    decisions=len(horizon_records),
                    evaluated=len(evaluated),
                    pending=sum(
                        record.outcome_status == OutcomeStatus.PENDING
                        for record in horizon_records
                    ),
                    insufficient_data=sum(
                        record.outcome_status == OutcomeStatus.INSUFFICIENT_DATA
                        for record in horizon_records
                    ),
                    hit_rate=hit_rate,
                    mean_realized_return=mean_realized,
                    benchmark_evaluated=len(benchmark_evaluated),
                    mean_benchmark_return=mean_benchmark,
                    mean_excess_return=mean_excess,
                    median_excess_return=(statistics.median(excess_values) if excess_values else None),
                    excess_return_lower_95=lower_95,
                    max_drawdown=max_drawdown,
                    mean_expected_return=mean_expected,
                    calibration_error=(
                        abs(mean_expected - mean_realized)
                        if mean_expected is not None and mean_realized is not None
                        else None
                    ),
                    sample_status=(
                        "sufficient"
                        if len(benchmark_evaluated) >= min_sample
                        else "insufficient_benchmark"
                        if len(evaluated) >= min_sample
                        else "insufficient_sample"
                    ),
                )
            )
        return summaries
