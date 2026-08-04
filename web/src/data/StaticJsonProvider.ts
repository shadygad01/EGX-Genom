// Reads the dashboard's JSON artifacts published alongside the static
// site (see agx_research.dashboard.export / the `export-dashboard` CLI
// subcommand, and .github/workflows/deploy-pages.yml's "generate dashboard
// artifacts" step). This is the provider GitHub Pages uses: no backend,
// no API, just the files the research pipeline already wrote to
// `web/public/data/` before the Vite build ran.

import type {
  AcquisitionDecision,
  ArtifactPublicationManifest,
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
import type { CapitalAllocationPlan, PositionAwareDecision } from "../types";
import { LiveDecisionsUnavailableError, type DashboardDataProvider, type DecideRequest } from "./DataProvider";

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

  getClaims(): Promise<InvestmentClaim[]> {
    return fetchList<InvestmentClaim>("claims.json");
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

  getFinancialCoverage(): Promise<FinancialCoverageReport | null> {
    return fetchObject<FinancialCoverageReport>("financial_coverage.json");
  }

  getSourceMetrics(): Promise<SourceMetricsRow[]> {
    return fetchList<SourceMetricsRow>("source_metrics.json");
  }

  getMarketBreadth(): Promise<MarketBreadthReport | null> {
    return fetchObject<MarketBreadthReport>("market_breadth.json");
  }

  getMarketRegime(): Promise<MarketRegimeReport | null> {
    return fetchObject<MarketRegimeReport>("market_regime.json");
  }

  getAcquisitionDecisions(): Promise<AcquisitionDecision[]> {
    return fetchList<AcquisitionDecision>("acquisition_decisions.json");
  }

  getDecisionReadiness(): Promise<DecisionReadiness[]> {
    return fetchList<DecisionReadiness>("decision_readiness.json");
  }

  getTickerDataGapReport(): Promise<TickerDataGapReport[]> {
    return fetchList<TickerDataGapReport>("ticker_data_gap_report.json");
  }

  getSourceTruth(): Promise<SourceTruthRow[]> {
    return fetchList<SourceTruthRow>("source_truth.json");
  }

  getDecisionHistory(): Promise<DecisionRecord[]> {
    return fetchList<DecisionRecord>("decision_history.json");
  }

  getDecisionPerformance(): Promise<DecisionPerformanceSummary[]> {
    return fetchList<DecisionPerformanceSummary>("decision_performance.json");
  }

  getSystemMaturity(): Promise<SystemMaturityReport | null> {
    return fetchObject<SystemMaturityReport>("system_maturity.json");
  }

  getDiscoveryReport(): Promise<DiscoveryOutcome[]> {
    return fetchList<DiscoveryOutcome>("discovery_report.json");
  }

  getDiscoveryMetrics(): Promise<DiscoveryMetrics | null> {
    return fetchObject<DiscoveryMetrics>("discovery_metrics.json");
  }

  getEndpointCandidates(): Promise<EndpointCandidate[]> {
    return fetchList<EndpointCandidate>("endpoint_candidates.json");
  }

  getPortfolioSummary(): Promise<PortfolioSummaryReport | null> {
    return fetchObject<PortfolioSummaryReport>("portfolio_summary.json");
  }

  getMacroSnapshot(): Promise<import("./DataProvider").MacroSnapshot | null> {
    return fetchObject<import("./DataProvider").MacroSnapshot>("macro_snapshot.json");
  }

  getWarnings(): Promise<MonitoringWarningsReport | null> {
    return fetchObject<MonitoringWarningsReport>("warnings.json");
  }

  getCommitteeSummary(): Promise<CommitteeSummaryReport | null> {
    return fetchObject<CommitteeSummaryReport>("committee_summary.json");
  }

  getShadowFund(): Promise<ShadowFundPublicState | null> {
    return fetchObject<ShadowFundPublicState>("shadow_fund.json");
  }

  async getShadowFundHistory(): Promise<ShadowFundHistory> {
    const data = await fetchObject<ShadowFundHistory>("shadow_fund_history.json");
    return data ?? { nav_series: [], transactions: [] };
  }

  getArtifactManifest(): Promise<ArtifactPublicationManifest | null> {
    return fetchObject<ArtifactPublicationManifest>("manifest.json");
  }

  async postDecisions(_request: DecideRequest): Promise<PositionAwareDecision[]> {
    throw new LiveDecisionsUnavailableError(
      "Personalized decisions need a live backend. decision_service depends on your own portfolio " +
        "holdings, which this platform never autonomously discovers or precomputes into the " +
        "static dashboard -- run `npm run dev -w api` locally with DECISION_DATA_DIR set (see " +
        "README's 'Personalized decisions' section), or use `agx decide` directly."
    );
  }

  async postCapitalAllocation(_request: DecideRequest): Promise<CapitalAllocationPlan> {
    throw new LiveDecisionsUnavailableError(
      "Capital allocation needs a live backend, for the same reason personalized decisions do -- " +
        "there is nothing to rank or recycle without your own real portfolio holdings. Run " +
        "`npm run dev -w api` locally with DECISION_DATA_DIR set, or use `agx allocate-capital` directly."
    );
  }
}
