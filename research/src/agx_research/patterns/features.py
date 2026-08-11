"""The Feature Factory: programmatic feature generation over a `ResearchPanel`.

Every feature is produced by looping a small set of parameterized
transforms over a declared window grid (`PRICE_WINDOWS`, `VOLUME_WINDOWS`,
`CROSS_SECTIONAL_WINDOWS`) rather than a developer hand-writing one
function per experiment — the mission's own requirement ("generate
features programmatically rather than requiring manual feature
definitions for every experiment"). Window/threshold grids here are
declared, uncalibrated starting points, the same posture this codebase
already uses throughout for constants with no real multi-year EGX history
to calibrate against yet (see e.g. `market_memory.regime`'s own
`REGIME_LOOKBACK_DAYS` comment) — not a claim that these specific numbers
are optimal.

`FeatureSeries.as_of_value(t)` is the single point-in-time-safe join
primitive every downstream stage (candidate generation, evaluation,
live activation) must use to read a feature at some row date `t`: it only
ever returns the most recent entry whose own date is `<= t`, so a feature
can never be read before it existed. For price/volume/cross-sectional
features that date *is* the trading day itself (same-day close, no
assumed publication delay — consistent with `data.point_in_time`'s "0 lag
for near-real-time sources" default). For macro features the stored date
is already `data.point_in_time.known_as_of()` — the observation's date
*after* its source's assumed publication lag — never the raw
`observation_date`, so no separate lag needs to be re-applied at read
time. For fundamental features the stored date is `period_end_date +
ASSUMED_FILING_LAG_DAYS`, the same declared-floor treatment applied for
the identical reason `data.point_in_time.ASSUMED_PUBLICATION_LAG_DAYS`
exists: a filing is never public the instant its period ends.
"""

from __future__ import annotations

import statistics
from bisect import bisect_right
from datetime import date, timedelta
from enum import Enum

from pydantic import BaseModel, Field

from agx_research.data.point_in_time import known_as_of
from agx_research.features.correlation import pearson_correlation
from agx_research.patterns.panel import ResearchPanel

# Declared, uncalibrated window grids -- see module docstring.
PRICE_WINDOWS: tuple[int, ...] = (1, 3, 5, 10, 20, 60)
VOLUME_WINDOWS: tuple[int, ...] = (5, 10, 20)
CROSS_SECTIONAL_WINDOWS: tuple[int, ...] = (5, 10, 20)
VOLATILITY_REGIME_LOOKBACK_DAYS = 120

# A conservative floor for when an EGX quarterly/annual filing actually
# became public after its period end -- declared, not measured (no
# per-filing publication-timestamp evidence exists in this codebase yet),
# same posture as `data.point_in_time.ASSUMED_PUBLICATION_LAG_DAYS`.
ASSUMED_FILING_LAG_DAYS = 45

_MARKET_SCOPE = ""  # ticker="" marks a market-wide / cross-sectional-aggregate feature


class FeatureCategory(str, Enum):
    PRICE = "price"
    VOLUME = "volume"
    CROSS_SECTIONAL = "cross_sectional"
    FUNDAMENTAL = "fundamental"
    MACRO = "macro"


class FeatureSpec(BaseModel):
    id: str
    category: FeatureCategory
    name: str
    description: str
    parameters: dict[str, float | int | str] = Field(default_factory=dict)


class FeatureSeries(BaseModel):
    id: str
    spec: FeatureSpec
    ticker: str
    dates: list[date] = Field(default_factory=list)
    values: list[float | None] = Field(default_factory=list)

    def as_of_value(self, t: date) -> float | None:
        """The most recent non-null value dated at or before `t` — the
        only point-in-time-safe way to read this feature for a row
        anchored at `t`. `self.dates` must be ascending (guaranteed by
        every builder in this module)."""
        idx = bisect_right(self.dates, t) - 1
        while idx >= 0:
            if self.values[idx] is not None:
                return self.values[idx]
            idx -= 1
        return None

    def lagged_as_of_value(self, t: date, lag: int) -> float | None:
        """The value exactly `lag` positions before the as-of index for
        `t`, in this series' own date sequence -- the point-in-time-safe
        primitive lead/lag candidate generation (`candidates.py`) uses to
        test "X lagged by `lag` periods predicts Y anchored at `t`".
        `lag=0` is exactly `as_of_value(t)`. Unlike `as_of_value`, this
        does *not* skip nulls looking further back -- a lead/lag claim
        about "the value exactly `lag` periods ago" should honestly read
        as unavailable (`None`) if that specific position has no
        observation, not silently substitute an even-older one."""
        if lag <= 0:
            return self.as_of_value(t)
        idx = bisect_right(self.dates, t) - 1 - lag
        if idx < 0:
            return None
        return self.values[idx]

    def non_null_count(self) -> int:
        return sum(1 for v in self.values if v is not None)


def _returns_nd(adjusted_close: list[float], n: int) -> list[float | None]:
    return [
        (adjusted_close[i] - adjusted_close[i - n]) / adjusted_close[i - n]
        if i >= n and adjusted_close[i - n] != 0
        else None
        for i in range(len(adjusted_close))
    ]


def _daily_returns(adjusted_close: list[float]) -> list[float | None]:
    return [None] + [
        (adjusted_close[i] - adjusted_close[i - 1]) / adjusted_close[i - 1]
        if adjusted_close[i - 1] != 0
        else None
        for i in range(1, len(adjusted_close))
    ]


def _rolling(values: list[float], window: int, fn) -> list[float | None]:
    out: list[float | None] = []
    for i in range(len(values)):
        if i + 1 < window:
            out.append(None)
            continue
        out.append(fn(values[i + 1 - window : i + 1]))
    return out


def _percentile_rank(value: float, population: list[float]) -> float:
    if not population:
        return 0.5
    below = sum(1 for v in population if v < value)
    equal = sum(1 for v in population if v == value)
    return (below + 0.5 * equal) / len(population)


class FeatureFactory:
    """Runs every registered transform against one `ResearchPanel`."""

    def __init__(
        self,
        panel: ResearchPanel,
        *,
        price_windows: tuple[int, ...] = PRICE_WINDOWS,
        volume_windows: tuple[int, ...] = VOLUME_WINDOWS,
        cross_sectional_windows: tuple[int, ...] = CROSS_SECTIONAL_WINDOWS,
    ):
        self.panel = panel
        self.price_windows = price_windows
        self.volume_windows = volume_windows
        self.cross_sectional_windows = cross_sectional_windows

    # ---- price transforms ----

    def build_price_features(self, ticker: str) -> list[FeatureSeries]:
        s = self.panel.series[ticker]
        dates = s.dates
        closes = s.adjusted_close
        out: list[FeatureSeries] = []

        returns_by_window: dict[int, list[float | None]] = {}
        for n in self.price_windows:
            returns_by_window[n] = _returns_nd(closes, n)
            out.append(
                self._series(
                    f"return_{n}d", FeatureCategory.PRICE, ticker, dates, returns_by_window[n],
                    f"{n}-trading-day forward-looking-free adjusted return ending at each date",
                    {"window": n},
                )
            )
            # Acceleration: change in the N-day return over the trailing N days.
            accel = [
                returns_by_window[n][i] - returns_by_window[n][i - n]
                if i >= n and returns_by_window[n][i] is not None and returns_by_window[n][i - n] is not None
                else None
                for i in range(len(closes))
            ]
            out.append(
                self._series(
                    f"acceleration_{n}d", FeatureCategory.PRICE, ticker, dates, accel,
                    f"Change in the {n}-day return over the trailing {n} days (momentum of momentum)",
                    {"window": n},
                )
            )
            # Rolling high/low distance.
            highs = _rolling(s.high, n, max)
            lows = _rolling(s.low, n, min)
            dist_high = [
                (closes[i] - highs[i]) / highs[i] if highs[i] not in (None, 0) else None
                for i in range(len(closes))
            ]
            dist_low = [
                (closes[i] - lows[i]) / lows[i] if lows[i] not in (None, 0) else None
                for i in range(len(closes))
            ]
            out.append(
                self._series(
                    f"distance_from_high_{n}d", FeatureCategory.PRICE, ticker, dates, dist_high,
                    f"Close vs. trailing {n}-day rolling high, as a fraction (drawdown from high)",
                    {"window": n},
                )
            )
            out.append(
                self._series(
                    f"distance_from_low_{n}d", FeatureCategory.PRICE, ticker, dates, dist_low,
                    f"Close vs. trailing {n}-day rolling low, as a fraction",
                    {"window": n},
                )
            )

        daily = _daily_returns(closes)
        daily_clean_by_index: list[float | None] = daily
        for n in self.price_windows:
            if n < 2:
                continue
            vol = _rolling_with_none(daily_clean_by_index, n, lambda v: statistics.pstdev(v) if len(v) > 1 else None)
            out.append(
                self._series(
                    f"volatility_{n}d", FeatureCategory.PRICE, ticker, dates, vol,
                    f"Population stdev of daily adjusted returns over the trailing {n} days",
                    {"window": n},
                )
            )

        vol_20 = next((fs.values for fs in out if fs.spec.id == "volatility_20d"), None)
        if vol_20 is not None:
            regime = _rolling_with_none(
                vol_20,
                VOLATILITY_REGIME_LOOKBACK_DAYS,
                lambda v: _percentile_rank(v[-1], v[:-1]) if len(v) > 1 else None,
            )
            out.append(
                self._series(
                    "volatility_regime_pct", FeatureCategory.PRICE, ticker, dates, regime,
                    "Percentile rank of current 20-day volatility within its own trailing "
                    f"{VOLATILITY_REGIME_LOOKBACK_DAYS}-day history",
                    {"lookback": VOLATILITY_REGIME_LOOKBACK_DAYS},
                )
            )
        return out

    # ---- volume transforms ----

    def build_volume_features(self, ticker: str) -> list[FeatureSeries]:
        s = self.panel.series[ticker]
        dates = s.dates
        volume = [float(v) for v in s.volume]
        daily = _daily_returns(s.adjusted_close)
        out: list[FeatureSeries] = []

        for n in self.volume_windows:
            trailing_mean = _rolling_trailing_exclusive(volume, n, lambda v: statistics.fmean(v))
            relative_volume = [
                volume[i] / trailing_mean[i] if trailing_mean[i] not in (None, 0) else None
                for i in range(len(volume))
            ]
            out.append(
                self._series(
                    f"relative_volume_{n}d", FeatureCategory.VOLUME, ticker, dates, relative_volume,
                    f"Today's volume vs. the trailing {n}-day average (excluding today)",
                    {"window": n},
                )
            )
            trailing_std = _rolling_trailing_exclusive(
                volume, n, lambda v: statistics.pstdev(v) if len(v) > 1 else None
            )
            anomaly = [
                (volume[i] - trailing_mean[i]) / trailing_std[i]
                if trailing_mean[i] is not None and trailing_std[i] not in (None, 0)
                else None
                for i in range(len(volume))
            ]
            out.append(
                self._series(
                    f"turnover_anomaly_{n}d", FeatureCategory.VOLUME, ticker, dates, anomaly,
                    f"Z-score of today's volume vs. the trailing {n}-day distribution",
                    {"window": n},
                )
            )
            accel = [
                relative_volume[i] - relative_volume[i - n]
                if i >= n and relative_volume[i] is not None and relative_volume[i - n] is not None
                else None
                for i in range(len(volume))
            ]
            out.append(
                self._series(
                    f"volume_acceleration_{n}d", FeatureCategory.VOLUME, ticker, dates, accel,
                    f"Change in relative volume over the trailing {n} days",
                    {"window": n},
                )
            )
            pv_corr = _rolling_pair_corr(daily, volume, n)
            out.append(
                self._series(
                    f"price_volume_correlation_{n}d", FeatureCategory.VOLUME, ticker, dates, pv_corr,
                    f"Trailing {n}-day Pearson correlation of daily return and volume level "
                    "(price-volume divergence when strongly negative on rising price)",
                    {"window": n},
                )
            )
            pct = _rolling_with_none(
                volume, n, lambda v: _percentile_rank(v[-1], v[:-1]) if len(v) > 1 else None
            )
            out.append(
                self._series(
                    f"rolling_volume_percentile_{n}d", FeatureCategory.VOLUME, ticker, dates, pct,
                    f"Percentile rank of today's volume within its own trailing {n}-day history",
                    {"window": n},
                )
            )
        return out

    # ---- cross-sectional transforms ----

    def build_cross_sectional_features(self) -> list[FeatureSeries]:
        """Market-/sector-relative features, computed once per calendar
        date across every ticker with data that day (not per-ticker in
        isolation) — the shared-window discipline `market_memory.regime`/
        `market_memory.breadth` already document: a ticker's own last-N
        dates can silently not overlap another's, so this always keys off
        one shared calendar (`ResearchPanel.all_dates()`)."""
        calendar = self.panel.all_dates()
        out: list[FeatureSeries] = []

        for n in self.cross_sectional_windows:
            returns_by_ticker: dict[str, dict[date, float]] = {}
            for ticker, s in self.panel.series.items():
                nd = _returns_nd(s.adjusted_close, n)
                returns_by_ticker[ticker] = {
                    d: v for d, v in zip(s.dates, nd) if v is not None
                }

            market_pctile: dict[str, list[float | None]] = {t: [] for t in self.panel.tickers}
            sector_pctile: dict[str, list[float | None]] = {t: [] for t in self.panel.tickers}
            rel_strength: dict[str, list[float | None]] = {t: [] for t in self.panel.tickers}
            dispersion_series: list[float | None] = []

            for d in calendar:
                cross_section = {t: r[d] for t, r in returns_by_ticker.items() if d in r}
                values = list(cross_section.values())
                dispersion_series.append(statistics.pstdev(values) if len(values) > 1 else None)
                market_mean = statistics.fmean(values) if values else None

                by_sector: dict[str, list[float]] = {}
                for t, v in cross_section.items():
                    sector = self.panel.sectors.get(t)
                    if sector:
                        by_sector.setdefault(sector, []).append(v)

                for ticker in self.panel.tickers:
                    if ticker not in cross_section:
                        market_pctile[ticker].append(None)
                        sector_pctile[ticker].append(None)
                        rel_strength[ticker].append(None)
                        continue
                    value = cross_section[ticker]
                    market_pctile[ticker].append(_percentile_rank(value, values))
                    rel_strength[ticker].append(value - market_mean if market_mean is not None else None)
                    sector = self.panel.sectors.get(ticker)
                    sector_population = by_sector.get(sector, []) if sector else []
                    sector_pctile[ticker].append(
                        _percentile_rank(value, sector_population) if sector_population else None
                    )

            for ticker in self.panel.tickers:
                s = self.panel.series[ticker]
                out.append(
                    self._series(
                        f"market_percentile_{n}d", FeatureCategory.CROSS_SECTIONAL, ticker,
                        calendar, market_pctile[ticker],
                        f"Percentile rank of this ticker's {n}-day return among all tickers that date",
                        {"window": n},
                    )
                )
                out.append(
                    self._series(
                        f"sector_percentile_{n}d", FeatureCategory.CROSS_SECTIONAL, ticker,
                        calendar, sector_pctile[ticker],
                        f"Percentile rank of this ticker's {n}-day return within its own sector that date",
                        {"window": n},
                    )
                )
                out.append(
                    self._series(
                        f"relative_strength_{n}d", FeatureCategory.CROSS_SECTIONAL, ticker,
                        calendar, rel_strength[ticker],
                        f"This ticker's {n}-day return minus the equal-weighted market's {n}-day return",
                        {"window": n},
                    )
                )
                rank_pct = market_pctile[ticker]
                rank_change = [
                    rank_pct[i] - rank_pct[i - n]
                    if i >= n and rank_pct[i] is not None and rank_pct[i - n] is not None
                    else None
                    for i in range(len(calendar))
                ]
                out.append(
                    self._series(
                        f"rank_change_{n}d", FeatureCategory.CROSS_SECTIONAL, ticker,
                        calendar, rank_change,
                        f"Change in market-percentile rank over the trailing {n} days (leadership rotation)",
                        {"window": n},
                    )
                )

            out.append(
                self._series(
                    f"cross_sectional_dispersion_{n}d", FeatureCategory.CROSS_SECTIONAL, _MARKET_SCOPE,
                    calendar, dispersion_series,
                    f"Cross-sectional stdev of {n}-day returns across the universe that date",
                    {"window": n},
                )
            )

        breadth, hhi = self._breadth_and_concentration(calendar)
        out.append(
            self._series(
                "market_breadth", FeatureCategory.CROSS_SECTIONAL, _MARKET_SCOPE, calendar, breadth,
                "Fraction of tickers with a positive daily adjusted return that date", {},
            )
        )
        out.append(
            self._series(
                "volume_concentration_hhi", FeatureCategory.CROSS_SECTIONAL, _MARKET_SCOPE, calendar, hhi,
                "Herfindahl-Hirschman index of each ticker's share of total daily volume "
                "(higher = fewer names dominate turnover)",
                {},
            )
        )
        return out

    def _breadth_and_concentration(
        self, calendar: list[date]
    ) -> tuple[list[float | None], list[float | None]]:
        daily_by_ticker: dict[str, dict[date, float]] = {}
        volume_by_ticker: dict[str, dict[date, float]] = {}
        for ticker, s in self.panel.series.items():
            daily = _daily_returns(s.adjusted_close)
            daily_by_ticker[ticker] = {d: v for d, v in zip(s.dates, daily) if v is not None}
            volume_by_ticker[ticker] = dict(zip(s.dates, s.volume))

        breadth: list[float | None] = []
        hhi: list[float | None] = []
        for d in calendar:
            day_returns = [r[d] for r in daily_by_ticker.values() if d in r]
            breadth.append(
                sum(1 for r in day_returns if r > 0) / len(day_returns) if day_returns else None
            )
            volumes = [v[d] for v in volume_by_ticker.values() if d in v]
            total = sum(volumes)
            hhi.append(sum((v / total) ** 2 for v in volumes) if total > 0 else None)
        return breadth, hhi

    # ---- fundamental transforms ----

    def build_fundamental_features(self, ticker: str) -> list[FeatureSeries]:
        """Only ever computed from `ResearchPanel.financial_statements` —
        never fabricated. Empty when nothing is collected for `ticker`
        (currently every ticker, per `docs/PATTERN_DISCOVERY_DATA_AUDIT.md`),
        which is the honest, expected result, not a bug."""
        items = self.panel.financial_statements.get(ticker, [])
        if not items:
            return []

        by_line: dict[str, list[tuple[date, str, float]]] = {}
        for item in items:
            by_line.setdefault(item.line_item, []).append(
                (item.period_end_date, item.period_type, item.value)
            )

        out: list[FeatureSeries] = []
        for line_item, entries in by_line.items():
            entries.sort(key=lambda e: e[0])
            dates = [known_as_of(d, source=None) + timedelta(days=ASSUMED_FILING_LAG_DAYS) for d, _, _ in entries]
            values = [v for _, _, v in entries]

            yoy = [
                (values[i] - values[i - 4]) / abs(values[i - 4])
                if i >= 4 and entries[i][1] == "QUARTERLY" and values[i - 4] != 0
                else (
                    (values[i] - values[i - 1]) / abs(values[i - 1])
                    if i >= 1 and entries[i][1] == "ANNUAL" and values[i - 1] != 0
                    else None
                )
                for i in range(len(values))
            ]
            qoq = [
                (values[i] - values[i - 1]) / abs(values[i - 1])
                if i >= 1 and entries[i][1] == "QUARTERLY" and values[i - 1] != 0
                else None
                for i in range(len(values))
            ]
            trend = [
                statistics.fmean(values[max(0, i - 3) : i + 1]) if i >= 1 else None
                for i in range(len(values))
            ]
            accel = [
                yoy[i] - yoy[i - 1] if i >= 1 and yoy[i] is not None and yoy[i - 1] is not None else None
                for i in range(len(values))
            ]

            out.append(
                self._series(
                    f"{line_item}_yoy_growth", FeatureCategory.FUNDAMENTAL, ticker, dates, yoy,
                    f"Year-over-year growth of {line_item}", {"line_item": line_item},
                )
            )
            out.append(
                self._series(
                    f"{line_item}_qoq_growth", FeatureCategory.FUNDAMENTAL, ticker, dates, qoq,
                    f"Quarter-over-quarter growth of {line_item}", {"line_item": line_item},
                )
            )
            out.append(
                self._series(
                    f"{line_item}_rolling_trend", FeatureCategory.FUNDAMENTAL, ticker, dates, trend,
                    f"Trailing 4-period rolling mean of {line_item}", {"line_item": line_item},
                )
            )
            out.append(
                self._series(
                    f"{line_item}_yoy_acceleration", FeatureCategory.FUNDAMENTAL, ticker, dates, accel,
                    f"Change in {line_item}'s YoY growth vs. the prior period", {"line_item": line_item},
                )
            )
        return out

    # ---- macro transforms ----

    def build_macro_features(self) -> list[FeatureSeries]:
        out: list[FeatureSeries] = []
        for series_id, observations in self.panel.macro_series.items():
            source = self.panel.macro_series_sources.get(series_id)
            ordered = sorted(observations, key=lambda o: o.observation_date)
            dates = [known_as_of(o.observation_date, source=source) for o in ordered]
            values = [o.value for o in ordered]

            out.append(
                self._series(
                    f"{series_id}_level", FeatureCategory.MACRO, _MARKET_SCOPE, dates, values,
                    f"Level of macro series {series_id}", {"series_id": series_id},
                )
            )
            change = [
                values[i] - values[i - 1] if i >= 1 else None for i in range(len(values))
            ]
            out.append(
                self._series(
                    f"{series_id}_change", FeatureCategory.MACRO, _MARKET_SCOPE, dates, change,
                    f"Period-over-period change in {series_id}", {"series_id": series_id},
                )
            )
            accel = [
                change[i] - change[i - 1] if i >= 1 and change[i] is not None and change[i - 1] is not None else None
                for i in range(len(values))
            ]
            out.append(
                self._series(
                    f"{series_id}_acceleration", FeatureCategory.MACRO, _MARKET_SCOPE, dates, accel,
                    f"Change in {series_id}'s period-over-period change", {"series_id": series_id},
                )
            )
            pctile = [
                _percentile_rank(values[i], values[:i]) if i >= 1 else None for i in range(len(values))
            ]
            out.append(
                self._series(
                    f"{series_id}_rolling_percentile", FeatureCategory.MACRO, _MARKET_SCOPE, dates, pctile,
                    f"Percentile rank of {series_id}'s current level within its full prior history",
                    {"series_id": series_id},
                )
            )
        return out

    def build_all(self) -> list[FeatureSeries]:
        out: list[FeatureSeries] = []
        for ticker in self.panel.tickers:
            out.extend(self.build_price_features(ticker))
            out.extend(self.build_volume_features(ticker))
            out.extend(self.build_fundamental_features(ticker))
        out.extend(self.build_cross_sectional_features())
        out.extend(self.build_macro_features())
        return out

    @staticmethod
    def _series(
        feature_key: str,
        category: FeatureCategory,
        ticker: str,
        dates: list[date],
        values: list[float | None],
        description: str,
        parameters: dict[str, float | int | str],
    ) -> FeatureSeries:
        feature_id = f"{feature_key}:{ticker}" if ticker else f"{feature_key}:MARKET"
        return FeatureSeries(
            id=feature_id,
            spec=FeatureSpec(
                id=feature_key,
                category=category,
                name=feature_key,
                description=description,
                parameters=parameters,
            ),
            ticker=ticker,
            dates=list(dates),
            values=list(values),
        )


def _rolling_with_none(values: list[float | None], window: int, fn) -> list[float | None]:
    out: list[float | None] = []
    for i in range(len(values)):
        if i + 1 < window:
            out.append(None)
            continue
        chunk = values[i + 1 - window : i + 1]
        if any(v is None for v in chunk):
            out.append(None)
            continue
        out.append(fn(chunk))
    return out


def _rolling_trailing_exclusive(values: list[float], window: int, fn) -> list[float | None]:
    """Trailing `window` values strictly *before* index i (excludes today) —
    matches `market_memory.breadth`'s trailing-volume convention: today's
    own value must never be part of its own baseline."""
    out: list[float | None] = []
    for i in range(len(values)):
        chunk = values[max(0, i - window) : i]
        out.append(fn(chunk) if len(chunk) >= 2 else None)
    return out


def _rolling_pair_corr(a: list[float | None], b: list[float], window: int) -> list[float | None]:
    out: list[float | None] = []
    for i in range(len(a)):
        if i + 1 < window:
            out.append(None)
            continue
        a_chunk = a[i + 1 - window : i + 1]
        b_chunk = b[i + 1 - window : i + 1]
        if any(v is None for v in a_chunk):
            out.append(None)
            continue
        out.append(pearson_correlation(a_chunk, b_chunk))
    return out


__all__ = [
    "ASSUMED_FILING_LAG_DAYS",
    "CROSS_SECTIONAL_WINDOWS",
    "PRICE_WINDOWS",
    "VOLATILITY_REGIME_LOOKBACK_DAYS",
    "VOLUME_WINDOWS",
    "FeatureCategory",
    "FeatureFactory",
    "FeatureSeries",
    "FeatureSpec",
]
