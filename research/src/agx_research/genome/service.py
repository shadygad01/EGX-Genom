"""AlphaGenome: the service that enforces "genes are immutable, never overwritten."

`mutate()` is the one operation that changes how the system understands an
existing idea, and it is deliberately incapable of overwriting anything:
it always mints a new gene id, links it to its parent, and marks the parent
`REPLACED` — the parent's full history remains in
`GeneRepository.history(parent_id)` exactly as it was.
"""

from __future__ import annotations

from datetime import date, datetime
from pathlib import Path

from agx_research.domain.identifiers import new_id
from agx_research.domain.provenance import Provenance, ProvenanceRef
from agx_research.genome.gene import Gene, GeneStatus, can_transition
from agx_research.genome.repository import GeneRepository
from agx_research.knowledge.schema import KnowledgeObject, PerformanceRecord


class AlphaGenome:
    def __init__(self, persist_path: Path | str | None = None):
        self.repository = GeneRepository(persist_path)

    def promote_to_gene(self, knowledge: KnowledgeObject) -> Gene:
        """Create a generation-0 gene wrapping a newly promoted KnowledgeObject."""
        gene = Gene(
            id=new_id("gene"),
            knowledge_id=knowledge.id,
            generation=0,
            evidence=list(knowledge.supporting_evidence),
            status=GeneStatus.PROMOTED,
            provenance=Provenance(
                produced_by="alpha_genome.promote_to_gene",
                produced_at=datetime.now(),
                inputs=[
                    ProvenanceRef(kind="knowledge", ref_id=knowledge.id, ref_version=knowledge.version)
                ],
            ),
        )
        return self.repository.add(gene)

    def transition_status(
        self, gene_id: str, target: GeneStatus, *, reason: str | None = None
    ) -> Gene:
        current = self.repository.latest(gene_id)
        if current is None:
            raise KeyError(f"No gene with id {gene_id}")
        if not can_transition(current.status, target):
            raise ValueError(f"Cannot transition gene {gene_id}: {current.status} -> {target}")
        next_revision = current.model_copy(
            update={
                "version": current.version + 1,
                "status": target,
                "retired_at": date.today() if target == GeneStatus.RETIRED else current.retired_at,
                "retirement_reason": reason if target == GeneStatus.RETIRED else current.retirement_reason,
            }
        )
        return self.repository.add(next_revision)

    def mutate(self, parent_gene_id: str, new_knowledge: KnowledgeObject, mutation_notes: str) -> Gene:
        """Create a new gene superseding `parent_gene_id`.

        The parent is marked REPLACED and gains a forward link to the
        child; it is never overwritten or deleted, so the parent's full
        history remains queryable via `repository.history(parent_gene_id)`.
        """
        parent = self.repository.latest(parent_gene_id)
        if parent is None:
            raise KeyError(f"No gene with id {parent_gene_id}")

        child = Gene(
            id=new_id("gene"),
            knowledge_id=new_knowledge.id,
            generation=parent.generation + 1,
            parent_gene_ids=[parent.id],
            mutation_notes=mutation_notes,
            evidence=list(new_knowledge.supporting_evidence),
            status=GeneStatus.PROMOTED,
            provenance=Provenance(
                produced_by="alpha_genome.mutate",
                produced_at=datetime.now(),
                inputs=[
                    ProvenanceRef(kind="gene", ref_id=parent.id, ref_version=parent.version),
                    ProvenanceRef(
                        kind="knowledge", ref_id=new_knowledge.id, ref_version=new_knowledge.version
                    ),
                ],
            ),
        )
        self.repository.add(child)

        updated_parent = parent.model_copy(
            update={
                "version": parent.version + 1,
                "status": GeneStatus.REPLACED,
                "child_gene_ids": [*parent.child_gene_ids, child.id],
            }
        )
        self.repository.add(updated_parent)
        return child

    def merge(
        self, parent_gene_ids: list[str], new_knowledge: KnowledgeObject, mutation_notes: str
    ) -> Gene:
        """Synthesize multiple genes into one new gene (multi-parent lineage).

        The explicit resolution of the multi-parent question deferred in
        docs/EPOCH_II_REPORT.md: `mutate()` remains single-parent (a
        refinement of one idea); `merge()` is for a discovery whose
        evidence genuinely synthesizes several prior genes. Every parent is
        marked REPLACED with a forward link to the child; as always,
        nothing is overwritten.
        """
        if len(parent_gene_ids) < 2:
            raise ValueError("merge() requires at least two parent genes; use mutate() for one")
        parents = []
        for parent_id in parent_gene_ids:
            parent = self.repository.latest(parent_id)
            if parent is None:
                raise KeyError(f"No gene with id {parent_id}")
            parents.append(parent)

        child = Gene(
            id=new_id("gene"),
            knowledge_id=new_knowledge.id,
            generation=max(parent.generation for parent in parents) + 1,
            parent_gene_ids=[parent.id for parent in parents],
            mutation_notes=mutation_notes,
            evidence=list(new_knowledge.supporting_evidence),
            status=GeneStatus.PROMOTED,
            provenance=Provenance(
                produced_by="alpha_genome.merge",
                produced_at=datetime.now(),
                inputs=[
                    *[
                        ProvenanceRef(kind="gene", ref_id=parent.id, ref_version=parent.version)
                        for parent in parents
                    ],
                    ProvenanceRef(
                        kind="knowledge", ref_id=new_knowledge.id, ref_version=new_knowledge.version
                    ),
                ],
            ),
        )
        self.repository.add(child)

        for parent in parents:
            self.repository.add(
                parent.model_copy(
                    update={
                        "version": parent.version + 1,
                        "status": GeneStatus.REPLACED,
                        "child_gene_ids": [*parent.child_gene_ids, child.id],
                    }
                )
            )
        return child

    def record_performance(self, gene_id: str, record: PerformanceRecord) -> Gene:
        current = self.repository.latest(gene_id)
        if current is None:
            raise KeyError(f"No gene with id {gene_id}")
        next_revision = current.model_copy(
            update={
                "version": current.version + 1,
                "performance_history": [*current.performance_history, record],
            }
        )
        return self.repository.add(next_revision)

    def lineage(self, gene_id: str) -> list[Gene]:
        """Walk parent links back to the root gene, oldest first."""
        chain: list[Gene] = []
        current = self.repository.latest(gene_id)
        while current is not None:
            chain.append(current)
            if not current.parent_gene_ids:
                break
            current = self.repository.latest(current.parent_gene_ids[0])
        return list(reversed(chain))
