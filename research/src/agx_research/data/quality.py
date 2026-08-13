"""Mechanical data-quality validation for raw market data.

"Never fabricate data" cuts both ways: this codebase must also actively
catch obviously malformed input rather than silently computing statistics
over garbage. This is deliberately simple, mechanical sanity-checking — not
a replacement for a real vendor's own data-quality process, which is future
work once a real vendor exists. It exists so that a corrupted CSV row (or a
future vendor feed with a parsing bug) produces a loud, structured signal
instead of a silently wrong correlation three layers downstream.
"""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel

from agx_research.data.schemas import PriceBar


class QualityIssueSeverity(str, Enum):
    WARNING = "warning"
    ERROR = "error"


class QualityIssue(BaseModel):
    ticker: str
    trade_date: str
    severity: QualityIssueSeverity
    description: str


def validate_price_bars(ticker: str, bars: list[PriceBar]) -> list[QualityIssue]:
    """Check one ticker's price history for structurally impossible data.

    `bars` is checked as given (not re-sorted) so out-of-order input is
    itself flagged rather than silently corrected.
    """
    issues: list[QualityIssue] = []
    seen_dates: set = set()
    previous_date = None
    previous_close: float | None = None

    for bar in bars:
        date_str = bar.trade_date.isoformat()

        if bar.open <= 0 or bar.high <= 0 or bar.low <= 0 or bar.close <= 0:
            issues.append(
                QualityIssue(
                    ticker=ticker,
                    trade_date=date_str,
                    severity=QualityIssueSeverity.ERROR,
                    description="Non-positive open/high/low/close price.",
                )
            )
        if bar.high < bar.low:
            issues.append(
                QualityIssue(
                    ticker=ticker,
                    trade_date=date_str,
                    severity=QualityIssueSeverity.ERROR,
                    description=f"high ({bar.high}) is below low ({bar.low}).",
                )
            )
        if bar.high < max(bar.open, bar.close):
            issues.append(
                QualityIssue(
                    ticker=ticker,
                    trade_date=date_str,
                    severity=QualityIssueSeverity.ERROR,
                    description="high is below the greater of open/close.",
                )
            )
        if bar.low > min(bar.open, bar.close):
            issues.append(
                QualityIssue(
                    ticker=ticker,
                    trade_date=date_str,
                    severity=QualityIssueSeverity.ERROR,
                    description="low is above the lesser of open/close.",
                )
            )
        if bar.volume < 0:
            issues.append(
                QualityIssue(
                    ticker=ticker,
                    trade_date=date_str,
                    severity=QualityIssueSeverity.ERROR,
                    description="Negative volume.",
                )
            )
        if bar.volume == 0:
            issues.append(
                QualityIssue(
                    ticker=ticker,
                    trade_date=date_str,
                    severity=QualityIssueSeverity.WARNING,
                    description="Zero volume (possibly a halted or illiquid session).",
                )
            )
        if previous_close is not None and previous_close > 0:
            session_return = abs(bar.close / previous_close - 1)
            if session_return > 0.50:
                issues.append(
                    QualityIssue(
                        ticker=ticker,
                        trade_date=date_str,
                        severity=QualityIssueSeverity.WARNING,
                        description=(
                            f"Extreme close-to-close move ({session_return:.1%}); "
                            "review split, dividend, corporate action, or bad quote before valuation."
                        ),
                    )
                )
        if bar.trade_date in seen_dates:
            issues.append(
                QualityIssue(
                    ticker=ticker,
                    trade_date=date_str,
                    severity=QualityIssueSeverity.ERROR,
                    description="Duplicate trade_date in this series.",
                )
            )
        seen_dates.add(bar.trade_date)
        if previous_date is not None and bar.trade_date < previous_date:
            issues.append(
                QualityIssue(
                    ticker=ticker,
                    trade_date=date_str,
                    severity=QualityIssueSeverity.ERROR,
                    description=f"Out of order: precedes prior bar dated {previous_date.isoformat()}.",
                )
            )
        previous_date = bar.trade_date
        previous_close = bar.close

    return issues
