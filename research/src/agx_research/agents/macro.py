"""Macro agent: relates macroeconomic series moves to stock returns.

Real, mechanical implementation: Pearson correlation between a macro
series' day-over-day percentage changes and each ticker's adjusted daily
returns over the snapshot window. Proposes a finding when |correlation|
clears the threshold. The proposed rationale is a stated mechanism
hypothesis (judged downstream by the causal gate/economist reviewer),
never asserted as established truth.
"""

from __future__ import annotations

from datetime import datetime

from agx_research.agents.base import ResearchAgent, ResearchFinding
from agx_research.config import Horizon
from agx_research.data.adjustments import adjusted_returns_for_ticker
from agx_research.data.snapshot import DatasetSnapshot
from agx_research.domain.provenance import Provenance, ProvenanceRef
from agx_research.features.correlation import pearson_correlation

_SERIES_MECHANISMS: dict[str, str] = {
    "BRENT_USD": "oil-price exposure of input costs and export revenues",
    "EGP_USD": "currency exposure of imported costs, foreign-currency debt, and repatriated earnings",
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
                common_dates = sorted(set(macro_changes_by_date) & set(returns_by_date))
                if len(common_dates) < 4:
                    continue
                aligned_macro = [macro_changes_by_date[d] for d in common_dates]
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
