// Shared read logic for any JSON file agx_research.storage.JsonFileRepository
// persists: `Record<id, T[]>`, where the last array entry per id is the
// current revision. KnowledgeStoreReader predates this and keeps its own
// copy (it also needs getById/revisionsFor, which a flat "latest" reader
// doesn't) -- this is the generic version for readers that only need
// "every id's latest revision," same as `Repository.all_latest()` in Python.

import { readFile } from "node:fs/promises";

type PersistedStore<T> = Record<string, T[]>;

async function loadStore<T>(path: string): Promise<PersistedStore<T>> {
  try {
    const raw = await readFile(path, "utf-8");
    return JSON.parse(raw) as PersistedStore<T>;
  } catch (err: unknown) {
    if (err instanceof Error && "code" in err && (err as NodeJS.ErrnoException).code === "ENOENT") {
      return {};
    }
    throw err;
  }
}

export async function readAllLatest<T>(path: string): Promise<T[]> {
  const store = await loadStore<T>(path);
  return Object.values(store)
    .filter((revisions) => revisions.length > 0)
    .map((revisions) => revisions[revisions.length - 1]);
}
