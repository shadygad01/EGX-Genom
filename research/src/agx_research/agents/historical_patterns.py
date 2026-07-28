"""Historical Patterns agent: matches a ticker's current price-return
pattern against its own past episodes, over years of history, to see
whether similar patterns tended to be followed by a consistent subsequent
return (feeding the "what historical cases are similar?" explainability
requirement).

Real, mechanical implementation: for each ticker, take the most recent
`window`-day adjusted-return path as the "current pattern," slide the same
window across the rest of the ticker's own history (`snapshot.
long_price_history` -- a much wider window than every other agent's
`price_history`, see `data/snapshot.py`'s `pattern_lookback_days`), and
rank every non-overlapping historical window by mean-centered Euclidean
distance to the current one. The `top_k` closest analogs' actual
subsequent `forward_horizon`-day returns are the "what happened next"
evidence. A finding is proposed only when enough analogs exist *and* they
agree in direction beyond `agreement_threshold` -- anything weaker is an
honest skip (no invented pattern), never a forced signal.
"""

from __future__ import annotations

import math
import statistics
from datetime import datetime

from agx_research.agents.base import ResearchAgent, ResearchFinding
from agx_research.config import Horizon
from agx_research.data.adjustments import adjusted_daily_returns
from agx_research.data.snapshot import DatasetSnapshot
from agx_research.domain.provenance import Provenance, ProvenanceRef


def _mean_centered(vector: list[float]) -> list[float]:
    mean = statistics.fmean(vector)
    return [v - mean for v in vector]


def _euclidean_distance(a: list[float], b: list[float]) -> float:
    return math.sqrt(sum((x - y) ** 2 for x, y in zip(a, b)))


def _cumulative_return(returns: list[float]) -> float:
    total = 1.0
    for r in returns:
        total *= 1 + r
    return total - 1.0


class HistoricalPatternsAgent(ResearchAgent):
    name = "historical_patterns_agent"
    version = "1.0.0"

    def __init__(
        self,
        window: int = 20,
        forward_horizon: int = 10,
        top_k: int = 5,
        min_analogs: int = 4,
        agreement_threshold: float = 0.7,
    ):
        self.window = window
        self.forward_horizon = forward_horizon
        self.top_k = top_k
        self.min_analogs = min_analogs
        self.agreement_threshold = agreement_threshold

    def research(self, snapshot: DatasetSnapshot) -> list[ResearchFinding]:
        findings: list[ResearchFinding] = []
        for ticker in sorted(snapshot.tickers):
            long_bars = snapshot.long_price_history.get(ticker, [])
            if len(long_bars) < self.window + self.forward_horizon + 1:
                continue
            events = snapshot.long_corporate_events.get(ticker, [])
            returns = adjusted_daily_returns(long_bars, events)
            dates = sorted(b.trade_date for b in long_bars)
            n = len(returns)
            current_start = n - self.window
            if current_start <= self.forward_horizon:
                continue
            current_pattern = _mean_centered(returns[current_start:])

            candidates: list[tuple[float, int, float]] = []
            for start in range(0, current_start - self.forward_horizon):
                historical_window = returns[start : start + self.window]
                distance = _euclidean_distance(
                    current_pattern, _mean_centered(historical_window)
                )
                forward_returns = returns[start + self.window : start + self.window + self.forward_horizon]
                candidates.append((distance, start, _cumulative_return(forward_returns)))
            candidates.sort(key=lambda c: c[0])

            selected: list[tuple[float, int, float]] = []
            for distance, start, forward_return in candidates:
                if any(abs(start - s) < self.window for _, s, _ in selected):
                    continue
                selected.append((distance, start, forward_return))
                if len(selected) >= self.top_k:
                    break
            if len(selected) < self.min_analogs:
                continue

            positive = sum(1 for _, _, fr in selected if fr > 0)
            negative = len(selected) - positive
            agreement = max(positive, negative) / len(selected)
            if agreement < self.agreement_threshold:
                continue
            direction = "positive" if positive >= negative else "negative"
            mean_forward_return = statistics.fmean(fr for _, _, fr in selected)

            analog_evidence = [
                f"episode {dates[start + 1]}..{dates[start + self.window]} "
                f"(distance={distance:.4f}, next_{self.forward_horizon}d_return={forward_return:+.2%})"
                for distance, start, forward_return in selected
            ]

            findings.append(
                ResearchFinding(
                    agent_name=self.name,
                    agent_version=self.version,
                    observed_at=snapshot.as_of,
                    observation=(
                        f"{ticker}'s most recent {self.window}-trading-day adjusted-return pattern "
                        f"matches {len(selected)} non-overlapping historical episodes across "
                        f"{len(long_bars)} bars of its own history; {max(positive, negative)}/"
                        f"{len(selected)} were followed by a {direction} {self.forward_horizon}-day "
                        f"return (mean {mean_forward_return:+.2%})"
                    ),
                    proposed_hypothesis_statement=(
                        f"{ticker} tends toward a {direction} return over the next "
                        f"{self.forward_horizon} trading days when its recent return path "
                        "resembles these historical analogs"
                    ),
                    proposed_economic_rationale=(
                        "A recurring return-path shape may reflect similar underlying "
                        "supply/demand conditions (e.g. accumulation or distribution phases) "
                        "recurring across market cycles, producing similar subsequent returns."
                    ),
                    proposed_candidate_cause=(
                        "Recurring supply/demand regime produces analogous forward returns"
                    ),
                    affected_assets=[ticker],
                    horizon=Horizon.SWING,
                    evidence=[
                        f"window_days={self.window}",
                        f"forward_horizon_days={self.forward_horizon}",
                        f"analogs_matched={len(selected)}",
                        f"directional_agreement={agreement:.2%}",
                        f"mean_forward_return={mean_forward_return:+.4f}",
                        *analog_evidence,
                    ],
                    provenance=Provenance(
                        produced_by=f"{self.name}@{self.version}",
                        produced_at=datetime.now(),
                        inputs=[ProvenanceRef(kind="dataset_snapshot", ref_id=snapshot.id)],
                    ),
                )
            )
        return findings
