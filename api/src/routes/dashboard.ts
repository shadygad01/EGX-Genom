import type { FastifyInstance } from "fastify";
import type { ArtifactsReader } from "../artifactsStore.js";
import { readAllLatest } from "../versionedStore.js";

export async function dashboardRoutes(
  app: FastifyInstance,
  opts: { eventsStorePath: string; runsStorePath: string; artifacts: ArtifactsReader }
): Promise<void> {
  const { eventsStorePath, runsStorePath, artifacts } = opts;

  app.get("/events", async () => readAllLatest(eventsStorePath));
  app.get("/runtime-metrics", async () => readAllLatest(runsStorePath));
  app.get("/patterns", async () => artifacts.patterns());
  app.get("/recommendations", async () => artifacts.recommendations());
  app.get("/market-state", async () => artifacts.marketState());
  app.get("/universe", async () => artifacts.universe());
  app.get("/system-status", async () => artifacts.systemStatus());
  app.get("/source-registry", async () => artifacts.sourceRegistry());

  app.get("/investment-cases", async () => artifacts.investmentCases());
  app.get("/collector-status", async () => artifacts.collectorStatus());
  app.get("/runtime-status", async () => artifacts.runtimeStatus());
  app.get("/dashboard-metrics", async () => artifacts.dashboardMetrics());
  app.get("/mission-status", async () => artifacts.missionStatus());
  app.get("/execution-report", async () => artifacts.executionReport());
  app.get("/genes", async () => artifacts.genes());
  app.get("/papers", async () => artifacts.papers());
  app.get("/claims", async () => artifacts.claims());
  app.get("/hypotheses", async () => artifacts.hypotheses());
  app.get("/knowledge-graph", async () => artifacts.knowledgeGraph());
  app.get("/financial-statements", async () => artifacts.financialStatements());
  app.get("/financial-coverage", async () => artifacts.financialCoverage());
  app.get("/source-metrics", async () => artifacts.sourceMetrics());
  app.get("/market-breadth", async () => artifacts.marketBreadth());
  app.get("/market-regime", async () => artifacts.marketRegime());
  app.get("/acquisition-decisions", async () => artifacts.acquisitionDecisions());
  app.get("/decision-readiness", async () => artifacts.decisionReadiness());
  app.get("/ticker-data-gaps", async () => artifacts.tickerDataGapReport());
  app.get("/source-truth", async () => artifacts.sourceTruth());
  app.get("/decision-history", async () => artifacts.decisionHistory());
  app.get("/decision-performance", async () => artifacts.decisionPerformance());
  app.get("/system-maturity", async () => artifacts.systemMaturity());
  app.get("/discovery-report", async () => artifacts.discoveryReport());
  app.get("/discovery-metrics", async () => artifacts.discoveryMetrics());
  app.get("/endpoint-candidates", async () => artifacts.endpointCandidates());

  // CIO Desk artifacts (Institutional Investment Operating System mission):
  // the autonomous, position-unaware model portfolio's summary, warnings,
  // and investment committee agreement -- same read-only pattern as every
  // other route above.
  app.get("/portfolio-summary", async () => artifacts.portfolioSummary());
  app.get("/warnings", async () => artifacts.warnings());
  app.get("/committee-summary", async () => artifacts.committeeSummary());

  // Shadow Fund: the persistent virtual-portfolio state produced by
  // shadow_fund/engine.py as a stage inside `agx run` -- read-only here,
  // same as every other artifact above (never computed on demand).
  app.get("/shadow-fund", async () => artifacts.shadowFund());
  app.get("/shadow-fund-history", async () => artifacts.shadowFundHistory());

  // Artifact provenance (AD-64): where the bundle this api/ instance is
  // serving actually came from -- see docs/ARCHITECTURE_DECISIONS.md.
  app.get("/manifest", async () => artifacts.manifest());
  app.get("/macro-snapshot", async () => artifacts.macroSnapshot());
}
