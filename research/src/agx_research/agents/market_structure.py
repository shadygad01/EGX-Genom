"""Market Structure agent: looks for lead-lag and co-movement relationships
between tickers (an instance of the vision document's "does EGX70 lead
EGX30?" style hypothesis).

This is the one agent with a working, concrete implementation in the
scaffold — an illustrative example of the `ResearchAgent` contract. It
consumes the `pairwise_return_correlation` feature and proposes a finding
when correlation exceeds a threshold; it makes no claim about lead vs. lag
timing yet (that requires lagged correlation across multiple windows, left
as future work) and should not be read as validated Alpha — it is only a
candidate observation for the hypothesis pipeline to test.
"""

from __future__ import annotations

from datetime import datetime

from agx_research.agents.base import ResearchAgent, ResearchFinding
from agx_research.config import Horizon
from agx_research.data.snapshot import DatasetSnapshot
from agx_research.domain.provenance import Provenance, ProvenanceRef
from agx_research.features.correlation import (
    PAIRWISE_RETURN_CORRELATION,
    compute_pairwise_return_correlation,
)


class MarketStructureAgent(ResearchAgent):
    name = "market_structure_agent"
    version = "0.1.0"

    def __init__(self, ticker_pairs: list[tuple[str, str]], correlation_threshold: float = 0.5):
        self.ticker_pairs = ticker_pairs
        self.correlation_threshold = correlation_threshold

    def research(self, snapshot: DatasetSnapshot) -> list[ResearchFinding]:
        findings: list[ResearchFinding] = []
        for ticker_a, ticker_b in self.ticker_pairs:
            correlation = compute_pairwise_return_correlation(snapshot, ticker_a, ticker_b)
            if correlation is None or abs(correlation) < self.correlation_threshold:
                continue
            findings.append(
                ResearchFinding(
                    agent_name=self.name,
                    agent_version=self.version,
                    observed_at=snapshot.as_of,
                    observation=(
                        f"{ticker_a} and {ticker_b} daily returns show "
                        f"{correlation:+.2f} correlation over the last {snapshot.lookback_days} days"
                    ),
                    proposed_hypothesis_statement=(
                        f"{ticker_a} return co-movement with {ticker_b} predicts "
                        f"short-horizon direction beyond chance"
                    ),
                    affected_assets=[ticker_a, ticker_b],
                    horizon=Horizon.MICRO,
                    evidence=[
                        f"{PAIRWISE_RETURN_CORRELATION.id}"
                        f"_v{PAIRWISE_RETURN_CORRELATION.version}={correlation:.4f}",
                        f"lookback_days={snapshot.lookback_days}",
                    ],
                    provenance=Provenance(
                        produced_by=f"{self.name}@{self.version}",
                        produced_at=datetime.now(),
                        inputs=[
                            ProvenanceRef(kind="dataset_snapshot", ref_id=snapshot.id),
                            ProvenanceRef(
                                kind="feature",
                                ref_id=PAIRWISE_RETURN_CORRELATION.id,
                                ref_version=PAIRWISE_RETURN_CORRELATION.version,
                            ),
                        ],
                    ),
                )
            )
        return findings
