"""Liquidity agent: relates trading volume to subsequent returns.

Real, mechanical implementation: correlation between each ticker's volume
z-score on day t-1 and its adjusted return on day t. A notable
relationship proposes a volume-leads-return hypothesis. Foreign/local flow
decomposition (the vision's "do foreign inflows predict banking strength?")
remains data-blocked — volume is the flow proxy actually present in the
snapshot.
"""

from __future__ import annotations

import statistics
from datetime import datetime

from agx_research.agents.base import ResearchAgent, ResearchFinding
from agx_research.config import Horizon
from agx_research.data.adjustments import adjusted_returns_for_ticker
from agx_research.data.snapshot import DatasetSnapshot
from agx_research.domain.provenance import Provenance, ProvenanceRef
from agx_research.features.correlation import pearson_correlation


class LiquidityAgent(ResearchAgent):
    name = "liquidity_agent"
    version = "1.0.0"

    def __init__(self, correlation_threshold: float = 0.5):
        self.correlation_threshold = correlation_threshold

    def research(self, snapshot: DatasetSnapshot) -> list[ResearchFinding]:
        findings: list[ResearchFinding] = []
        for ticker in sorted(snapshot.tickers):
            bars = snapshot.price_history.get(ticker, [])
            returns = adjusted_returns_for_ticker(snapshot, ticker)
            if len(bars) < 6 or len(returns) < 5:
                continue
            volumes = [float(b.volume) for b in bars]
            mean_volume = statistics.fmean(volumes)
            std_volume = statistics.pstdev(volumes)
            if std_volume == 0:
                continue
            z_scores = [(v - mean_volume) / std_volume for v in volumes]

            # volume z-score at day t-1 (bars index t-1) vs return at day t
            # (returns index t-1 corresponds to bars[t-1] -> bars[t]).
            lagged_z = z_scores[:-2] if len(z_scores) > len(returns) else z_scores[: len(returns) - 1]
            next_returns = returns[1:][: len(lagged_z)]
            lagged_z = lagged_z[: len(next_returns)]
            correlation = pearson_correlation(lagged_z, next_returns)
            if correlation is None or abs(correlation) < self.correlation_threshold:
                continue

            findings.append(
                ResearchFinding(
                    agent_name=self.name,
                    agent_version=self.version,
                    observed_at=snapshot.as_of,
                    observation=(
                        f"{ticker} prior-day volume z-score shows {correlation:+.2f} "
                        f"correlation with next-day adjusted return"
                    ),
                    proposed_hypothesis_statement=(
                        f"{ticker} unusual volume precedes directional next-day returns"
                    ),
                    proposed_economic_rationale=(
                        f"Unusual volume in {ticker} may reflect informed or institutional "
                        "flow whose price impact completes over the following session "
                        "rather than instantly (liquidity-driven continuation)."
                    ),
                    proposed_candidate_cause="Informed/institutional flow with delayed price impact",
                    affected_assets=[ticker],
                    horizon=Horizon.MICRO,
                    evidence=[
                        f"volume_return_correlation={correlation:.4f}",
                        f"observations={len(lagged_z)}",
                    ],
                    provenance=Provenance(
                        produced_by=f"{self.name}@{self.version}",
                        produced_at=datetime.now(),
                        inputs=[ProvenanceRef(kind="dataset_snapshot", ref_id=snapshot.id)],
                    ),
                )
            )
        return findings
