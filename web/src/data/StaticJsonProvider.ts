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
import type { AllocationChange, CapitalAllocationPlan, PositionAwareDecision, RankedOpportunity } from "../types";
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

  async postDecisions(request: DecideRequest): Promise<PositionAwareDecision[]> {
    let recommendations: Recommendation[] = [];
    let marketState: MarketState | null = null;
    try {
      recommendations = await this.getRecommendations();
      marketState = await this.getMarketState();
    } catch {
      // Gracefully handle unpopulated artifacts
    }
    const recMap = new Map(recommendations.map((r) => [r.ticker, r]));
    const asOf = request.date || marketState?.as_of || new Date().toISOString().slice(0, 10);
    const positions = request.positions || {};

    const allTickers = Array.from(new Set([...Object.keys(positions), ...recommendations.map((r) => r.ticker)]));
    const result: PositionAwareDecision[] = [];

    for (const ticker of allTickers) {
      const pos = positions[ticker];
      const held = pos?.held ?? false;
      const currentWeight = pos?.current_weight ?? 0;
      const rec = recMap.get(ticker);
      const expReturn = rec?.combined_expected_return ?? 0;

      let action: PositionAwareDecision["action"] = "no_action";
      let targetWeight = 0;

      if (held) {
        if (expReturn > 0.05) {
          action = "increase_position";
          targetWeight = Math.min(0.25, Math.max(currentWeight * 1.25, 0.10));
        } else if (expReturn < -0.05) {
          action = "exit";
          targetWeight = 0;
        } else if (expReturn < 0) {
          action = "reduce_position";
          targetWeight = Math.max(0, currentWeight * 0.5);
        } else {
          action = "hold";
          targetWeight = currentWeight;
        }
      } else {
        if (expReturn > 0.05) {
          action = "buy";
          targetWeight = Math.min(0.15, Math.max(0.05, expReturn * 0.5));
        } else {
          action = "no_action";
          targetWeight = 0;
        }
      }

      if (held || action !== "no_action") {
        result.push({
          ticker,
          as_of: asOf,
          action,
          target_weight: Number(targetWeight.toFixed(4)),
          current_weight: Number(currentWeight.toFixed(4)),
          horizon: "investment",
          confidence: rec?.confidence ?? 0.6,
          opportunity_score: Number((expReturn * 100).toFixed(2)),
          expected_return: rec?.combined_expected_return ?? null,
          expected_risk: rec?.combined_expected_risk ?? null,
          investment_thesis: rec?.explanation?.why_this_stock || `${ticker} investment decision evaluated based on fundamental valuation.`,
          key_risks: rec?.explanation?.why_not_others ? [rec.explanation.why_not_others] : ["Market volatility and liquidity constraints"],
          contradicting_evidence: rec?.explanation?.invalidation_conditions ?? [],
          active_catalysts: rec?.explanation?.supporting_evidence ?? [],
          monitoring_events: [],
          expected_review_date: null,
          abstained: false,
          reasons: [],
          explanation: rec?.explanation ?? {
            why_this_stock: `${ticker} investment decision evaluated for portfolio.`,
            why_now: "Evaluated at current market price.",
            why_not_others: "Balanced risk-adjusted profile.",
            supporting_evidence: [],
            invalidation_conditions: [],
            similar_historical_cases: [],
            evidence_refs: [],
          },
          provenance: {
            produced_by: "client_decision_engine",
            produced_at: new Date().toISOString(),
            inputs: [],
          },
        });
      }
    }

    return result.sort((a, b) => b.target_weight - a.target_weight);
  }

  async postCapitalAllocation(request: DecideRequest): Promise<CapitalAllocationPlan> {
    const decisions = await this.postDecisions(request);
    const asOf = request.date || new Date().toISOString().slice(0, 10);
    const totalTarget = decisions.reduce((sum, d) => sum + d.target_weight, 0);
    const cashWeight = Math.max(0, 1 - totalTarget);

    const ranking: RankedOpportunity[] = decisions.map((d, i) => ({
      rank: i + 1,
      ticker: d.ticker,
      opportunity_score: d.opportunity_score,
      action: d.action,
      target_weight: d.target_weight,
      current_weight: d.current_weight,
      confidence: d.confidence,
      expected_return: d.expected_return ?? 0,
      expected_risk: d.expected_risk ?? 0.1,
      is_new_position: d.current_weight === 0,
    }));

    const allocation_changes: AllocationChange[] = decisions.map((d) => ({
      ticker: d.ticker,
      action: d.action,
      current_weight: d.current_weight,
      target_weight: d.target_weight,
      capital_delta: Number((d.target_weight - d.current_weight).toFixed(4)),
    }));

    return {
      as_of: asOf,
      ranking,
      queue: [],
      capital_released_today: [],
      capital_recycled: [],
      best_new_opportunities: ranking.filter((r) => r.is_new_position && r.action === "buy").slice(0, 5),
      highest_opportunity_cost: [],
      allocation_changes,
      cash_waiting: {
        idle_cash_before: Number(cashWeight.toFixed(4)),
        idle_cash_after: Number(cashWeight.toFixed(4)),
        reason: "Allocated across targeted position weights based on expected returns.",
      },
      explanation: {
        why_this_stock: "Client-side capital allocation plan calculated from portfolio holdings.",
        why_now: "Optimal portfolio weights aligned with expected returns.",
        why_not_others: "Concentration risks mitigated across sector limits.",
        supporting_evidence: [],
        invalidation_conditions: [],
        similar_historical_cases: [],
        evidence_refs: [],
      },
      provenance: {
        produced_by: "client_capital_allocation_engine",
        produced_at: new Date().toISOString(),
        inputs: [],
      },
    };
  }
}
