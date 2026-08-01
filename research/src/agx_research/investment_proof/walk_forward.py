"""Phase 2: Walk-Forward Infrastructure.

Investigated first, per the mission's own discipline of reusing rather
than duplicating: `runtime.engine.RuntimeEngine.run_range()` already
replays the *research* pipeline day by day, deterministically, with
per-day failure isolation and non-trading-day handling; `meta.
decision_ledger.DecisionLedger` already evaluates recorded decisions
against later real prices. Neither, though, ever calls
`RecommendationService.recommend()` or a portfolio constructor across a
date range -- there was no driver connecting "research pipeline produced
knowledge" to "here is what the decision engine would have recommended
each day, and how it performed once evaluated." `WalkForwardInfrastructure`
is that driver: it reuses the same trading calendar
(`market_memory.calendar.StaticEGXCalendar`) and the same real services
(`RecommendationService`, `DecisionLedger`) rather than reimplementing
either, and adds only the day-stepping loop that was genuinely missing.

Per the mission's explicit instruction, this never simulates fake
history: `run_replay()` only ever calls real services against whatever
`KnowledgeStore`/`DatasetSnapshot` data the caller actually has (mock or
real). `required_datasets()` names exactly what's needed for a
statistically meaningful walk-forward run and reports each as
`"available"` or `"ready_for_data"` -- never a fabricated readiness claim.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, timedelta
from typing import Callable

from agx_research.data.snapshot import DatasetSnapshot
from agx_research.market_memory.calendar import StaticEGXCalendar, TradingCalendar
from agx_research.meta.decision_engine import Recommendation
from agx_research.meta.decision_ledger import DecisionLedger
from agx_research.meta.recommendation_service import RecommendationService

#: A meaningful walk-forward INVESTMENT-horizon backtest needs the
#: forward window (126 trading days, ~6 calendar months) PLUS enough
#: independent decision points to reach DecisionLedger's own 30-decision
#: floor for a real performance claim -- same posture as every other
#: declared-not-measured threshold in this codebase.
MIN_TRADING_DAYS_FOR_MEANINGFUL_REPLAY = 252  # ~1 real EGX trading year


@dataclass
class RequiredDataset:
    name: str
    description: str
    status: str  # "available" | "ready_for_data"
    detail: str = ""


@dataclass
class WalkForwardRunReport:
    start: date
    end: date
    trading_days_replayed: int
    non_trading_days_skipped: int
    recommendations_recorded: int
    tickers: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)


class WalkForwardInfrastructure:
    """Composes `RecommendationService` + `DecisionLedger` over a real
    trading-day range. `snapshot_provider`/`knowledge_provider` are
    injected callables (`date -> DatasetSnapshot`/`date -> KnowledgeStore`)
    so this engine never depends on one specific data source -- any future
    dataset plugs in by supplying a new callable, never a redesign here.
    """

    def __init__(
        self,
        recommendation_service_provider: Callable[[date], RecommendationService],
        ledger: DecisionLedger,
        *,
        calendar: TradingCalendar | None = None,
    ):
        self.recommendation_service_provider = recommendation_service_provider
        self.ledger = ledger
        self.calendar = calendar or StaticEGXCalendar()

    def run_replay(
        self, start: date, end: date, tickers: list[str], *, latest_prices_provider: Callable[[date], dict[str, float]] | None = None
    ) -> WalkForwardRunReport:
        report = WalkForwardRunReport(start=start, end=end, trading_days_replayed=0, non_trading_days_skipped=0, recommendations_recorded=0, tickers=tickers)
        current = start
        while current <= end:
            if not self.calendar.is_trading_day(current):
                report.non_trading_days_skipped += 1
                current += timedelta(days=1)
                continue
            try:
                service = self.recommendation_service_provider(current)
                latest_prices = latest_prices_provider(current) if latest_prices_provider else None
                recommendations: list[Recommendation] = service.recommend(tickers, current, latest_prices=latest_prices)
                self.ledger.record_recommendations(recommendations)
                report.recommendations_recorded += len(recommendations)
                report.trading_days_replayed += 1
            except Exception as exc:  # per-day isolation, matching RuntimeEngine.run_range's own discipline
                report.errors.append(f"{current.isoformat()}: {type(exc).__name__}: {exc}")
            current += timedelta(days=1)
        return report

    def evaluate(self, snapshot: DatasetSnapshot, *, benchmark_ticker: str = "EGX30") -> None:
        """Thin pass-through to the real evaluator -- kept here only so a
        caller has one engine object for the whole walk-forward workflow,
        not a second evaluation mechanism."""
        self.ledger.evaluate_expired(snapshot, benchmark_ticker=benchmark_ticker)

    @staticmethod
    def required_datasets(*, real_trading_days_available: int = 0, real_benchmark_series_available: bool = False) -> list[RequiredDataset]:
        return [
            RequiredDataset(
                name="multi_year_real_egx_price_history",
                description=(
                    f"At least {MIN_TRADING_DAYS_FOR_MEANINGFUL_REPLAY} real, contiguous EGX trading days per "
                    "ticker -- enough for the INVESTMENT horizon's 126-trading-day forward window plus a real "
                    "sample of independent decision points."
                ),
                status="available" if real_trading_days_available >= MIN_TRADING_DAYS_FOR_MEANINGFUL_REPLAY else "ready_for_data",
                detail=f"{real_trading_days_available} real trading days currently available.",
            ),
            RequiredDataset(
                name="real_egx30_index_level_price_series",
                description="A real price series under the 'EGX30' (or equivalent) ticker id for benchmark comparison (see TD-58).",
                status="available" if real_benchmark_series_available else "ready_for_data",
            ),
            RequiredDataset(
                name="daily_promoted_knowledge_snapshots",
                description="A KnowledgeStore snapshot per trading day, produced by the real research pipeline (ProductionPipeline/DailyResearchPipeline), not synthetic.",
                status="ready_for_data",
                detail="Mechanism exists (ProductionPipeline); real daily history has not yet accumulated at scale.",
            ),
        ]


__all__ = [
    "MIN_TRADING_DAYS_FOR_MEANINGFUL_REPLAY",
    "RequiredDataset",
    "WalkForwardInfrastructure",
    "WalkForwardRunReport",
]
