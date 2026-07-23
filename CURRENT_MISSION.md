# Current Mission

**Build the complete AGX Production User Experience — a world-class
Research Intelligence Platform, not a stock website, dashboard, or CRUD
app.**

The project owner has declared the backend architecture, the research
engine, and the production pipeline complete: no more backend redesign
work. Full engineering ownership has been handed to the frontend — the
visual/UX bar is a combination of Bloomberg Terminal, Koyfin, TradingView,
Notion, and institutional sell-side research. The interface must explain
not only *what* AGX recommends, but *why*, *how* it reached that
conclusion, and *what evidence* supports or contradicts every thesis.

**Hard constraint, unchanged from the backend mission's own discipline:**
the frontend consumes artifacts only. No calculation happens in `web/` —
every number a page shows must already exist in a dashboard artifact
`research/src/agx_research/dashboard/export.py` or
`production/artifacts.py` produces. A UI need with no backing artifact
gets either (a) a new thin backend export (a `model_dump(mode="json")`
over an already-tested model, same pattern as every prior artifact) or
(b) an honest "not yet available" gap in the UI — never a fabricated
number.

The application is nine sections: AI Briefing (landing page), Opportunity
Center, Company Research Workspace, Market Intelligence, Research Center,
Knowledge Graph, Mission Control, Source Intelligence, System
Administration. See `docs/ARCHITECTURE.md`'s "Frontend: Production User
Experience" section (to be added as this mission progresses) for the
per-section content spec.

## What this phase engineered so far

**Frontend Audit.** Read the entire repository, every architecture and
Mission Control document, the existing `web/` implementation (a single
hardcoded knowledge table, `App.tsx`), the production pipeline, and every
JSON artifact AGX produces, before writing any code — per the mission's
explicit "audit before rebuild" instruction.

**Backend: six new dashboard artifacts.** Before the frontend could cover
the 9-section spec honestly, the domain models it needed (genes, papers,
hypotheses, the knowledge graph, financial statement line items, source
reputation) had to actually be exported. Added `genes.json`, `papers.json`,
`hypotheses.json`, `knowledge_graph.json`, `financial_statements.json`,
`source_metrics.json` — all thin `model_dump(mode="json")` exports, no new
calculations. Found and fixed a real pre-existing bug while wiring the
knowledge graph: `ProductionPipeline` computed graph edges every run but
never persisted them (no path was ever passed to the `KnowledgeGraph`
constructor) — fixed by pointing it at `<data-dir>/graph_nodes.json`/
`graph_edges.json`, the same composition pattern already used for the
hypothesis/paper repositories and the genome. Also closed a pre-existing
API/static-provider parity gap: 6 "bonus" artifacts from the earlier
Production Pipeline mission (`investment_cases`, `collector_status`,
`runtime_status`, `dashboard_metrics`, `mission_status`,
`execution_report`) were only ever wired into `StaticJsonProvider`, never
into `api/`'s `ArtifactsReader`/routes.

**Design system + routed application shell.** Institutional dark-theme-
first design tokens (`web/src/styles/tokens.css`), a shared primitive
library (`Card`, `Badge`, `StatTile`, `Meter`, `DataTable`, `Section`,
`EmptyState`/`LoadingState`/`ErrorState`), a persistent `Sidebar`/`TopBar`
`AppShell`, and `react-router-dom` routes for all 9 sections — replacing
the single hardcoded table `App.tsx` used to render. A `useArtifact` hook
is the one seam every page uses to pull data through
`DashboardDataProvider` with consistent loading/error handling; no page
calls the provider directly.

**AI Briefing** (the landing page, the mission's "signature experience")
is fully built: System Health, Changes Since Yesterday (derived from
`ExecutionReport`'s before/after counts — a real artifact field, not a
frontend computation), Market Summary, Top Opportunities, Biggest Risks,
Most Important News, Upcoming Catalysts, Knowledge Changes, Scientific
Discoveries, and Portfolio. Verified in both light and dark theme via a
headless-browser smoke test against real artifacts produced by
`agx run` in mock mode.

The remaining 8 sections render as honest "under construction"
placeholders (`ComingSoon`) — each names what it will show and why it
isn't built yet, never a fabricated screen.

## What's next

Opportunity Center (task next in sequence) — see `NEXT_MISSIONS.md` for
the full remaining order.

## What did NOT change

Per the mission's explicit instruction, no backend redesign happened
beyond the sanctioned artifact-export extension point: `hypotheses/`,
`validation/`, `agents/`, `orchestration/`, `production/pipeline.py`'s
internal stage logic, `KnowledgeStore.promote()`'s signature, and every
other backend invariant `CLAUDE.md` documents are unchanged. The one
backend fix (wiring a persist path into `KnowledgeGraph`'s existing
constructor parameter) is additive composition, not a redesign — it
follows the exact pattern already used for every other repository in the
same function.
