from datetime import date, datetime

from agx_research.config import Horizon
from agx_research.collectors.raw import RawDocument, build_raw_document
from agx_research.meta.decision_ledger import DecisionPerformanceSummary
from agx_research.meta.publication_gate import (
    ExternalPublicationEvidence,
    LegalPublicationApproval,
    PublicationEvidenceRef,
    evaluate_publication_gate,
)


def performance(horizon: Horizon) -> DecisionPerformanceSummary:
    return DecisionPerformanceSummary(
        horizon=horizon, decisions=30, evaluated=30, pending=0,
        insufficient_data=0, hit_rate=0.6, mean_realized_return=0.03,
        benchmark_evaluated=30, mean_benchmark_return=0.01,
        mean_excess_return=0.02, mean_expected_return=0.03,
        median_excess_return=0.015, excess_return_lower_95=0.005,
        max_drawdown=-0.10, calibration_error=0.0, sample_status="sufficient",
    )


def raw(source_id: str, content: str) -> RawDocument:
    return build_raw_document(
        source_id=source_id, collector="test", collector_version="1",
        original_url=f"https://example.test/{source_id}", content_text=content,
        schema_version="1", license="cleared",
        fetched_at=datetime(2026, 7, 27, 12, 0),
    )


def ref(document: RawDocument, group: str) -> PublicationEvidenceRef:
    return PublicationEvidenceRef(
        raw_document_id=document.id, source_id=document.source_id,
        content_hash=document.content_hash, fetched_at=document.fetched_at,
        coverage_pct=1.0, independent_group=group,
    )


def complete_external() -> tuple[ExternalPublicationEvidence, list[RawDocument], set[str]]:
    fields = [
        "live_egx_market_data", "official_disclosures_four_periods",
        "current_cbe_capmas_macro", "two_source_price_corroboration",
    ]
    documents = {
        field: raw(f"source_{field}", field) for field in fields
    }
    second_price = raw("source_second_price", "independent price")
    external = ExternalPublicationEvidence(
        **{field: True for field in fields},
        evidence_refs={
            field: [ref(document, document.source_id)]
            for field, document in documents.items()
        },
    )
    external.evidence_refs["two_source_price_corroboration"].append(
        ref(second_price, second_price.source_id)
    )
    raw_documents = [*documents.values(), second_price]
    return external, raw_documents, {document.source_id for document in raw_documents}


def legal_approval() -> tuple[LegalPublicationApproval, RawDocument]:
    document = raw("legal_review", "signed legal approval")
    return LegalPublicationApproval(
        reviewer="Counsel", scope="public research", approved_at=datetime(2026, 7, 1),
        expires_at=date(2026, 12, 31), conflicts_disclosed=True,
        methodology_approved=True, evidence=ref(document, "legal"),
    ), document


def test_publication_gate_fails_closed_without_external_evidence():
    report = evaluate_publication_gate([], as_of=date(2026, 7, 28))
    assert report.publication_ready is False
    assert len(report.blockers) == 6


def test_invalid_input_file_is_exposed_as_a_gate_blocker():
    report = evaluate_publication_gate(
        [], as_of=date(2026, 7, 28), input_errors=["publication evidence schema invalid"]
    )
    assert report.publication_ready is False
    assert report.checks[0].id == "publication_input_validation"
    assert "schema invalid" in (report.checks[0].blocker or "")


def test_boolean_claim_without_reference_does_not_pass():
    external, documents, cleared = complete_external()
    external.evidence_refs["live_egx_market_data"] = []
    legal, legal_document = legal_approval()
    report = evaluate_publication_gate(
        [performance(horizon) for horizon in Horizon],
        as_of=date(2026, 7, 28), external=external,
        legal=legal, raw_documents=[*documents, legal_document],
        legally_cleared_source_ids=cleared,
    )
    assert report.publication_ready is False
    assert next(row for row in report.checks if row.id == "live_egx_market_data").passed is False


def test_complete_current_evidence_passes_gate():
    external, documents, cleared = complete_external()
    legal, legal_document = legal_approval()
    report = evaluate_publication_gate(
        [performance(horizon) for horizon in Horizon],
        as_of=date(2026, 7, 28), external=external, legal=legal,
        raw_documents=[*documents, legal_document],
        legally_cleared_source_ids=cleared,
    )
    assert report.publication_ready is True
    assert report.blockers == []


def test_unknown_or_tampered_raw_reference_fails_closed():
    external, documents, cleared = complete_external()
    external.evidence_refs["live_egx_market_data"][0] = (
        external.evidence_refs["live_egx_market_data"][0].model_copy(
            update={"content_hash": "0" * 64}
        )
    )
    legal, legal_document = legal_approval()
    report = evaluate_publication_gate(
        [performance(horizon) for horizon in Horizon],
        as_of=date(2026, 7, 28), external=external, legal=legal,
        raw_documents=[*documents, legal_document],
        legally_cleared_source_ids=cleared,
    )
    assert report.publication_ready is False
    assert next(
        check for check in report.checks if check.id == "live_egx_market_data"
    ).evidence_refs == []
