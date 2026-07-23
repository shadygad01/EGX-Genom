// The one seam between the dashboard's components and where its data comes
// from. Every method here returns exactly the shapes web/src/types.ts
// defines (which mirror the pydantic models research/ produces) -- a
// component that talks to a DashboardDataProvider never knows, and never
// needs to know, whether the values came from a static JSON file (GitHub
// Pages) or a live HTTP endpoint (a hosted api/). See
// docs/ARCHITECTURE.md's "Dashboard data providers" section, and
// StaticJsonProvider/ApiProvider for the two implementations.

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

export interface DashboardDataProvider {
  getKnowledge(): Promise<KnowledgeObject[]>;
  getEvents(): Promise<Event[]>;
  getPatterns(): Promise<Pattern[]>;
  getRecommendations(): Promise<Recommendation[]>;
  getMarketState(): Promise<MarketState | null>;
  getRuntimeMetrics(): Promise<RunRecord[]>;
  getSystemStatus(): Promise<DashboardSystemStatus | null>;
  getSourceRegistry(): Promise<SourceSpec[]>;
}
