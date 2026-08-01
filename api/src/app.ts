import Fastify, { type FastifyInstance } from "fastify";
import { ArtifactsReader } from "./artifactsStore.js";
import { KnowledgeStoreReader } from "./knowledgeStore.js";
import { dashboardRoutes } from "./routes/dashboard.js";
import { decisionsRoutes } from "./routes/decisions.js";
import { healthRoutes } from "./routes/health.js";
import { knowledgeRoutes } from "./routes/knowledge.js";

export interface AppConfig {
  knowledgeStorePath: string;
  eventsStorePath: string;
  runsStorePath: string;
  artifactsDir: string;
  // See routes/decisions.ts: null means the live Decision Center endpoint
  // is honestly unconfigured rather than guessing a directory.
  decisionDataDir: string | null;
  universeSeedDir: string;
  researchDir: string;
}

export function buildApp(config: AppConfig): FastifyInstance {
  const app = Fastify({ logger: true });
  const store = new KnowledgeStoreReader(config.knowledgeStorePath);
  const artifacts = new ArtifactsReader(config.artifactsDir);

  app.register(healthRoutes);
  app.register(knowledgeRoutes, { store });
  app.register(dashboardRoutes, {
    eventsStorePath: config.eventsStorePath,
    runsStorePath: config.runsStorePath,
    artifacts,
  });
  app.register(decisionsRoutes, {
    decisionDataDir: config.decisionDataDir,
    universeSeedDir: config.universeSeedDir,
    researchDir: config.researchDir,
  });

  return app;
}
