// Reads pre-computed dashboard artifact snapshots -- the exact same files
// `agx_research.cli export-dashboard` writes for the static GitHub Pages
// build (patterns.json, recommendations.json, market_state.json,
// system_status.json, source_registry.json). These five aren't simple
// versioned repositories: recommendations/market_state are computed
// on-demand by the research engine, source_registry is a static Python
// catalog, and patterns is reserved for an unimplemented agent -- none of
// them have a "live" TypeScript-side recomputation, so the API reads the
// same generated snapshot a production deployment would refresh on a
// schedule (see docs/ARCHITECTURE.md's "Dashboard data providers" section).
// This is what makes ApiProvider and StaticJsonProvider consume "exactly
// the same contract": in production they can even be the same file.

import { readFile } from "node:fs/promises";

async function readJsonOrDefault<T>(path: string, fallback: T): Promise<T> {
  try {
    const raw = await readFile(path, "utf-8");
    return JSON.parse(raw) as T;
  } catch (err: unknown) {
    if (err instanceof Error && "code" in err && (err as NodeJS.ErrnoException).code === "ENOENT") {
      return fallback;
    }
    throw err;
  }
}

export class ArtifactsReader {
  constructor(private readonly artifactsDir: string) {}

  private path(filename: string): string {
    return `${this.artifactsDir}/${filename}`;
  }

  patterns<T = unknown>(): Promise<T[]> {
    return readJsonOrDefault<T[]>(this.path("patterns.json"), []);
  }

  recommendations<T = unknown>(): Promise<T[]> {
    return readJsonOrDefault<T[]>(this.path("recommendations.json"), []);
  }

  marketState<T = unknown>(): Promise<T | null> {
    return readJsonOrDefault<T | null>(this.path("market_state.json"), null);
  }

  systemStatus<T = unknown>(): Promise<T | null> {
    return readJsonOrDefault<T | null>(this.path("system_status.json"), null);
  }

  sourceRegistry<T = unknown>(): Promise<T[]> {
    return readJsonOrDefault<T[]>(this.path("source_registry.json"), []);
  }
}
