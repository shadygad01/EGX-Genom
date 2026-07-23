import Fastify, { type FastifyInstance } from "fastify";
import { KnowledgeStoreReader } from "./knowledgeStore.js";
import { healthRoutes } from "./routes/health.js";
import { knowledgeRoutes } from "./routes/knowledge.js";

export function buildApp(knowledgeStorePath: string): FastifyInstance {
  const app = Fastify({ logger: true });
  const store = new KnowledgeStoreReader(knowledgeStorePath);

  app.register(healthRoutes);
  app.register(knowledgeRoutes, { store });

  return app;
}
