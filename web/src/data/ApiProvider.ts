// Reads the same eight resources from a hosted api/ instance instead of
// static files. Vite's dev server proxies "/api" to localhost:3001 (see
// vite.config.ts); a real production deployment would point this at
// wherever api/ is hosted. Every endpoint returns exactly the same shape
// StaticJsonProvider's matching artifact file does (see api/src/routes/dashboard.ts
// and docs/ARCHITECTURE.md) -- that's what makes switching providers safe.

import type {
  AcquisitionDecision,
  ArtifactPublicationManifest,
  CapitalAllocationPlan,
  CollectorStatusRow,
  DashboardMetrics,
  DashboardSystemStatus,
  DecisionReadiness,
  DecisionPerformanceSummary,
  DecisionRecord,
  DiscoveryMetrics,
  DiscoveryOutcome,
  EndpointCandidate,
  Event,
  ExecutionReport,
  FinancialCoverageReport,
  FinancialStatementLineItem,
  Gene,
  Hypothesis,
  InvestmentClaim,
  InvestmentCases,
  KnowledgeGraphData,
  KnowledgeObject,
  CommitteeSummaryReport,
  MarketBreadthReport,
  MarketRegimeReport,
  MarketState,
  MissionStatus,
  MonitoringWarningsReport,
  Pattern,
  PortfolioSummaryReport,
  PositionAwareDecision,
  SystemMaturityReport,
  Recommendation,
  ResearchPaper,
  RunRecord,
  ShadowFundHistory,
  ShadowFundPublicState,
  SourceMetricsRow,
  SourceSpec,
  SourceTruthRow,
  TickerDataGapReport,
  UniverseArtifact,
} from "../types";
import type { DashboardDataProvider, DecideRequest } from "./DataProvider";

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

  getUniverse(): Promise<UniverseArtifact | null> {
    return fetchJson<UniverseArtifact | null>("/universe");
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

  getClaims(): Promise<InvestmentClaim[]> {
    return fetchJson<InvestmentClaim[]>("/claims");
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

  getFinancialCoverage(): Promise<FinancialCoverageReport | null> {
    return fetchJson<FinancialCoverageReport | null>("/financial-coverage");
  }

  getSourceMetrics(): Promise<SourceMetricsRow[]> {
    return fetchJson<SourceMetricsRow[]>("/source-metrics");
  }

  getMarketBreadth(): Promise<MarketBreadthReport | null> {
    return fetchJson<MarketBreadthReport | null>("/market-breadth");
  }

  getMarketRegime(): Promise<MarketRegimeReport | null> {
    return fetchJson<MarketRegimeReport | null>("/market-regime");
  }

  getAcquisitionDecisions(): Promise<AcquisitionDecision[]> {
    return fetchJson<AcquisitionDecision[]>("/acquisition-decisions");
  }

  getDecisionReadiness(): Promise<DecisionReadiness[]> {
    return fetchJson<DecisionReadiness[]>("/decision-readiness");
  }

  getTickerDataGapReport(): Promise<TickerDataGapReport[]> {
    return fetchJson<TickerDataGapReport[]>("/ticker-data-gaps");
  }

  getSourceTruth(): Promise<SourceTruthRow[]> {
    return fetchJson<SourceTruthRow[]>("/source-truth");
  }

  getDecisionHistory(): Promise<DecisionRecord[]> {
    return fetchJson<DecisionRecord[]>("/decision-history");
  }

  getDecisionPerformance(): Promise<DecisionPerformanceSummary[]> {
    return fetchJson<DecisionPerformanceSummary[]>("/decision-performance");
  }

  getSystemMaturity(): Promise<SystemMaturityReport | null> {
    return fetchJson<SystemMaturityReport | null>("/system-maturity");
  }

  getDiscoveryReport(): Promise<DiscoveryOutcome[]> {
    return fetchJson<DiscoveryOutcome[]>("/discovery-report");
  }

  getDiscoveryMetrics(): Promise<DiscoveryMetrics | null> {
    return fetchJson<DiscoveryMetrics | null>("/discovery-metrics");
  }

  getEndpointCandidates(): Promise<EndpointCandidate[]> {
    return fetchJson<EndpointCandidate[]>("/endpoint-candidates");
  }

  getPortfolioSummary(): Promise<PortfolioSummaryReport | null> {
    return fetchJson<PortfolioSummaryReport | null>("/portfolio-summary");
  }

  getWarnings(): Promise<MonitoringWarningsReport | null> {
    return fetchJson<MonitoringWarningsReport | null>("/warnings");
  }

  getCommitteeSummary(): Promise<CommitteeSummaryReport | null> {
    return fetchJson<CommitteeSummaryReport | null>("/committee-summary");
  }

  getShadowFund(): Promise<ShadowFundPublicState | null> {
    return fetchJson<ShadowFundPublicState | null>("/shadow-fund");
  }

  getShadowFundHistory(): Promise<ShadowFundHistory> {
    return fetchJson<ShadowFundHistory>("/shadow-fund-history");
  }

  getArtifactManifest(): Promise<ArtifactPublicationManifest | null> {
    return fetchJson<ArtifactPublicationManifest | null>("/manifest");
  }

  async postDecisions(request: DecideRequest): Promise<PositionAwareDecision[]> {
    const response = await fetch("/api/decisions", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(request),
    });
    const body = await response.json();
    if (!response.ok) {
      throw new Error(body?.error ?? `Failed to compute decisions: ${response.status}`);
    }
    return body as PositionAwareDecision[];
  }

  async postCapitalAllocation(request: DecideRequest): Promise<CapitalAllocationPlan> {
    const response = await fetch("/api/capital-allocation", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(request),
    });
    const body = await response.json();
    if (!response.ok) {
      throw new Error(body?.error ?? `Failed to compute capital allocation: ${response.status}`);
    }
    return body as CapitalAllocationPlan;
  }
}
