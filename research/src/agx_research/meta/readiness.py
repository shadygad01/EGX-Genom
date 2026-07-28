"""Per-ticker evidence readiness and explicit abstention decisions."""

from __future__ import annotations

from datetime import date, timedelta
from enum import Enum

from pydantic import BaseModel, Field

from agx_research.config import Horizon
from agx_research.financials.provider import FinancialStatementProvider
from agx_research.knowledge.schema import KnowledgeObject
from agx_research.market_memory.state import MarketState


class ReadinessStatus(str, Enum):
    READY = "ready"
    DEGRADED = "degraded"
    BLOCKED = "blocked"


class DecisionReadiness(BaseModel):
    ticker: str
    as_of: date
    status: ReadinessStatus
    decision: str
    ready_horizons: list[Horizon] = Field(default_factory=list)
    horizon_blockers: dict[Horizon, list[str]] = Field(default_factory=dict)
    price_observations: int = 0
    latest_price_date: date | None = None
    news_items: int = 0
    corporate_events: int = 0
    financial_periods: int = 0
    macro_series: int = 0
    active_knowledge: int = 0
    blockers: list[str] = Field(default_factory=list)
    next_actions: list[str] = Field(default_factory=list)


_GAP_LAYER_THRESHOLDS: dict[str, int] = {
    "financials": 2,
    "disclosures": 1,
    "news": 1,
    "macro": 3,
    "knowledge": 1,
}


class DataLayerGap(BaseModel):
    layer: str
    count: int
    threshold: int
    complete: bool
    completeness_pct: float


class TickerDataGapReport(BaseModel):
    ticker: str
    as_of: date
    status: ReadinessStatus
    decision: str
    ready_horizons: list[Horizon] = Field(default_factory=list)
    swing_ready: bool
    investment_ready: bool
    price_observations: int
    latest_price_date: date | None
    layers: list[DataLayerGap]
    overall_completeness_pct: float
    blockers: list[str] = Field(default_factory=list)
    next_actions: list[str] = Field(default_factory=list)


def build_ticker_data_gap_report(
    readiness_rows: list[DecisionReadiness],
) -> list[TickerDataGapReport]:
    """Decompose each `DecisionReadiness` row into the five named data
    layers (Financials/Disclosures/News/Macro/Knowledge) with an explicit
    completeness percentage per layer, so it's visible at a glance exactly
    which layer blocks a given ticker's Swing/Investment readiness.

    This is a pure re-derivation of `assess_decision_readiness`'s own
    counts and thresholds -- it introduces no second set of gates that
    could ever disagree with the readiness this report is describing.
    """
    reports: list[TickerDataGapReport] = []
    for row in readiness_rows:
        layer_counts = {
            "financials": row.financial_periods,
            "disclosures": row.corporate_events,
            "news": row.news_items,
            "macro": row.macro_series,
            "knowledge": row.active_knowledge,
        }
        layers = [
            DataLayerGap(
                layer=layer,
                count=count,
                threshold=_GAP_LAYER_THRESHOLDS[layer],
                complete=count >= _GAP_LAYER_THRESHOLDS[layer],
                completeness_pct=round(
                    min(count / _GAP_LAYER_THRESHOLDS[layer], 1.0) * 100, 1
                ),
            )
            for layer, count in layer_counts.items()
        ]
        overall_pct = round(sum(layer.completeness_pct for layer in layers) / len(layers), 1)
        reports.append(
            TickerDataGapReport(
                ticker=row.ticker,
                as_of=row.as_of,
                status=row.status,
                decision=row.decision,
                ready_horizons=row.ready_horizons,
                swing_ready=Horizon.SWING in row.ready_horizons,
                investment_ready=Horizon.INVESTMENT in row.ready_horizons,
                price_observations=row.price_observations,
                latest_price_date=row.latest_price_date,
                layers=layers,
                overall_completeness_pct=overall_pct,
                blockers=row.blockers,
                next_actions=row.next_actions,
            )
        )
    return reports


def assess_decision_readiness(
    market_state: MarketState,
    financials: FinancialStatementProvider,
    knowledge: list[KnowledgeObject],
) -> list[DecisionReadiness]:
    snapshot = market_state.dataset_snapshot
    macro_series = sum(1 for values in snapshot.macro_series.values() if values)
    rows: list[DecisionReadiness] = []
    for ticker in sorted(snapshot.tickers):
        prices = snapshot.price_history.get(ticker, [])
        latest_price = max((bar.trade_date for bar in prices), default=None)
        price_is_fresh = latest_price is not None and (market_state.as_of - latest_price).days <= 7
        news = [item for item in snapshot.news if ticker in item.tickers]
        events = snapshot.corporate_events.get(ticker, [])
        items = financials.get_line_items(
            ticker, market_state.as_of - timedelta(days=730), market_state.as_of
        )
        financial_periods = len({item.period_end_date for item in items})
        active_knowledge = [
            item
            for item in knowledge
            if ticker in item.affected_assets and item.status.value != "retired"
        ]

        knowledge_by_horizon = {
            horizon: [item for item in active_knowledge if item.horizon == horizon]
            for horizon in Horizon
        }
        horizon_blockers: dict[Horizon, list[str]] = {
            Horizon.MICRO: [],
            Horizon.SWING: [],
            Horizon.INVESTMENT: [],
        }
        if len(prices) < 60:
            horizon_blockers[Horizon.MICRO].append("أقل من 60 مشاهدة سعرية.")
        if not price_is_fresh:
            horizon_blockers[Horizon.MICRO].append("بيانات السعر قديمة.")
        if not knowledge_by_horizon[Horizon.MICRO]:
            horizon_blockers[Horizon.MICRO].append("لا توجد معرفة نشطة للأفق القصير.")

        if len(prices) < 120:
            horizon_blockers[Horizon.SWING].append("أقل من 120 مشاهدة سعرية.")
        if not price_is_fresh:
            horizon_blockers[Horizon.SWING].append("بيانات السعر قديمة.")
        if not (news or events):
            horizon_blockers[Horizon.SWING].append("لا يوجد خبر أو حدث حديث للشركة.")
        if not knowledge_by_horizon[Horizon.SWING]:
            horizon_blockers[Horizon.SWING].append("لا توجد معرفة نشطة للأفق المتوسط.")

        if len(prices) < 252:
            horizon_blockers[Horizon.INVESTMENT].append("أقل من 252 مشاهدة سعرية.")
        if not price_is_fresh:
            horizon_blockers[Horizon.INVESTMENT].append("بيانات السعر قديمة.")
        if financial_periods < 4:
            horizon_blockers[Horizon.INVESTMENT].append(
                "أقل من أربع فترات مالية قابلة للمقارنة."
            )
        if macro_series < 3:
            horizon_blockers[Horizon.INVESTMENT].append("أقل من ثلاث سلاسل اقتصاد كلي.")
        if not knowledge_by_horizon[Horizon.INVESTMENT]:
            horizon_blockers[Horizon.INVESTMENT].append(
                "لا توجد معرفة نشطة للأفق الطويل."
            )

        ready_horizons = [
            horizon for horizon, reasons in horizon_blockers.items() if not reasons
        ]

        blockers: list[str] = []
        next_actions: list[str] = []
        if not prices:
            blockers.append("لا يتوفر سجل أسعار موثوق.")
            next_actions.append("اربط مصدر أسعار وحجم تداول عاملًا للبورصة المصرية.")
        elif not price_is_fresh:
            blockers.append("أحدث مشاهدة سعرية قديمة.")
            next_actions.append("حدّث جامع الأسعار وتحقق من تغطية أيام التداول.")
        if financial_periods < 2:
            blockers.append("يتوفر أقل من فترتين ماليتين.")
            next_actions.append("اجمع فترتين ماليتين قابلتين للمقارنة.")
        if not news and not events:
            blockers.append("لا يوجد خبر أو حدث مؤسسي مرتبط بالسهم داخل النافذة.")
            next_actions.append("حسّن ربط أسماء الشركات ورموز الأسهم بالأخبار.")
        if macro_series < 3:
            blockers.append("سياق الاقتصاد الكلي يحتوي أقل من ثلاث سلاسل مكتملة.")
            next_actions.append("استعد ثلاث سلاسل اقتصاد كلي حديثة على الأقل.")
        if not active_knowledge:
            blockers.append("لا يغطي السهم أي كائن معرفة نشط ومتحقق منه.")
            next_actions.append("مرّر الفرضيات عبر التحقق قبل إصدار أي قرار.")

        decision_allowed = bool(ready_horizons and active_knowledge)
        status = (
            ReadinessStatus.READY
            if decision_allowed
            else ReadinessStatus.DEGRADED
            if prices
            else ReadinessStatus.BLOCKED
        )
        rows.append(
            DecisionReadiness(
                ticker=ticker,
                as_of=market_state.as_of,
                status=status,
                decision="researchable" if decision_allowed else "abstain",
                ready_horizons=ready_horizons,
                horizon_blockers=horizon_blockers,
                price_observations=len(prices),
                latest_price_date=latest_price,
                news_items=len(news),
                corporate_events=len(events),
                financial_periods=financial_periods,
                macro_series=macro_series,
                active_knowledge=len(active_knowledge),
                blockers=blockers,
                next_actions=next_actions,
            )
        )
    return rows
