"""News Intelligence agent: classifies news-flow sentiment and relates it
to subsequent price behavior.

Real, mechanical event-study-lite, mirroring `CorporateEventsAgent`
exactly: for each ticker's sentiment-classified news item with enough
return history on both sides, compare mean adjusted return after the item
to before it. `news_sentiment.classify_headline_sentiment()` is a
declared, uncalibrated keyword heuristic (TD-35) -- never a fabricated NLP
score -- so a headline that matches nothing is silently skipped, not
guessed.
"""

from __future__ import annotations

import statistics
from datetime import datetime

from agx_research.agents.base import ResearchAgent, ResearchFinding
from agx_research.agents.news_sentiment import classify_headline_sentiment
from agx_research.config import Horizon
from agx_research.data.adjustments import adjusted_returns_for_ticker
from agx_research.data.snapshot import DatasetSnapshot
from agx_research.domain.provenance import Provenance, ProvenanceRef


class NewsIntelligenceAgent(ResearchAgent):
    name = "news_intelligence_agent"
    version = "1.0.0"

    def __init__(self, min_shift: float = 0.002, min_side_observations: int = 3):
        self.min_shift = min_shift
        self.min_side_observations = min_side_observations

    def research(self, snapshot: DatasetSnapshot) -> list[ResearchFinding]:
        findings: list[ResearchFinding] = []
        news_by_ticker: dict[str, list] = {}
        for item in snapshot.news:
            for ticker in item.tickers:
                news_by_ticker.setdefault(ticker, []).append(item)

        for ticker, items in news_by_ticker.items():
            bars = snapshot.price_history.get(ticker, [])
            if len(bars) < 2 * self.min_side_observations + 1:
                continue
            returns = adjusted_returns_for_ticker(snapshot, ticker)
            return_dates = sorted(b.trade_date for b in bars)[1:]  # return t is dated by day t

            for item in items:
                sentiment = classify_headline_sentiment(item.headline)
                if sentiment is None:
                    continue

                before = [r for r, d in zip(returns, return_dates) if d <= item.published_at]
                after = [r for r, d in zip(returns, return_dates) if d > item.published_at]
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
                            f"{ticker} mean adjusted return shifted {shift:+.4f} following "
                            f"{sentiment} news ({item.source}, {item.published_at.isoformat()}): "
                            f'"{item.headline}"'
                        ),
                        proposed_hypothesis_statement=(
                            f"{ticker} exhibits {direction} price drift following {sentiment} news"
                        ),
                        proposed_economic_rationale=(
                            f"Markets may underreact to {sentiment} news sentiment, incorporating "
                            f"it into {ticker}'s price gradually rather than instantly "
                            "(post-news drift)."
                        ),
                        proposed_candidate_cause=f"Gradual incorporation of {sentiment} news sentiment",
                        affected_assets=[ticker],
                        horizon=Horizon.MICRO,
                        evidence=[
                            f"pre_news_mean={statistics.fmean(before):.6f}",
                            f"post_news_mean={statistics.fmean(after):.6f}",
                            f"shift={shift:.6f}",
                            f"sentiment={sentiment}",
                            f"headline={item.headline}",
                            f"published_at={item.published_at.isoformat()}",
                            f"source={item.source}",
                        ],
                        provenance=Provenance(
                            produced_by=f"{self.name}@{self.version}",
                            produced_at=datetime.now(),
                            inputs=[ProvenanceRef(kind="dataset_snapshot", ref_id=snapshot.id)],
                        ),
                    )
                )
        return findings
