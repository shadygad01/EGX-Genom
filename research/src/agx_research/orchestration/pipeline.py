"""The end-to-end daily research pipeline: one trading day, every subsystem.

This is the integration the epoch reports kept naming as the top gap: a
single, auditable chain from market state to (possibly) promoted
knowledge, walking each hypothesis through its full gate pipeline with the
real validators — nothing skips the lifecycle, and a failure at any gate
leaves the hypothesis persisted at that gate (remembered, not retried into
existence).

Chain per run:
  MarketMemory.reconstruct -> agents propose findings -> Hypothesis per
  finding -> gate walk (observation / hypothesis / data collection /
  experiments / statistical validation / stress test / backtest / review
  board as peer validation) -> causal gate + adversarial attacks ->
  KnowledgeStore.promote -> AlphaGenome gene -> ResearchPaper -> Knowledge
  Graph projection -> ResearchSession record.

Honesty rules encoded here, not just documented:

- Confidence is derived, never invented: `min(1 - bootstrap_p, cap)`
  then adjusted by the adversarial scientist's attack results. The cap
  (default 0.9) exists because no single-window study justifies
  certainty.
- Expected return/risk are *measured historical* mean/std of the primary
  asset's adjusted daily returns over the snapshot window — labeled as
  such, not forecasts.
- A hypothesis with no stated economic rationale fails the causal gate and
  is never promoted, no matter how significant its statistics.
"""

from __future__ import annotations

import statistics as _stats
from dataclasses import dataclass, field
from datetime import date, datetime

from pydantic import BaseModel, Field

from agx_research.adversarial.scientist import AdversarialScientist, apply_adversarial_review
from agx_research.agents.base import ResearchAgent, ResearchFinding
from agx_research.causal.assessment import CandidateCause
from agx_research.causal.reasoner import EconomicRationaleGate
from agx_research.domain.identifiers import new_id
from agx_research.domain.provenance import Provenance
from agx_research.events.graph_integration import project_events
from agx_research.genome.service import AlphaGenome
from agx_research.graph.builder import edges_from_provenance
from agx_research.graph.knowledge_graph import KnowledgeGraph
from agx_research.graph.nodes import GraphNode, NodeType
from agx_research.hypotheses.experiment_factory import ExperimentFactory
from agx_research.hypotheses.hypothesis import Hypothesis, StageResult
from agx_research.hypotheses.pipeline import StageName
from agx_research.hypotheses.repository import HypothesisRepository
from agx_research.hypotheses.statistic import series_for_hypothesis
from agx_research.knowledge.store import KnowledgeStore
from agx_research.market_memory.memory import MarketMemory
from agx_research.market_memory.state import MarketState
from agx_research.orchestration.artifacts import ArtifactKind, ArtifactRepository
from agx_research.orchestration.session import ResearchSession
from agx_research.papers.generator import generate_paper
from agx_research.papers.repository import PaperRepository
from agx_research.review.board import ScientificReviewBoard
from agx_research.review.candidate import PromotionCandidate
from agx_research.review.reviewers import (
    EconomistReviewer,
    PeerValidatorReviewer,
    RiskReviewer,
    StatisticianReviewer,
)
from agx_research.validation.backtest import NaiveDirectionalBacktester
from agx_research.validation.statistical import SignificanceThresholdValidator, StatisticalEvidence
from agx_research.validation.stress_test import HistoricalWorstWindowStressTester


@dataclass
class PipelineConfig:
    alpha: float = 0.05
    min_observations: int = 6
    min_sample_size_for_review: int = 5
    max_expected_risk: float = 0.10
    min_hit_rate: float = 0.5
    min_sharpe: float = 0.0
    confidence_cap: float = 0.9
    adversarial_min_sample_size: int = 5
    extra_agents: list[ResearchAgent] = field(default_factory=list)


class HypothesisOutcome(BaseModel):
    hypothesis_id: str
    final_stage: str
    promoted: bool
    knowledge_id: str | None = None
    gene_id: str | None = None
    paper_id: str | None = None
    rejection_reason: str | None = None


class PipelineResult(BaseModel):
    session: ResearchSession
    outcomes: list[HypothesisOutcome] = Field(default_factory=list)


class DailyResearchPipeline:
    def __init__(
        self,
        market_memory: MarketMemory,
        agents: list[ResearchAgent],
        *,
        config: PipelineConfig | None = None,
        hypothesis_repository: HypothesisRepository | None = None,
        knowledge_store: KnowledgeStore | None = None,
        genome: AlphaGenome | None = None,
        paper_repository: PaperRepository | None = None,
        artifact_repository: ArtifactRepository | None = None,
        graph: KnowledgeGraph | None = None,
    ):
        self.market_memory = market_memory
        self.agents = agents
        self.config = config or PipelineConfig()
        self.hypotheses = hypothesis_repository or HypothesisRepository()
        self.knowledge = knowledge_store or KnowledgeStore()
        self.genome = genome or AlphaGenome()
        self.papers = paper_repository or PaperRepository()
        self.artifacts = artifact_repository or ArtifactRepository()
        self.graph = graph or KnowledgeGraph()
        self.causal_gate = EconomicRationaleGate()
        self.adversarial = AdversarialScientist(
            min_sample_size=self.config.adversarial_min_sample_size
        )

    def run(self, as_of: date) -> PipelineResult:
        started_at = datetime.now()
        try:
            market_state = self.market_memory.reconstruct(as_of)
            snapshot = market_state.dataset_snapshot
            project_events(self.graph, market_state.events)

            findings: list[ResearchFinding] = []
            for agent in self.agents:
                findings.extend(agent.research(snapshot))

            artifact_ids: list[str] = []
            outcomes = [
                self._process_finding(finding, market_state, artifact_ids) for finding in findings
            ]

            session = ResearchSession(
                id=new_id("session"),
                run_date=as_of,
                dataset_snapshot_id=snapshot.id,
                agent_versions={agent.name: agent.version for agent in self.agents},
                findings=findings,
                hypothesis_ids=[o.hypothesis_id for o in outcomes],
                knowledge_ids=[o.knowledge_id for o in outcomes if o.knowledge_id],
                artifact_ids=artifact_ids,
                started_at=started_at,
                completed_at=datetime.now(),
            )
            return PipelineResult(session=session, outcomes=outcomes)
        finally:
            # A full EGX30+EGX70 run creates hundreds of hypotheses and
            # experiment artifacts. Preserve every revision, but persist the
            # daily transaction once instead of rewriting growing JSON files
            # after every gate/artifact (quadratic at production scale).
            self.hypotheses.flush()
            self.artifacts.flush()

    # ---- per-hypothesis gate walk -------------------------------------

    def _process_finding(
        self,
        finding: ResearchFinding,
        market_state: MarketState,
        artifact_ids: list[str],
    ) -> HypothesisOutcome:
        snapshot = market_state.dataset_snapshot
        hypothesis = Hypothesis.from_finding(finding)
        cfg = self.config

        def advance(stage: StageName, passed: bool, notes: str, **metrics: float) -> bool:
            nonlocal hypothesis
            hypothesis = hypothesis.advance(
                StageResult(
                    stage_name=stage.value,
                    passed=passed,
                    evaluated_at=datetime.now(),
                    notes=notes,
                    metrics=metrics,
                )
            )
            self.hypotheses.add(hypothesis, persist=False)
            return passed

        def rejected(reason: str) -> HypothesisOutcome:
            return HypothesisOutcome(
                hypothesis_id=hypothesis.id,
                final_stage=hypothesis.current_stage_name,
                promoted=False,
                rejection_reason=reason,
            )

        # 1. OBSERVATION: the finding exists and is recorded.
        advance(StageName.OBSERVATION, True, f"Recorded from finding {finding.id}")

        # 2. HYPOTHESIS: a falsifiable statement about identified assets.
        ok = advance(
            StageName.HYPOTHESIS,
            bool(hypothesis.statement.strip()) and bool(hypothesis.affected_assets),
            "Statement and affected assets present",
        )
        if not ok:
            return rejected("Empty statement or no affected assets")

        # 3. DATA_COLLECTION: the snapshot actually covers the claim.
        try:
            series = series_for_hypothesis(hypothesis, snapshot)
            n = len(series[0])
        except ValueError as exc:
            advance(StageName.DATA_COLLECTION, False, str(exc))
            return rejected(f"No statistic defined: {exc}")
        ok = advance(
            StageName.DATA_COLLECTION,
            n >= cfg.min_observations,
            f"{n} aligned observations (min {cfg.min_observations})",
            observations=float(n),
        )
        if not ok:
            return rejected("Insufficient data in snapshot")

        # 4. EXPERIMENT: the factory's full battery, each stored as an artifact.
        factory = ExperimentFactory(
            stress_tester=HistoricalWorstWindowStressTester()
        )
        try:
            experiment_results = factory.run_all(hypothesis, snapshot)
        except ValueError as exc:
            advance(StageName.EXPERIMENT, False, str(exc))
            return rejected(f"Experiments could not run: {exc}")
        for name, result in experiment_results.items():
            stored = self.artifacts.store(
                kind=ArtifactKind.EXPERIMENT_RESULT,
                payload=result,
                provenance=Provenance(
                    produced_by=name,
                    produced_at=datetime.now(),
                    inputs=hypothesis.provenance.inputs,
                ),
                persist=False,
            )
            artifact_ids.append(stored.id)
        ok = advance(
            StageName.EXPERIMENT,
            len(experiment_results) >= 3,
            f"{len(experiment_results)} experiments produced results",
        )
        if not ok:
            return rejected("Too few experiments could run")

        # 5. STATISTICAL_VALIDATION: significance of the bootstrap evidence.
        bootstrap = experiment_results.get("BootstrapExperiment")
        if bootstrap is None:
            advance(StageName.STATISTICAL_VALIDATION, False, "No bootstrap result")
            return rejected("No bootstrap evidence")
        validation = SignificanceThresholdValidator(alpha=cfg.alpha).validate(bootstrap)
        ok = advance(
            StageName.STATISTICAL_VALIDATION,
            validation.passed,
            validation.notes,
            p_value=bootstrap.p_value,
        )
        if not ok:
            return rejected(f"Not statistically significant: {validation.notes}")

        # 6. STRESS_TEST
        stress = HistoricalWorstWindowStressTester().run(hypothesis, snapshot)
        ok = advance(StageName.STRESS_TEST, stress.passed, stress.notes)
        if not ok:
            return rejected(f"Failed stress test: {stress.notes}")

        # 7. BACKTEST
        backtest = NaiveDirectionalBacktester(
            min_hit_rate=cfg.min_hit_rate, min_sharpe=cfg.min_sharpe
        ).run(hypothesis, snapshot)
        ok = advance(
            StageName.BACKTEST,
            backtest.passed,
            backtest.notes,
            hit_rate=backtest.hit_rate or 0.0,
            sharpe=backtest.sharpe_ratio or 0.0,
        )
        if not ok:
            return rejected(f"Failed backtest: {backtest.notes}")

        # Causal gate + candidate assembly (before the board, which consumes both).
        rationale = finding.proposed_economic_rationale
        candidate_causes = (
            [CandidateCause(description=finding.proposed_candidate_cause, mechanism=rationale or "")]
            if finding.proposed_candidate_cause
            else []
        )
        causal_assessment = self.causal_gate.assess(
            hypothesis, candidate_causes=candidate_causes, economic_rationale=rationale
        )

        primary_returns = series[0]
        evidence = StatisticalEvidence(
            method="BootstrapExperiment",
            statistic=bootstrap.statistic,
            p_value=bootstrap.p_value,
            sample_size=bootstrap.sample_size,
        )
        # Adversarial attacks adjust the evidence-derived confidence.
        attack_results = self.adversarial.attack(
            hypothesis, experiment_results, snapshot, economic_rationale=rationale
        )
        base_confidence = min(1.0 - bootstrap.p_value, cfg.confidence_cap)
        confidence = apply_adversarial_review(base_confidence, attack_results)

        candidate = PromotionCandidate(
            confidence=confidence,
            statistical_evidence=evidence,
            economic_explanation=rationale or "",
            expected_return=_stats.fmean(primary_returns),
            expected_risk=_stats.pstdev(primary_returns),
            supporting_evidence=[
                *finding.evidence,
                f"backtest_hit_rate={backtest.hit_rate:.3f}",
                f"backtest_sharpe={backtest.sharpe_ratio:.3f}",
                f"stress={stress.notes}",
            ],
        )

        # 8. PEER_VALIDATION: the full review board.
        board = ScientificReviewBoard(
            [
                StatisticianReviewer(alpha=cfg.alpha, min_sample_size=cfg.min_sample_size_for_review),
                EconomistReviewer(),
                RiskReviewer(max_expected_risk=cfg.max_expected_risk),
                PeerValidatorReviewer(snapshot=snapshot, alpha=cfg.alpha),
            ]
        )
        decision = board.review(
            hypothesis=hypothesis,
            candidate=candidate,
            experiment_results=experiment_results,
            causal_assessment=causal_assessment,
        )
        board_notes = "; ".join(
            f"{r.reviewer_role.value}:{'pass' if r.passed else 'FAIL'}" for r in decision.reports
        )
        ok = advance(StageName.PEER_VALIDATION, decision.approved, board_notes)
        if not ok:
            return rejected(f"Review board rejected: {board_notes}")

        # Promotion: the only write into the knowledge store.
        knowledge = self.knowledge.promote(
            hypothesis,
            confidence=candidate.confidence,
            statistical_evidence=candidate.statistical_evidence,
            economic_explanation=candidate.economic_explanation,
            expected_return=candidate.expected_return,
            expected_risk=candidate.expected_risk,
            supporting_evidence=candidate.supporting_evidence,
        )
        gene = self.genome.promote_to_gene(knowledge)
        paper = generate_paper(
            gene=gene,
            hypothesis=hypothesis,
            knowledge=knowledge,
            experiment_results=experiment_results,
            causal_assessment=causal_assessment,
            dataset_snapshot_id=snapshot.id,
        )
        self.papers.add(paper)
        publication = self.artifacts.store(
            kind=ArtifactKind.KNOWLEDGE_PUBLICATION,
            payload=knowledge,
            provenance=knowledge.provenance,
            persist=False,
        )
        artifact_ids.append(publication.id)

        # Graph projection: hypothesis -> knowledge -> gene -> paper.
        self.graph.add_node(
            GraphNode(id=hypothesis.id, node_type=NodeType.HYPOTHESIS, label=hypothesis.statement)
        )
        self.graph.add_node(
            GraphNode(id=knowledge.id, node_type=NodeType.KNOWLEDGE, label=knowledge.economic_explanation)
        )
        self.graph.add_node(GraphNode(id=gene.id, node_type=NodeType.GENE, label=f"gene gen {gene.generation}"))
        self.graph.add_node(GraphNode(id=paper.id, node_type=NodeType.RESEARCH_PAPER, label=paper.title))
        for entity_type, entity_id, entity_version, provenance in (
            (NodeType.KNOWLEDGE, knowledge.id, knowledge.version, knowledge.provenance),
            (NodeType.GENE, gene.id, gene.version, gene.provenance),
            (NodeType.RESEARCH_PAPER, paper.id, paper.version, paper.provenance),
        ):
            for edge in edges_from_provenance(entity_type, entity_id, entity_version, provenance):
                # KnowledgeObject inherits its hypothesis's id (Epoch I
                # contract), so its provenance edge would self-loop -- skip.
                if edge.source_id != edge.target_id:
                    self.graph.add_edge(edge)

        return HypothesisOutcome(
            hypothesis_id=hypothesis.id,
            final_stage=hypothesis.current_stage_name,
            promoted=True,
            knowledge_id=knowledge.id,
            gene_id=gene.id,
            paper_id=paper.id,
        )
