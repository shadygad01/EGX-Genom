# Next Missions

In build order for the Production User Experience mission (see
`CURRENT_MISSION.md`). Each remaining section is built against
already-exported dashboard artifacts wherever possible; any that need a
new thin backend export are called out below.

## 1. Opportunity Center

Every opportunity ranked by confidence, from `getRecommendations()`
(already exported): ticker, company, confidence, expected return/drawdown,
investment horizon, supporting/contradicting evidence
(`Explanation.supporting_evidence`/`invalidation_conditions`), historical
similar cases (`Explanation.similar_historical_cases`), upcoming
catalysts, research summary, risk summary. Clicking a row opens the
Company Research Workspace (`/company/:ticker`, already routed).

## 2. Company Research Workspace

Per-ticker deep page: current investment thesis (`Recommendation` +
`Explanation`), knowledge timeline (`getKnowledge()` filtered by
`affected_assets`), news timeline (`MarketState.dataset_snapshot.news`
filtered by ticker), financial statements (`getFinancialStatements()`,
already exported), corporate actions
(`MarketState.dataset_snapshot.corporate_events`), research papers
(`getPapers()`, already exported, filtered by `knowledge_id`), genes
(`getGenes()`, already exported), supporting/contradicting evidence,
historical similar cases, sector/macro context. Route already wired
(`/company/:ticker`, currently a placeholder).

## 3. Market Intelligence

EGX30/EGX70 breadth, sector rotation, macro dashboard
(`MarketState.dataset_snapshot.macro_series`), upcoming earnings/corporate
actions/disclosures, market regime, historical comparison. **Known gap:**
no "market regime" artifact currently exists — needs an honest empty state
or a new thin export once a regime classification exists upstream; do not
fabricate one in the frontend.

## 4. Research Center

Hypotheses (`getHypotheses()`, already exported), experiments, knowledge
objects (`getKnowledge()`), scientific papers (`getPapers()`), review
board, validation queue, discovery history, retired knowledge, active
research. **Known gap:** no repository persists past `BoardDecision`s from
`review.ScientificReviewBoard` — the review-board detail view will need an
honest gap acknowledgment, not fabricated history, unless/until that
repository is built.

## 5. Knowledge Graph view

Interactive, searchable, zoomable graph from `getKnowledgeGraph()`
(already exported — nodes + edges, mechanically derived from
`Provenance` via `graph.edges_from_provenance()`). Needs a rendering
library decision (e.g. a lightweight force-directed layout) — evaluate
before adding a new dependency, per the "no over-engineering" ethos.

## 6. Mission Control page

Current mission, project progress, pipeline health
(`getMissionStatus()`/`getExecutionReport()`, already exported),
collectors (`getCollectorStatus()`), discovery engine, knowledge/genome
status, runtime status (`getRuntimeStatus()`), source health, execution
history, current blockers. Largely a UI composition over artifacts that
already exist.

## 7. Source Intelligence

Every connected source's health, availability, coverage, freshness,
latency, qualification, discovery date, last success/failure, collected
documents, validation score — from `getSourceRegistry()` and
`getSourceMetrics()` (both already exported).

## 8. System Administration

Runtime, configuration, execution history, replay, logs, artifacts,
versions, performance. Largely `getExecutionReport()`/
`getDashboardMetrics()`/`getRuntimeMetrics()` composition; replay/logs may
need a new thin export if no artifact currently carries that detail.

## Ongoing: Mission Control docs

Update `MISSION_CONTROL.md`, `CURRENT_MISSION.md`, `NEXT_MISSIONS.md`,
`PROJECT_PROGRESS.md`, `docs/ROADMAP.md`, `CHANGELOG.md` after every
milestone (each numbered item above), per the mission's explicit
discipline requirement.

## After all 9 sections: quality pass

Responsive layout, accessibility, performance, loading/error/empty states,
theme consistency, navigation consistency, cross-page consistency — the
mission's own quality checklist, re-verified once every section exists
rather than assumed page by page.

## Beyond this

The backend/data-acquisition mission's own next-steps (EGX official
connection, richer PDF-based extraction, calibration passes once real data
exists) remain valid but are explicitly paused per the project owner's
instruction not to do backend work during this phase — see
`docs/ROADMAP.md`'s "Post-1.0" section for where they resume once the
frontend mission completes.
