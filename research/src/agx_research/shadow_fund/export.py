"""Dashboard-facing exports derived from `ShadowFundLedger`'s append-only
daily history -- `shadow_fund.json` (today's full state) and
`shadow_fund_history.json` (the NAV time series + the all-time transaction/
closed-position log), following the same "small current-state artifact +
separate history artifact" split `meta.decision_ledger` already uses
(`decision_performance.json` vs `decision_history.json`). Growth here is
bounded by real trading activity (transactions only exist where the
rebalance threshold was actually crossed), not by elapsed time x universe
size -- the exact axis that made `provenance_index.json` unbounded
(TD-63); still worth watching, see the matching technical-debt entry.
"""

from __future__ import annotations

from agx_research.shadow_fund.models import ShadowFundHistory, ShadowFundNavPoint, ShadowFundPublicState
from agx_research.shadow_fund.repository import ShadowFundLedger


def export_shadow_fund(ledger: ShadowFundLedger) -> ShadowFundPublicState | None:
    """Today's complete Shadow Fund state, or `None` if the fund hasn't
    started yet (no trading day has run since this package shipped)."""
    latest = ledger.latest_snapshot()
    if latest is None:
        return None

    closed_positions = [
        closed for snapshot in ledger.daily_history() for closed in snapshot.closed_positions_today
    ]

    return ShadowFundPublicState(
        date=latest.date,
        inception_date=latest.inception_date,
        nav=latest.nav,
        cash=latest.cash,
        cash_pct=latest.cash_pct,
        invested_pct=latest.invested_pct,
        daily_return_pct=latest.daily_return_pct,
        cumulative_return_pct=latest.cumulative_return_pct,
        benchmark_ticker=latest.benchmark_ticker,
        benchmark_nav=latest.benchmark_nav,
        benchmark_cumulative_return_pct=latest.benchmark_cumulative_return_pct,
        excess_return_pct=latest.cumulative_return_pct - latest.benchmark_cumulative_return_pct,
        open_positions=latest.open_positions,
        closed_positions=closed_positions,
        transactions=latest.transactions,
        capital_allocation_plan=latest.capital_allocation_plan,
        risk=latest.risk,
        attribution=latest.attribution,
        provenance=latest.provenance,
    )


def export_shadow_fund_history(ledger: ShadowFundLedger) -> ShadowFundHistory:
    history = ledger.daily_history()
    nav_series = [
        ShadowFundNavPoint(
            date=snapshot.date,
            nav=snapshot.nav,
            cash=snapshot.cash,
            cash_pct=snapshot.cash_pct,
            invested_pct=snapshot.invested_pct,
            daily_return_pct=snapshot.daily_return_pct,
            cumulative_return_pct=snapshot.cumulative_return_pct,
            benchmark_nav=snapshot.benchmark_nav,
            benchmark_cumulative_return_pct=snapshot.benchmark_cumulative_return_pct,
        )
        for snapshot in history
    ]
    transactions = [txn for snapshot in history for txn in snapshot.transactions]
    return ShadowFundHistory(nav_series=nav_series, transactions=transactions)
