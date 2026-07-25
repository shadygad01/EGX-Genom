# Free-source expansion and decision routing (2026-07-25)

## What changed

This sprint reopens the previously frozen acquisition catalog only for a
source or series that has a legal, documented, machine-readable route and a
declared consumer in the investment-decision chain.

- **GDELT DOC 2.0**: free, no-key JSON news metadata. AGX queries Egypt/EGX,
  stores only headline, canonical link, date and matched tickers, and routes
  resulting events into the recommendation risk/confidence overlay.
- **FRED expansion**: Brent, WTI, broad USD, VIX, gold, US 2Y/10Y yields and
  high-yield credit spread. These daily risk factors route through the Macro
  Agent and the normal validation/knowledge pipeline.
- **World Bank expansion**: Egypt inflation, real GDP growth, current account,
  reserves, official FX, lending rate, unemployment, trade, FDI and external
  debt. Annual series remain useful for investment-horizon context but no
  longer get falsely paired by row position with daily returns.

Official references:

- GDELT DOC API: https://blog.gdeltproject.org/gdelt-doc-2-0-api-debuts/
- FRED CSV endpoint and series pages: https://fred.stlouisfed.org/
- World Bank Indicators API: https://api.worldbank.org/v2

## Decision-engine guarantee

`production/decision_lineage.py` is a fail-closed registry. Every source in
`IMPLEMENTED` state must declare:

1. the canonical records it produces;
2. the research/event consumer that uses those records; and
3. a route ending at `meta_decision_engine`.

Every production run exports `decision_source_routes.json`. Promoting a new
source without adding its route raises an error and is covered by a regression
test. Recommendation provenance now carries active event references and direct
source evidence instead of stopping at the horizon prediction.

## Important limitation

Free macro/news breadth does not replace licensed EGX OHLCV, official
constituents, audited filings or corporate-action data. If no trustworthy price
history and validated knowledge exist, AGX must still abstain rather than emit a
buy/sell decision. Sources requiring a user key or blocked by terms/WAF remain
`NEEDS_KEY`, `TOS_REVIEW` or `PLANNED`; catalog presence is not treated as live
decision input.
