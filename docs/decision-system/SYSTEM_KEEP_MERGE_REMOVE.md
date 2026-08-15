# System Disposition Matrix

| System/source family | Disposition | Reason |
|---|---|---|
| PositionAwareDecision | KEEP / canonical | Existing production contract is portfolio-aware and provenance-backed |
| CapitalAllocationEngine | KEEP | Provides relative opportunity, capital flows, and cash waiting without a second score |
| Existing readiness/publication gates | KEEP / single gate system | Fail-closed behavior is already tested; do not create parallel gates |
| Financial collectors/provider | KEEP and validate | Financial coverage is now 101/101 and feeds valuation/readiness |
| Macro overlay and country risk | KEEP as secondary | Useful for exposure and veto context, not a standalone ticker signal |
| News/event platform | KEEP with value gate | Decision impact matters more than article volume |
| Cross-stock network | KEEP ISOLATED | Exploratory behavioral signatures; no unsupported mechanism claims |
| SMC/technical research | KEEP as execution sensor | Do not let execution structure become fundamental thesis |
| Research papers/methodology sources | KEEP OUTSIDE CORE | Supports method improvement, not per-ticker evidence |
| Economic releases label | MERGE into macro capability | Avoid duplicate strategy taxonomy and consumers |
| Google Scholar/ResearchGate planned sources | ARCHIVE/REMOVE from acquisition catalog | Unmapped, redundant with cleaner methodology sources, and no production consumer |
| Unmapped social/trend/hiring/patent sources | ARCHIVE until a validated consumer exists | No current capability route or decision impact |
| New external-sector PDF collectors | DEFER | Unvalidated predictive value and high maintenance cost |
| New dashboard pages that recompute truth | REJECT | Violates canonical artifact rule |
