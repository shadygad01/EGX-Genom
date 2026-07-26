// Reads the dashboard's JSON artifacts published alongside the static
// site (see agx_research.dashboard.export / the `export-dashboard` CLI
// subcommand, and .github/workflows/deploy-pages.yml's "generate dashboard
// artifacts" step). This is the provider GitHub Pages uses: no backend,
// no API, just the files the research pipeline already wrote to
// `web/public/data/` before the Vite build ran.

import type {
  AcquisitionDecision,
  CollectorStatusRow,
  DashboardMetrics,
  DashboardSystemStatus,
  DecisionReadiness,
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
  UniverseArtifact,
} from "../types";
import type { DashboardDataProvider } from "./DataProvider";

async function fetchList<T>(filename: string): Promise<T[]> {
  const response = await fetch(`${import.meta.env.BASE_URL}data/${filename}`);
  if (response.status === 404) return [];
  if (!response.ok) {
    throw new Error(`Failed to fetch ${filename}: ${response.status}`);
  }
  return response.json();
}

async function fetchObject<T>(filename: string): Promise<T | null> {
  const response = await fetch(`${import.meta.env.BASE_URL}data/${filename}`);
  if (response.status === 404) return null;
  if (!response.ok) {
    throw new Error(`Failed to fetch ${filename}: ${response.status}`);
  }
  return response.json();
}

export class StaticJsonProvider implements DashboardDataProvider {
  getKnowledge(): Promise<KnowledgeObject[]> {
    return fetchList<KnowledgeObject>("knowledge.json");
  }

  getEvents(): Promise<Event[]> {
    return fetchList<Event>("events.json");
  }

  getPatterns(): Promise<Pattern[]> {
    return fetchList<Pattern>("patterns.json");
  }

  getRecommendations(): Promise<Recommendation[]> {
    return fetchList<Recommendation>("recommendations.json");
  }

  getMarketState(): Promise<MarketState | null> {
    return fetchObject<MarketState>("market_state.json");
  }

  getUniverse(): Promise<UniverseArtifact | null> {
    return fetchObject<UniverseArtifact>("universe.json");
  }

  getRuntimeMetrics(): Promise<RunRecord[]> {
    return fetchList<RunRecord>("runtime_metrics.json");
  }

  getSystemStatus(): Promise<DashboardSystemStatus | null> {
    return fetchObject<DashboardSystemStatus>("system_status.json");
  }

  getSourceRegistry(): Promise<SourceSpec[]> {
    return fetchList<SourceSpec>("source_registry.json");
  }

  getInvestmentCases(): Promise<InvestmentCases | null> {
    return fetchObject<InvestmentCases>("investment_cases.json");
  }

  getCollectorStatus(): Promise<CollectorStatusRow[]> {
    return fetchList<CollectorStatusRow>("collector_status.json");
  }

  getRuntimeStatus(): Promise<RunRecord | null> {
    return fetchObject<RunRecord>("runtime_status.json");
  }

  getDashboardMetrics(): Promise<DashboardMetrics | null> {
    return fetchObject<DashboardMetrics>("dashboard_metrics.json");
  }

  getMissionStatus(): Promise<MissionStatus | null> {
    return fetchObject<MissionStatus>("mission_status.json");
  }

  getExecutionReport(): Promise<ExecutionReport | null> {
    return fetchObject<ExecutionReport>("execution_report.json");
  }

  getGenes(): Promise<Gene[]> {
    return fetchList<Gene>("genes.json");
  }

  getPapers(): Promise<ResearchPaper[]> {
    return fetchList<ResearchPaper>("papers.json");
  }

  getHypotheses(): Promise<Hypothesis[]> {
    return fetchList<Hypothesis>("hypotheses.json");
  }

  async getKnowledgeGraph(): Promise<KnowledgeGraphData> {
    const data = await fetchObject<KnowledgeGraphData>("knowledge_graph.json");
    return data ?? { nodes: [], edges: [] };
  }

  getFinancialStatements(): Promise<FinancialStatementLineItem[]> {
    return fetchList<FinancialStatementLineItem>("financial_statements.json");
  }

  getSourceMetrics(): Promise<SourceMetricsRow[]> {
    return fetchList<SourceMetricsRow>("source_metrics.json");
  }

  getAcquisitionDecisions(): Promise<AcquisitionDecision[]> {
    return fetchList<AcquisitionDecision>("acquisition_decisions.json");
  }

  getDecisionReadiness(): Promise<DecisionReadiness[]> {
    return fetchList<DecisionReadiness>("decision_readiness.json");
  }
}
