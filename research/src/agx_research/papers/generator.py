"""Mechanically assembles a ResearchPaper from the evidence that already exists.

Every sentence in every section traces to a field on an input object —
`gene`, `hypothesis`, `knowledge`, the experiment results, and (optionally)
a `CausalAssessment`. There is no free-text generation divorced from data.
"""

from __future__ import annotations

from datetime import datetime

from agx_research.causal.assessment import CausalAssessment
from agx_research.domain.identifiers import new_id
from agx_research.domain.provenance import Provenance, ProvenanceRef
from agx_research.genome.gene import Gene
from agx_research.hypotheses.experiment import ExperimentResult
from agx_research.hypotheses.hypothesis import Hypothesis
from agx_research.knowledge.schema import KnowledgeObject
from agx_research.papers.paper import ResearchPaper


def generate_paper(
    *,
    gene: Gene,
    hypothesis: Hypothesis,
    knowledge: KnowledgeObject,
    experiment_results: dict[str, ExperimentResult],
    causal_assessment: CausalAssessment | None = None,
    dataset_snapshot_id: str | None = None,
) -> ResearchPaper:
    experiments_section = (
        "; ".join(
            f"{name}: statistic={result.statistic:.4f}, p_value={result.p_value:.4g}, "
            f"n={result.sample_size}"
            for name, result in experiment_results.items()
        )
        or "No experiments were run."
    )

    evidence_section = "; ".join(knowledge.supporting_evidence) or "No additional supporting evidence recorded."
    evidence_section += (
        f" | statistical_evidence: method={knowledge.statistical_evidence.method}, "
        f"statistic={knowledge.statistical_evidence.statistic:.4f}, "
        f"p_value={knowledge.statistical_evidence.p_value:.4g}, "
        f"sample_size={knowledge.statistical_evidence.sample_size}"
    )

    limitations_section = (
        causal_assessment.notes
        if causal_assessment is not None
        else (
            "No causal assessment was attached to this promotion; correlation-only "
            "evidence should be treated cautiously."
        )
    )

    provenance_inputs = [
        ProvenanceRef(kind="gene", ref_id=gene.id, ref_version=gene.version),
        ProvenanceRef(kind="hypothesis", ref_id=hypothesis.id, ref_version=hypothesis.version),
        ProvenanceRef(kind="knowledge", ref_id=knowledge.id, ref_version=knowledge.version),
    ]

    return ResearchPaper(
        id=new_id("paper"),
        title=hypothesis.statement,
        gene_id=gene.id,
        knowledge_id=knowledge.id,
        hypothesis_id=hypothesis.id,
        problem=(
            f'Does the following hold: "{hypothesis.statement}"? Evaluated for '
            f"{', '.join(hypothesis.affected_assets)} over the {hypothesis.horizon.value} horizon."
        ),
        observation=(
            f"Originally proposed by {hypothesis.created_by} on {hypothesis.created_at.isoformat()}."
        ),
        methodology=(
            f"Validation pipeline: {' -> '.join(gate.name for gate in hypothesis.pipeline)}. "
            f"Final gate reached: {hypothesis.current_stage_name}."
        ),
        dataset=(
            f"Dataset snapshot {dataset_snapshot_id}."
            if dataset_snapshot_id
            else "Dataset snapshot id not provided to the generator; trace it via the "
            "hypothesis's provenance chain instead."
        ),
        experiments=experiments_section,
        evidence=evidence_section,
        results=(
            f"Expected return {knowledge.expected_return:.4f}, expected risk "
            f"{knowledge.expected_risk:.4f}, confidence {knowledge.confidence:.2f}. "
            f"Gene generation {gene.generation}, status {gene.status.value}."
        ),
        limitations=limitations_section,
        conclusion=knowledge.economic_explanation,
        future_work=(
            "Monitor performance history for degradation (gene.performance_history); "
            "retire or mutate this gene if confidence weakens."
        ),
        published_at=datetime.now(),
        provenance=Provenance(
            produced_by="papers.generator.generate_paper",
            produced_at=datetime.now(),
            inputs=provenance_inputs,
        ),
    )
