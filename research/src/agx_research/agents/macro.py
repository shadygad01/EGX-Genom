"""Macro agent: relates macroeconomic series moves to stock returns.

Real, mechanical implementation: Pearson correlation between a macro
series' period-over-period percentage changes and each ticker's adjusted
daily returns over the snapshot window. Proposes a finding when
|correlation| clears the threshold. The proposed rationale is a stated
mechanism hypothesis (judged downstream by the causal gate/economist
reviewer), never asserted as established truth.

Macro series publish at their own frequency (daily FRED series, monthly
CAPMAS, annual World Bank/UN SDG) which almost never lands exactly on a
trading day -- aligning by raw date equality silently starved every
lower-frequency series of any correlation at all. `_forward_fill_onto`
carries each macro observation's latest known percentage change forward
onto every trading day up to (not including) the next observation --
standard last-observation-carried-forward step alignment, the same
"assume nothing changed until told otherwise" discipline real point-in-
time backtesting uses. This never looks ahead: a trading day is only ever
assigned a change from an observation dated on or before it.
`data.snapshot.build_snapshot`'s `macro_series_sources`-driven filtering
(`data.point_in_time`) is what keeps an observation out of the snapshot
entirely until it was actually knowable in the first place; this
alignment only decides which already-admitted observation applies to
which trading day.
"""

from __future__ import annotations

from bisect import bisect_right
from datetime import date, datetime

from agx_research.agents.base import ResearchAgent, ResearchFinding
from agx_research.config import Horizon
from agx_research.data.adjustments import adjusted_returns_for_ticker
from agx_research.data.snapshot import DatasetSnapshot
from agx_research.domain.provenance import Provenance, ProvenanceRef
from agx_research.features.correlation import pearson_correlation


def _forward_fill_onto(
    changes_by_date: dict[date, float], trading_dates: list[date]
) -> dict[date, float]:
    """Carry each macro observation's change forward onto every trading
    date on or after it, up to the next observation -- never onto a
    trading date before the observation's own date (no look-ahead)."""
    observed_dates = sorted(changes_by_date)
    aligned: dict[date, float] = {}
    for trading_date in trading_dates:
        idx = bisect_right(observed_dates, trading_date) - 1
        if idx >= 0:
            aligned[trading_date] = changes_by_date[observed_dates[idx]]
    return aligned

# Mock fixtures (`research/data/mock/macro/`) and real LIVE production data
# (`production/collector_plan.py`'s `LIVE_FRED_SERIES_IDS`/
# `LIVE_WORLDBANK_INDICATORS`) name the same real-world series under
# different ids -- both are declared here so a real run's findings get a
# real mechanism sentence instead of silently falling back to the generic
# "sensitivity to {series_id}" below for every series a real run actually
# produces.
_SERIES_MECHANISMS: dict[str, str] = {
    "BRENT_USD": "oil-price exposure of input costs and export revenues",
    "DCOILBRENTEU": "oil-price exposure of input costs and export revenues",
    "DCOILWTICO": "oil-price exposure of input costs and export revenues",
    "EGP_USD": "currency exposure of imported costs, foreign-currency debt, and repatriated earnings",
    "egypt_official_fx_egp_per_usd": (
        "currency exposure of imported costs, foreign-currency debt, and repatriated earnings"
    ),
    "DTWEXBGS": "broad-dollar exposure affecting import costs and dollar-denominated debt",
    "VIXCLS": "global risk aversion affecting emerging-market capital flows and equity risk premia",
    "DGS2": "short-term US rate exposure affecting the relative attractiveness of EGP carry",
    "DGS10": "global discount-rate exposure affecting the present value of future earnings",
    "BAMLH0A0HYM2": "global credit-risk-appetite exposure affecting emerging-market funding costs",
    "egypt_cpi_inflation": "domestic inflation exposure affecting real margins and consumer demand",
    "egypt_real_gdp_growth": "domestic demand exposure affecting revenue growth",
    "egypt_current_account_pct_gdp": "external-balance exposure affecting FX availability and EGP stability",
    "egypt_total_reserves_usd": "FX-reserve exposure affecting import cover and currency stability",
    "egypt_lending_rate": "domestic interest-rate exposure affecting financing costs and discount rates",
    "egypt_unemployment_rate": "labor-market exposure affecting consumer demand",
    "egypt_exports_pct_gdp": "export-sector exposure to external demand and FX earnings",
    "egypt_imports_pct_gdp": "import-dependence exposure to FX cost and input pricing",
    "egypt_fdi_net_inflows_pct_gdp": "foreign-investment-flow exposure affecting FX supply and EGP stability",
    "egypt_external_debt_usd": "external-debt exposure affecting FX-denominated debt-service burden",
}


class MacroAgent(ResearchAgent):
    name = "macro_agent"
    version = "1.0.0"

    def __init__(self, correlation_threshold: float = 0.5):
        self.correlation_threshold = correlation_threshold

    def research(self, snapshot: DatasetSnapshot) -> list[ResearchFinding]:
        findings: list[ResearchFinding] = []
        for series_id, observations in snapshot.macro_series.items():
            if len(observations) < 4:
                continue
            macro_changes_by_date = {
                curr.observation_date: (curr.value - prev.value) / prev.value
                for prev, curr in zip(observations, observations[1:])
                if prev.value != 0
            }
            for ticker in sorted(snapshot.tickers):
                bars = snapshot.price_history.get(ticker, [])
                returns = adjusted_returns_for_ticker(snapshot, ticker)
                returns_by_date = {bar.trade_date: value for bar, value in zip(bars[1:], returns)}
                trading_dates = sorted(returns_by_date)
                forward_filled_macro = _forward_fill_onto(macro_changes_by_date, trading_dates)
                common_dates = sorted(forward_filled_macro)
                if len(common_dates) < 4:
                    continue
                aligned_macro = [forward_filled_macro[d] for d in common_dates]
                aligned_returns = [returns_by_date[d] for d in common_dates]
                correlation = pearson_correlation(aligned_macro, aligned_returns)
                if correlation is None or abs(correlation) < self.correlation_threshold:
                    continue
                mechanism = _SERIES_MECHANISMS.get(series_id, f"sensitivity to {series_id}")
                findings.append(
                    ResearchFinding(
                        agent_name=self.name,
                        agent_version=self.version,
                        observed_at=snapshot.as_of,
                        observation=(
                            f"{ticker} adjusted returns show {correlation:+.2f} correlation "
                            f"with {series_id} daily changes over {snapshot.lookback_days} days"
                        ),
                        proposed_hypothesis_statement=(
                            f"{ticker} returns co-move with {series_id} changes beyond chance"
                        ),
                        proposed_economic_rationale=(
                            f"{ticker}'s cash flows plausibly carry {mechanism}, which would "
                            f"produce genuine sensitivity of its returns to {series_id} moves."
                        ),
                        proposed_candidate_cause=f"{ticker} exposure via {mechanism}",
                        affected_assets=[ticker],
                        horizon=Horizon.SWING,
                        evidence=[
                            f"macro_correlation={correlation:.4f}",
                            f"series={series_id}",
                            f"observations={len(common_dates)}",
                        ],
                        provenance=Provenance(
                            produced_by=f"{self.name}@{self.version}",
                            produced_at=datetime.now(),
                            inputs=[ProvenanceRef(kind="dataset_snapshot", ref_id=snapshot.id)],
                        ),
                    )
                )
        return findings
