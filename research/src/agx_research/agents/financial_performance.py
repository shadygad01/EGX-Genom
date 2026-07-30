"""Financial Performance agent: relates fundamentals (growth, leverage) to
forward returns.

Real, mechanical implementation, mirroring `agents.corporate_events`'s
event-study-lite structure: for each ticker with enough comparable
financial-statement periods, compute (a) a revenue growth-trend shift
(the most recent period-over-period growth rate vs. the ticker's own
trailing average) and (b) a leverage-trend shift (debt-to-equity, most
recent period vs. its own trailing average). A shift beyond a declared
threshold proposes an INVESTMENT-horizon hypothesis -- fundamentals are a
long-run signal, never a short-run one, matching the mission this agent
was built for (long-term EGX investing specifically; see
`docs/DECISION_EVIDENCE_MATRIX.md` Q2/Q3 and
`docs/ARCHITECTURE_ADVERSARIAL_REVIEW.md` R9).

Both signals are read directly from whatever `line_item`s a source
actually reports (`financials.schema.STANDARD_LINE_ITEMS`' `revenue`/
`total_debt`/`total_equity`) -- never a derived ratio invented ahead of
what a real collector actually produces. A ticker whose collected
statements don't include a needed line item simply produces no finding
for that signal, never a fabricated one. `min_periods` (default 4)
matches `meta.readiness.assess_decision_readiness`'s own INVESTMENT-
horizon floor deliberately, not an independently chosen number.

Deliberately not built as three separately-maintained "Reads" (Valuation/
Growth/Balance-Sheet Safety): both signals below come from the same
snapshot field and the same per-ticker extraction, closing the
three-way-disagreement risk `docs/ARCHITECTURE_ADVERSARIAL_REVIEW.md`
Section 1.9 named. Valuation (Q1) is deliberately not attempted here: it
needs a current price *and* a peer/own-history multiple band, which is a
decision-time computation (the Decision Service), not a research-time
finding -- the same "research vs. decide" boundary
`agents.base.ResearchAgent`'s own docstring already draws.
"""

from __future__ import annotations

import statistics
from datetime import date, datetime

from agx_research.agents.base import ResearchAgent, ResearchFinding
from agx_research.config import Horizon
from agx_research.data.snapshot import DatasetSnapshot
from agx_research.domain.provenance import Provenance, ProvenanceRef
from agx_research.financials.schema import FinancialStatementLineItem


def _periods_for(
    items: list[FinancialStatementLineItem], line_item: str
) -> list[tuple[date, float]]:
    by_period = {i.period_end_date: i.value for i in items if i.line_item == line_item}
    return sorted(by_period.items())


class FinancialPerformanceAgent(ResearchAgent):
    name = "financial_performance_agent"
    version = "1.0.0"

    def __init__(
        self,
        min_periods: int = 4,
        min_growth_shift: float = 0.05,
        min_leverage_shift: float = 0.15,
    ):
        self.min_periods = min_periods
        self.min_growth_shift = min_growth_shift
        self.min_leverage_shift = min_leverage_shift

    def research(self, snapshot: DatasetSnapshot) -> list[ResearchFinding]:
        findings: list[ResearchFinding] = []
        for ticker, items in snapshot.financial_statements.items():
            findings.extend(self._growth_trend_finding(ticker, items, snapshot))
            findings.extend(self._leverage_trend_finding(ticker, items, snapshot))
        return findings

    def _growth_trend_finding(
        self, ticker: str, items: list[FinancialStatementLineItem], snapshot: DatasetSnapshot
    ) -> list[ResearchFinding]:
        periods = _periods_for(items, "revenue")
        if len(periods) < self.min_periods:
            return []
        values = [v for _, v in periods]
        growth_rates = [
            (values[i] - values[i - 1]) / values[i - 1]
            for i in range(1, len(values))
            if values[i - 1] != 0
        ]
        if len(growth_rates) < self.min_periods - 1:
            return []
        recent = growth_rates[-1]
        trailing = statistics.fmean(growth_rates[:-1]) if len(growth_rates) > 1 else growth_rates[-1]
        shift = recent - trailing
        if abs(shift) < self.min_growth_shift:
            return []
        direction = "accelerating" if shift > 0 else "decelerating"
        latest_period = periods[-1][0]
        return [
            ResearchFinding(
                agent_name=self.name,
                agent_version=self.version,
                observed_at=snapshot.as_of,
                observation=(
                    f"{ticker} revenue growth rate shifted {shift:+.4f} in its most recent "
                    f"reported period ({latest_period.isoformat()}) vs. its own trailing average"
                ),
                proposed_hypothesis_statement=f"{ticker} exhibits {direction} revenue growth",
                proposed_economic_rationale=(
                    f"A material change in {ticker}'s reported revenue growth rate plausibly "
                    "precedes a corresponding re-rating of its long-term earnings power, which "
                    "markets may incorporate gradually rather than instantly."
                ),
                proposed_candidate_cause=f"{direction.capitalize()} revenue growth",
                affected_assets=[ticker],
                horizon=Horizon.INVESTMENT,
                evidence=[
                    f"recent_growth_rate={recent:.4f}",
                    f"trailing_growth_rate={trailing:.4f}",
                    f"shift={shift:.4f}",
                    f"periods={len(periods)}",
                    f"latest_period_end={latest_period.isoformat()}",
                ],
                provenance=Provenance(
                    produced_by=f"{self.name}@{self.version}",
                    produced_at=datetime.now(),
                    inputs=[ProvenanceRef(kind="dataset_snapshot", ref_id=snapshot.id)],
                ),
            )
        ]

    def _leverage_trend_finding(
        self, ticker: str, items: list[FinancialStatementLineItem], snapshot: DatasetSnapshot
    ) -> list[ResearchFinding]:
        debt_periods = dict(_periods_for(items, "total_debt"))
        equity_periods = dict(_periods_for(items, "total_equity"))
        common = sorted(set(debt_periods) & set(equity_periods))
        if len(common) < self.min_periods:
            return []
        ratios = [
            (period, debt_periods[period] / equity_periods[period])
            for period in common
            if equity_periods[period] != 0
        ]
        if len(ratios) < self.min_periods:
            return []
        values = [r for _, r in ratios]
        recent = values[-1]
        trailing = statistics.fmean(values[:-1])
        if trailing == 0:
            return []
        shift = (recent - trailing) / abs(trailing)
        if abs(shift) < self.min_leverage_shift:
            return []
        direction = "rising" if shift > 0 else "falling"
        safety = "deteriorating" if shift > 0 else "improving"
        latest_period = ratios[-1][0]
        return [
            ResearchFinding(
                agent_name=self.name,
                agent_version=self.version,
                observed_at=snapshot.as_of,
                observation=(
                    f"{ticker} debt-to-equity ratio is {direction} ({recent:.3f} vs. trailing "
                    f"average {trailing:.3f}) as of {latest_period.isoformat()}"
                ),
                proposed_hypothesis_statement=f"{ticker} exhibits {safety} balance-sheet leverage",
                proposed_economic_rationale=(
                    f"A material change in {ticker}'s leverage plausibly changes its cost of "
                    "capital and downside risk, which a long-term valuation should reflect."
                ),
                proposed_candidate_cause=f"{direction.capitalize()} leverage",
                affected_assets=[ticker],
                horizon=Horizon.INVESTMENT,
                evidence=[
                    f"recent_debt_to_equity={recent:.4f}",
                    f"trailing_debt_to_equity={trailing:.4f}",
                    f"shift_pct={shift:.4f}",
                    f"periods={len(ratios)}",
                    f"latest_period_end={latest_period.isoformat()}",
                ],
                provenance=Provenance(
                    produced_by=f"{self.name}@{self.version}",
                    produced_at=datetime.now(),
                    inputs=[ProvenanceRef(kind="dataset_snapshot", ref_id=snapshot.id)],
                ),
            )
        ]
