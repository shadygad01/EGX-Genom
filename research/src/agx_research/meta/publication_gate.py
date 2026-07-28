"""Fail-closed publication gate separating research output from public decisions."""

from __future__ import annotations

from datetime import date, datetime

from pydantic import BaseModel, Field

from agx_research.collectors.raw import RawDocument
from agx_research.config import Horizon
from agx_research.meta.decision_engine import (
    DecisionAction,
    PublicationStatus,
    Recommendation,
)
from agx_research.meta.decision_ledger import DecisionPerformanceSummary


class PublicationEvidenceRef(BaseModel):
    raw_document_id: str
    source_id: str
    content_hash: str = Field(pattern=r"^[0-9a-f]{64}$")
    fetched_at: datetime
    coverage_pct: float = Field(ge=0.0, le=1.0)
    independent_group: str


class ExternalPublicationEvidence(BaseModel):
    """Human-supplied claims are invalid unless backed by explicit references."""

    live_egx_market_data: bool = False
    official_disclosures_four_periods: bool = False
    current_cbe_capmas_macro: bool = False
    two_source_price_corroboration: bool = False
    evidence_refs: dict[str, list[PublicationEvidenceRef]] = Field(default_factory=dict)


class LegalPublicationApproval(BaseModel):
    reviewer: str
    scope: str
    approved_at: datetime
    expires_at: date
    conflicts_disclosed: bool = False
    methodology_approved: bool = False
    evidence: PublicationEvidenceRef


class PublicationGateCheck(BaseModel):
    id: str
    label: str
    passed: bool
    evidence_refs: list[str] = Field(default_factory=list)
    blocker: str | None = None


class PublicationGateReport(BaseModel):
    as_of: date
    publication_ready: bool
    checks: list[PublicationGateCheck]
    blockers: list[str]


_EXTERNAL_CHECKS = {
    "live_egx_market_data": "بيانات EGX حية ومسموح باستخدامها",
    "official_disclosures_four_periods": "إفصاحات رسمية وأربع فترات مالية",
    "current_cbe_capmas_macro": "بيانات CBE وCAPMAS حديثة",
    "two_source_price_corroboration": "تأكيد السعر من مصدرين مستقلين",
}

_MAX_EVIDENCE_AGE_DAYS = {
    "live_egx_market_data": 7,
    "official_disclosures_four_periods": 550,
    "current_cbe_capmas_macro": 45,
    "two_source_price_corroboration": 7,
}


def _reference_matches_raw(
    ref: PublicationEvidenceRef,
    raw_by_id: dict[str, RawDocument],
    *,
    as_of: date,
    max_age_days: int,
    legally_cleared_source_ids: set[str] | None,
) -> bool:
    raw = raw_by_id.get(ref.raw_document_id)
    return bool(
        raw
        and raw.source_id == ref.source_id
        and raw.content_hash == ref.content_hash
        and raw.fetched_at == ref.fetched_at
        and ref.coverage_pct == 1.0
        and ref.fetched_at.date() <= as_of
        and (as_of - ref.fetched_at.date()).days <= max_age_days
        and (
            legally_cleared_source_ids is None
            or ref.source_id in legally_cleared_source_ids
        )
    )


def evaluate_publication_gate(
    performance: list[DecisionPerformanceSummary],
    *,
    as_of: date,
    external: ExternalPublicationEvidence | None = None,
    legal: LegalPublicationApproval | None = None,
    raw_documents: list[RawDocument] | None = None,
    legally_cleared_source_ids: set[str] | None = None,
    input_errors: list[str] | None = None,
) -> PublicationGateReport:
    external = external or ExternalPublicationEvidence()
    raw_by_id = {document.id: document for document in (raw_documents or [])}
    checks: list[PublicationGateCheck] = []
    if input_errors:
        checks.append(PublicationGateCheck(
            id="publication_input_validation",
            label="سلامة ملفات أدلة النشر",
            passed=False,
            blocker="; ".join(input_errors),
        ))
    for field_name, label in _EXTERNAL_CHECKS.items():
        refs = external.evidence_refs.get(field_name, [])
        verified_refs = [
            ref for ref in refs
            if _reference_matches_raw(
                ref,
                raw_by_id,
                as_of=as_of,
                max_age_days=_MAX_EVIDENCE_AGE_DAYS[field_name],
                legally_cleared_source_ids=legally_cleared_source_ids,
            )
        ]
        independence_ok = (
            len({ref.independent_group for ref in verified_refs}) >= 2
            if field_name == "two_source_price_corroboration"
            else True
        )
        passed = bool(getattr(external, field_name)) and bool(verified_refs) and independence_ok
        checks.append(PublicationGateCheck(
            id=field_name,
            label=label,
            passed=passed,
            evidence_refs=[ref.raw_document_id for ref in verified_refs],
            blocker=None if passed else f"{label}: الشرط أو مرجع الدليل غير مكتمل.",
        ))

    by_horizon = {row.horizon: row for row in performance}
    performance_ok = all(
        (row := by_horizon.get(horizon)) is not None
        and row.sample_status == "sufficient"
        and row.benchmark_evaluated >= 30
        and row.mean_excess_return is not None
        and row.mean_excess_return > 0
        and row.median_excess_return is not None
        and row.median_excess_return > 0
        and row.excess_return_lower_95 is not None
        and row.excess_return_lower_95 > 0
        and row.mean_realized_return is not None
        and row.mean_realized_return > 0
        and row.max_drawdown is not None
        and row.max_drawdown >= -0.25
        for horizon in Horizon
    )
    checks.append(PublicationGateCheck(
        id="benchmark_performance",
        label="30 نتيجة متفوقة على EGX30 لكل أفق بعد التكلفة",
        passed=performance_ok,
        blocker=None if performance_ok else "الأداء لا يثبت تفوقًا موجبًا بثقة 95% وثباتًا ومخاطرة مقبولة لكل الآفاق.",
    ))

    legal_ok = bool(
        legal
        and legal.reviewer.strip()
        and legal.scope.strip()
        and _reference_matches_raw(
            legal.evidence,
            raw_by_id,
            as_of=as_of,
            max_age_days=366,
            legally_cleared_source_ids=None,
        )
        and legal.conflicts_disclosed
        and legal.methodology_approved
        and legal.approved_at.date() <= as_of <= legal.expires_at
    )
    checks.append(PublicationGateCheck(
        id="legal_approval",
        label="مراجعة قانونية بشرية سارية",
        passed=legal_ok,
        evidence_refs=[legal.evidence.raw_document_id] if legal else [],
        blocker=None if legal_ok else "لا توجد موافقة قانونية بشرية كاملة وسارية.",
    ))
    blockers = [check.blocker for check in checks if check.blocker]
    return PublicationGateReport(
        as_of=as_of,
        publication_ready=all(check.passed for check in checks),
        checks=checks,
        blockers=blockers,
    )


def apply_publication_gate(
    recommendations: list[Recommendation], report: PublicationGateReport
) -> list[Recommendation]:
    """Promote only non-abstaining decisions after the complete gate passes."""

    output = [item.model_copy(deep=True) for item in recommendations]
    for recommendation in output:
        for decision in recommendation.horizon_decisions.values():
            executable_buy = (
                decision.action != DecisionAction.BUY_CANDIDATE
                or (
                    decision.entry_value is not None
                    and decision.invalidation_value is not None
                )
            )
            decision.publication_status = (
                PublicationStatus.PUBLICATION_READY
                if report.publication_ready
                and decision.action != DecisionAction.ABSTAIN
                and executable_buy
                else PublicationStatus.RESEARCH_ONLY
            )
            decision.max_position_pct = (
                min(0.05, max(0.01, decision.confidence * 0.05))
                if decision.publication_status == PublicationStatus.PUBLICATION_READY
                and decision.action == DecisionAction.BUY_CANDIDATE
                else 0.0
            )
            if not report.publication_ready:
                decision.abstention_reasons.extend(
                    blocker for blocker in report.blockers
                    if blocker not in decision.abstention_reasons
                )
            if not executable_buy:
                blocker = "Buy decision lacks numeric entry and invalidation levels."
                if blocker not in decision.abstention_reasons:
                    decision.abstention_reasons.append(blocker)
    return output
