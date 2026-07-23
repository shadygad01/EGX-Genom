// Reads the dashboard's JSON artifacts published alongside the static
// site (see agx_research.dashboard.export / the `export-dashboard` CLI
// subcommand, and .github/workflows/deploy-pages.yml's "generate dashboard
// artifacts" step). This is the provider GitHub Pages uses: no backend,
// no API, just the files the research pipeline already wrote to
// `web/public/data/` before the Vite build ran.

import type {
  DashboardSystemStatus,
  Event,
  KnowledgeObject,
  MarketState,
  Pattern,
  Recommendation,
  RunRecord,
  SourceSpec,
} from "../types";
import type { DashboardDataProvider } from "./DataProvider";

async function fetchList<T>(filename: string): Promise<T[]> {
  const response = await fetch(`${import.meta.env.BASE_URL}data/${filename}`);
  if (response.status === 404) return [];
  if (!response.ok) {
    throw new Error(`Failed to fetch ${filename}: ${response.status}`);
  }
  return response.json();
}

async function fetchObject<T>(filename: string): Promise<T | null> {
  const response = await fetch(`${import.meta.env.BASE_URL}data/${filename}`);
  if (response.status === 404) return null;
  if (!response.ok) {
    throw new Error(`Failed to fetch ${filename}: ${response.status}`);
  }
  return response.json();
}

export class StaticJsonProvider implements DashboardDataProvider {
  getKnowledge(): Promise<KnowledgeObject[]> {
    return fetchList<KnowledgeObject>("knowledge.json");
  }

  getEvents(): Promise<Event[]> {
    return fetchList<Event>("events.json");
  }

  getPatterns(): Promise<Pattern[]> {
    return fetchList<Pattern>("patterns.json");
  }

  getRecommendations(): Promise<Recommendation[]> {
    return fetchList<Recommendation>("recommendations.json");
  }

  getMarketState(): Promise<MarketState | null> {
    return fetchObject<MarketState>("market_state.json");
  }

  getRuntimeMetrics(): Promise<RunRecord[]> {
    return fetchList<RunRecord>("runtime_metrics.json");
  }

  getSystemStatus(): Promise<DashboardSystemStatus | null> {
    return fetchObject<DashboardSystemStatus>("system_status.json");
  }

  getSourceRegistry(): Promise<SourceSpec[]> {
    return fetchList<SourceSpec>("source_registry.json");
  }
}
