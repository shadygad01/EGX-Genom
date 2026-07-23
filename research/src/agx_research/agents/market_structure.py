"""Market Structure agent: looks for lead-lag and co-movement relationships
between tickers (an instance of the vision document's "does EGX70 lead
EGX30?" style hypothesis).

This is the one agent with a working, concrete implementation in the
scaffold — an illustrative example of the `ResearchAgent` contract. It
computes same-day return correlation between a pair of tickers and proposes
a finding when correlation exceeds a threshold; it makes no claim about lead
vs. lag timing yet (that requires lagged correlation across multiple
windows, left as future work) and should not be read as validated Alpha —
it is only a candidate observation for the hypothesis pipeline to test.
"""

from __future__ import annotations

from datetime import date, timedelta

from agx_research.agents.base import ResearchAgent, ResearchFinding
from agx_research.config import Horizon
from agx_research.data.provider import DataProvider


def _daily_returns(closes: list[float]) -> list[float]:
    return [(closes[i] - closes[i - 1]) / closes[i - 1] for i in range(1, len(closes))]


def _pearson_correlation(a: list[float], b: list[float]) -> float | None:
    n = min(len(a), len(b))
    if n < 2:
        return None
    a, b = a[-n:], b[-n:]
    mean_a, mean_b = sum(a) / n, sum(b) / n
    cov = sum((x - mean_a) * (y - mean_b) for x, y in zip(a, b))
    var_a = sum((x - mean_a) ** 2 for x in a)
    var_b = sum((y - mean_b) ** 2 for y in b)
    if var_a == 0 or var_b == 0:
        return None
    return cov / (var_a**0.5 * var_b**0.5)


class MarketStructureAgent(ResearchAgent):
    name = "market_structure_agent"

    def __init__(self, ticker_pairs: list[tuple[str, str]], lookback_days: int = 30,
                 correlation_threshold: float = 0.5):
        self.ticker_pairs = ticker_pairs
        self.lookback_days = lookback_days
        self.correlation_threshold = correlation_threshold

    def research(self, data_provider: DataProvider, as_of: date) -> list[ResearchFinding]:
        start = as_of - timedelta(days=self.lookback_days)
        findings: list[ResearchFinding] = []
        for ticker_a, ticker_b in self.ticker_pairs:
            bars_a = data_provider.get_price_history(ticker_a, start, as_of)
            bars_b = data_provider.get_price_history(ticker_b, start, as_of)
            if len(bars_a) < 3 or len(bars_b) < 3:
                continue
            returns_a = _daily_returns([b.close for b in bars_a])
            returns_b = _daily_returns([b.close for b in bars_b])
            correlation = _pearson_correlation(returns_a, returns_b)
            if correlation is None or abs(correlation) < self.correlation_threshold:
                continue
            findings.append(
                ResearchFinding(
                    agent_name=self.name,
                    observed_at=as_of,
                    observation=(
                        f"{ticker_a} and {ticker_b} daily returns show "
                        f"{correlation:+.2f} correlation over the last {self.lookback_days} days"
                    ),
                    proposed_hypothesis_statement=(
                        f"{ticker_a} return co-movement with {ticker_b} predicts "
                        f"short-horizon direction beyond chance"
                    ),
                    affected_assets=[ticker_a, ticker_b],
                    horizon=Horizon.MICRO,
                    evidence=[
                        f"pearson_correlation={correlation:.4f}",
                        f"lookback_days={self.lookback_days}",
                    ],
                )
            )
        return findings
