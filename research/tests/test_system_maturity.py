from datetime import date, datetime

from agx_research.config import Horizon
from agx_research.collectors.raw import build_raw_document
from agx_research.meta.decision_ledger import DecisionPerformanceSummary
from agx_research.meta.publication_gate import LegalPublicationApproval, PublicationEvidenceRef
from agx_research.meta.system_maturity import SystemMaturityLevel, compute_system_maturity

AS_OF = date(2026, 7, 28)


def performance(horizon: Horizon, *, evaluated: int, significant_positive: bool) -> DecisionPerformanceSummary:
    return DecisionPerformanceSummary(
        horizon=horizon, decisions=evaluated, evaluated=evaluated, pending=0,
        insufficient_data=0, hit_rate=0.6 if evaluated else None,
        mean_realized_return=0.03 if evaluated else None,
        benchmark_evaluated=evaluated,
        mean_benchmark_return=0.01 if evaluated else None,
        mean_excess_return=0.02 if significant_positive else (-0.01 if evaluated else None),
        mean_expected_return=0.03 if evaluated else None,
        median_excess_return=0.015 if significant_positive else (-0.01 if evaluated else None),
        excess_return_lower_95=0.005 if significant_positive else (-0.02 if evaluated else None),
        max_drawdown=-0.10 if evaluated else None,
        calibration_error=0.0 if evaluated else None,
        sample_status="sufficient" if evaluated >= 30 else "insufficient",
    )


def legal_approval() -> LegalPublicationApproval:
    document = build_raw_document(
        source_id="legal_review", collector="test", collector_version="1",
        original_url="https://example.test/legal_review", content_text="signed legal approval",
        schema_version="1", license="cleared", fetched_at=datetime(2026, 7, 1, 12, 0),
    )
    return LegalPublicationApproval(
        reviewer="Counsel", scope="public research", approved_at=datetime(2026, 7, 1),
        expires_at=date(2026, 12, 31), conflicts_disclosed=True, methodology_approved=True,
        evidence=PublicationEvidenceRef(
            raw_document_id=document.id, source_id=document.source_id,
            content_hash=document.content_hash, fetched_at=document.fetched_at,
            coverage_pct=1.0, independent_group="legal",
        ),
    )


def test_no_history_at_all_is_early():
    report = compute_system_maturity([], as_of=AS_OF)
    assert report.level == SystemMaturityLevel.EARLY


def test_some_history_below_ten_is_early():
    performances = [performance(h, evaluated=5, significant_positive=False) for h in Horizon]
    report = compute_system_maturity(performances, as_of=AS_OF)
    assert report.level == SystemMaturityLevel.EARLY


def test_ten_to_thirty_evaluated_is_validating():
    performances = [performance(h, evaluated=15, significant_positive=False) for h in Horizon]
    report = compute_system_maturity(performances, as_of=AS_OF)
    assert report.level == SystemMaturityLevel.VALIDATING


def test_thirty_plus_but_mixed_results_is_developing():
    performances = [performance(h, evaluated=30, significant_positive=False) for h in Horizon]
    report = compute_system_maturity(performances, as_of=AS_OF)
    assert report.level == SystemMaturityLevel.DEVELOPING


def test_thirty_plus_all_significant_and_positive_is_established():
    performances = [performance(h, evaluated=30, significant_positive=True) for h in Horizon]
    report = compute_system_maturity(performances, as_of=AS_OF)
    assert report.level == SystemMaturityLevel.ESTABLISHED
    assert report.governance_reviewed is False


def test_established_plus_valid_governance_review_is_verified():
    performances = [performance(h, evaluated=30, significant_positive=True) for h in Horizon]
    report = compute_system_maturity(performances, as_of=AS_OF, governance=legal_approval())
    assert report.level == SystemMaturityLevel.VERIFIED
    assert report.governance_reviewed is True


def test_governance_review_alone_never_substitutes_for_real_track_record():
    """A human sign-off can only ever raise the ceiling, never invent a
    track record that doesn't exist -- the exact opposite of the old
    gate, which required both simultaneously and blocked publishing
    entirely when either was missing."""
    performances = [performance(h, evaluated=5, significant_positive=False) for h in Horizon]
    report = compute_system_maturity(performances, as_of=AS_OF, governance=legal_approval())
    assert report.level == SystemMaturityLevel.EARLY


def test_one_lagging_horizon_caps_the_whole_report_below_established():
    performances = [
        performance(Horizon.MICRO, evaluated=30, significant_positive=True),
        performance(Horizon.SWING, evaluated=30, significant_positive=True),
        performance(Horizon.INVESTMENT, evaluated=30, significant_positive=False),
    ]
    report = compute_system_maturity(performances, as_of=AS_OF)
    assert report.level == SystemMaturityLevel.DEVELOPING
    assert report.horizons_meeting_significance_floor == 2
    assert report.total_horizons == 3


def test_expired_governance_review_does_not_count():
    performances = [performance(h, evaluated=30, significant_positive=True) for h in Horizon]
    expired = legal_approval().model_copy(update={"expires_at": date(2026, 1, 1)})
    report = compute_system_maturity(performances, as_of=AS_OF, governance=expired)
    assert report.level == SystemMaturityLevel.ESTABLISHED
    assert report.governance_reviewed is False
