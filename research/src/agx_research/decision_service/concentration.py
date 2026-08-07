"""Sector and correlation concentration overrides for `DecisionService.decide_portfolio()`.

Two hard, portfolio-level caps, computed *before* any capital is
attributed by `capital_allocation.CapitalAllocationEngine` (which never
rescoring/reweighs anything `decide_portfolio()` already computed --
these caps must therefore live here, not there). Both reuse an existing
declared-uncalibrated posture rather than inventing a new one:

- **Sector cap** reuses `portfolio.concentration_limits
  .MAX_SECTOR_CONCENTRATION` (0.40) verbatim -- the same permanent number
  `investment_proof.portfolio_validation.PortfolioValidationEngine` already
  validates *after the fact*; this
  module is what makes that number actually block an over-concentrated
  allocation instead of merely flagging it once it has already happened,
  the same "declared -> enforced" step `liquidity_floor.py` and
  `country_risk.py` already took for their own thresholds.
- **Correlation-cluster cap** is new: a candidate whose real, adjusted-
  return Pearson correlation (`features.correlation
  .compute_pairwise_return_correlation`, never a fabricated covariance
  matrix -- a full mean-variance optimizer is deliberately out of scope,
  see `portfolio/constructor.py`'s own docstring on why) to one or more
  already-allocated, higher-ranked tickers exceeds
  `CORRELATION_CONCENTRATION_THRESHOLD` has its combined exposure to that
  correlated cluster capped at `MAX_CORRELATED_CLUSTER_WEIGHT`, the same
  numeric ceiling as the sector cap by declared design choice, not reuse
  of the same underlying fact.

Both caps are walked in a single pass over tickers ordered by their own
pre-cap target weight, descending (ties broken by ticker) -- the same
best-ranked-first order `CapitalAllocationEngine._rank()`/
`_match_capital_flows()` already use, so "which ticker gets the room in a
crowded sector/cluster" is always the strongest idea, never allocation
order happening to favor a weaker one. Any weight trimmed by a cap is
never redistributed to another ticker -- it returns to cash, exactly like
every other unmet-demand case in this platform (Article VII: "no capital
movement is fabricated"); capital waits for a better, less-concentrated
opportunity rather than being forced into a name that's already
overexposed via a correlated peer or a crowded sector.
"""

from __future__ import annotations

from agx_research.data.snapshot import DatasetSnapshot
from agx_research.features.correlation import compute_pairwise_return_correlation
from agx_research.portfolio.concentration_limits import MAX_SECTOR_CONCENTRATION

_EPS = 1e-9

#: Declared, uncalibrated -- same posture as `MAX_SECTOR_CONCENTRATION`
#: and every other declared-not-measured constant in this codebase
#: (docs/TECHNICAL_DEBT.md). No real multi-year EGX portfolio history
#: exists yet to test whether 0.70 is the correlation level that actually
#: separates a real concentrated bet from ordinary co-movement.
CORRELATION_CONCENTRATION_THRESHOLD = 0.70

#: Declared, uncalibrated. Set equal to `MAX_SECTOR_CONCENTRATION` by
#: deliberate design choice (one "how much of the portfolio in one
#: crowded bucket" ceiling, applied consistently to two different kinds
#: of buckets), not because a sector and a correlated cluster are the
#: same concept.
MAX_CORRELATED_CLUSTER_WEIGHT = MAX_SECTOR_CONCENTRATION


def compute_concentration_caps(
    base_targets: dict[str, float],
    *,
    snapshot: DatasetSnapshot | None = None,
    sectors: dict[str, str] | None = None,
    max_sector_weight: float = MAX_SECTOR_CONCENTRATION,
    correlation_threshold: float = CORRELATION_CONCENTRATION_THRESHOLD,
    max_correlated_cluster_weight: float = MAX_CORRELATED_CLUSTER_WEIGHT,
) -> dict[str, tuple[float, list[str]]]:
    """Cap each ticker's pre-override target weight against sector and
    correlation-cluster concentration, walking best-scored-first.

    Returns `{ticker: (capped_weight, reasons)}` for every ticker in
    `base_targets`. A ticker whose `snapshot`/`sectors` data is
    unavailable is honestly left uncapped by the corresponding check
    (an absent input never fabricates a pass *or* a fail) -- exactly the
    same "no data -> no fabricated verdict" posture `liquidity_floor
    .compute_illiquid_tickers()` already documents for missing price
    history, applied here to missing sector/return data instead.
    """
    ordered = sorted(base_targets, key=lambda t: (-base_targets[t], t))
    sector_used: dict[str, float] = {}
    allocated: list[tuple[str, float]] = []
    result: dict[str, tuple[float, list[str]]] = {}

    for ticker in ordered:
        weight = base_targets[ticker]
        reasons: list[str] = []

        if weight <= _EPS:
            result[ticker] = (weight, reasons)
            continue

        if sectors is not None:
            sector = sectors.get(ticker)
            if sector is not None:
                used = sector_used.get(sector, 0.0)
                room = max(0.0, max_sector_weight - used)
                if weight > room + _EPS:
                    reasons.append(
                        f"Sector concentration cap: {sector} sector already accounts for "
                        f"{used:.2%} of the portfolio (limit {max_sector_weight:.0%}); "
                        f"{ticker} capped to {room:.2%} instead of {weight:.2%} (hard "
                        "override, not weighted evidence)."
                    )
                    weight = room
                sector_used[sector] = used + weight

        if snapshot is not None and weight > _EPS:
            cluster_weight = 0.0
            correlated_with: list[str] = []
            for other_ticker, other_weight in allocated:
                if other_weight <= _EPS:
                    continue
                corr = compute_pairwise_return_correlation(snapshot, ticker, other_ticker)
                if corr is not None and corr >= correlation_threshold:
                    cluster_weight += other_weight
                    correlated_with.append(f"{other_ticker} (r={corr:.2f})")
            if cluster_weight > _EPS:
                room = max(0.0, max_correlated_cluster_weight - cluster_weight)
                if weight > room + _EPS:
                    reasons.append(
                        f"Correlation concentration cap: {ticker}'s daily returns correlate "
                        f"at or above {correlation_threshold:.2f} with already-allocated "
                        f"{', '.join(correlated_with)} (combined {cluster_weight:.2%} of the "
                        f"portfolio, limit {max_correlated_cluster_weight:.0%}); capped to "
                        f"{room:.2%} instead of {weight:.2%} (hard override, not weighted "
                        "evidence)."
                    )
                    weight = room

        allocated.append((ticker, weight))
        result[ticker] = (weight, reasons)

    return result


__all__ = [
    "CORRELATION_CONCENTRATION_THRESHOLD",
    "MAX_CORRELATED_CLUSTER_WEIGHT",
    "compute_concentration_caps",
]
