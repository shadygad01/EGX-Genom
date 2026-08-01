"""Phase 5: Confidence Calibration.

Wraps `meta.decision_ledger.DecisionLedger` (the only real source of
predicted-confidence-vs-observed-outcome pairs in this codebase) with
Brier score, a binned reliability curve, and expected calibration error
(ECE) -- none of which existed before. Nothing here fabricates a
calibration result: below `min_sample` benchmark-evaluated records (the
same 30-decision floor `DecisionLedger.performance_summary()` and
`docs/DECISION_SYSTEM_ACCEPTANCE.md` already require), every statistic is
`None` and `sample_status="insufficient"` -- ready for data, not a made-up
number standing in for one.
"""

from __future__ import annotations

from pydantic import BaseModel, Field

from agx_research.config import Horizon
from agx_research.meta.decision_ledger import DecisionLedger, DecisionRecord, OutcomeStatus

DEFAULT_MIN_SAMPLE = 30
#: Ten equal-width confidence bins, [0.0-0.1) .. [0.9-1.0] -- a
#: conventional reliability-diagram resolution, not a calibrated choice
#: (same declared-not-measured posture as this codebase's other constants;
#: see docs/TECHNICAL_DEBT.md).
_BIN_COUNT = 10


class ReliabilityBin(BaseModel):
    bin_lower: float
    bin_upper: float
    count: int
    mean_predicted_confidence: float | None = None
    observed_hit_rate: float | None = None


class CalibrationReport(BaseModel):
    horizon: Horizon
    sample_size: int
    min_sample: int
    sample_status: str  # "sufficient" | "insufficient"
    brier_score: float | None = None
    expected_calibration_error: float | None = None
    reliability_curve: list[ReliabilityBin] = Field(default_factory=list)
    mean_expected_return: float | None = None
    mean_realized_return: float | None = None
    calibration_error: float | None = None


class ConfidenceCalibrationFramework:
    def __init__(self, ledger: DecisionLedger, *, min_sample: int = DEFAULT_MIN_SAMPLE):
        self.ledger = ledger
        self.min_sample = min_sample

    def calibration_report(self, horizon: Horizon) -> CalibrationReport:
        records = [
            record
            for record in self.ledger.all_latest()
            if record.horizon == horizon
            and record.outcome_status == OutcomeStatus.EVALUATED
            and record.hit is not None
        ]
        sample_size = len(records)
        summary = next(
            (s for s in self.ledger.performance_summary(min_sample=self.min_sample) if s.horizon == horizon), None
        )
        report = CalibrationReport(
            horizon=horizon,
            sample_size=sample_size,
            min_sample=self.min_sample,
            sample_status="sufficient" if sample_size >= self.min_sample else "insufficient",
            mean_expected_return=summary.mean_expected_return if summary else None,
            mean_realized_return=summary.mean_realized_return if summary else None,
            calibration_error=summary.calibration_error if summary else None,
        )
        if sample_size < self.min_sample:
            return report  # honest early return -- ready for data, no fabricated statistic

        report.brier_score = _brier_score(records)
        report.reliability_curve = _reliability_curve(records)
        report.expected_calibration_error = _expected_calibration_error(report.reliability_curve, sample_size)
        return report


def _brier_score(records: list[DecisionRecord]) -> float:
    """Mean squared error between stated confidence and the binary
    realized outcome (excess-return-positive == 1, else 0) -- the standard
    proper scoring rule for a probabilistic forecast, lower is better
    (0 = perfect, 0.25 = a coin flip at 50% confidence, 1 = perfectly
    wrong)."""
    return sum((record.confidence - (1.0 if record.hit else 0.0)) ** 2 for record in records) / len(records)


def _reliability_curve(records: list[DecisionRecord]) -> list[ReliabilityBin]:
    bins: list[ReliabilityBin] = []
    for index in range(_BIN_COUNT):
        lower, upper = index / _BIN_COUNT, (index + 1) / _BIN_COUNT
        in_bin = [
            record
            for record in records
            if lower <= record.confidence < upper or (upper == 1.0 and record.confidence == 1.0)
        ]
        bins.append(
            ReliabilityBin(
                bin_lower=lower,
                bin_upper=upper,
                count=len(in_bin),
                mean_predicted_confidence=(
                    sum(record.confidence for record in in_bin) / len(in_bin) if in_bin else None
                ),
                observed_hit_rate=(
                    sum(1 for record in in_bin if record.hit) / len(in_bin) if in_bin else None
                ),
            )
        )
    return bins


def _expected_calibration_error(bins: list[ReliabilityBin], sample_size: int) -> float:
    """Sample-weighted mean absolute gap between predicted confidence and
    observed hit rate across non-empty bins -- lower is better calibrated."""
    return sum(
        (b.count / sample_size) * abs(b.mean_predicted_confidence - b.observed_hit_rate)
        for b in bins
        if b.count > 0
    )


__all__ = ["CalibrationReport", "ConfidenceCalibrationFramework", "DEFAULT_MIN_SAMPLE", "ReliabilityBin"]
