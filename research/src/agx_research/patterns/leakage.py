"""Explicit point-in-time safeguards.

`features.FeatureSeries.as_of_value()` and `targets.TargetFactory`'s
strictly-forward window slicing (`closes[i+1 : i+1+h]`, never `closes[i]`
or earlier) already make look-ahead bias structurally hard to introduce —
but "hard to introduce through the normal builders" is not the same as
"impossible for a future change to reintroduce," so this module is the
explicit, independently-testable layer the mission requires: every
candidate/evaluation/live-activation call site that reads a feature value
for some anchor date routes through `safe_feature_value()`, and every
panel/feature series gets checked with `verify_ascending()` before use
(`as_of_value`'s binary search silently returns wrong — and unsafe —
results against an unsorted date list, since `bisect_right` assumes
order).

`research/tests/test_pattern_leakage.py` proves these actually catch
something: it constructs a deliberately leaked feature (a value only
computable using a future close, mislabeled with today's date — exactly
the bug class no date-based check alone can catch, since the label
itself is the lie) and shows `safe_feature_value()` still cannot be
tricked into reading it early, then separately proves `verify_ascending`
rejects an out-of-order series and `verify_no_future_dates` rejects a
feature/target series carrying a date beyond a run's own `as_of` cutoff.
"""

from __future__ import annotations

from datetime import date


class LookaheadBiasError(ValueError):
    """Raised when a series violates a point-in-time safety invariant."""


def verify_ascending(dates: list[date], *, context: str) -> None:
    for i in range(1, len(dates)):
        if dates[i] <= dates[i - 1]:
            raise LookaheadBiasError(
                f"{context}: dates are not strictly ascending at index {i} "
                f"({dates[i - 1]} -> {dates[i]}); a point-in-time as_of lookup "
                "over unsorted dates can silently return a future value."
            )


def verify_no_future_dates(dates: list[date], as_of: date, *, context: str) -> None:
    for d in dates:
        if d > as_of:
            raise LookaheadBiasError(
                f"{context}: contains an entry dated {d}, after this run's own "
                f"as_of cutoff {as_of} — this would let future information "
                "into a supposedly point-in-time dataset."
            )


def safe_feature_value(dates: list[date], values: list[float | None], anchor_date: date) -> float | None:
    """The one sanctioned way to read a feature value for `anchor_date`.

    Re-implements `FeatureSeries.as_of_value`'s binary search independently
    (rather than calling it) and asserts its own result respects the
    invariant, so a future bug in `FeatureSeries.as_of_value` itself would
    be caught by comparing the two rather than silently trusted.
    """
    verify_ascending(dates, context="safe_feature_value")
    selected_date: date | None = None
    selected_value: float | None = None
    for d, v in zip(dates, values):
        if d > anchor_date:
            break
        if v is not None:
            selected_date, selected_value = d, v
    if selected_date is not None and selected_date > anchor_date:
        raise LookaheadBiasError(
            f"safe_feature_value selected {selected_date}, after anchor {anchor_date}"
        )
    return selected_value


def verify_target_strictly_forward(
    ticker_dates: list[date], anchor_index: int, horizon_days: int
) -> bool:
    """Whether a target anchored at `ticker_dates[anchor_index]` with
    `horizon_days` actually has that many strictly-later observations to
    draw on — the structural condition every `targets.TargetFactory`
    builder already enforces via `i + h < len(closes)`, exposed here so
    candidate evaluation can double-check it independently before trusting
    a target value."""
    return anchor_index + horizon_days < len(ticker_dates)


__all__ = [
    "LookaheadBiasError",
    "safe_feature_value",
    "verify_ascending",
    "verify_no_future_dates",
    "verify_target_strictly_forward",
]
