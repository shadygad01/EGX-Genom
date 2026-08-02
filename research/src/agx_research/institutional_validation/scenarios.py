"""Repeatable scenario builders for Institutional Investment Validation.

Every scenario is deterministic (seeded where randomness is used) and
built from real platform classes -- `KnowledgeStore`, `MarketMemory`,
`RecommendationService`, `PortfolioConstructor`, `DecisionService`,
`ContinuousLearningMonitor`, `DecisionLedger` -- never a hand-rolled
stand-in for them. Two kinds of scenario appear here, and neither is
mislabeled as the other:

- **Real-coverage scenarios** (`real_universe_tickers`) read the actual
  checked-in `EGX30.csv`/`EGX70.csv` and the actual mock price CSVs, to
  report what the platform can do *today* with the data it actually has.
- **Synthetic scenarios** (everything else) generate deterministic,
  clearly-synthetic price/knowledge data to stress-test a mechanism at
  scale or under an edge condition mock data can't otherwise reach (e.g. a
  full 101-ticker universe, a sustained thesis failure). Nothing produced
  here is ever presented as real research -- every synthetic
  `KnowledgeObject.creator_agent`/`economic_explanation` says so plainly.
"""

from __future__ import annotations

import csv
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from pathlib import Path

from agx_research.config import Horizon
from agx_research.data.provider import DataProvider
from agx_research.data.schemas import CorporateEvent, MacroObservation, NewsItem, PriceBar
from agx_research.data.snapshot import DatasetSnapshot
from agx_research.decision_service.country_risk import CountryRiskAssessment, CountryRiskSeverity
from agx_research.decision_service.position import PositionState
from agx_research.decision_service.service import DecisionService, PositionAwareDecision
from agx_research.domain.provenance import Provenance
from agx_research.genome.service import AlphaGenome
from agx_research.knowledge.lifecycle import KnowledgeStatus
from agx_research.knowledge.schema import KnowledgeObject
from agx_research.knowledge.store import KnowledgeStore
from agx_research.learning.monitor import ContinuousLearningMonitor
from agx_research.market_memory.calendar import StaticEGXCalendar
from agx_research.market_memory.memory import MarketMemory
from agx_research.meta.decision_engine import Recommendation
from agx_research.meta.decision_quality import apply_decision_quality_gate
from agx_research.meta.recommendation_service import RecommendationService
from agx_research.universe.provider import MappingUniverseProvider
from agx_research.universe.sector import StaticSectorProvider
from agx_research.validation.statistical import StatisticalEvidence

UNIVERSE_DIR = Path(__file__).resolve().parents[3] / "data" / "universe"
_CALENDAR = StaticEGXCalendar()

SYNTHETIC_CREATOR_AGENT = "institutional_validation.synthetic"


# --- Real universe coverage --------------------------------------------------


def real_universe_tickers() -> tuple[list[str], list[str]]:
    """The actual, checked-in EGX30/EGX70 constituent lists -- real tickers,
    real ISINs, not a placeholder. Returns (egx30, egx70)."""

    def read(path: Path) -> list[str]:
        with path.open(newline="", encoding="utf-8") as f:
            return [row["ticker"] for row in csv.DictReader(f)]

    return read(UNIVERSE_DIR / "EGX30.csv"), read(UNIVERSE_DIR / "EGX70.csv")


# --- Synthetic in-memory data provider ---------------------------------------


class InMemoryDataProvider(DataProvider):
    """A `DataProvider` backed by an in-memory dict instead of CSVs/a live
    vendor -- the same structural role `MockDataProvider` already plays,
    just for scenario data built in Python rather than checked-in files.
    Corporate events/macro/news are deliberately empty: no scenario in this
    package currently needs them, and returning `[]` is honest (never a
    fabricated event)."""

    def __init__(self, price_history: dict[str, list[PriceBar]]):
        self._price_history = price_history

    def get_price_history(self, ticker: str, start: date, end: date) -> list[PriceBar]:
        return [
            bar for bar in self._price_history.get(ticker, []) if start <= bar.trade_date <= end
        ]

    def get_corporate_events(self, ticker: str, start: date, end: date) -> list[CorporateEvent]:
        return []

    def get_macro_series(self, series_id: str, start: date, end: date) -> list[MacroObservation]:
        return []

    def get_news(self, ticker: str | None, start: date, end: date) -> list[NewsItem]:
        return []


def synthetic_price_series(
    ticker: str, start: date, num_trading_days: int, *, daily_return: float, start_price: float = 100.0
) -> list[PriceBar]:
    """Deterministic OHLCV bars on real EGX trading days only (Fri/Sat
    weekend, per `StaticEGXCalendar`), stepping `start_price` by a constant
    `daily_return` each day -- a smooth, predictable trend, not noise, so a
    scenario's expected direction is unambiguous and reproducible."""
    bars: list[PriceBar] = []
    current = start
    price = start_price
    produced = 0
    while produced < num_trading_days:
        if _CALENDAR.is_trading_day(current):
            price *= 1 + daily_return
            bars.append(
                PriceBar(
                    ticker=ticker,
                    trade_date=current,
                    open=price,
                    high=price,
                    low=price,
                    close=price,
                    volume=1_000_000,
                )
            )
            produced += 1
        current += timedelta(days=1)
    return bars


def _force_publication_ready(recommendations: list[Recommendation], as_of: date) -> list[Recommendation]:
    """Runs the *real* `apply_decision_quality_gate()`, rather than
    hand-setting `publication_status`.

    This matters for a real reason a first attempt at this module got
    wrong: `PortfolioConstructor` also requires `HorizonDecision.
    max_position_pct` to be positive, and that field is set *only* by
    the quality gate (`meta/decision_quality.py`), never by
    `MetaDecisionEngine`. Hand-setting `publication_status` alone silently
    left `max_position_pct=0.0`, which made every synthetic BUY_CANDIDATE
    portfolio-ineligible even though it scored positive -- a scenario-
    construction bug this framework's own Q6 check caught by refusing to
    accept a portfolio with real positions but a zero weight sum. Using
    the real gate function is both the fix and the more honest test: this
    framework's synthetic recommendations are built through the real
    `RecommendationService`/`MetaDecisionEngine` code, so their
    Explanations are already complete and genuinely pass quality on
    their own merits -- "force" only in the sense that this scenario
    framework never fabricates a fake blocked state to test around.
    """
    del as_of  # kept for call-site compatibility; the gate is per-decision now
    return apply_decision_quality_gate(recommendations)


# --- Full-universe synthetic scenario (Q1/Q2/Q3/Q4/Q6) ----------------------

#: Four deterministic profiles cycled across a synthetic universe so a
#: full-scale run genuinely exercises every decision outcome, not just
#: "everything is a buy" (which would prove nothing about rejection).
_PROFILES = [
    # (expected_return, expected_risk, confidence, reference_price_factor)
    (0.15, 0.05, 0.85),  # strong, high-confidence -> BUY_CANDIDATE
    (-0.08, 0.06, 0.75),  # negative -> AVOID
    (0.05, 0.04, 0.45),  # positive but low-confidence -> ABSTAIN
    (0.03, 0.05, 0.65),  # modest, sub-1.0 score -> WATCH
]


@dataclass
class SyntheticUniverseScenario:
    scenario_id: str
    as_of: date
    tickers: list[str]
    knowledge_store: KnowledgeStore
    latest_prices: dict[str, float]
    recommendations: list[Recommendation] = field(default_factory=list)


def synthetic_full_universe(
    tickers: list[str], as_of: date, *, scenario_id: str = "synthetic_full_universe"
) -> SyntheticUniverseScenario:
    """One promoted, INVESTMENT-horizon `KnowledgeObject` per ticker,
    profile chosen deterministically by index so the resulting recommendation
    set spans BUY_CANDIDATE/AVOID/ABSTAIN/WATCH in real, roughly-even
    proportions -- a genuine stress test of ranking/rejection at full
    universe scale, clearly synthetic (see module docstring), never
    presented as real research.
    """
    knowledge_store = KnowledgeStore()
    latest_prices: dict[str, float] = {}
    for index, ticker in enumerate(sorted(tickers)):
        expected_return, expected_risk, confidence = _PROFILES[index % len(_PROFILES)]
        # Small deterministic per-ticker jitter so tickers sharing a profile
        # aren't bit-for-bit identical, without breaking the intended outcome.
        jitter = ((index * 37) % 11 - 5) / 1000.0
        knowledge_store._repo.add(
            KnowledgeObject(
                id=f"synthetic-{ticker}",
                discovery_date=as_of - timedelta(days=30),
                creator_agent=SYNTHETIC_CREATOR_AGENT,
                supporting_evidence=[f"Synthetic scale-test evidence for {ticker} (not real research)."],
                confidence=confidence,
                statistical_evidence=StatisticalEvidence(
                    method="synthetic", statistic=0.0, p_value=0.01, sample_size=252
                ),
                economic_explanation=(
                    f"Synthetic profile {index % len(_PROFILES)} generated for institutional "
                    "validation scale-testing -- not a real economic finding."
                ),
                affected_assets=[ticker],
                horizon=Horizon.INVESTMENT,
                expected_return=expected_return + jitter,
                expected_risk=expected_risk,
                status=KnowledgeStatus.PROMOTED,
                provenance=Provenance(produced_by=SYNTHETIC_CREATOR_AGENT, produced_at=datetime.now()),
            )
        )
        latest_prices[ticker] = 50.0 + index

    recommendation_service = RecommendationService(knowledge_store)
    recommendations = recommendation_service.recommend(tickers, as_of, latest_prices=latest_prices)
    # Publication-readiness is a separate concern (legal/evidence-volume
    # gates) this scenario deliberately isolates itself from, so the
    # portfolio/ranking mechanism itself can be stress-tested independently
    # -- via the real gate function, see `_force_publication_ready`.
    recommendations = _force_publication_ready(recommendations, as_of)

    return SyntheticUniverseScenario(
        scenario_id=scenario_id,
        as_of=as_of,
        tickers=tickers,
        knowledge_store=knowledge_store,
        latest_prices=latest_prices,
        recommendations=recommendations,
    )


def all_reject_universe(tickers: list[str], as_of: date) -> SyntheticUniverseScenario:
    """Every ticker draws only from the negative/low-confidence profiles --
    never the BUY/WATCH-eligible ones -- so nothing in this universe is
    ever fundable, by construction rather than by coincidence of which
    profile a given ticker's index happens to land on."""
    knowledge_store = KnowledgeStore()
    latest_prices: dict[str, float] = {}
    for index, ticker in enumerate(tickers):
        negative = index % 2 == 0
        knowledge_store._repo.add(
            KnowledgeObject(
                id=f"synthetic-{ticker}",
                discovery_date=as_of - timedelta(days=30),
                creator_agent=SYNTHETIC_CREATOR_AGENT,
                supporting_evidence=[f"Synthetic all-reject evidence for {ticker} (not real research)."],
                confidence=0.75 if negative else 0.40,
                statistical_evidence=StatisticalEvidence(
                    method="synthetic", statistic=0.0, p_value=0.02, sample_size=100
                ),
                economic_explanation="Synthetic all-reject thesis for cash-holding validation.",
                affected_assets=[ticker],
                horizon=Horizon.INVESTMENT,
                expected_return=-0.05 if negative else 0.05,
                expected_risk=0.05,
                status=KnowledgeStatus.PROMOTED,
                provenance=Provenance(produced_by=SYNTHETIC_CREATOR_AGENT, produced_at=datetime.now()),
            )
        )
        latest_prices[ticker] = 50.0 + index

    recommendation_service = RecommendationService(knowledge_store)
    recommendations = recommendation_service.recommend(tickers, as_of, latest_prices=latest_prices)
    return SyntheticUniverseScenario(
        scenario_id="all_reject_universe",
        as_of=as_of,
        tickers=tickers,
        knowledge_store=knowledge_store,
        latest_prices=latest_prices,
        recommendations=recommendations,
    )


def zero_evidence_universe(tickers: list[str], as_of: date) -> SyntheticUniverseScenario:
    """An empty `KnowledgeStore` -- every ticker must be rejected by
    absence, never a fabricated recommendation (Principle 1)."""
    knowledge_store = KnowledgeStore()
    recommendation_service = RecommendationService(knowledge_store)
    recommendations = recommendation_service.recommend(tickers, as_of)
    return SyntheticUniverseScenario(
        scenario_id="zero_evidence_universe",
        as_of=as_of,
        tickers=tickers,
        knowledge_store=knowledge_store,
        latest_prices={},
        recommendations=recommendations,
    )


# --- Country-risk crisis override scenario (Q4/Q6 falsification) ------------


def country_crisis_scenario(as_of: date) -> tuple[list[Recommendation], CountryRiskAssessment]:
    """The strongest possible synthetic buy signal, deliberately paired
    with a CRISIS country-risk assessment -- an attempt to falsify the
    hard-override rule (`decision_service.service._resolve_action`/target
    weight zeroing) by giving the evidence side every reason to win."""
    knowledge_store = KnowledgeStore()
    ticker = "CRISISTEST"
    knowledge_store._repo.add(
        KnowledgeObject(
            id=f"synthetic-{ticker}",
            discovery_date=as_of - timedelta(days=10),
            creator_agent=SYNTHETIC_CREATOR_AGENT,
            supporting_evidence=["Synthetic maximal-conviction evidence (not real research)."],
            confidence=0.99,
            statistical_evidence=StatisticalEvidence(
                method="synthetic", statistic=0.0, p_value=0.001, sample_size=500
            ),
            economic_explanation="Synthetic maximal-conviction thesis for override falsification testing.",
            affected_assets=[ticker],
            horizon=Horizon.INVESTMENT,
            expected_return=0.50,
            expected_risk=0.01,
            status=KnowledgeStatus.PROMOTED,
            provenance=Provenance(produced_by=SYNTHETIC_CREATOR_AGENT, produced_at=datetime.now()),
        )
    )
    recommendation_service = RecommendationService(knowledge_store)
    recommendations = recommendation_service.recommend([ticker], as_of, latest_prices={ticker: 100.0})
    recommendations = _force_publication_ready(recommendations, as_of)

    crisis = CountryRiskAssessment(
        as_of=as_of, severity=CountryRiskSeverity.CRISIS, reasons=["Synthetic sovereign downgrade for testing."]
    )
    return recommendations, crisis


# --- Thesis-failure / continuous-learning scenario (Q8) ---------------------


@dataclass
class ThesisLifecycleScenario:
    knowledge_store: KnowledgeStore
    genome: AlphaGenome
    monitor: ContinuousLearningMonitor
    failing_ticker: str
    holding_ticker: str
    evaluation_dates: list[date]


#: SWING (20 trading-day forward window), not INVESTMENT (126), chosen only
#: to keep this scenario's synthetic data volume manageable -- the
#: mechanism under test (`ContinuousLearningMonitor`) is horizon-agnostic.
_THESIS_HORIZON = Horizon.SWING


def thesis_lifecycle_scenario(start: date) -> ThesisLifecycleScenario:
    """One knowledge object whose real synthetic price path *contradicts*
    its expected return (`FAILTEST`, engineered to decline) and one whose
    path *confirms* it (`HOLDTEST`, engineered to rise) -- proving both
    directions: a genuinely failing thesis gets retired, and a genuinely
    holding one does not (a false-positive retirement would be its own
    failure mode, and this scenario would catch it)."""
    failing_ticker, holding_ticker = "FAILTEST", "HOLDTEST"
    discovery_date = start

    # Enough trading days for lookback (60) plus the SWING forward window
    # (20) plus margin for three separate, spaced evaluation dates.
    trading_days = 110
    price_history = {
        failing_ticker: synthetic_price_series(
            failing_ticker, discovery_date, trading_days, daily_return=-0.01
        ),
        holding_ticker: synthetic_price_series(
            holding_ticker, discovery_date, trading_days, daily_return=0.01
        ),
    }
    data_provider = InMemoryDataProvider(price_history)
    universe = MappingUniverseProvider({failing_ticker: failing_ticker, holding_ticker: holding_ticker})
    market_memory = MarketMemory(
        data_provider, universe, StaticSectorProvider(), macro_series_ids=[], lookback_days=60
    )

    knowledge_store = KnowledgeStore()
    genome = AlphaGenome()
    for ticker in (failing_ticker, holding_ticker):
        knowledge = knowledge_store._repo.add(
            KnowledgeObject(
                id=f"synthetic-{ticker}",
                discovery_date=discovery_date,
                creator_agent=SYNTHETIC_CREATOR_AGENT,
                supporting_evidence=[f"Synthetic thesis-lifecycle evidence for {ticker} (not real research)."],
                confidence=0.80,
                statistical_evidence=StatisticalEvidence(
                    method="synthetic", statistic=0.0, p_value=0.02, sample_size=100
                ),
                economic_explanation=f"Synthetic {ticker} thesis for continuous-learning validation.",
                affected_assets=[ticker],
                horizon=_THESIS_HORIZON,
                expected_return=0.10,  # both start out expecting a positive return
                expected_risk=0.05,
                status=KnowledgeStatus.PROMOTED,
                provenance=Provenance(produced_by=SYNTHETIC_CREATOR_AGENT, produced_at=datetime.now()),
            )
        )
        genome.promote_to_gene(knowledge)

    monitor = ContinuousLearningMonitor(knowledge_store, genome, market_memory, min_records=3)

    # Three evaluation dates, spaced so each falls on a real trading day
    # well inside the generated price history, each producing one new
    # PerformanceRecord.
    all_trading_days = [bar.trade_date for bar in price_history[failing_ticker]]
    evaluation_dates = [all_trading_days[70], all_trading_days[85], all_trading_days[100]]

    return ThesisLifecycleScenario(
        knowledge_store=knowledge_store,
        genome=genome,
        monitor=monitor,
        failing_ticker=failing_ticker,
        holding_ticker=holding_ticker,
        evaluation_dates=evaluation_dates,
    )


# --- Benchmark-comparison scenario (Q7) --------------------------------------


@dataclass
class BenchmarkScenario:
    snapshot_at_evaluation: DatasetSnapshot
    ticker: str
    benchmark_ticker: str
    recommendation: Recommendation
    entry_price: float
    exit_price: float
    benchmark_entry_price: float
    benchmark_exit_price: float


def benchmark_scenario(as_of: date, valid_until: date) -> BenchmarkScenario:
    """A traded ticker and a literal `EGX30`-named benchmark ticker, both
    with known, hand-computable price paths, to prove
    `DecisionLedger.evaluate_expired()`'s excess-return arithmetic is
    correct -- independent of whether a real EGX30 index feed exists."""
    ticker, benchmark_ticker = "BENCHTEST", "EGX30"
    trading_days = 40
    # Ticker returns +1%/day; benchmark returns +0.3%/day -- a real,
    # hand-verifiable positive excess return once evaluated.
    ticker_bars = synthetic_price_series(ticker, as_of, trading_days, daily_return=0.01, start_price=100.0)
    benchmark_bars = synthetic_price_series(
        benchmark_ticker, as_of, trading_days, daily_return=0.003, start_price=100.0
    )

    snapshot = DatasetSnapshot(
        id="benchmark-scenario-snapshot",
        as_of=ticker_bars[-1].trade_date,
        lookback_days=trading_days,
        macro_lookback_days=0,
        tickers=[ticker, benchmark_ticker],
        macro_series_ids=[],
        price_history={ticker: ticker_bars, benchmark_ticker: benchmark_bars},
    )

    knowledge_store = KnowledgeStore()
    knowledge_store._repo.add(
        KnowledgeObject(
            id=f"synthetic-{ticker}",
            discovery_date=as_of,
            creator_agent=SYNTHETIC_CREATOR_AGENT,
            supporting_evidence=["Synthetic benchmark-comparison evidence (not real research)."],
            confidence=0.80,
            statistical_evidence=StatisticalEvidence(
                method="synthetic", statistic=0.0, p_value=0.02, sample_size=100
            ),
            economic_explanation="Synthetic thesis for benchmark-comparison validation.",
            affected_assets=[ticker],
            horizon=Horizon.MICRO,
            expected_return=0.05,
            expected_risk=0.02,
            status=KnowledgeStatus.PROMOTED,
            provenance=Provenance(produced_by=SYNTHETIC_CREATOR_AGENT, produced_at=datetime.now()),
        )
    )
    recommendation_service = RecommendationService(knowledge_store)
    recommendations = recommendation_service.recommend([ticker], as_of, latest_prices={ticker: ticker_bars[0].close})
    recommendations = _force_publication_ready(recommendations, as_of)
    recommendation = recommendations[0]
    for decision in recommendation.horizon_decisions.values():
        decision.valid_until = valid_until

    entry_price = next(bar.close for bar in ticker_bars if bar.trade_date >= as_of)
    exit_price = next(bar.close for bar in ticker_bars if bar.trade_date >= valid_until)
    benchmark_entry_price = next(bar.close for bar in benchmark_bars if bar.trade_date >= as_of)
    benchmark_exit_price = next(bar.close for bar in benchmark_bars if bar.trade_date >= valid_until)

    return BenchmarkScenario(
        snapshot_at_evaluation=snapshot,
        ticker=ticker,
        benchmark_ticker=benchmark_ticker,
        recommendation=recommendation,
        entry_price=entry_price,
        exit_price=exit_price,
        benchmark_entry_price=benchmark_entry_price,
        benchmark_exit_price=benchmark_exit_price,
    )


# --- Evidence-chain scenario (Q10) -------------------------------------------


@dataclass
class _PromotableEvidenceStub:
    """A minimal, structural `PromotableEvidence` -- deliberately not a
    real `Hypothesis` (which requires walking a full gate pipeline with
    real stage history to become `is_ready_for_promotion`). `KnowledgeStore
    .promote()` only depends on this Protocol's shape (see its own
    docstring), so a validation-only stub satisfying it exactly is the
    correct, minimal way to exercise the promotion boundary without
    re-running System 07's already-separately-tested pipeline walk."""

    id: str
    version: int
    created_by: str
    created_at: date
    horizon: Horizon
    affected_assets: list[str]
    is_ready_for_promotion: bool
    current_stage_name: str


@dataclass
class EvidenceChainScenario:
    hypothesis_stub: _PromotableEvidenceStub
    knowledge: KnowledgeObject
    recommendation: Recommendation
    position_aware_decision: PositionAwareDecision


def evidence_chain_scenario(as_of: date) -> EvidenceChainScenario:
    """Walks hypothesis-stub -> promoted knowledge -> recommendation ->
    position-aware decision using only real platform code, to trace
    exactly how far a real `Provenance` chain reaches (Q10)."""
    ticker = "CHAINTEST"
    stub = _PromotableEvidenceStub(
        id="synthetic-hyp-chaintest",
        version=1,
        created_by=SYNTHETIC_CREATOR_AGENT,
        created_at=as_of - timedelta(days=5),
        horizon=Horizon.INVESTMENT,
        affected_assets=[ticker],
        is_ready_for_promotion=True,
        current_stage_name="promotion",
    )
    knowledge_store = KnowledgeStore()
    knowledge = knowledge_store.promote(
        stub,
        confidence=0.80,
        statistical_evidence=StatisticalEvidence(method="synthetic", statistic=0.0, p_value=0.02, sample_size=100),
        economic_explanation="Synthetic evidence-chain thesis for Q10 traceability validation.",
        expected_return=0.10,
        expected_risk=0.04,
        supporting_evidence=["Synthetic evidence-chain supporting note (not real research)."],
    )

    recommendation_service = RecommendationService(knowledge_store)
    recommendations = recommendation_service.recommend([ticker], as_of, latest_prices={ticker: 80.0})
    recommendations = _force_publication_ready(recommendations, as_of)
    recommendation = recommendations[0]

    decisions = DecisionService().decide_portfolio(
        [recommendation],
        {ticker: PositionState(ticker=ticker, held=False)},
        as_of,
        country_risk=CountryRiskAssessment(as_of=as_of, severity=CountryRiskSeverity.NORMAL),
    )

    return EvidenceChainScenario(
        hypothesis_stub=stub,
        knowledge=knowledge,
        recommendation=recommendation,
        position_aware_decision=decisions[0],
    )


__all__ = [
    "BenchmarkScenario",
    "EvidenceChainScenario",
    "InMemoryDataProvider",
    "SyntheticUniverseScenario",
    "ThesisLifecycleScenario",
    "benchmark_scenario",
    "country_crisis_scenario",
    "evidence_chain_scenario",
    "real_universe_tickers",
    "synthetic_full_universe",
    "synthetic_price_series",
    "thesis_lifecycle_scenario",
    "zero_evidence_universe",
]
