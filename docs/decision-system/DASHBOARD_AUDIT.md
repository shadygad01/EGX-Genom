# Dashboard Audit

The dashboard should remain a consumer of canonical artifacts. It should not calculate an alternative truth in the browser. The primary screen should lead with market posture, actionable decisions, decision changes, vetoes/risks, catalysts, portfolio impact, and review conditions. Research details belong one level deeper.

The current frontend already consumes decision, case, monitoring, market, and portfolio artifacts. The key acceptance rule is therefore not a cosmetic rewrite: every page must resolve its values from the same manifest and canonical artifact set, and any stale/replay state must be visible and fail closed. The normal research-only disclaimer is distinct from a replay warning and must remain.

## Acceptance checks

1. Live manifest is present and matches the workflow commit.
2. No replay warning is shown when `pipeline_mode=live`.
3. Decision pages expose why, why-not, risks, conflicts, invalidation, evidence freshness, and history when available.
4. Browser code does not independently recompute action, rank, or allocation truth.
5. Data gaps and abstentions remain visible rather than being hidden by empty-state design.
