# EGX-Genom source audit — 2026-08-13

## Scope and standard

Every source is classified by four tests: whether its endpoint responds, whether its collector parses usable records, whether records are fresh and internally valid, and whether the records reach a decision consumer. A catalog row alone is not treated as operational evidence.

## Live evidence

The latest complete live run produced 38 dashboard artifacts and recorded 52 catalogued source states. The price composite produced 11,585 records, was fresh, corroborated, and reached the decision path. It is currently the effective price source for all 101 EGX30/EGX70 tickers. The official EGX prices page failed twice on read timeout and produced zero records; it must remain a declared fallback, not a falsely advertised live primary.

World Bank, UN Data, CAPMAS, Egypt NSDP, EGX disclosures, Enterprise Press, public Egyptian financial/news sources, and selected issuer IR collectors produced records that reached downstream consumers. `egxpilot_fundamentals` and `chief_egx_financials` are useful but degraded because coverage is incomplete; their missingness must remain visible in decision gates.

FRED is catalogued and has a real collector, but its current live CSV request timed out in the sandbox and was excluded from the live macro capability after three consecutive production timeouts. A fresh direct probe on 2026-08-13 also timed out after 25 seconds. It should not be re-enabled until a successful live fetch and parsed-record test are captured.

Stooq is correctly not used: its own robots policy disallows the CSV download mechanism. Yahoo Finance and StockAnalysis are not independent dashboard capabilities; they are legs inside the price composite and must be shown as provider legs, not double-counted as independent evidence. Mubasher is a post-close fallback leg and should not be treated as full independent corroboration.

GDELT failed with HTTP 429 in the last live run. The news path still has usable primary/secondary records from EGX disclosures, Enterprise Press, Alborsa, Masrawy Economy, Amwal Alghad, and selected IR sources. GDELT should remain a rate-limited optional discovery source, never a decision blocker or sole news source.

## Sources that should be removed from active decision routing

The following catalogued sources are currently planned, disabled, explicitly blocked, or not connected to a verified endpoint: generic named news placeholders with no verified feed, Moody's/S&P/Fitch rating placeholders, Trading Economics without a key, IMF/OECD placeholders without a wired public endpoint, and the disabled EGX official bulk endpoint. They may remain in a historical catalog only for audit traceability, but they must not consume daily capability attempts or appear as if they are live decision inputs.

## Priority for the refactor

The first implementation pass should strengthen the sources with demonstrated public access: World Bank, UN Data, CAPMAS, Egypt NSDP, EGX disclosures, the price composite, and the verified Egyptian public news/IR collectors. It should add explicit source-health and decision-contribution fields to the dashboard. It should not add guessed endpoints for CBE, FRA, exchange pages, or named news outlets. A source is activated only after a real fetch, parse, freshness, and consumer test.

The intended outcome is a truthful dashboard: current prices and six-month-low alerts can be populated from the working composite, valuation can use only validated financial periods, and the decision board must show `BUY / HOLD / WATCHLIST / ABSTAIN` together with source coverage and blockers rather than hiding missing data.

## Refactor actions completed

The active capability pools were rewritten to include only free sources with recent live evidence: the price composite; the verified EGX disclosure, public news, and issuer-IR paths; and World Bank, UN Data, CAPMAS, and Egypt NSDP for macroeconomic inputs. FRED and Stooq are now disabled tombstones in the source registry: their collectors remain unit-tested, but they are not eligible for production collection or daily decision routing. Unverified CBE, IMF, OECD, ratings, Trading Economics, government-placeholder, and generic news rows remain audit history only and are removed from active capability selection.

Source Intelligence now consumes `source_truth.json` and displays records produced, decision-path usage, corroboration, and a top-level health summary. This makes it possible to see whether a source merely exists in the catalog or actually contributed validated data to the investment decision.
