"""Corporate Events agent: studies price behavior around disclosed events.

Real, mechanical event-study-lite: for each corporate event in the
snapshot with enough return history on both sides, compare mean adjusted
return after the event to before it. A notable shift proposes a
post-event-drift hypothesis (single-asset). This is a candidate
observation for the pipeline to test — the tiny per-event sample is
exactly what the statistical gates and adversarial small-sample attack
exist to judge.
"""

from __future__ import annotations

import statistics
from datetime import datetime

from agx_research.agents.base import ResearchAgent, ResearchFinding
from agx_research.config import Horizon
from agx_research.data.adjustments import adjusted_returns_for_ticker
from agx_research.data.snapshot import DatasetSnapshot
from agx_research.domain.provenance import Provenance, ProvenanceRef


class CorporateEventsAgent(ResearchAgent):
    name = "corporate_events_agent"
    version = "1.0.0"

    def __init__(self, min_shift: float = 0.002, min_side_observations: int = 3):
        self.min_shift = min_shift
        self.min_side_observations = min_side_observations

    def research(self, snapshot: DatasetSnapshot) -> list[ResearchFinding]:
        findings: list[ResearchFinding] = []
        for ticker, events in snapshot.corporate_events.items():
            bars = snapshot.price_history.get(ticker, [])
            if len(bars) < 2 * self.min_side_observations + 1:
                continue
            returns = adjusted_returns_for_ticker(snapshot, ticker)
            return_dates = sorted(b.trade_date for b in bars)[1:]  # return t is dated by day t

            for event in events:
                before = [r for r, d in zip(returns, return_dates) if d <= event.event_date]
                after = [r for r, d in zip(returns, return_dates) if d > event.event_date]
                if len(before) < self.min_side_observations or len(after) < self.min_side_observations:
                    continue
                shift = statistics.fmean(after) - statistics.fmean(before)
                if abs(shift) < self.min_shift:
                    continue
                direction = "upward" if shift > 0 else "downward"
                findings.append(
                    ResearchFinding(
                        agent_name=self.name,
                        agent_version=self.version,
                        observed_at=snapshot.as_of,
                        observation=(
                            f"{ticker} mean adjusted return shifted {shift:+.4f} "
                            f"after its {event.event_type} on {event.event_date.isoformat()}"
                        ),
                        proposed_hypothesis_statement=(
                            f"{ticker} exhibits {direction} post-{event.event_type.lower()} drift"
                        ),
                        proposed_economic_rationale=(
                            f"Markets may underreact to {event.event_type.lower()} disclosures, "
                            f"incorporating the information into {ticker}'s price gradually "
                            "rather than instantly (post-event drift)."
                        ),
                        proposed_candidate_cause=(
                            f"Gradual incorporation of {event.event_type.lower()} information"
                        ),
                        affected_assets=[ticker],
                        horizon=Horizon.SWING,
                        evidence=[
                            f"pre_event_mean={statistics.fmean(before):.6f}",
                            f"post_event_mean={statistics.fmean(after):.6f}",
                            f"shift={shift:.6f}",
                            f"event_date={event.event_date.isoformat()}",
                        ],
                        provenance=Provenance(
                            produced_by=f"{self.name}@{self.version}",
                            produced_at=datetime.now(),
                            inputs=[ProvenanceRef(kind="dataset_snapshot", ref_id=snapshot.id)],
                        ),
                    )
                )
        return findings
