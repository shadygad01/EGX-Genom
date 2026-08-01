"""ShadowFundEngine.advance() -- the Shadow Fund's one state transition.

Deliberately **not** a new decision engine (per the mission that created
this package): every target weight comes from the exact same
`decision_service.DecisionService.decide_portfolio()` every other
position-aware consumer (`agx decide`, `agx allocate-capital`, the live
`api/` routes) already calls -- the only difference is *whose* position
state is fed in. A real investor's holdings can never be autonomously
discovered (`decision_service/__init__.py`'s standing rule, unchanged).
The Shadow Fund's own holdings are not that: they are entirely the
platform's own prior output, reproducible from an all-cash inception plus
every day's own autonomous decisions -- so, unlike a real investor's
portfolio, it is both safe and correct to drive `decide_portfolio()`
autonomously here, inside the daily production pipeline. This is the one
deliberate, documented exception to "never wire decision_service into a
scheduled run"; do not generalize it to real `PositionState`.

Capital-deployment/recycling bookkeeping is not re-derived here either --
`capital_allocation.CapitalAllocationEngine.build()` already computes the
exact queue/recycling/opportunity-cost view the Shadow Fund's transactions
came from, so today's `CapitalAllocationPlan` is computed once and stored
alongside the snapshot, not recomputed a second way.
"""

from __future__ import annotations

import statistics
from datetime import date, datetime

from agx_research.capital_allocation.engine import CapitalAllocationEngine
from agx_research.data.adjustments import compute_adjusted_closes
from agx_research.data.snapshot import DatasetSnapshot
from agx_research.decision_service.country_risk import CountryRiskAssessment
from agx_research.decision_service.position import PositionState
from agx_research.decision_service.service import DecisionService, PositionAction
from agx_research.domain.provenance import Provenance, ProvenanceRef
from agx_research.knowledge.store import KnowledgeStore
from agx_research.meta.decision_engine import Recommendation
from agx_research.meta.decision_ledger import DEFAULT_TRANSACTION_COST_BPS
from agx_research.shadow_fund.models import (
    ShadowFundAttributionEntry,
    ShadowFundClosedPosition,
    ShadowFundPosition,
    ShadowFundRiskMetrics,
    ShadowFundSnapshot,
    ShadowFundTransaction,
)

#: Notional NAV-per-unit at inception -- an index convention (a fund
#: "launches at 100"), not a fabricated real capital figure. All returns
#: are read as percentages off this base.
INCEPTION_NAV = 100.0

#: A weight move smaller than this is treated as price drift, not a real
#: rebalancing decision -- without this, the fund would generate a
#: transaction on nearly every ticker nearly every day as `decide_portfolio`'s
#: continuous scores wobble by fractions of a point, which is not how an
#: institutional fund actually trades and would make "rebalancing history"
#: noise instead of signal. Declared, not tuned; see AD entry for the
#: repayment/revisit trigger.
REBALANCE_THRESHOLD_PCT = 0.01

#: Minimum trading days of real daily-return history before volatility/
#: Sharpe-like/drawdown are reported instead of an honest "insufficient
#: sample" -- same posture as `DecisionPerformanceSummary.sample_status`.
MIN_RISK_SAMPLE_DAYS = 20

_EPS = 1e-9


def _latest_price_on_or_before(prices_by_date: dict[date, float], as_of: date) -> float | None:
    eligible = {d: p for d, p in prices_by_date.items() if d <= as_of}
    if not eligible:
        return None
    return eligible[max(eligible)]


def advance(
    previous: ShadowFundSnapshot | None,
    recommendations: list[Recommendation],
    as_of: date,
    snapshot: DatasetSnapshot,
    *,
    country_risk: CountryRiskAssessment,
    illiquid_tickers: set[str] | None = None,
    knowledge_store: KnowledgeStore | None = None,
    benchmark_ticker: str = "EGX30",
    transaction_cost_bps: float = DEFAULT_TRANSACTION_COST_BPS,
    prior_daily_returns: list[float] | None = None,
    prior_nav_series: list[float] | None = None,
) -> ShadowFundSnapshot:
    """Compute the Shadow Fund's state for `as_of` given its own state the
    prior trading day (`previous`, `None` only at inception).

    `prior_daily_returns`/`prior_nav_series` are the fund's own past daily
    series (oldest first, excluding today) -- passed in rather than read
    from a repository here, so this function stays a pure computation over
    its arguments like every other engine in this codebase
    (`DecisionService.decide_portfolio`, `CapitalAllocationEngine.build`).
    """
    illiquid_tickers = illiquid_tickers or set()
    inception_date = previous.inception_date if previous is not None else as_of

    positions: dict[str, PositionState] = {}
    if previous is not None:
        for pos in previous.open_positions:
            positions[pos.ticker] = PositionState(
                ticker=pos.ticker,
                held=True,
                current_weight=pos.weight,
                average_cost=pos.average_cost,
            )

    decisions = DecisionService().decide_portfolio(
        recommendations,
        positions,
        as_of,
        country_risk=country_risk,
        illiquid_tickers=illiquid_tickers,
        corporate_events=snapshot.corporate_events,
        knowledge_store=knowledge_store,
    )
    decisions_by_ticker = {d.ticker: d for d in decisions}

    # Kept per-ticker (not just the latest price) so a previously-held
    # position's drift below is derived from prior.date and as_of on the
    # *same* freshly-computed series -- compute_adjusted_closes re-applies
    # every known corporate event on every call, so mixing today's series
    # with yesterday's stored ShadowFundPosition.market_price would silently
    # inject a fake NAV jump the moment a new split/dividend is discovered
    # for a ticker between two runs (the series gets rebased, the stored
    # price doesn't).
    adjusted_by_ticker: dict[str, dict[date, float]] = {}
    prices: dict[str, float] = {}
    for ticker in set(positions) | set(decisions_by_ticker):
        adjusted_by_ticker[ticker] = compute_adjusted_closes(
            snapshot.price_history.get(ticker, []), snapshot.corporate_events.get(ticker, [])
        )
        price = _latest_price_on_or_before(adjusted_by_ticker[ticker], as_of)
        if price is not None and price > 0:
            prices[ticker] = price

    benchmark_adjusted = compute_adjusted_closes(
        snapshot.price_history.get(benchmark_ticker, []),
        snapshot.corporate_events.get(benchmark_ticker, []),
    )
    benchmark_price = _latest_price_on_or_before(benchmark_adjusted, as_of)

    # 1. Mark yesterday's book to today's prices before any trading --
    #    this is the fund's real daily return, independent of whatever it
    #    decides to trade today.
    attribution_state: dict[str, float] = dict(previous.attribution_state) if previous else {}
    if previous is None:
        pre_rebalance_cash = INCEPTION_NAV
        drifted_value: dict[str, float] = {}
        pre_rebalance_nav = INCEPTION_NAV
    else:
        pre_rebalance_cash = previous.cash
        drifted_value = {}
        for pos in previous.open_positions:
            adjusted_series = adjusted_by_ticker.get(pos.ticker, {})
            price_today = _latest_price_on_or_before(adjusted_series, as_of)
            price_prior = _latest_price_on_or_before(adjusted_series, previous.date)
            growth = (
                (price_today / price_prior) if (price_today and price_prior and price_prior > 0) else 1.0
            )
            new_value = pos.market_value * growth
            drifted_value[pos.ticker] = new_value
            attribution_state[pos.ticker] = attribution_state.get(pos.ticker, 0.0) + (new_value - pos.market_value)
        pre_rebalance_nav = pre_rebalance_cash + sum(drifted_value.values())

    daily_return_pct = (
        (pre_rebalance_nav / previous.nav - 1.0) if previous is not None and previous.nav > 0 else None
    )

    # 2. Rebalance toward today's target weights, above the declared
    #    no-churn threshold, funding buys from cash and returning sale
    #    proceeds (net of transaction cost) to cash.
    open_map: dict[str, ShadowFundPosition] = {}
    closed_today: list[ShadowFundClosedPosition] = []
    transactions: list[ShadowFundTransaction] = []
    cash = pre_rebalance_cash
    all_tickers = sorted(set(drifted_value) | set(decisions_by_ticker))
    previous_open_by_ticker = {p.ticker: p for p in (previous.open_positions if previous else [])}

    for ticker in all_tickers:
        current_value = drifted_value.get(ticker, 0.0)
        current_weight = (current_value / pre_rebalance_nav) if pre_rebalance_nav > 0 else 0.0
        decision = decisions_by_ticker.get(ticker)
        prior_pos = previous_open_by_ticker.get(ticker)
        # An abstained held ticker reports target_weight=0.0 purely to keep
        # decide_portfolio's own scoring simple (CLAUDE.md's capital_allocation
        # rule) -- it is an evidence gap, never a real sell signal, and
        # capital_allocation.CapitalAllocationEngine already excludes it from
        # capital-flow matching for exactly this reason. Treating it as a
        # genuine target here would fabricate a liquidation nothing
        # recommended, so an abstained holding is held unchanged instead.
        abstained_held = decision is not None and decision.abstained and prior_pos is not None
        target_weight = 0.0 if (decision is None or abstained_held) else decision.target_weight
        price = prices.get(ticker)
        delta = 0.0 if abstained_held else (target_weight - current_weight)

        if price is None or abstained_held or abs(delta) < REBALANCE_THRESHOLD_PCT:
            # No fresh price, or the move is drift-noise: carry the drifted
            # position forward unchanged, no transaction.
            if current_value > _EPS and prior_pos is not None:
                open_map[ticker] = ShadowFundPosition(
                    ticker=ticker,
                    entry_date=prior_pos.entry_date,
                    average_cost=prior_pos.average_cost,
                    weight=current_weight,
                    target_weight=target_weight,
                    market_price=price if price is not None else prior_pos.market_price,
                    market_value=current_value,
                    unrealized_pnl_pct=(
                        ((price / prior_pos.average_cost) - 1.0)
                        if price and prior_pos.average_cost > 0
                        else prior_pos.unrealized_pnl_pct
                    ),
                    horizon=decision.horizon.value if decision is not None else prior_pos.horizon,
                    confidence=decision.confidence if decision is not None else prior_pos.confidence,
                    investment_thesis=(
                        decision.investment_thesis if decision is not None else prior_pos.investment_thesis
                    ),
                )
            continue

        transaction_cost = abs(delta) * pre_rebalance_nav * (transaction_cost_bps / 10_000.0)
        cash_delta = -delta * pre_rebalance_nav - transaction_cost
        cash += cash_delta
        attribution_state[ticker] = attribution_state.get(ticker, 0.0) - transaction_cost

        action = decision.action if decision is not None else (
            PositionAction.EXIT if current_value > _EPS else PositionAction.NO_ACTION
        )
        transactions.append(
            ShadowFundTransaction(
                id=f"txn_{ticker}_{as_of.isoformat()}",
                date=as_of,
                ticker=ticker,
                action=action,
                weight_before=current_weight,
                weight_after=max(target_weight, 0.0),
                weight_delta=delta,
                price=price,
                cash_delta=cash_delta,
                transaction_cost=transaction_cost,
                investment_thesis=(
                    decision.investment_thesis if decision is not None else f"{ticker}: exit, no current evidence."
                ),
                confidence=decision.confidence if decision is not None else 0.0,
                provenance=Provenance(
                    produced_by="shadow_fund.engine@1.0.0",
                    produced_at=datetime.now(),
                    inputs=[ProvenanceRef(kind="position_aware_decision", ref_id=ticker)],
                ),
            )
        )

        if target_weight <= _EPS:
            if prior_pos is not None:
                realized_pct = ((price / prior_pos.average_cost) - 1.0) if prior_pos.average_cost > 0 else 0.0
                closed_today.append(
                    ShadowFundClosedPosition(
                        ticker=ticker,
                        entry_date=prior_pos.entry_date,
                        exit_date=as_of,
                        average_cost=prior_pos.average_cost,
                        exit_price=price,
                        realized_pnl_pct=realized_pct,
                    )
                )
            continue

        if prior_pos is not None and delta > 0:
            # Increasing: weighted-average cost across old + newly added weight.
            added_weight = target_weight - current_weight
            total_weight = current_weight + added_weight
            average_cost = (
                (prior_pos.average_cost * current_weight + price * added_weight) / total_weight
                if total_weight > 0
                else price
            )
        elif prior_pos is not None:
            # Reducing but still open: cost basis of the remaining shares is unchanged.
            average_cost = prior_pos.average_cost
        else:
            # Brand-new position.
            average_cost = price

        open_map[ticker] = ShadowFundPosition(
            ticker=ticker,
            entry_date=prior_pos.entry_date if prior_pos is not None else as_of,
            average_cost=average_cost,
            weight=target_weight,
            target_weight=target_weight,
            market_price=price,
            market_value=target_weight * pre_rebalance_nav,
            unrealized_pnl_pct=((price / average_cost) - 1.0) if average_cost > 0 else None,
            horizon=decision.horizon.value if decision is not None else "investment",
            confidence=decision.confidence if decision is not None else 0.0,
            investment_thesis=decision.investment_thesis if decision is not None else "",
        )

    nav = cash + sum(pos.market_value for pos in open_map.values())
    # Recompute weights against the post-trade NAV (transaction costs are a
    # small, real drag; without this, weights would sum to slightly more
    # than 1.0 on a day with heavy trading).
    for ticker, pos in list(open_map.items()):
        open_map[ticker] = pos.model_copy(update={"weight": pos.market_value / nav if nav > 0 else 0.0})

    if benchmark_price is not None:
        if previous is None or previous.benchmark_nav <= 0:
            benchmark_nav = INCEPTION_NAV
        else:
            prior_benchmark_price = _latest_price_on_or_before(
                benchmark_adjusted, previous.date
            )
            if prior_benchmark_price and prior_benchmark_price > 0:
                benchmark_nav = previous.benchmark_nav * (benchmark_price / prior_benchmark_price)
            else:
                benchmark_nav = previous.benchmark_nav
    else:
        benchmark_nav = previous.benchmark_nav if previous is not None else INCEPTION_NAV

    cumulative_return_pct = nav / INCEPTION_NAV - 1.0
    benchmark_cumulative_return_pct = benchmark_nav / INCEPTION_NAV - 1.0

    open_positions = sorted(open_map.values(), key=lambda p: p.ticker)

    capital_plan = None
    if decisions:
        capital_plan = CapitalAllocationEngine().build(decisions, as_of)

    total_gain = nav - INCEPTION_NAV
    attribution: list[ShadowFundAttributionEntry] = []
    open_tickers = {p.ticker for p in open_positions}
    for ticker, contribution in sorted(attribution_state.items()):
        attribution.append(
            ShadowFundAttributionEntry(
                ticker=ticker,
                contribution_pct_of_total_gain=(
                    (contribution / total_gain) if abs(total_gain) > _EPS else None
                ),
                status="open" if ticker in open_tickers else "closed",
            )
        )

    all_returns = list(prior_daily_returns or [])
    if daily_return_pct is not None:
        all_returns.append(daily_return_pct)
    all_nav = list(prior_nav_series or [])
    all_nav.append(nav)
    risk = _compute_risk(all_returns, all_nav, open_positions)

    return ShadowFundSnapshot(
        date=as_of,
        inception_date=inception_date,
        nav=nav,
        cash=cash,
        cash_pct=(cash / nav) if nav > 0 else 0.0,
        invested_pct=1.0 - ((cash / nav) if nav > 0 else 0.0),
        daily_return_pct=daily_return_pct,
        cumulative_return_pct=cumulative_return_pct,
        benchmark_ticker=benchmark_ticker,
        benchmark_nav=benchmark_nav,
        benchmark_cumulative_return_pct=benchmark_cumulative_return_pct,
        open_positions=open_positions,
        closed_positions_today=closed_today,
        transactions=transactions,
        capital_allocation_plan=capital_plan,
        risk=risk,
        attribution=attribution,
        attribution_state=attribution_state,
        provenance=Provenance(
            produced_by="shadow_fund.engine@1.0.0",
            produced_at=datetime.now(),
            inputs=[ProvenanceRef(kind="recommendation", ref_id=rec.ticker) for rec in recommendations],
        ),
    )


def _compute_risk(
    daily_returns_pct: list[float], nav_series: list[float], open_positions: list[ShadowFundPosition]
) -> ShadowFundRiskMetrics:
    sample_days = len(daily_returns_pct)
    sufficient = sample_days >= MIN_RISK_SAMPLE_DAYS

    volatility = None
    sharpe = None
    if sufficient:
        stdev = statistics.stdev(daily_returns_pct)
        volatility = stdev * (252 ** 0.5)
        mean_return = statistics.fmean(daily_returns_pct)
        sharpe = (mean_return / stdev) * (252 ** 0.5) if stdev > _EPS else None

    max_drawdown = None
    if len(nav_series) >= 2:
        peak = nav_series[0]
        drawdown = 0.0
        for value in nav_series:
            peak = max(peak, value)
            drawdown = min(drawdown, (value / peak - 1.0) if peak > 0 else 0.0)
        max_drawdown = drawdown

    weights = [p.weight for p in open_positions]
    herfindahl = sum(w * w for w in weights) if weights else None
    largest = max(weights) if weights else None

    return ShadowFundRiskMetrics(
        volatility_annualized_pct=volatility,
        max_drawdown_pct=max_drawdown,
        sharpe_like_ratio=sharpe,
        herfindahl_index=herfindahl,
        largest_position_pct=largest,
        sample_days=sample_days,
        sample_status="sufficient" if sufficient else "insufficient_sample",
    )
