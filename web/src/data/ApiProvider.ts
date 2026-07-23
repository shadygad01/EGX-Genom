// Reads the same eight resources from a hosted api/ instance instead of
// static files. Vite's dev server proxies "/api" to localhost:3001 (see
// vite.config.ts); a real production deployment would point this at
// wherever api/ is hosted. Every endpoint returns exactly the same shape
// StaticJsonProvider's matching artifact file does (see api/src/routes/dashboard.ts
// and docs/ARCHITECTURE.md) -- that's what makes switching providers safe.

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
import type { DashboardDataProvider } from "./DataProvider";

async function fetchJson<T>(path: string): Promise<T> {
  const response = await fetch(`/api${path}`);
  if (!response.ok) {
    throw new Error(`Failed to fetch ${path}: ${response.status}`);
  }
  return response.json();
}

export class ApiProvider implements DashboardDataProvider {
  getKnowledge(): Promise<KnowledgeObject[]> {
    return fetchJson<KnowledgeObject[]>("/knowledge");
  }

  getEvents(): Promise<Event[]> {
    return fetchJson<Event[]>("/events");
  }

  getPatterns(): Promise<Pattern[]> {
    return fetchJson<Pattern[]>("/patterns");
  }

  getRecommendations(): Promise<Recommendation[]> {
    return fetchJson<Recommendation[]>("/recommendations");
  }

  getMarketState(): Promise<MarketState | null> {
    return fetchJson<MarketState | null>("/market-state");
  }

  getRuntimeMetrics(): Promise<RunRecord[]> {
    return fetchJson<RunRecord[]>("/runtime-metrics");
  }

  getSystemStatus(): Promise<DashboardSystemStatus | null> {
    return fetchJson<DashboardSystemStatus | null>("/system-status");
  }

  getSourceRegistry(): Promise<SourceSpec[]> {
    return fetchJson<SourceSpec[]>("/source-registry");
  }

  getInvestmentCases(): Promise<InvestmentCases | null> {
    return fetchJson<InvestmentCases | null>("/investment-cases");
  }

  getCollectorStatus(): Promise<CollectorStatusRow[]> {
    return fetchJson<CollectorStatusRow[]>("/collector-status");
  }

  getRuntimeStatus(): Promise<RunRecord | null> {
    return fetchJson<RunRecord | null>("/runtime-status");
  }

  getDashboardMetrics(): Promise<DashboardMetrics | null> {
    return fetchJson<DashboardMetrics | null>("/dashboard-metrics");
  }

  getMissionStatus(): Promise<MissionStatus | null> {
    return fetchJson<MissionStatus | null>("/mission-status");
  }

  getExecutionReport(): Promise<ExecutionReport | null> {
    return fetchJson<ExecutionReport | null>("/execution-report");
  }

  getGenes(): Promise<Gene[]> {
    return fetchJson<Gene[]>("/genes");
  }

  getPapers(): Promise<ResearchPaper[]> {
    return fetchJson<ResearchPaper[]>("/papers");
  }

  getHypotheses(): Promise<Hypothesis[]> {
    return fetchJson<Hypothesis[]>("/hypotheses");
  }

  getKnowledgeGraph(): Promise<KnowledgeGraphData> {
    return fetchJson<KnowledgeGraphData>("/knowledge-graph");
  }

  getFinancialStatements(): Promise<FinancialStatementLineItem[]> {
    return fetchJson<FinancialStatementLineItem[]>("/financial-statements");
  }

  getSourceMetrics(): Promise<SourceMetricsRow[]> {
    return fetchJson<SourceMetricsRow[]>("/source-metrics");
  }
}
