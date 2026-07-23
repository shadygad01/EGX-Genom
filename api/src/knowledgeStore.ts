// Thin read-only wrapper around the JSON file that agx_research.knowledge.store.KnowledgeStore
// persists to. The API deliberately contains no knowledge-lifecycle logic of its own — see
// docs/ARCHITECTURE.md for why business logic stays in `research/`.

import { readFile } from "node:fs/promises";
import type { KnowledgeObject } from "./types.js";

type PersistedStore = Record<string, KnowledgeObject[]>;

export class KnowledgeStoreReader {
  constructor(private readonly path: string) {}

  private async load(): Promise<PersistedStore> {
    try {
      const raw = await readFile(this.path, "utf-8");
      return JSON.parse(raw) as PersistedStore;
    } catch (err: unknown) {
      if (err instanceof Error && "code" in err && (err as NodeJS.ErrnoException).code === "ENOENT") {
        return {};
      }
      throw err;
    }
  }

  async allLatest(): Promise<KnowledgeObject[]> {
    const store = await this.load();
    return Object.values(store)
      .filter((revisions) => revisions.length > 0)
      .map((revisions) => revisions[revisions.length - 1]);
  }

  async getById(id: string): Promise<KnowledgeObject | null> {
    const store = await this.load();
    const revisions = store[id];
    if (!revisions || revisions.length === 0) return null;
    return revisions[revisions.length - 1];
  }

  async revisionsFor(id: string): Promise<KnowledgeObject[]> {
    const store = await this.load();
    return store[id] ?? [];
  }
}
