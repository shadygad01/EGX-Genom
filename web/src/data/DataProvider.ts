// The one seam between the dashboard's components and where its data comes
// from. Every method here returns exactly the shapes web/src/types.ts
// defines (which mirror the pydantic models research/ produces) -- a
// component that talks to a DashboardDataProvider never knows, and never
// needs to know, whether the values came from a static JSON file (GitHub
// Pages) or a live HTTP endpoint (a hosted api/). See
// docs/ARCHITECTURE.md's "Dashboard data providers" section, and
// StaticJsonProvider/ApiProvider for the two implementations.

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
  FinancialStatementLineItem,
  FinancialCoverageReport,
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
  PositionInput,
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

// Unified macroeconomic snapshot produced by fetch_macro_data.py.
// All fields are real, sourced from Yahoo Finance / World Bank / FRED.
export interface MacroSnapshot {
  as_of: string;
  egp_usd: {
    current: number | null;
    date: string | null;
    change_30d_pct: number | null;
    series_length: number;
  };
  cpi_inflation_pct: {
    current: number | null;
    date: string | null;
    regime: string;
  };
  brent_usd: {
    current: number | null;
    date: string | null;
  };
  interest_rate_real_pct: {
    current: number | null;
    date: string | null;
  };
  gdp_growth_pct: {
    current: number | null;
    date: string | null;
  };
  decision_implications: string[];
  sources: Record<string, string>;
}

export interface DecideRequest {
  date: string;
  positions?: Record<string, PositionInput>;
}

// Thrown by StaticJsonProvider.postDecisions() -- decision_service is a live,
// on-demand computation (it depends on the investor's own position state,
// which can never be autonomously discovered or precomputed into a static
// artifact -- see CLAUDE.md's decision_service rules). Pages catch this
// specifically to render an honest "needs a live backend" state rather than
// a generic fetch-failure error.
export class LiveDecisionsUnavailableError extends Error {
  constructor(message: string) {
    super(message);
    this.name = "LiveDecisionsUnavailableError";
  }
}

// Every method here mirrors exactly one dashboard artifact file (see
// docs/ARCHITECTURE.md's "Dashboard data providers" section) -- no
// component ever computes a value that isn't already one of these fields.
// The core artifacts are always present (both StaticJsonProvider's fixed
// contract and ProductionPipeline produce them); the rest are only
// produced by the full production pipeline (`agx run`) and resolve to an
// honest empty/null value when absent, never a fabricated one.
export interface DashboardDataProvider {
  getKnowledge(): Promise<KnowledgeObject[]>;
  getEvents(): Promise<Event[]>;
  getPatterns(): Promise<Pattern[]>;
  getRecommendations(): Promise<Recommendation[]>;
  getMarketState(): Promise<MarketState | null>;
  getUniverse(): Promise<UniverseArtifact | null>;
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
  getClaims(): Promise<InvestmentClaim[]>;
  getHypotheses(): Promise<Hypothesis[]>;
  getKnowledgeGraph(): Promise<KnowledgeGraphData>;
  getFinancialStatements(): Promise<FinancialStatementLineItem[]>;
  getFinancialCoverage(): Promise<FinancialCoverageReport | null>;
  getSourceMetrics(): Promise<SourceMetricsRow[]>;
  getMarketBreadth(): Promise<MarketBreadthReport | null>;
  getMarketRegime(): Promise<MarketRegimeReport | null>;
  getAcquisitionDecisions(): Promise<AcquisitionDecision[]>;
  getDecisionReadiness(): Promise<DecisionReadiness[]>;
  getTickerDataGapReport(): Promise<TickerDataGapReport[]>;
  getSourceTruth(): Promise<SourceTruthRow[]>;
  getDecisionHistory(): Promise<DecisionRecord[]>;
  getDecisionPerformance(): Promise<DecisionPerformanceSummary[]>;
  getSystemMaturity(): Promise<SystemMaturityReport | null>;
  getDiscoveryReport(): Promise<DiscoveryOutcome[]>;
  getDiscoveryMetrics(): Promise<DiscoveryMetrics | null>;
  getEndpointCandidates(): Promise<EndpointCandidate[]>;

  // CIO Desk artifacts: the autonomous, position-unaware model portfolio's
  // summary, monitoring warnings, and investment committee agreement.
  getPortfolioSummary(): Promise<PortfolioSummaryReport | null>;
  getWarnings(): Promise<MonitoringWarningsReport | null>;
  getCommitteeSummary(): Promise<CommitteeSummaryReport | null>;

  // Macroeconomic snapshot: real EGP/USD, CPI, Brent, GDP, interest rate.
  // Produced by research/scripts/fetch_macro_data.py and exported to
  // web/public/data/macro_snapshot.json — never fabricated.
  getMacroSnapshot(): Promise<MacroSnapshot | null>;

  // Shadow Fund: the persistent virtual-portfolio state produced
  // autonomously as a stage inside `agx run` (shadow_fund/engine.py) --
  // unlike postDecisions/postCapitalAllocation below, this is a real
  // static dashboard artifact (both providers read it the same way),
  // never a live on-demand call, because the fund's own state (not a
  // real investor's) is safe to precompute.
  getShadowFund(): Promise<ShadowFundPublicState | null>;
  getShadowFundHistory(): Promise<ShadowFundHistory>;

  // Artifact provenance (AD-64, docs/ARCHITECTURE_DECISIONS.md): where the
  // currently-served bundle actually came from. `null` means no manifest
  // was published alongside it at all -- itself a signal the bundle
  // predates provenance tracking or wasn't written by a provenance-aware
  // exporter. See web/src/lib/provenance.ts's `isProductionVerified()`.
  getArtifactManifest(): Promise<ArtifactPublicationManifest | null>;

  // The one write-shaped call on this interface: computes fresh, position-
  // aware decisions on demand (see api/src/routes/decisions.ts). Never
  // cached, never a static artifact -- StaticJsonProvider always rejects
  // with LiveDecisionsUnavailableError.
  postDecisions(request: DecideRequest): Promise<PositionAwareDecision[]>;

  // Capital Allocation Intelligence: same on-demand, position-aware-only
  // shape as postDecisions -- there is nothing to rank/recycle without a
  // real portfolio, so this is never a static artifact either (see
  // capital_allocation/__init__.py).
  postCapitalAllocation(request: DecideRequest): Promise<CapitalAllocationPlan>;
}
