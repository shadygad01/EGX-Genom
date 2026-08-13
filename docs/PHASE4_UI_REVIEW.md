# Phase 4 UI review

The refactored local dashboard was opened at `/cases` using `/tmp/valuation-dashboard` artifacts and the modified provider/API/frontend code.

The Investment Cases page now renders a dedicated **Quantitative research candidates** table before the recommendation table. The current replay artifacts produced two candidates, ranked by expected return: EXPA at 20.71 versus target 21.55 (+4.06%, 252 days, 66.7% evidence completeness), and ARCC at 75.00 versus target 76.14 (+1.52%, 252 days, 66.7% evidence completeness). Both are visibly marked `WATCHLIST — GATED`, not buy recommendations.

The EXPA detail page now renders a **Quantitative watchlist candidate** card with expected return, current/target price, target horizon, evidence completeness, and execution blockers. The blockers shown are insufficient macro coverage and insufficient exchange-rate data. The valuation section remains visible below it with price versus fair value (-3.90%), weighted fair value, P/B, market P/E, market cap, and beta.

The UI also continues to display the existing production/replay provenance banner and the research-only disclaimer. This is correct: the current local artifact bundle is replay-generated and must not be presented as an executable investment recommendation.
