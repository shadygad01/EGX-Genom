"""The seven charter data-quality scores, computed mechanically per batch.

No downstream system may ignore data quality: `CollectionBatch` results
are wrapped in a `QualityAssessment` before materialization, and
`CollectionService` refuses to materialize a batch whose composite
confidence falls below a configurable floor (never silently degrading
what reaches the platform).

- `coverage_score`: fraction of the batch's declared scope (tickers,
  series, date range) actually produced by parsing.
- `freshness_score`: how close the newest record is to the fetch time,
  relative to the source's declared update frequency (a same-day fetch on
  a daily source scores 1.0; scores decay as staleness grows).
- `reliability_score`: currently the source's declared/measured prior
  (`SourceSpec.reliability_score`) — a per-batch reliability measurement
  needs cross-source corroboration history, which is the Event Platform's
  job over time, not a single collector run's.
- `consistency_score`: agreement with a second source over the same
  values, when one is supplied; **None** (never a guessed number) when no
  second source is available for this batch.
- `completeness_score`: fraction of parsed records with no missing
  required fields (parse warnings count directly against this).
- `validation_score`: fraction of parsed price bars passing
  `data.quality.validate_price_bars` with no ERROR-severity issues.
- `confidence_score`: the composite — the mean of every *measured*
  component (consistency excluded when unavailable) — documented, not
  arbitrary.
"""

from __future__ import annotations

from pydantic import BaseModel, Field

from agx_research.collectors.base import CollectionBatch
from agx_research.data.quality import QualityIssueSeverity, validate_price_bars


class QualityAssessment(BaseModel):
    coverage_score: float = Field(ge=0.0, le=1.0)
    freshness_score: float = Field(ge=0.0, le=1.0)
    reliability_score: float = Field(ge=0.0, le=1.0)
    consistency_score: float | None = Field(default=None, ge=0.0, le=1.0)
    completeness_score: float = Field(ge=0.0, le=1.0)
    validation_score: float = Field(ge=0.0, le=1.0)
    confidence_score: float = Field(ge=0.0, le=1.0)
    notes: str = ""


def _validation_score(batch: CollectionBatch) -> float:
    if not batch.price_bars:
        return 1.0  # nothing to invalidate
    by_ticker: dict[str, list] = {}
    for bar in batch.price_bars:
        by_ticker.setdefault(bar.ticker, []).append(bar)
    total = len(batch.price_bars)
    errors = 0
    for ticker, bars in by_ticker.items():
        issues = validate_price_bars(ticker, bars)
        errors += sum(1 for i in issues if i.severity == QualityIssueSeverity.ERROR)
    return max(0.0, 1.0 - errors / total)


def _completeness_score(batch: CollectionBatch) -> float:
    produced = (
        len(batch.price_bars)
        + len(batch.macro_observations)
        + len(batch.news_items)
        + len(batch.corporate_events)
        + len(batch.index_constituents)
        + len(batch.financial_statement_line_items)
    )
    if produced == 0:
        return 0.0 if batch.parse_warnings else 1.0
    return produced / (produced + len(batch.parse_warnings))


def assess_quality(
    batch: CollectionBatch,
    *,
    expected_records: int,
    source_reliability: float,
    freshness_score: float = 1.0,
    consistency_score: float | None = None,
) -> QualityAssessment:
    produced = (
        len(batch.price_bars)
        + len(batch.macro_observations)
        + len(batch.news_items)
        + len(batch.corporate_events)
        + len(batch.index_constituents)
        + len(batch.financial_statement_line_items)
    )
    coverage = min(1.0, produced / expected_records) if expected_records > 0 else (
        1.0 if produced > 0 else 0.0
    )
    completeness = _completeness_score(batch)
    validation = _validation_score(batch)

    measured = [coverage, freshness_score, source_reliability, completeness, validation]
    if consistency_score is not None:
        measured.append(consistency_score)
    confidence = sum(measured) / len(measured)

    return QualityAssessment(
        coverage_score=coverage,
        freshness_score=freshness_score,
        reliability_score=source_reliability,
        consistency_score=consistency_score,
        completeness_score=completeness,
        validation_score=validation,
        confidence_score=confidence,
        notes=(
            f"{produced} record(s) from {expected_records} expected; "
            f"{len(batch.parse_warnings)} parse warning(s)."
        ),
    )
