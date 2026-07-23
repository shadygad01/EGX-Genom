"""Technical Structure agent: price-trend regularities as candidate hypotheses.

Real, mechanical implementation: a short/long moving-average comparison on
adjusted closes. When the short MA sits decisively above (below) the long
MA, it proposes a continuation hypothesis — as a candidate observation for
the pipeline to test, not an encoded trading rule (the vision explicitly
forbids the latter; the difference is that nothing here bypasses
validation).
"""

from __future__ import annotations

import statistics
from datetime import datetime

from agx_research.agents.base import ResearchAgent, ResearchFinding
from agx_research.config import Horizon
from agx_research.data.adjustments import compute_adjusted_closes
from agx_research.data.snapshot import DatasetSnapshot
from agx_research.domain.provenance import Provenance, ProvenanceRef


class TechnicalStructureAgent(ResearchAgent):
    name = "technical_structure_agent"
    version = "1.0.0"

    def __init__(self, short_window: int = 3, long_window: int = 8, min_gap: float = 0.005):
        if short_window >= long_window:
            raise ValueError("short_window must be smaller than long_window")
        self.short_window = short_window
        self.long_window = long_window
        self.min_gap = min_gap

    def research(self, snapshot: DatasetSnapshot) -> list[ResearchFinding]:
        findings: list[ResearchFinding] = []
        for ticker in sorted(snapshot.tickers):
            bars = snapshot.price_history.get(ticker, [])
            if len(bars) < self.long_window:
                continue
            events = snapshot.corporate_events.get(ticker, [])
            adjusted = compute_adjusted_closes(bars, events)
            closes = [adjusted[d] for d in sorted(adjusted)]

            short_ma = statistics.fmean(closes[-self.short_window :])
            long_ma = statistics.fmean(closes[-self.long_window :])
            if long_ma == 0:
                continue
            gap = (short_ma - long_ma) / long_ma
            if abs(gap) < self.min_gap:
                continue
            direction = "above" if gap > 0 else "below"
            trend = "upward" if gap > 0 else "downward"

            findings.append(
                ResearchFinding(
                    agent_name=self.name,
                    agent_version=self.version,
                    observed_at=snapshot.as_of,
                    observation=(
                        f"{ticker} {self.short_window}-day MA is {gap:+.3%} {direction} its "
                        f"{self.long_window}-day MA on adjusted closes"
                    ),
                    proposed_hypothesis_statement=(
                        f"{ticker} short-term {trend} trend persists beyond chance"
                    ),
                    proposed_economic_rationale=(
                        f"A sustained MA gap in {ticker} may reflect gradual position "
                        "building by investors who spread orders over days to limit "
                        "market impact, producing short-horizon trend persistence."
                    ),
                    proposed_candidate_cause="Order-splitting flow producing trend persistence",
                    affected_assets=[ticker],
                    horizon=Horizon.MICRO,
                    evidence=[
                        f"short_ma={short_ma:.4f}",
                        f"long_ma={long_ma:.4f}",
                        f"ma_gap={gap:.5f}",
                    ],
                    provenance=Provenance(
                        produced_by=f"{self.name}@{self.version}",
                        produced_at=datetime.now(),
                        inputs=[ProvenanceRef(kind="dataset_snapshot", ref_id=snapshot.id)],
                    ),
                )
            )
        return findings
