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
  app.get("/hypotheses", async () => artifacts.hypotheses());
  app.get("/knowledge-graph", async () => artifacts.knowledgeGraph());
  app.get("/financial-statements", async () => artifacts.financialStatements());
  app.get("/source-metrics", async () => artifacts.sourceMetrics());
  app.get("/acquisition-decisions", async () => artifacts.acquisitionDecisions());
  app.get("/decision-readiness", async () => artifacts.decisionReadiness());
  app.get("/ticker-data-gaps", async () => artifacts.tickerDataGapReport());
  app.get("/source-truth", async () => artifacts.sourceTruth());
  app.get("/decision-history", async () => artifacts.decisionHistory());
  app.get("/decision-performance", async () => artifacts.decisionPerformance());
  app.get("/publication-gate", async () => artifacts.publicationGate());
}
