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
  app.get("/system-status", async () => artifacts.systemStatus());
  app.get("/source-registry", async () => artifacts.sourceRegistry());
}
