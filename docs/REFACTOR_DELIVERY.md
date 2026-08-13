# EGX-Genom Institutional Refactor Delivery

## Decision architecture

The dashboard now separates three states that must not be conflated. An **executable decision** is still produced only by the existing readiness and decision-quality gates. A **quantitative research candidate** is produced when the latest price is below a populated weighted fair value built from multiple valuation models, even if macro, FX, news, freshness, liquidity, or governance evidence blocks execution. A stock with neither an executable decision nor a populated fair value remains an explicit abstention/data-gap item.

This separation prevents the common institutional error of showing an attractive valuation gap as an automatic buy signal. The new `research_candidates.json` artifact is ranked by expected return to target and includes a default one-year target horizon, evidence completeness, valuation models, current and target prices, and every blocker and next action that prevented execution.

## Data and free-source policy

The project remains limited to the EGX30/EGX70 universe resolved by the collected universe provider. The price path continues to use public sources, including the official EGX market-watch collector already integrated in the repository. Macro and economic inputs remain sourced from free public channels already catalogued by the project, including World Bank, CAPMAS, UN Data, Egypt NSDP/MPED, and public market feeds. No paid API, subscription, or premium data package was introduced.

The system does not backfill missing fundamentals or macro values with estimates. Missing inputs remain visible as blockers. This is intentional for an investment-manager workflow: an unavailable number is safer than a fabricated number.

## Dashboard changes

The Investment Cases page now contains a dedicated **Quantitative research candidates** table above the executable recommendation table. It shows ticker, current price, target price, expected return, target horizon, evidence completeness, and a gated watchlist status. The per-ticker detail page shows the same candidate information together with the blockers, followed by the existing valuation section and execution-plan section.

The existing six-month-low browser notification remains active. The recommendation table still ranks executable recommendations by expected return and horizon, while the new candidate table ranks valuation-led watchlist opportunities independently. Provenance and research-only warnings remain visible for replay-generated bundles.

## Verification

The refactor was checked with the following gates:

| Area | Result |
| --- | --- |
| Research-candidate unit tests | Passed, including exclusion of expensive/missing-value stocks and blocker preservation |
| Decision-readiness and valuation tests | Passed |
| Dashboard export and artifact validation | Passed, including round-trip counts and universe membership checks |
| API route tests | Passed, including `/research-candidates` honest empty-list behavior |
| TypeScript compilation | Passed |
| Web provider tests | Passed |
| End-to-end mock pipeline | Passed; produced and validated `research_candidates.json` |
| Production pipeline regression tests | Passed after the final routing fix: 5/5 targeted tests |
| Full research suite | Passed: **1,229 tests**, 7 non-blocking pytest collection warnings |
| GitHub Actions CI | Passed on `main` at commit `61daafb`, including TypeScript/API/web, ruff, Truth Preservation, full pytest, contract freshness, and artifact provenance gates |
| Local visual review | Passed; EXPA and ARCC appeared in ranked candidate table and EXPA detail card |

## Current evidence boundary

The latest validated state contains executable-looking Investment Cases such as EXPA and ARCC, while the code-push publication currently exposes an honest empty `research_candidates.json` because no historical candidate artifact was available in the restored state. This avoids inventing a research candidate; the next scheduled live run is responsible for regenerating the candidate artifact from fresh multi-model valuation evidence. The dashboard displays the distinction and blockers rather than promoting valuation alone to an executable buy.

The final Pages deployment completed successfully for the code-push snapshot, and the public page plus required artifacts are reachable. `macro_snapshot.json`, `market_state.json`, `universe.json`, `recommendations.json`, and `knowledge.json` return HTTP 200; `research_candidates.json` returns HTTP 200 with an honest empty list. The code-push bundle includes `manifest.json` with `pipeline_mode="replay"`, so CIO Desk reports that the snapshot is not a fresh canonical live run rather than showing a misleading missing-manifest warning. Scheduled runs remain the authoritative path for fresh prices, macro data, candidate generation, and canonical live provenance. A separate final-public-check evidence file records the URLs, checks, and visual findings.

The free-source production pipeline must continue to refresh prices intraday while allowing macro and fundamental sources to refresh at their natural publication frequency. The dashboard can refresh every minute without pretending that annual GDP or quarterly financial statements changed every minute.
