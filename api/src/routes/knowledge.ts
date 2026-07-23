import type { FastifyInstance } from "fastify";
import type { KnowledgeStoreReader } from "../knowledgeStore.js";

export async function knowledgeRoutes(
  app: FastifyInstance,
  opts: { store: KnowledgeStoreReader }
): Promise<void> {
  const { store } = opts;

  app.get("/knowledge", async () => {
    return store.allLatest();
  });

  app.get<{ Params: { id: string } }>("/knowledge/:id", async (request, reply) => {
    const knowledge = await store.getById(request.params.id);
    if (!knowledge) {
      return reply.status(404).send({ error: "not_found", id: request.params.id });
    }
    return knowledge;
  });

  app.get<{ Params: { id: string } }>("/knowledge/:id/revisions", async (request) => {
    return store.revisionsFor(request.params.id);
  });
}
