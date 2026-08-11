"""The Target Factory: forward-looking outcome series, always computed
strictly *after* the anchor date they're paired against a feature at.

Every target here is built the same way `data.adjustments.
horizon_forward_returns` already computes a forward return — from
split/dividend-adjusted closes, using the anchor date's own close as the
entry reference price (the same convention `validation.backtest.
NaiveDirectionalBacktester` and `hypotheses.experiment_factory`'s
experiments already rely on) — but reading strictly `closes[i+1 : i+1+h]`
for MFE/MAE/drawdown, never `closes[i]` itself, is what keeps this
leakage-safe: the *feature* at row `i` may only depend on information
available up to and including day `i` (`features.FeatureSeries.as_of_value`
enforces that on the read side), while every target value at row `i`
depends only on strictly later bars. `patterns.leakage` tests this
boundary directly with a deliberately broken target builder.
"""

from __future__ import annotations

import statistics
from datetime import date
from enum import Enum

from pydantic import BaseModel, Field

from agx_research.patterns.panel import ResearchPanel

TARGET_HORIZONS: tuple[int, ...] = (5, 10, 20, 60)
DEFAULT_EXCEEDANCE_THRESHOLDS: tuple[float, ...] = (0.02, 0.05)


class TargetKind(str, Enum):
    FORWARD_RETURN = "forward_return"
    MFE = "mfe"
    MAE = "mae"
    MAX_DRAWDOWN_AFTER_SIGNAL = "max_drawdown_after_signal"
    PROB_POSITIVE = "prob_positive"
    PROB_EXCEEDS = "prob_exceeds"
    RELATIVE_RETURN_MARKET = "relative_return_market"
    RELATIVE_RETURN_SECTOR = "relative_return_sector"
    BARRIER_OUTCOME = "barrier_outcome"


# (upper_pct, lower_pct) pairs, e.g. (0.05, -0.03) = "+5% before -3%".
# Declared, uncalibrated starting grid -- same posture as every other
# declared constant in this package.
DEFAULT_BARRIERS: tuple[tuple[float, float], ...] = ((0.05, -0.03), (0.10, -0.05))
DEFAULT_BARRIER_MAX_HORIZON_DAYS = 20


class TargetSpec(BaseModel):
    id: str
    kind: TargetKind
    horizon_days: int
    threshold: float | None = None
    threshold_lower: float | None = None


class TargetSeries(BaseModel):
    id: str
    spec: TargetSpec
    ticker: str
    dates: list[date] = Field(default_factory=list)
    values: list[float | None] = Field(default_factory=list)

    def value_at(self, t: date) -> float | None:
        try:
            return self.values[self.dates.index(t)]
        except ValueError:
            return None

    def observations(self) -> list[tuple[date, float]]:
        return [(d, v) for d, v in zip(self.dates, self.values) if v is not None]


def forward_return_series(closes: list[float], h: int) -> list[float | None]:
    """Public: the same forward-return arithmetic `TargetFactory` uses
    internally, exposed so `baselines.py` computes the identical
    momentum/mean-reversion/market-return baselines from one shared
    definition rather than a parallel one."""
    n = len(closes)
    return [
        (closes[i + h] - closes[i]) / closes[i] if i + h < n and closes[i] != 0 else None
        for i in range(n)
    ]


class TargetFactory:
    def __init__(self, panel: ResearchPanel, *, horizons: tuple[int, ...] = TARGET_HORIZONS):
        self.panel = panel
        self.horizons = horizons
        self._market_forward: dict[int, dict[date, float]] = {}
        self._sector_forward: dict[tuple[str, int], dict[date, float]] = {}

    def build_forward_returns(self, ticker: str) -> list[TargetSeries]:
        s = self.panel.series[ticker]
        closes = s.adjusted_close
        out = []
        for h in self.horizons:
            values = self._forward_return_series(closes, h)
            out.append(self._series(f"forward_return_{h}d", TargetKind.FORWARD_RETURN, h, None, ticker, s.dates, values))
        return out

    def build_mfe_mae(self, ticker: str) -> list[TargetSeries]:
        s = self.panel.series[ticker]
        closes, highs, lows = s.adjusted_close, s.high, s.low
        n = len(closes)
        out = []
        for h in self.horizons:
            mfe: list[float | None] = []
            mae: list[float | None] = []
            drawdown: list[float | None] = []
            for i in range(n):
                if i + h >= n or closes[i] == 0:
                    mfe.append(None)
                    mae.append(None)
                    drawdown.append(None)
                    continue
                entry = closes[i]
                window_highs = highs[i + 1 : i + 1 + h]
                window_lows = lows[i + 1 : i + 1 + h]
                window_closes = closes[i + 1 : i + 1 + h]
                mfe.append((max(window_highs) - entry) / entry)
                mae.append((min(window_lows) - entry) / entry)
                running_peak = entry
                max_dd = 0.0
                for c in window_closes:
                    running_peak = max(running_peak, c)
                    if running_peak > 0:
                        max_dd = min(max_dd, (c - running_peak) / running_peak)
                drawdown.append(max_dd)
            out.append(self._series(f"mfe_{h}d", TargetKind.MFE, h, None, ticker, s.dates, mfe))
            out.append(self._series(f"mae_{h}d", TargetKind.MAE, h, None, ticker, s.dates, mae))
            out.append(
                self._series(
                    f"max_drawdown_after_signal_{h}d",
                    TargetKind.MAX_DRAWDOWN_AFTER_SIGNAL, h, None, ticker, s.dates, drawdown,
                )
            )
        return out

    def build_probability_targets(
        self, ticker: str, *, thresholds: tuple[float, ...] = DEFAULT_EXCEEDANCE_THRESHOLDS
    ) -> list[TargetSeries]:
        s = self.panel.series[ticker]
        closes = s.adjusted_close
        out = []
        for h in self.horizons:
            forward = self._forward_return_series(closes, h)
            positive = [None if v is None else (1.0 if v > 0 else 0.0) for v in forward]
            out.append(self._series(f"prob_positive_{h}d", TargetKind.PROB_POSITIVE, h, None, ticker, s.dates, positive))
            for threshold in thresholds:
                exceeds = [None if v is None else (1.0 if v > threshold else 0.0) for v in forward]
                out.append(
                    self._series(
                        f"prob_exceeds_{threshold:.0%}_{h}d",
                        TargetKind.PROB_EXCEEDS, h, threshold, ticker, s.dates, exceeds,
                    )
                )
        return out

    def build_relative_targets(self, ticker: str) -> list[TargetSeries]:
        s = self.panel.series[ticker]
        closes = s.adjusted_close
        out = []
        for h in self.horizons:
            own_forward = dict(zip(s.dates, self._forward_return_series(closes, h)))
            market_forward = self._market_forward_returns(h)
            values = [
                own_forward[d] - market_forward[d]
                if own_forward.get(d) is not None and market_forward.get(d) is not None
                else None
                for d in s.dates
            ]
            out.append(
                self._series(
                    f"relative_return_market_{h}d", TargetKind.RELATIVE_RETURN_MARKET, h, None, ticker, s.dates, values
                )
            )
            sector = self.panel.sectors.get(ticker)
            if sector:
                sector_forward = self._sector_forward_returns(sector, h)
                sector_values = [
                    own_forward[d] - sector_forward[d]
                    if own_forward.get(d) is not None and sector_forward.get(d) is not None
                    else None
                    for d in s.dates
                ]
                out.append(
                    self._series(
                        f"relative_return_sector_{h}d", TargetKind.RELATIVE_RETURN_SECTOR, h, None, ticker, s.dates, sector_values
                    )
                )
        return out

    def build_all(self, ticker: str) -> list[TargetSeries]:
        return [
            *self.build_forward_returns(ticker),
            *self.build_mfe_mae(ticker),
            *self.build_probability_targets(ticker),
            *self.build_relative_targets(ticker),
        ]

    # ---- shared helpers ----

    def _forward_return_series(self, closes: list[float], h: int) -> list[float | None]:
        return forward_return_series(closes, h)

    def _market_forward_returns(self, h: int) -> dict[date, float]:
        if h in self._market_forward:
            return self._market_forward[h]
        by_date: dict[date, list[float]] = {}
        for s in self.panel.series.values():
            for d, v in zip(s.dates, self._forward_return_series(s.adjusted_close, h)):
                if v is not None:
                    by_date.setdefault(d, []).append(v)
        result = {d: statistics.fmean(vs) for d, vs in by_date.items()}
        self._market_forward[h] = result
        return result

    def _sector_forward_returns(self, sector: str, h: int) -> dict[date, float]:
        key = (sector, h)
        if key in self._sector_forward:
            return self._sector_forward[key]
        by_date: dict[date, list[float]] = {}
        for ticker, s in self.panel.series.items():
            if self.panel.sectors.get(ticker) != sector:
                continue
            for d, v in zip(s.dates, self._forward_return_series(s.adjusted_close, h)):
                if v is not None:
                    by_date.setdefault(d, []).append(v)
        result = {d: statistics.fmean(vs) for d, vs in by_date.items()}
        self._sector_forward[key] = result
        return result

    @staticmethod
    def _series(
        target_key: str,
        kind: TargetKind,
        horizon_days: int,
        threshold: float | None,
        ticker: str,
        dates: list[date],
        values: list[float | None],
        threshold_lower: float | None = None,
    ) -> TargetSeries:
        target_id = f"{target_key}:{ticker}"
        return TargetSeries(
            id=target_id,
            spec=TargetSpec(
                id=target_key, kind=kind, horizon_days=horizon_days,
                threshold=threshold, threshold_lower=threshold_lower,
            ),
            ticker=ticker,
            dates=list(dates),
            values=list(values),
        )

    def build_barrier_targets(
        self,
        ticker: str,
        *,
        barriers: tuple[tuple[float, float], ...] = DEFAULT_BARRIERS,
        max_horizon_days: int = DEFAULT_BARRIER_MAX_HORIZON_DAYS,
    ) -> list[TargetSeries]:
        """`+upper_pct before -lower_pct` (or vice versa), first-touch,
        walking `closes[i+1:i+1+max_horizon_days]` day by day using that
        day's High for the upper barrier and Low for the lower barrier
        (the same "read High/Low for path-dependent outcomes, never just
        Close" discipline `build_mfe_mae` already uses) -- strictly
        forward-looking, identical leakage posture to every other target
        this factory builds. `+1.0` = upper touched first, `-1.0` = lower
        touched first, `0.0` = neither touched within `max_horizon_days`
        (a real "no-touch" outcome, not a fabricated breakeven)."""
        s = self.panel.series[ticker]
        closes, highs, lows = s.adjusted_close, s.high, s.low
        n = len(closes)
        out = []
        for upper_pct, lower_pct in barriers:
            values: list[float | None] = []
            for i in range(n):
                if i + 1 >= n or closes[i] == 0:
                    values.append(None)
                    continue
                entry = closes[i]
                upper_price = entry * (1 + upper_pct)
                lower_price = entry * (1 + lower_pct)
                window_end = min(n, i + 1 + max_horizon_days)
                outcome = 0.0
                for j in range(i + 1, window_end):
                    upper_hit = highs[j] >= upper_price
                    lower_hit = lows[j] <= lower_price
                    if upper_hit and lower_hit:
                        # Both touched the same bar -- can't tell which came
                        # first from daily OHLC alone; report as a tie
                        # (0.0) rather than fabricate an intrabar order.
                        outcome = 0.0
                        break
                    if upper_hit:
                        outcome = 1.0
                        break
                    if lower_hit:
                        outcome = -1.0
                        break
                if window_end <= i + 1:
                    values.append(None)
                else:
                    values.append(outcome)
            label = f"barrier_+{upper_pct:.0%}_{lower_pct:.0%}_{max_horizon_days}d"
            out.append(
                self._series(
                    label, TargetKind.BARRIER_OUTCOME, max_horizon_days, upper_pct, ticker, s.dates, values,
                    threshold_lower=lower_pct,
                )
            )
        return out


__all__ = [
    "DEFAULT_EXCEEDANCE_THRESHOLDS",
    "TARGET_HORIZONS",
    "TargetFactory",
    "TargetKind",
    "TargetSeries",
    "TargetSpec",
    "forward_return_series",
]
