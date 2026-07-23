from datetime import datetime

from agx_research.domain.provenance import Provenance
from agx_research.orchestration.artifacts import ArtifactKind, ArtifactRepository


def test_store_mints_a_new_artifact_by_default():
    repo = ArtifactRepository()
    artifact = repo.store(
        kind=ArtifactKind.CORRELATION_MATRIX,
        payload={"COMI": {"MFPC": 0.42}},
        provenance=Provenance(produced_by="test", produced_at=datetime.now()),
    )
    assert artifact.version == 1
    assert repo.latest(artifact.id) == artifact


def test_store_versions_the_same_logical_artifact_across_calls():
    repo = ArtifactRepository()
    first = repo.store(
        kind=ArtifactKind.CORRELATION_MATRIX,
        payload={"COMI": {"MFPC": 0.42}},
        provenance=Provenance(produced_by="test", produced_at=datetime.now()),
        artifact_id="daily_correlation_matrix",
    )
    second = repo.store(
        kind=ArtifactKind.CORRELATION_MATRIX,
        payload={"COMI": {"MFPC": 0.45}},
        provenance=Provenance(produced_by="test", produced_at=datetime.now()),
        artifact_id="daily_correlation_matrix",
    )

    assert first.version == 1
    assert second.version == 2
    assert repo.latest("daily_correlation_matrix") == second
    assert len(repo.history("daily_correlation_matrix")) == 2


def test_store_accepts_a_pydantic_payload():
    from agx_research.hypotheses.experiment import ExperimentResult

    repo = ArtifactRepository()
    result = ExperimentResult(statistic=1.2, p_value=0.03, sample_size=30)
    artifact = repo.store(
        kind=ArtifactKind.EXPERIMENT_RESULT,
        payload=result,
        provenance=Provenance(produced_by="test", produced_at=datetime.now()),
    )
    assert artifact.payload["p_value"] == 0.03
