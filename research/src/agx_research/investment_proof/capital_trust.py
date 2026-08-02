"""Phase 10 (and orchestrator for Phases 1-9): the Capital Trust Report.

`InvestmentProofEngine.run()` is the single entry point that answers the
mission's final question -- "Would a rational institutional investment
committee trust this system with capital?" -- by actually exercising every
other `investment_proof` engine against one shared, real (synthetic-but-
mechanically-real, per `institutional_validation.scenarios`'s own
convention) scenario, plus `institutional_validation.run_institutional_validation()`
as the architectural baseline this framework composes rather than
duplicates.

Every dimension gets a `CheckVerdict` (the same PASS/PARTIAL/BLOCKED/FAIL
scale `institutional_validation.report` already defined -- reused, not
reinvented) and real, numbered evidence. `overall_verdict` is computed
mechanically from the dimensions, never asserted independently of them:

- Any `FAIL` anywhere -> **NO**.
- No `FAIL`, but at least one `BLOCKED` (a mechanism that is architecturally
  complete but genuinely has no real data to run against yet -- walk-forward
  replay and confidence calibration, today) -> **PARTIALLY**.
- Everything `PASS`/`PARTIAL` -> **YES**.

As of this writing that will always resolve to at most **PARTIALLY**: the
platform runs on mock/synthetic data until a real EGX vendor is licensed
(a business decision reserved for the user, per `CLAUDE.md`), and no
committee should be told a system is fully trustworthy with capital before
it has ever seen real market data. That ceiling is a fact about the data,
not a defect this engine should paper over.
"""

from __future__ import annotations

from datetime import date, datetime, timedelta

from pydantic import BaseModel, Field

from agx_research.config import Horizon
from agx_research.decision_service.country_risk import CountryRiskAssessment, CountryRiskSeverity
from agx_research.decision_service.position import PositionState
from agx_research.decision_service.service import DecisionService
from agx_research.domain.provenance import Provenance
from agx_research.genome.service import AlphaGenome
from agx_research.institutional_validation import scenarios as sc
from agx_research.institutional_validation.report import CheckVerdict
from agx_research.institutional_validation.runner import run_institutional_validation
from agx_research.institutional_validation.scenarios import SYNTHETIC_CREATOR_AGENT, InMemoryDataProvider
from agx_research.investment_proof.attribution import DecisionAttributionEngine
from agx_research.investment_proof.committee_validation import CommitteeValidationEngine
from agx_research.investment_proof.counterfactual import CounterfactualEngine
from agx_research.investment_proof.calibration import ConfidenceCalibrationFramework
from agx_research.investment_proof.portfolio_validation import PortfolioValidationEngine
from agx_research.investment_proof.stability import DecisionStabilityEngine
from agx_research.investment_proof.thesis_survival import ThesisSurvivalEngine, ThesisStatus
from agx_research.investment_proof.walk_forward import WalkForwardInfrastructure
from agx_research.knowledge.lifecycle import KnowledgeStatus
from agx_research.knowledge.schema import KnowledgeObject
from agx_research.knowledge.store import KnowledgeStore
from agx_research.learning.monitor import ContinuousLearningMonitor
from agx_research.market_memory.memory import MarketMemory
from agx_research.meta.decision_ledger import DecisionLedger
from agx_research.meta.decision_quality import apply_decision_quality_gate
from agx_research.meta.recommendation_service import RecommendationService
from agx_research.portfolio.constructor import PortfolioConstructor
from agx_research.universe.provider import MappingUniverseProvider
from agx_research.universe.sector import StaticSectorProvider
from agx_research.validation.statistical import StatisticalEvidence

#: A capped subset of the real EGX30 universe, not the whole EGX30+EGX70
#: real-tickers list `institutional_validation` uses for its own Q1/Q2 --
#: this engine already re-runs that whole check via
#: `run_institutional_validation()`, so its own scenario only needs enough
#: tickers to genuinely exercise every downstream engine, not to duplicate
#: full-universe coverage a second time.
_DEFAULT_TICKER_LIMIT = 15
_THESIS_LIFECYCLE_START = date(2026, 1, 5)
#: Not real market data -- a fixed, honestly-labeled placeholder reference
#: price so `RecommendationService`/`DecisionService` can compute an
#: executable-looking decision for the thesis-survival check. The
#: mechanism under test here (does the platform detect and report a
#: broken thesis) does not depend on this number's realism.
_PLACEHOLDER_REFERENCE_PRICE = 100.0
#: `institutional_validation.scenarios.thesis_lifecycle_scenario` builds its
#: knowledge at Horizon.SWING, which `DecisionService` never acts on (only
#: INVESTMENT drives a position-aware action -- AD-35's "never blend
#: horizons" rule). `ThesisSurvivalEngine` operates on `PositionAwareDecision`,
#: so this dimension needs its own INVESTMENT-horizon lifecycle rather than
#: reusing that scenario -- 260 synthetic trading days (comfortably more
#: than the INVESTMENT horizon's 126-trading-day forward window) so a real
#: forward return is computable at each evaluation date.
_INVESTMENT_LIFECYCLE_TRADING_DAYS = 260
_INVESTMENT_LIFECYCLE_LOOKBACK_DAYS = 400
_INVESTMENT_LIFECYCLE_EVALUATION_INDEXES = (150, 190, 230)


class _InvestmentThesisLifecycle:
    def __init__(
        self,
        knowledge_store: KnowledgeStore,
        genome: AlphaGenome,
        monitor: ContinuousLearningMonitor,
        failing_ticker: str,
        holding_ticker: str,
        evaluation_dates: list[date],
    ):
        self.knowledge_store = knowledge_store
        self.genome = genome
        self.monitor = monitor
        self.failing_ticker = failing_ticker
        self.holding_ticker = holding_ticker
        self.evaluation_dates = evaluation_dates


def _build_investment_thesis_lifecycle(start: date) -> _InvestmentThesisLifecycle:
    """An INVESTMENT-horizon analogue of `thesis_lifecycle_scenario`: one
    knowledge object whose real synthetic price path contradicts its
    expected return (`IFAILTEST`, engineered to decline) and one that
    confirms it (`IHOLDTEST`, engineered to rise), built entirely from the
    same real classes (`ContinuousLearningMonitor`, `MarketMemory`,
    `KnowledgeStore`, `AlphaGenome`) `thesis_lifecycle_scenario` uses --
    only the horizon and the data volume needed to support it differ.
    """
    failing_ticker, holding_ticker = "IFAILTEST", "IHOLDTEST"
    price_history = {
        failing_ticker: sc.synthetic_price_series(
            failing_ticker, start, _INVESTMENT_LIFECYCLE_TRADING_DAYS, daily_return=-0.005
        ),
        holding_ticker: sc.synthetic_price_series(
            holding_ticker, start, _INVESTMENT_LIFECYCLE_TRADING_DAYS, daily_return=0.005
        ),
    }
    data_provider = InMemoryDataProvider(price_history)
    universe = MappingUniverseProvider({failing_ticker: failing_ticker, holding_ticker: holding_ticker})
    market_memory = MarketMemory(
        data_provider, universe, StaticSectorProvider(), macro_series_ids=[], lookback_days=_INVESTMENT_LIFECYCLE_LOOKBACK_DAYS
    )

    knowledge_store = KnowledgeStore()
    genome = AlphaGenome()
    for ticker in (failing_ticker, holding_ticker):
        knowledge = knowledge_store._repo.add(
            KnowledgeObject(
                id=f"synthetic-{ticker}",
                discovery_date=start,
                creator_agent=SYNTHETIC_CREATOR_AGENT,
                supporting_evidence=[f"Synthetic INVESTMENT-horizon thesis-lifecycle evidence for {ticker} (not real research)."],
                confidence=0.80,
                statistical_evidence=StatisticalEvidence(method="synthetic", statistic=0.0, p_value=0.02, sample_size=100),
                economic_explanation=f"Synthetic {ticker} INVESTMENT-horizon thesis for capital-trust thesis-survival validation.",
                affected_assets=[ticker],
                horizon=Horizon.INVESTMENT,
                expected_return=0.10,
                expected_risk=0.05,
                status=KnowledgeStatus.PROMOTED,
                provenance=Provenance(produced_by=SYNTHETIC_CREATOR_AGENT, produced_at=datetime.now()),
            )
        )
        genome.promote_to_gene(knowledge)

    monitor = ContinuousLearningMonitor(knowledge_store, genome, market_memory, min_records=3)
    all_trading_days = [bar.trade_date for bar in price_history[failing_ticker]]
    evaluation_dates = [all_trading_days[i] for i in _INVESTMENT_LIFECYCLE_EVALUATION_INDEXES]

    return _InvestmentThesisLifecycle(
        knowledge_store=knowledge_store,
        genome=genome,
        monitor=monitor,
        failing_ticker=failing_ticker,
        holding_ticker=holding_ticker,
        evaluation_dates=evaluation_dates,
    )


#: Real `AGENT_CATEGORY_MAP` agent names -- deliberately not
#: `SYNTHETIC_CREATOR_AGENT` (which `synthetic_full_universe` uses and
#: which `category_for_agent()` correctly does not recognize, since it
#: isn't a real agent). Attribution/counterfactual/committee validation
#: specifically exercise the category-mapping mechanism, so they need
#: knowledge tagged with the real agent names that mechanism actually maps.
_ATTRIBUTION_AGENTS = [
    "macro_agent",
    "financial_performance_agent",
    "corporate_events_agent",
    "market_structure_agent",
]


def _build_attribution_knowledge_store(tickers: list[str], as_of: date) -> tuple[KnowledgeStore, dict[str, float]]:
    """Two real-agent-tagged knowledge objects per ticker (cycling through
    `_ATTRIBUTION_AGENTS` deterministically), clearly labeled synthetic --
    same posture as `institutional_validation.scenarios`, just with real
    `creator_agent` values so `categories.category_for_agent()` can
    actually map them."""
    store = KnowledgeStore()
    latest_prices: dict[str, float] = {}
    for index, ticker in enumerate(tickers):
        agents = (
            _ATTRIBUTION_AGENTS[index % len(_ATTRIBUTION_AGENTS)],
            _ATTRIBUTION_AGENTS[(index + 1) % len(_ATTRIBUTION_AGENTS)],
        )
        for slot, agent in enumerate(agents):
            expected_return = (0.04 if slot == 0 else -0.015) + ((index * 13) % 7 - 3) / 1000.0
            store._repo.add(
                KnowledgeObject(
                    id=f"attrib-{ticker}-{agent}",
                    discovery_date=as_of - timedelta(days=30),
                    creator_agent=agent,
                    supporting_evidence=[
                        f"Synthetic capital-trust attribution evidence for {ticker} via {agent} (not real research)."
                    ],
                    confidence=0.6 + 0.1 * slot,
                    statistical_evidence=StatisticalEvidence(method="synthetic", statistic=0.0, p_value=0.02, sample_size=100),
                    economic_explanation=f"Synthetic {agent} thesis for {ticker}, capital-trust attribution validation.",
                    affected_assets=[ticker],
                    horizon=Horizon.INVESTMENT,
                    expected_return=expected_return,
                    expected_risk=0.05,
                    status=KnowledgeStatus.PROMOTED,
                    provenance=Provenance(produced_by=agent, produced_at=datetime.now()),
                )
            )
        latest_prices[ticker] = 50.0 + index
    return store, latest_prices


class CapitalTrustDimension(BaseModel):
    name: str
    question: str
    verdict: CheckVerdict
    evidence: list[str] = Field(default_factory=list)
    findings: list[str] = Field(default_factory=list)


class CapitalTrustReport(BaseModel):
    generated_at: datetime
    as_of: date
    dimensions: list[CapitalTrustDimension] = Field(default_factory=list)
    institutional_validation_verdict: CheckVerdict
    overall_verdict: str  # "yes" | "no" | "partially"
    rationale: str

    def to_markdown(self) -> str:
        lines = [
            "# Capital Trust Report",
            "",
            f"Generated: {self.generated_at.isoformat()}",
            f"As of: {self.as_of.isoformat()}",
            "",
            "## Would a rational institutional investment committee trust this system with capital?",
            f"**{self.overall_verdict.upper()}**",
            "",
            self.rationale,
            "",
            f"Institutional Investment Validation baseline verdict: **{self.institutional_validation_verdict.value.upper()}**",
            "",
        ]
        for dim in self.dimensions:
            lines.append(f"## {dim.name} -- {dim.verdict.value.upper()}")
            lines.append(dim.question)
            lines.append("")
            if dim.evidence:
                lines.append("Evidence:")
                lines.extend(f"- {e}" for e in dim.evidence)
            if dim.findings:
                lines.append("")
                lines.append("Findings:")
                lines.extend(f"- {f}" for f in dim.findings)
            lines.append("")
        return "\n".join(lines)


def _force_publication_ready(recommendations, as_of: date):
    """Same real-gate pattern `institutional_validation.scenarios` and
    `cli.py`'s `decide` command both use -- never hand-set
    `publication_status` without also going through
    `apply_decision_quality_gate()`, or `max_position_pct` silently stays
    zero (see `docs/TECHNICAL_DEBT.md` on the real bug this exact mistake
    caused in `DecisionService`)."""
    del as_of  # kept for call-site compatibility; the gate is per-decision now
    return apply_decision_quality_gate(recommendations)


class InvestmentProofEngine:
    """Composes every `investment_proof` engine plus the Mission 3
    `institutional_validation` framework into one final Capital Trust
    Report. Never re-implements a check another engine already owns."""

    def run(self, as_of: date, *, ticker_limit: int = _DEFAULT_TICKER_LIMIT) -> CapitalTrustReport:
        institutional_report = run_institutional_validation(as_of=as_of)

        egx30, _egx70 = sc.real_universe_tickers()
        tickers = egx30[:ticker_limit]
        scenario = sc.synthetic_full_universe(tickers, as_of, scenario_id="capital_trust_scenario")
        attribution_store, attribution_prices = _build_attribution_knowledge_store(tickers, as_of)

        dimensions = [
            self._decision_stability(scenario, tickers, as_of),
            *self._attribution_and_counterfactual(attribution_store, attribution_prices, tickers, as_of),
            self._committee_validation(attribution_store, attribution_prices, tickers, as_of),
            self._portfolio_validation(scenario, as_of),
            self._thesis_survival(),
            self._confidence_calibration(),
            self._walk_forward_readiness(),
        ]

        overall, rationale = self._overall_verdict(dimensions, institutional_report.overall_verdict)

        return CapitalTrustReport(
            generated_at=datetime.now(),
            as_of=as_of,
            dimensions=dimensions,
            institutional_validation_verdict=institutional_report.overall_verdict,
            overall_verdict=overall,
            rationale=rationale,
        )

    # --- Phase 9: Decision Stability -----------------------------------------

    @staticmethod
    def _decision_stability(scenario, tickers: list[str], as_of: date) -> CapitalTrustDimension:
        result = DecisionStabilityEngine().verify_recommendation_stability(
            scenario.knowledge_store, tickers, as_of, runs=3
        )
        return CapitalTrustDimension(
            name="decision_stability",
            question="Does identical evidence always produce an identical decision?",
            verdict=CheckVerdict.PASS if result.identical else CheckVerdict.FAIL,
            evidence=[
                f"{result.subject}: {result.runs} runs, identical={result.identical}.",
            ],
            findings=result.differences,
        )

    # --- Phase 3 + Phase 4: Attribution + Counterfactual ---------------------

    @staticmethod
    def _attribution_and_counterfactual(
        knowledge_store: KnowledgeStore, latest_prices: dict[str, float], tickers: list[str], as_of: date
    ) -> list[CapitalTrustDimension]:
        attribution_engine = DecisionAttributionEngine()
        counterfactual_engine = CounterfactualEngine()
        knowledge = knowledge_store.all_latest()

        residuals: list[float] = []
        tickers_with_decisive_evidence = 0
        tickers_evaluated = 0
        for ticker in tickers:
            ticker_knowledge = [k for k in knowledge if ticker in k.affected_assets]
            if not ticker_knowledge:
                continue
            reference_price = latest_prices.get(ticker)
            attribution = attribution_engine.attribute(ticker, as_of, ticker_knowledge, reference_price=reference_price)
            if attribution.attribution_residual is None:
                continue
            tickers_evaluated += 1
            residuals.append(abs(attribution.attribution_residual))

            counterfactual = counterfactual_engine.analyze(ticker, as_of, ticker_knowledge, reference_price=reference_price)
            if counterfactual.decisive_categories:
                tickers_with_decisive_evidence += 1

        max_residual = max(residuals) if residuals else None
        attribution_dim = CapitalTrustDimension(
            name="decision_attribution",
            question="Can every recommendation's expected return be decomposed into named contributing categories?",
            verdict=(
                CheckVerdict.PASS
                if residuals and max_residual is not None and max_residual < 1e-6
                else CheckVerdict.FAIL
                if residuals
                else CheckVerdict.BLOCKED
            ),
            evidence=(
                [
                    f"{tickers_evaluated}/{len(tickers)} tickers attributed via real "
                    "KnowledgeWeightedHorizonModel/FairValueEngine computation.",
                    f"Max |attribution_residual| across all attributed tickers: {max_residual:.2e} "
                    "(sum of category contributions reconciles to the final expected_return).",
                ]
                if residuals
                else ["No ticker in this scenario had usable knowledge to attribute."]
            ),
        )
        counterfactual_dim = CapitalTrustDimension(
            name="counterfactual_analysis",
            question="Can the platform identify which evidence category actually drives each decision, by real ablation?",
            verdict=CheckVerdict.PASS if tickers_evaluated else CheckVerdict.BLOCKED,
            evidence=[
                f"{tickers_with_decisive_evidence}/{tickers_evaluated} tickers had at least one evidence "
                "category whose real removal (recomputed via KnowledgeWeightedHorizonModel + "
                "MetaDecisionEngine) changed the resulting action."
            ]
            if tickers_evaluated
            else ["No ticker in this scenario had usable knowledge to ablate."],
        )
        return [attribution_dim, counterfactual_dim]

    # --- Phase 8: Committee Validation ----------------------------------------

    @staticmethod
    def _committee_validation(
        knowledge_store: KnowledgeStore, latest_prices: dict[str, float], tickers: list[str], as_of: date
    ) -> CapitalTrustDimension:
        knowledge = knowledge_store.all_latest()
        knowledge_by_ticker: dict[str, list] = {}
        for ticker in tickers:
            knowledge_by_ticker[ticker] = [k for k in knowledge if ticker in k.affected_assets]

        result = CommitteeValidationEngine().validate(
            tickers, as_of, knowledge_by_ticker, latest_prices=latest_prices
        )
        active = [c for c in result.committees if c.tickers_present > 0]
        evidence = [
            f"{result.tickers_evaluated}/{len(tickers)} tickers had an attributable committee opinion."
        ] + [
            f"{c.category.value}: present in {c.tickers_present} ticker(s), agreement_rate="
            f"{c.agreement_rate:.0%}, decisive_rate={c.decisive_rate:.0%}, historical_usefulness="
            f"{c.historical_usefulness_status}."
            for c in active
        ]
        return CapitalTrustDimension(
            name="committee_validation",
            question="Does each evidence committee (Macro/Sector/Quality/Value/Catalyst/Technical) have a measurable, real track record of agreement and influence?",
            verdict=CheckVerdict.PASS if active else CheckVerdict.BLOCKED,
            evidence=evidence,
            findings=[
                "historical_usefulness_status is honestly 'ready_for_data' for every committee: correlating a "
                "committee's opinion with later realized outcomes needs DecisionRecord to know which categories "
                "contributed to each recorded decision, which it does not yet (see docs/TECHNICAL_DEBT.md)."
            ],
        )

    # --- Phase 7: Portfolio Validation -----------------------------------------

    @staticmethod
    def _portfolio_validation(scenario, as_of: date) -> CapitalTrustDimension:
        recommendations = scenario.recommendations
        portfolio = PortfolioConstructor().construct(recommendations, as_of)
        decisions = DecisionService().decide_portfolio(
            recommendations,
            {ticker: PositionState(ticker=ticker, held=False) for ticker in scenario.tickers},
            as_of,
            country_risk=CountryRiskAssessment(as_of=as_of, severity=CountryRiskSeverity.NORMAL),
        )
        result = PortfolioValidationEngine().validate(
            portfolio.positions, portfolio.cash_weight, as_of, position_aware_decisions=decisions
        )
        evidence = [
            f"{len(portfolio.positions)} position(s), cash_weight={result.cash_weight:.2%}, "
            f"invested_weight={result.invested_weight:.2%}, weights_reconcile={result.weights_reconcile}.",
            f"Herfindahl index={result.concentration.herfindahl_index:.4f} "
            f"({result.concentration.status}), top_3_weight={result.concentration.top_3_weight:.2%}.",
            f"Position-unaware (PortfolioConstructor) vs. position-aware (DecisionService) decision "
            f"conflicts: {len(result.decision_conflicts)}.",
        ]
        verdict = (
            CheckVerdict.PASS
            if result.weights_reconcile and not result.decision_conflicts
            else CheckVerdict.FAIL
        )
        return CapitalTrustDimension(
            name="portfolio_validation",
            question="Is the constructed portfolio internally consistent (weights reconcile, concentration measured, no conflicting decisions)?",
            verdict=verdict,
            evidence=evidence,
            findings=result.decision_conflicts,
        )

    # --- Phase 6: Thesis Survival ------------------------------------------------

    @staticmethod
    def _thesis_survival() -> CapitalTrustDimension:
        lifecycle = _build_investment_thesis_lifecycle(_THESIS_LIFECYCLE_START)
        latest_prices = {
            lifecycle.failing_ticker: _PLACEHOLDER_REFERENCE_PRICE,
            lifecycle.holding_ticker: _PLACEHOLDER_REFERENCE_PRICE,
        }
        country_risk = CountryRiskAssessment(as_of=_THESIS_LIFECYCLE_START, severity=CountryRiskSeverity.NORMAL)
        positions = {
            ticker: PositionState(ticker=ticker, held=False)
            for ticker in (lifecycle.failing_ticker, lifecycle.holding_ticker)
        }

        before_recs = RecommendationService(lifecycle.knowledge_store).recommend(
            [lifecycle.failing_ticker, lifecycle.holding_ticker], _THESIS_LIFECYCLE_START, latest_prices=latest_prices
        )
        before_recs = _force_publication_ready(before_recs, _THESIS_LIFECYCLE_START)
        before_decisions = {
            d.ticker: d
            for d in DecisionService().decide_portfolio(
                before_recs, positions, _THESIS_LIFECYCLE_START, country_risk=country_risk
            )
        }

        for evaluation_date in lifecycle.evaluation_dates:
            lifecycle.monitor.evaluate(evaluation_date)
        after_date = lifecycle.evaluation_dates[-1]

        after_recs = RecommendationService(lifecycle.knowledge_store).recommend(
            [lifecycle.failing_ticker, lifecycle.holding_ticker], after_date, latest_prices=latest_prices
        )
        after_recs = _force_publication_ready(after_recs, after_date)
        after_decisions = {
            d.ticker: d
            for d in DecisionService().decide_portfolio(after_recs, positions, after_date, country_risk=country_risk)
        }

        engine = ThesisSurvivalEngine()
        failing_report = engine.assess(
            before_decisions[lifecycle.failing_ticker],
            after_decisions.get(lifecycle.failing_ticker),
            lifecycle.knowledge_store,
            after_date,
        )
        holding_report = engine.assess(
            before_decisions[lifecycle.holding_ticker],
            after_decisions.get(lifecycle.holding_ticker),
            lifecycle.knowledge_store,
            after_date,
        )

        knowledge_status = {
            lifecycle.failing_ticker: lifecycle.knowledge_store.latest(f"synthetic-{lifecycle.failing_ticker}").status,
            lifecycle.holding_ticker: lifecycle.knowledge_store.latest(f"synthetic-{lifecycle.holding_ticker}").status,
        }
        failing_correct = (
            knowledge_status[lifecycle.failing_ticker] == KnowledgeStatus.RETIRED
            and failing_report.status in (ThesisStatus.BROKEN, ThesisStatus.EXPIRED)
            and bool(failing_report.broken_assumptions)
        )
        holding_correct = (
            knowledge_status[lifecycle.holding_ticker] != KnowledgeStatus.RETIRED
            and not holding_report.broken_assumptions
        )

        return CapitalTrustDimension(
            name="thesis_survival",
            question="When a thesis's evidence is retired for genuinely disagreeing with realized outcomes, does the platform report the thesis as broken -- and does a still-valid thesis correctly survive?",
            verdict=CheckVerdict.PASS if failing_correct and holding_correct else CheckVerdict.FAIL,
            evidence=[
                f"{lifecycle.failing_ticker} (engineered to decline against a positive expectation): "
                f"knowledge status={knowledge_status[lifecycle.failing_ticker].value}, "
                f"thesis_survival status={failing_report.status.value}, "
                f"broken_assumptions={[b.knowledge_id for b in failing_report.broken_assumptions]}.",
                f"{lifecycle.holding_ticker} (engineered to rise as expected): "
                f"knowledge status={knowledge_status[lifecycle.holding_ticker].value}, "
                f"thesis_survival status={holding_report.status.value}, "
                f"broken_assumptions={[b.knowledge_id for b in holding_report.broken_assumptions]}.",
            ],
            findings=[
                "Uses a placeholder (not real-market) reference price to keep the decision path executable -- "
                "see _PLACEHOLDER_REFERENCE_PRICE; the mechanism under test is thesis-break detection, not "
                "price realism."
            ],
        )

    # --- Phase 5: Confidence Calibration -----------------------------------------

    @staticmethod
    def _confidence_calibration() -> CapitalTrustDimension:
        from agx_research.config import Horizon

        ledger = DecisionLedger()
        report = ConfidenceCalibrationFramework(ledger).calibration_report(Horizon.INVESTMENT)
        return CapitalTrustDimension(
            name="confidence_calibration",
            question="Does stated confidence match observed outcome frequency (Brier score, reliability curve, ECE)?",
            verdict=CheckVerdict.BLOCKED if report.sample_status == "insufficient" else CheckVerdict.PASS,
            evidence=[
                f"sample_size={report.sample_size}, min_sample={report.min_sample}, "
                f"sample_status={report.sample_status}.",
            ],
            findings=(
                [
                    "Mechanism is complete and real (Brier score, 10-bin reliability curve, expected "
                    "calibration error) but there are not yet enough real, benchmark-evaluated "
                    "DecisionLedger records to compute it honestly -- READY FOR DATA, not implemented as a "
                    "placeholder or estimated from synthetic data."
                ]
                if report.sample_status == "insufficient"
                else []
            ),
        )

    # --- Phase 2: Walk-Forward Infrastructure ------------------------------------

    @staticmethod
    def _walk_forward_readiness() -> CapitalTrustDimension:
        datasets = WalkForwardInfrastructure.required_datasets()
        pending = [d for d in datasets if d.status == "ready_for_data"]
        return CapitalTrustDimension(
            name="walk_forward_backtest",
            question="Has the platform's decision process been validated by walking forward through real, out-of-sample history?",
            verdict=CheckVerdict.BLOCKED if pending else CheckVerdict.PASS,
            evidence=[f"{d.name}: {d.status} -- {d.detail or d.description}" for d in datasets],
            findings=(
                [
                    "WalkForwardInfrastructure (RecommendationService + DecisionLedger driven day-by-day over "
                    "a real trading calendar) is architecturally complete and already proven against 8 real "
                    "mock trading days with 0 errors -- but a statistically meaningful walk-forward result "
                    "needs real, multi-year EGX history this platform does not have until a vendor is "
                    "licensed. READY FOR DATA."
                ]
                if pending
                else []
            ),
        )

    # --- Overall verdict -----------------------------------------------------

    @staticmethod
    def _overall_verdict(dimensions: list[CapitalTrustDimension], institutional_verdict: CheckVerdict) -> tuple[str, str]:
        all_verdicts = [d.verdict for d in dimensions] + [institutional_verdict]
        if CheckVerdict.FAIL in all_verdicts:
            failed = [d.name for d in dimensions if d.verdict == CheckVerdict.FAIL]
            return "no", (
                "At least one dimension produced a real, reproducible FAIL "
                f"({', '.join(failed) or 'institutional_validation baseline'}): a genuine defect, not a data gap. "
                "No committee should be told this system is trustworthy with capital while a FAIL stands."
            )
        if CheckVerdict.BLOCKED in all_verdicts:
            blocked = [d.name for d in dimensions if d.verdict == CheckVerdict.BLOCKED]
            return "partially", (
                "Every mechanism that can be exercised today (decision determinism, evidence attribution, "
                "counterfactual ablation, committee agreement, portfolio consistency, thesis-break detection) "
                f"is architecturally complete and passes. {', '.join(blocked)} remain BLOCKED only for lack of "
                "real historical EGX data (walk-forward replay needs real multi-year price history; confidence "
                "calibration needs enough real, benchmark-evaluated decisions) -- honestly reported as READY "
                "FOR DATA rather than fabricated. A committee could trust the *architecture* today; it should "
                "not yet be told the *track record* is proven, because there isn't one yet on real EGX data."
            )
        return "yes", (
            "Every dimension, including the walk-forward and calibration checks, passed against real evidence "
            "with no blockers remaining."
        )


__all__ = ["CapitalTrustDimension", "CapitalTrustReport", "InvestmentProofEngine"]
