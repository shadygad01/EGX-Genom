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

## Status: all 9 sections built

The application is nine sections, all now implemented and routed:
AI Briefing (landing page), Opportunity Center, Company Research
Workspace, Market Intelligence, Research Center, Knowledge Graph,
Mission Control, Source Intelligence, System Administration.

## What this phase engineered

**Frontend Audit.** Read the entire repository, every architecture and
Mission Control document, the existing `web/` implementation (a single
hardcoded knowledge table, `App.tsx`), the production pipeline, and every
JSON artifact AGX produces, before writing any code.

**Backend: six new dashboard artifacts.** `genes.json`, `papers.json`,
`hypotheses.json`, `knowledge_graph.json`, `financial_statements.json`,
`source_metrics.json` — thin `model_dump(mode="json")` exports, no new
calculations. Fixed a real pre-existing bug: `ProductionPipeline` computed
knowledge-graph edges every run but never persisted them (no path was
passed to the `KnowledgeGraph` constructor) — fixed by pointing it at
`<data-dir>/graph_nodes.json`/`graph_edges.json`, matching how the
hypothesis/paper repositories and the genome are already wired. Closed a
pre-existing `api/`/`StaticJsonProvider` parity gap for 6 earlier "bonus"
artifacts (`investment_cases`, `collector_status`, `runtime_status`,
`dashboard_metrics`, `mission_status`, `execution_report`) that were only
ever wired into the static provider.

**Design system + routed application shell.** Institutional dark-theme-
first design tokens (`web/src/styles/tokens.css`), a shared primitive
library (`Card`, `Badge`, `StatTile`, `Meter`, `DataTable`, `Section`,
`EmptyState`/`LoadingState`/`ErrorState`), a persistent `Sidebar`/`TopBar`
`AppShell`, and `react-router-dom` routes for all 9 sections. A
`useArtifact` hook is the one seam every page uses to pull data through
`DashboardDataProvider` with consistent loading/error handling.

**AI Briefing** — the landing page and "signature experience": System
Health, Changes Since Yesterday (from `ExecutionReport`'s before/after
counts), Market Summary, Top Opportunities, Biggest Risks, Most Important
News, Upcoming Catalysts, Knowledge Changes, Scientific Discoveries, and
Portfolio.

**Opportunity Center** — every recommendation ranked by confidence,
master/detail: ranked table + full `Explanation` (research/risk summary,
supporting/contradicting evidence, historical similar cases, upcoming
catalysts) for the selected row.

**Company Research Workspace** (`/company/:ticker`) — per-ticker deep
page: investment thesis, upcoming catalysts, knowledge timeline, research
papers and gene lineage (cross-referenced via knowledge object ids),
financial statements, corporate actions, news timeline. Market Regime &
Macro Exposure is an honest gap (no artifact exists upstream yet).

**Market Intelligence** — universe/sector composition, macro dashboard,
market-wide upcoming/recent corporate actions. Market Breadth & Liquidity
and Market Regime & Historical Comparison are honest gaps — the frontend
must not compute returns from raw price bars itself
(`data.adjustments`'s own rule).

**Research Center** — the 8-gate hypothesis pipeline (master/detail:
ranked list + full stage history), covering "Experiments," "Validation
Queue," "Active Research," and "Discovery History" as views over the same
underlying data; Knowledge Objects; Scientific Papers. Review Board is an
honest gap (no repository persists past `BoardDecision`s yet).

**Knowledge Graph** — interactive, searchable, pan/zoomable rendering of
`getKnowledgeGraph()`'s nodes and edges, using a small dependency-free
force-directed layout (`lib/forceLayout.ts`) rather than adding a
graph-rendering library for one page.

**Mission Control** — mission status, pipeline health (stage-by-stage),
knowledge/genome status, collectors, source health rollup, current
blockers, execution history. Discovery Engine detail is an honest gap (no
dashboard export yet for `acquisition_intelligence`).

**Source Intelligence** — every registered source, master/detail: health,
lifecycle, activation, reputation dimensions (availability, coverage,
freshness, latency, accuracy, schema stability) as meters, joined across
the source registry, source metrics, and the most recent collector run.

**System Administration** — runtime/versions, configuration, replay
capability, artifact inventory, per-stage performance (slowest first),
execution history with error/session detail. Logs is an honest gap (no
artifact carries raw log lines yet).

Every page above was verified in a headless browser (both light and dark
theme where relevant) against either real artifacts from a mock-mode
`agx run` or a synthetic fixture where the mock pipeline currently
produces no data (e.g. zero promoted knowledge/recommendations) — never
against untested markup.

## What's next

The quality pass: responsive layout, accessibility, performance,
cross-page consistency re-verified now that all 9 sections exist (see
`NEXT_MISSIONS.md`). No further page is queued unless the quality pass or
the project owner surfaces a genuine gap.

## What did NOT change

Per the mission's explicit instruction, no backend redesign happened
beyond the sanctioned artifact-export extension point: `hypotheses/`,
`validation/`, `agents/`, `orchestration/`, `production/pipeline.py`'s
internal stage logic, `KnowledgeStore.promote()`'s signature, and every
other backend invariant `CLAUDE.md` documents are unchanged. The one
backend fix (wiring a persist path into `KnowledgeGraph`'s existing
constructor parameter) is additive composition, not a redesign.
