"""Continuous Learning: knowledge is re-evaluated, weak knowledge retires.

`ContinuousLearningMonitor.evaluate(as_of)` computes each promoted
knowledge object's *realized* mean adjusted daily return from a later
MarketState (real observed data via Market Memory — never a simulation),
appends a PerformanceRecord to both the knowledge object and its gene, and
applies the retirement policy:

    retire when, with at least `min_records` observations, the realized
    mean return's sign disagrees with the expected return's sign in a
    majority of records.

Deterministic, mechanical, and fully audited: every retirement carries a
reason string with the counts that triggered it, and the knowledge/gene
history preserves every pre-retirement revision.
"""

from __future__ import annotations

import statistics
from datetime import date

from pydantic import BaseModel

from agx_research.data.adjustments import adjusted_returns_for_ticker
from agx_research.genome.gene import GeneStatus
from agx_research.genome.service import AlphaGenome
from agx_research.knowledge.lifecycle import KnowledgeStatus
from agx_research.knowledge.schema import KnowledgeObject, PerformanceRecord
from agx_research.knowledge.store import KnowledgeStore
from agx_research.market_memory.memory import MarketMemory


class EvaluationOutcome(BaseModel):
    knowledge_id: str
    realized_return: float | None = None
    retired: bool = False
    reason: str = ""


class ContinuousLearningMonitor:
    def __init__(
        self,
        knowledge_store: KnowledgeStore,
        genome: AlphaGenome,
        market_memory: MarketMemory,
        *,
        min_records: int = 3,
    ):
        self.knowledge_store = knowledge_store
        self.genome = genome
        self.market_memory = market_memory
        self.min_records = min_records

    def _gene_for_knowledge(self, knowledge_id: str):
        for gene in self.genome.repository.all_latest():
            if gene.knowledge_id == knowledge_id and gene.status in (
                GeneStatus.PROMOTED,
                GeneStatus.MONITORING,
            ):
                return gene
        return None

    def _should_retire(self, knowledge: KnowledgeObject) -> tuple[bool, str]:
        records = knowledge.performance_history
        if len(records) < self.min_records:
            return False, f"Only {len(records)}/{self.min_records} performance records so far."
        expected_positive = knowledge.expected_return > 0
        disagreements = sum(
            1 for r in records if (r.realized_return > 0) != expected_positive
        )
        if disagreements * 2 > len(records):
            return True, (
                f"Realized return sign disagreed with expectation in "
                f"{disagreements}/{len(records)} monitored records."
            )
        return False, (
            f"Sign agreement holding ({len(records) - disagreements}/{len(records)} records agree)."
        )

    def evaluate(self, as_of: date) -> list[EvaluationOutcome]:
        market_state = self.market_memory.reconstruct(as_of)
        snapshot = market_state.dataset_snapshot
        outcomes: list[EvaluationOutcome] = []

        for knowledge in self.knowledge_store.all_latest():
            if knowledge.status == KnowledgeStatus.RETIRED:
                continue
            primary = knowledge.affected_assets[0] if knowledge.affected_assets else None
            if primary is None:
                continue
            returns = adjusted_returns_for_ticker(snapshot, primary)
            if len(returns) < 3:
                outcomes.append(
                    EvaluationOutcome(
                        knowledge_id=knowledge.id,
                        reason=f"No usable realized data for {primary} as of {as_of.isoformat()}.",
                    )
                )
                continue

            realized = statistics.fmean(returns)
            record = PerformanceRecord(
                as_of=as_of,
                realized_return=realized,
                notes=f"Realized mean adjusted daily return of {primary} over the window ending {as_of.isoformat()}.",
            )
            updated = self.knowledge_store.record_performance(knowledge.id, record)
            if updated.status == KnowledgeStatus.PROMOTED:
                updated = self.knowledge_store.transition_status(
                    knowledge.id, KnowledgeStatus.MONITORING
                )
            gene = self._gene_for_knowledge(knowledge.id)
            if gene is not None:
                self.genome.record_performance(gene.id, record)
                if gene.status == GeneStatus.PROMOTED:
                    self.genome.transition_status(gene.id, GeneStatus.MONITORING)

            retire, reason = self._should_retire(updated)
            if retire:
                self.knowledge_store.transition_status(
                    knowledge.id, KnowledgeStatus.RETIRED, reason=reason
                )
                if gene is not None:
                    self.genome.transition_status(gene.id, GeneStatus.RETIRED, reason=reason)
            outcomes.append(
                EvaluationOutcome(
                    knowledge_id=knowledge.id,
                    realized_return=realized,
                    retired=retire,
                    reason=reason,
                )
            )
        return outcomes
