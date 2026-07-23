// The one seam between the dashboard's components and where its data comes
// from. Every method here returns exactly the shapes web/src/types.ts
// defines (which mirror the pydantic models research/ produces) -- a
// component that talks to a DashboardDataProvider never knows, and never
// needs to know, whether the values came from a static JSON file (GitHub
// Pages) or a live HTTP endpoint (a hosted api/). See
// docs/ARCHITECTURE.md's "Dashboard data providers" section, and
// StaticJsonProvider/ApiProvider for the two implementations.

import type {
  CollectorStatusRow,
  DashboardMetrics,
  DashboardSystemStatus,
  Event,
  ExecutionReport,
  FinancialStatementLineItem,
  Gene,
  Hypothesis,
  InvestmentCases,
  KnowledgeGraphData,
  KnowledgeObject,
  MarketState,
  MissionStatus,
  Pattern,
  Recommendation,
  ResearchPaper,
  RunRecord,
  SourceMetricsRow,
  SourceSpec,
} from "../types";

// Every method here mirrors exactly one dashboard artifact file (see
// docs/ARCHITECTURE.md's "Dashboard data providers" section) -- no
// component ever computes a value that isn't already one of these fields.
// The first eight are always present (both StaticJsonProvider's fixed
// contract and ProductionPipeline produce them); the rest are only
// produced by the full production pipeline (`agx run`) and resolve to an
// honest empty/null value when absent, never a fabricated one.
export interface DashboardDataProvider {
  getKnowledge(): Promise<KnowledgeObject[]>;
  getEvents(): Promise<Event[]>;
  getPatterns(): Promise<Pattern[]>;
  getRecommendations(): Promise<Recommendation[]>;
  getMarketState(): Promise<MarketState | null>;
  getRuntimeMetrics(): Promise<RunRecord[]>;
  getSystemStatus(): Promise<DashboardSystemStatus | null>;
  getSourceRegistry(): Promise<SourceSpec[]>;

  getInvestmentCases(): Promise<InvestmentCases | null>;
  getCollectorStatus(): Promise<CollectorStatusRow[]>;
  getRuntimeStatus(): Promise<RunRecord | null>;
  getDashboardMetrics(): Promise<DashboardMetrics | null>;
  getMissionStatus(): Promise<MissionStatus | null>;
  getExecutionReport(): Promise<ExecutionReport | null>;
  getGenes(): Promise<Gene[]>;
  getPapers(): Promise<ResearchPaper[]>;
  getHypotheses(): Promise<Hypothesis[]>;
  getKnowledgeGraph(): Promise<KnowledgeGraphData>;
  getFinancialStatements(): Promise<FinancialStatementLineItem[]>;
  getSourceMetrics(): Promise<SourceMetricsRow[]>;
}
