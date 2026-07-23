// Mirrors api/src/types.ts, which in turn mirrors the pydantic models in
// research/src/agx_research/{knowledge,events,meta,market_memory,runtime,sources,dashboard}/.
// Kept in sync with contracts/*.schema.json (regenerated via
// `uv run python research/scripts/export_schemas.py`) — CI fails if those files drift
// from the pydantic schemas, which is the forcing function to update this file too.
//
// One interface per resource DashboardDataProvider exposes (see
// web/src/data/DataProvider.ts) — StaticJsonProvider and ApiProvider both
// produce values shaped exactly like these, so components never need to
// know which one is in use.

export type Horizon = "micro" | "swing" | "investment";

export interface ProvenanceRef {
  kind: string;
  ref_id: string;
  ref_version: number | string | null;
}

export interface Provenance {
  produced_by: string;
  produced_at: string;
  inputs: ProvenanceRef[];
}

// --- knowledge.json / KnowledgeObject ---

export type KnowledgeStatus = "promoted" | "monitoring" | "retired";

export interface PerformanceRecord {
  as_of: string;
  realized_return: number;
  notes: string;
}

export interface StatisticalEvidence {
  method: string;
  statistic: number;
  p_value: number;
  sample_size: number;
  confidence_interval: [number, number] | null;
}

export interface KnowledgeObject {
  id: string;
  version: number;
  discovery_date: string;
  creator_agent: string;
  supporting_evidence: string[];
  confidence: number;
  statistical_evidence: StatisticalEvidence;
  economic_explanation: string;
  affected_assets: string[];
  horizon: Horizon;
  expected_return: number;
  expected_risk: number;
  status: KnowledgeStatus;
  performance_history: PerformanceRecord[];
  retired_at: string | null;
  retirement_reason: string | null;
  provenance: Provenance;
}

// --- events.json / Event ---

export type EntityKind = "company" | "sector" | "macro_series" | "market" | "unknown";

export interface EntityRef {
  kind: EntityKind;
  canonical_id: string;
  raw_mention: string;
  display_name: string | null;
}

export type EventType = "corporate" | "macroeconomic" | "political" | "market" | "technical" | "news";
export type EventSeverity = "low" | "medium" | "high" | "critical";
export type EventStatus =
  | "pending"
  | "confirmed"
  | "corroborated"
  | "disputed"
  | "retracted"
  | "superseded"
  | "archived";
export type EventRelationshipType =
  | "corroborates"
  | "supersedes"
  | "contradicts"
  | "causally_precedes"
  | "part_of";

export interface EventRelationship {
  related_event_id: string;
  relationship_type: EventRelationshipType;
  notes: string;
}

export interface Event {
  id: string;
  version: number;
  event_type: EventType;
  subtype: string;
  entities: EntityRef[];
  event_date: string;
  timestamp: string;
  source: string;
  sources: string[];
  confidence: number;
  severity: EventSeverity;
  status: EventStatus;
  impact_horizons: Horizon[];
  metadata: Record<string, unknown>;
  disputed_keys: string[];
  relationships: EventRelationship[];
  provenance: Provenance;
}

// --- patterns.json ---
// Reserved for agx_research.agents.historical_patterns.HistoricalPatternsAgent,
// which is not yet implemented (raises NotImplementedError) -- always [].
export type Pattern = never;

// --- recommendations.json / Recommendation ---

export interface Explanation {
  why_this_stock: string;
  why_now: string;
  why_not_others: string;
  supporting_evidence: string[];
  evidence_refs: ProvenanceRef[];
  similar_historical_cases: string[];
  invalidation_conditions: string[];
}

export interface Prediction {
  ticker: string;
  horizon: Horizon;
  as_of: string;
  model_id: string;
  model_version: string;
  expected_return: number;
  expected_risk: number;
  confidence: number;
  explanation: Explanation;
  supporting_knowledge_ids: string[];
  provenance: Provenance;
}

export interface Recommendation {
  ticker: string;
  as_of: string;
  combined_expected_return: number;
  combined_expected_risk: number;
  confidence: number;
  horizon_predictions: Partial<Record<Horizon, Prediction>>;
  supporting_knowledge_ids: string[];
  explanation: Explanation;
  provenance: Provenance;
}

// --- market_state.json / MarketState (nullable: null until a run has happened) ---

export interface PriceBar {
  ticker: string;
  trade_date: string;
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
}

export interface CorporateEvent {
  ticker: string;
  event_date: string;
  event_type: string;
  description: string;
  details: Record<string, unknown>;
}

export interface MacroObservation {
  series_id: string;
  observation_date: string;
  value: number;
}

export interface NewsItem {
  published_at: string;
  source: string;
  headline: string;
  tickers: string[];
  body: string | null;
}

export interface DatasetSnapshot {
  id: string;
  version: number;
  as_of: string;
  lookback_days: number;
  tickers: string[];
  macro_series_ids: string[];
  price_history: Record<string, PriceBar[]>;
  corporate_events: Record<string, CorporateEvent[]>;
  macro_series: Record<string, MacroObservation[]>;
  news: NewsItem[];
}

export interface TradingSession {
  session_date: string;
  is_trading_day: boolean;
  holiday_name: string | null;
  notes: string;
}

export interface MarketState {
  as_of: string;
  dataset_snapshot: DatasetSnapshot;
  constituents: Record<string, string>;
  sectors: Record<string, string>;
  trading_session: TradingSession;
  events: Event[];
}

// --- runtime_metrics.json / RunRecord ---

export type RunStatus = "succeeded" | "failed" | "skipped_non_trading";

export interface RunRecord {
  id: string;
  version: number;
  run_date: string;
  status: RunStatus;
  session_id: string | null;
  hypotheses: number;
  promoted: number;
  error: string | null;
  notes: string;
  started_at: string;
  completed_at: string;
}

// --- system_status.json / DashboardSystemStatus ---

export interface DashboardSystemStatus {
  generated_at: string;
  pipeline_run_date: string | null;
  runs: number;
  succeeded: number;
  failed: number;
  knowledge_objects: number;
  by_status: Record<string, number>;
}

// --- source_registry.json / SourceSpec ---

export type SourceCategory =
  | "official"
  | "company"
  | "market_data"
  | "news"
  | "arabic_news"
  | "macroeconomic"
  | "global_markets"
  | "alternative"
  | "research";

export type AccessMethod =
  | "csv_download"
  | "json_api"
  | "rss_feed"
  | "xbrl"
  | "pdf_download"
  | "html_scrape"
  | "manual";

export type SourceStatus = "implemented" | "planned" | "needs_key" | "tos_review" | "disabled";

export type LifecycleState = "candidate" | "quarantine" | "evaluation" | "trusted" | "core";

export type HealthStatus = "unknown" | "healthy" | "degraded" | "down";

export type ActivationStatus = "active" | "paused" | "retired";

export interface RetryPolicy {
  max_attempts: number;
  backoff_seconds: number;
  backoff_multiplier: number;
}

export interface RateLimit {
  requests_per_minute: number;
  min_seconds_between_requests: number;
}

export interface SourceSpec {
  id: string;
  version: number;
  name: string;
  category: SourceCategory;
  country: string;
  access_method: AccessMethod;
  status: SourceStatus;
  lifecycle_state: LifecycleState;
  health_status: HealthStatus;
  activation_status: ActivationStatus;
  base_url: string | null;
  authentication: string;
  reliability_score: number;
  freshness_score: number;
  historical_coverage: string;
  expected_latency: string;
  update_frequency: string;
  schema_version: string;
  collector: string | null;
  collector_version: string | null;
  retry_policy: RetryPolicy;
  rate_limit: RateLimit;
  license: string;
  terms_of_use_url: string | null;
  provenance_policy: string;
  validation_rules: string[];
  normalization_rules: string[];
  conflict_priority: number;
  priority: number;
  supported_entities: string[];
  supported_event_types: string[];
  supported_languages: string[];
  data_quality_score: number | null;
  reputation_score: number | null;
  notes: string;
}
