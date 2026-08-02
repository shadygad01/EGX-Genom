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

export type ReadinessStatus = "ready" | "degraded" | "blocked";

export interface DecisionReadiness {
  ticker: string;
  as_of: string;
  status: ReadinessStatus;
  decision: "researchable" | "abstain";
  ready_horizons: Horizon[];
  horizon_blockers?: Partial<Record<Horizon, string[]>>;
  price_observations: number;
  latest_price_date: string | null;
  news_items: number;
  corporate_events: number;
  financial_periods: number;
  fair_value_available: boolean;
  valuation: ValuationMetrics | null;
  // (current_price - weighted_fair_value) / weighted_fair_value: positive
  // means price sits above the calculated fair value (expensive), negative
  // means below it (a margin of safety). null when no fair value could be
  // computed (see fair_value_available).
  price_vs_fair_value_pct: number | null;
  macro_series: number;
  active_knowledge: number;
  blockers: string[];
  next_actions: string[];
}

export interface ValuationMetrics {
  ticker: string;
  as_of: string;
  latest_financial_period: string | null;
  latest_market_snapshot_date: string | null;
  current_price: number | null;
  market_cap: number | null;
  market_pe: number | null;
  market_eps: number | null;
  dividend_yield: number | null;
  beta: number | null;
  enterprise_value: number | null;
  ebitda: number | null;
  ev_to_ebitda: number | null;
  price_to_book: number | null;
  dcf_per_share: number | null;
  weighted_fair_value: number | null;
  bear_case: number | null;
  bull_case: number | null;
  included_models: string[];
  unavailable_reasons: string[];
}

export interface DataLayerGap {
  layer: "financials" | "disclosures" | "news" | "macro" | "knowledge";
  count: number;
  threshold: number;
  complete: boolean;
  completeness_pct: number;
}

export interface TickerDataGapReport {
  ticker: string;
  as_of: string;
  status: ReadinessStatus;
  decision: "researchable" | "abstain";
  ready_horizons: Horizon[];
  swing_ready: boolean;
  investment_ready: boolean;
  price_observations: number;
  latest_price_date: string | null;
  layers: DataLayerGap[];
  overall_completeness_pct: number;
  blockers: string[];
  next_actions: string[];
}

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
  horizon_decisions: Partial<Record<Horizon, HorizonDecision>>;
  supporting_knowledge_ids: string[];
  explanation: Explanation;
  provenance: Provenance;
}

export interface SourceTruthRow {
  source_id: string;
  name: string;
  category: string;
  catalogued: boolean;
  legally_usable: boolean;
  attempted_this_run: boolean;
  fetched_this_run: boolean;
  fresh: boolean;
  produced_records: number;
  reached_decision_path: boolean;
  corroborated: boolean;
  collector_status: string;
  blocker: string | null;
  last_run_at: string | null;
  consumers: string[];
}

export interface DecisionRecord {
  id: string;
  version: number;
  ticker: string;
  horizon: Horizon;
  as_of: string;
  action: DecisionAction;
  expected_return: number;
  expected_risk: number;
  confidence: number;
  valid_until: string;
  publication_status: string;
  outcome_status: "pending" | "evaluated" | "insufficient_data";
  entry_price: number | null;
  exit_price: number | null;
  gross_asset_return: number | null;
  realized_return: number | null;
  transaction_cost_bps: number | null;
  benchmark_ticker: string | null;
  benchmark_return: number | null;
  excess_return: number | null;
  hit: boolean | null;
}

export interface DecisionPerformanceSummary {
  horizon: Horizon;
  decisions: number;
  evaluated: number;
  pending: number;
  insufficient_data: number;
  hit_rate: number | null;
  mean_realized_return: number | null;
  benchmark_evaluated: number;
  mean_benchmark_return: number | null;
  mean_excess_return: number | null;
  median_excess_return: number | null;
  excess_return_lower_95: number | null;
  max_drawdown: number | null;
  mean_expected_return: number | null;
  calibration_error: number | null;
  sample_status: "sufficient" | "insufficient_sample" | "insufficient_benchmark";
}

export type SystemMaturityLevel = "early" | "validating" | "developing" | "established" | "verified";

export interface SystemMaturityReport {
  as_of: string;
  level: SystemMaturityLevel;
  rationale: string;
  horizons_meeting_significance_floor: number;
  total_horizons: number;
  min_evaluated_across_horizons: number;
  governance_reviewed: boolean;
}

export type DecisionAction = "buy_candidate" | "watch" | "avoid" | "abstain";
export type PublicationStatus = "research_only" | "publication_ready";
export type PriceConditionOperator = "at_or_below" | "below" | "not_applicable";

export interface HorizonDecision {
  horizon: Horizon;
  horizon_window: string;
  action: DecisionAction;
  expected_return: number;
  expected_risk: number;
  risk_metric: string;
  confidence: number;
  risk_adjusted_score: number;
  valid_until: string;
  entry_condition: string;
  reference_price: number | null;
  entry_operator: PriceConditionOperator;
  entry_value: number | null;
  invalidation_operator: PriceConditionOperator;
  invalidation_value: number | null;
  review_condition: string;
  invalidation_conditions: string[];
  max_position_pct: number;
  publication_status: PublicationStatus;
  abstention_reasons: string[];
  evidence_refs: ProvenanceRef[];
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
  macro_lookback_days: number;
  pattern_lookback_days: number;
  tickers: string[];
  macro_series_ids: string[];
  price_history: Record<string, PriceBar[]>;
  long_price_history: Record<string, PriceBar[]>;
  corporate_events: Record<string, CorporateEvent[]>;
  long_corporate_events: Record<string, CorporateEvent[]>;
  financial_statements: Record<string, FinancialStatementLineItem[]>;
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

export interface UniverseArtifact {
  as_of: string;
  count: number;
  tickers: string[];
  constituents: Record<string, string>;
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

export type EvidenceTier = "primary" | "discovery";

export interface RetryPolicy {
  max_attempts: number;
  backoff_seconds: number;
  backoff_multiplier: number;
}

export interface RateLimit {
  requests_per_minute: number;
  min_seconds_between_requests: number;
}

// --- investment_cases.json ---

export interface PortfolioPosition {
  ticker: string;
  weight: number;
  score: number;
  expected_return: number;
  expected_risk: number;
  confidence: number;
  supporting_knowledge_ids: string[];
}

export interface PortfolioRecommendation {
  id: string;
  version: number;
  as_of: string;
  positions: PortfolioPosition[];
  cash_weight: number;
  explanation: Explanation;
  provenance: Provenance;
}

export interface InvestmentCases {
  as_of: string | null;
  recommendations: Recommendation[];
  portfolio: PortfolioRecommendation | null;
  macro_overlay: MacroDecisionOverlay | null;
}

export interface MacroContribution {
  factor: string;
  series_id: string;
  importance_weight: number;
  effective_weight: number;
  signal: -1 | 0 | 1;
  latest_value: number;
  previous_value: number;
  latest_date: string;
  change_pct: number;
  impact: "supportive" | "neutral" | "adverse";
}

export interface MacroDecisionOverlay {
  as_of: string;
  decision: "supportive" | "cautious" | "defensive" | "insufficient_data";
  score: number;
  exposure_multiplier: number;
  available_weight: number;
  contributions: MacroContribution[];
  rationale: string;
}

// --- collector_status.json ---

export interface CollectorStatusRow {
  source_id: string;
  status: "COLLECTED" | "DEGRADED" | "STANDBY" | "FAILED" | "UNAVAILABLE";
  reason: string | null;
  connection_success: boolean;
  parse_success: boolean;
  yield: number;
  events_produced: number;
  documents_fetched: number;
  batches_materialized: number;
  batches_withheld: number;
  price_bars_written: number;
  macro_observations_written: number;
  news_items_written: number;
  corporate_events_written: number;
  index_constituents_written: number;
  financial_statement_line_items_written: number;
  events_registered: number;
  lifecycle_state: LifecycleState | null;
  health_status: HealthStatus | null;
  reputation_score: number | null;
  data_quality_score: number | null;
  integration_via: string | null;
  integrated_capabilities: string[];
}

// --- acquisition_decisions.json ---

export type CapabilityStrategyOutcome = "succeeded" | "zero_yield" | "failed" | "skipped";

export interface CapabilityStrategyAttempt {
  source_id: string;
  rank: number;
  composite_score: number;
  outcome: CapabilityStrategyOutcome;
  reason: string;
  yield_count: number;
}

export interface AcquisitionDecision {
  capability: string;
  decided_at: string;
  attempts: CapabilityStrategyAttempt[];
  selected_source_ids: string[];
  succeeded: boolean;
}

// --- discovery_report.json / discovery_metrics.json / endpoint_candidates.json
// (research/data/discovery/, written by the weekly Discovery workflow --
// see docs/DATA_ACQUISITION.md's "Discovery workflow" section. Absent
// until the first scheduled/workflow_dispatch run's PR merges -- an
// honest empty state, not a missing feature, until then.) ---

export interface DiscoveryOutcome {
  source_id: string;
  previous_status: string;
  current_status: string;
  discovered_endpoints: string[];
  verification_result: string;
  reason_for_failure: string | null;
  evidence: string[];
  recommendation: string;
  confidence: number;
  from_cache: boolean;
  verified_at: string;
}

export interface EndpointCandidate {
  source_id: string;
  discovered_url: string;
  access_method_guess: string;
  legality_verdict: string;
  robots_allows: boolean | null;
  stability_score: number;
  historical_score: number;
  composite_score: number;
  selected: boolean;
}

export interface DiscoveryMetrics {
  started_at: string;
  finished_at: string;
  duration_seconds: number;
  sources_in_report: number;
  sources_checked_fresh_this_run: number;
  sources_served_from_cache: number;
  sources_verified_reachable: number;
  by_verification_result: Record<string, number>;
  average_confidence_verified: number | null;
}

// --- runtime_status.json (same shape as one RunRecord) ---
export type RuntimeStatus = RunRecord;

// --- dashboard_metrics.json ---

export interface DashboardMetrics {
  generated_at: string;
  dashboard_dir: string;
  artifacts: Record<string, number>;
  total_artifacts: number;
}

// --- mission_status.json ---

export interface MissionStatus {
  generated_at: string;
  pipeline_status: StageStatus;
  pipeline_version: string;
  last_successful_pipeline_id: string | null;
  last_successful_pipeline_at: string | null;
  last_failed_pipeline_id: string | null;
  last_failed_pipeline_at: string | null;
  current_execution_mode: string;
  execution_duration_seconds: number;
  artifacts_produced: Record<string, number>;
  knowledge_updated: number;
  genome_updated: number;
  total_executions: number;
}

// --- execution_report.json ---

export type StageName =
  | "entrypoint"
  | "source_registry"
  | "discovery_engine"
  | "collector_selection"
  | "collector_execution"
  | "raw_archive"
  | "canonical_transformation"
  | "validation"
  | "event_platform"
  | "market_memory"
  | "knowledge_base"
  | "research_pipeline"
  | "genome"
  | "investment_case_generator"
  | "dashboard_artifact_generator"
  | "mission_control_update"
  | "execution_report";

export type StageStatus = "succeeded" | "partial" | "failed" | "skipped";

export interface StageResult {
  name: StageName;
  status: StageStatus;
  started_at: string;
  completed_at: string;
  duration_seconds: number;
  detail: string;
  error: string | null;
  warnings: string[];
}

export interface ExecutionReport {
  id: string;
  version: number;
  pipeline_version: string;
  execution_mode: string;
  run_dates: string[];
  started_at: string;
  completed_at: string;
  duration_seconds: number;
  overall_status: StageStatus;
  stages: StageResult[];
  artifacts_generated: Record<string, number>;
  errors: string[];
  warnings: string[];
  skipped_stages: string[];
  knowledge_before: number;
  knowledge_after: number;
  genome_before: number;
  genome_after: number;
  events_before: number;
  events_after: number;
}

// --- genes.json / Gene ---

export type GeneStatus = "promoted" | "monitoring" | "replaced" | "retired";

export interface Gene {
  id: string;
  version: number;
  knowledge_id: string;
  generation: number;
  parent_gene_ids: string[];
  child_gene_ids: string[];
  mutation_notes: string;
  evidence: string[];
  performance_history: PerformanceRecord[];
  status: GeneStatus;
  retired_at: string | null;
  retirement_reason: string | null;
  provenance: Provenance;
}

// --- papers.json / ResearchPaper ---

export interface ResearchPaper {
  id: string;
  version: number;
  title: string;
  gene_id: string;
  knowledge_id: string;
  hypothesis_id: string;
  problem: string;
  observation: string;
  methodology: string;
  dataset: string;
  experiments: string;
  evidence: string;
  results: string;
  limitations: string;
  conclusion: string;
  future_work: string;
  published_at: string;
  provenance: Provenance;
}

// --- hypotheses.json / Hypothesis ---

export interface GateSpec {
  name: string;
  order: number;
}

export interface HypothesisStageResult {
  stage_name: string;
  passed: boolean;
  evaluated_at: string;
  notes: string;
  metrics: Record<string, number>;
}

export interface Hypothesis {
  id: string;
  version: number;
  statement: string;
  created_by: string;
  created_at: string;
  horizon: Horizon;
  affected_assets: string[];
  provenance: Provenance;
  pipeline: GateSpec[];
  stage_index: number;
  stage_history: HypothesisStageResult[];
}

// --- knowledge_graph.json ---

export type NodeType =
  | "company"
  | "sector"
  | "market"
  | "event"
  | "hypothesis"
  | "experiment"
  | "feature"
  | "gene"
  | "research_paper"
  | "prediction"
  | "recommendation"
  | "knowledge"
  | "dataset_snapshot"
  | "research_finding"
  | "macro_series";

export interface GraphNode {
  id: string;
  version: number;
  node_type: NodeType;
  label: string;
  metadata: Record<string, unknown>;
}

export interface GraphEdge {
  id: string;
  version: number;
  source_id: string;
  source_type: NodeType;
  target_id: string;
  target_type: NodeType;
  relationship: string;
  metadata: Record<string, unknown>;
}

export interface KnowledgeGraphData {
  nodes: GraphNode[];
  edges: GraphEdge[];
}

// --- financial_statements.json / FinancialStatementLineItem ---

export interface FinancialStatementLineItem {
  ticker: string;
  period_end_date: string;
  period_type: string;
  statement_type: string;
  line_item: string;
  value: number;
  currency: string;
}

export interface TickerFinancialCoverage {
  ticker: string;
  covered: boolean;
  latest_period_end_date: string | null;
  present_items: string[];
  missing_items: string[];
}

export interface FinancialCoverageReport {
  as_of: string;
  universe_count: number;
  covered_count: number;
  coverage_percent: number;
  complete: boolean;
  required_latest_items: string[];
  tickers: TickerFinancialCoverage[];
}

// --- market_breadth.json ---

export interface MarketBreadthReport {
  as_of: string;
  universe_count: number;
  tickers_with_price_data: number;
  advancers: number;
  decliners: number;
  unchanged: number;
  advance_decline_ratio: number | null;
  average_daily_return_pct: number | null;
  tickers_with_volume_data: number;
  tickers_above_average_volume: number;
  tickers_below_average_volume: number;
}

// --- market_regime.json / MarketRegimeReport ---

export type MarketTrend = "bullish" | "bearish" | "neutral";
export type VolatilityLevel = "low" | "elevated" | "high";

export interface MarketRegimeReport {
  as_of: string;
  lookback_days: number;
  tickers_with_sufficient_data: number;
  trading_days_observed: number;
  cumulative_return_pct: number | null;
  daily_volatility_pct: number | null;
  trend: MarketTrend;
  volatility: VolatilityLevel;
  reasons: string[];
}

// --- source_metrics.json ---

export interface ReputationScore {
  availability: number | null;
  accuracy: number | null;
  freshness: number | null;
  coverage: number | null;
  latency: number | null;
  correction_rate: number | null;
  duplicate_rate: number | null;
  schema_stability: number | null;
  historical_usefulness: number | null;
  composite: number | null;
  observations: number;
}

export interface SourceMetricsRow {
  source_id: string;
  name: string;
  category: SourceCategory;
  runs_total: number;
  first_run_at: string | null;
  last_run_at: string | null;
  reputation: ReputationScore | null;
}

export interface SourceSpec {
  id: string;
  version: number;
  name: string;
  category: SourceCategory;
  country: string;
  access_method: AccessMethod;
  status: SourceStatus;
  legal_use_status: "cleared" | "research_only" | "review_required" | "blocked";
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
  integrated_via: string | null;
  integrated_capabilities: string[];
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
  evidence_tier: EvidenceTier;
  notes: string;
}

// --- decision_service / PositionAwareDecision (POST /decisions, live-computed --
// see api/src/routes/decisions.ts; not a static dashboard artifact, so only
// ApiProvider can serve it -- see Portfolio.tsx/CIODesk.tsx for the static-mode gap state) ---

export type PositionAction =
  | "buy"
  | "increase_position"
  | "hold"
  | "reduce_position"
  | "exit"
  | "no_action";

export interface PositionInput {
  held: boolean;
  current_weight?: number;
  average_cost?: number | null;
}

export interface PositionAwareDecision {
  ticker: string;
  as_of: string;
  action: PositionAction;
  target_weight: number;
  current_weight: number;
  horizon: Horizon;
  confidence: number;
  opportunity_score: number;
  expected_return: number | null;
  expected_risk: number | null;
  investment_thesis: string;
  key_risks: string[];
  contradicting_evidence: string[];
  active_catalysts: string[];
  monitoring_events: string[];
  expected_review_date: string | null;
  abstained: boolean;
  reasons: string[];
  explanation: Explanation;
  provenance: Provenance;
}

// --- portfolio_summary.json / dashboard.portfolio_summary.PortfolioSummaryReport ---

export interface ConcentrationCheck {
  herfindahl_index: number;
  status: "diversified" | "concentrated";
  max_position_weight: number;
  max_position_ticker: string | null;
  top_3_weight: number;
}

export interface SectorExposure {
  sector: string;
  weight: number;
  tickers: string[];
}

export interface PortfolioSummaryReport {
  as_of: string;
  is_live_portfolio: boolean;
  position_count: number;
  cash_weight: number;
  invested_weight: number;
  weights_reconcile: boolean;
  expected_return: number | null;
  expected_risk: number | null;
  concentration: ConcentrationCheck;
  sector_exposures: SectorExposure[];
  max_sector_weight: number | null;
  sector_concentration_status: "diversified" | "concentrated" | "not_evaluated";
  liquidity_violations: string[];
  decision_conflicts: string[];
}

// --- warnings.json / dashboard.monitoring.MonitoringWarningsReport ---

export type WarningCategory =
  | "broken_thesis"
  | "macro_risk_increased"
  | "catalyst_expired"
  | "liquidity_deterioration"
  | "portfolio_concentration"
  | "review_required";

export type WarningSeverity = "info" | "warning" | "critical";

export interface MonitoringWarning {
  category: WarningCategory;
  severity: WarningSeverity;
  ticker: string | null;
  title: string;
  detail: string;
}

export interface MonitoringWarningsReport {
  as_of: string;
  warnings: MonitoringWarning[];
}

// --- committee_summary.json / dashboard.committee_summary.CommitteeSummaryReport ---

export interface CommitteeOpinion {
  committee: string;
  stance: string;
  agreement_rate: number | null;
  decisive_rate: number | null;
  tickers_present: number;
  note: string;
}

export interface CommitteeSummaryReport {
  as_of: string;
  tickers_evaluated: number;
  opinions: CommitteeOpinion[];
}

// --- capital_allocation / CapitalAllocationEngine (POST /capital-allocation, live-computed --
// see data/DataProvider.ts's postCapitalAllocation; not a static dashboard artifact, same
// reason as PositionAwareDecision -- there is nothing to rank/recycle without a real portfolio) ---

export interface RankedOpportunity {
  rank: number;
  ticker: string;
  opportunity_score: number;
  action: PositionAction;
  target_weight: number;
  current_weight: number;
  confidence: number;
  expected_return: number | null;
  expected_risk: number | null;
  is_new_position: boolean;
}

export interface CapitalSource {
  ticker: string | null;
  amount: number;
}

export interface CapitalFlow {
  from_ticker: string | null;
  to_ticker: string | null;
  amount: number;
}

export interface CapitalQueueEntry {
  ticker: string;
  priority: number;
  action: PositionAction;
  target_weight: number;
  current_weight: number;
  capital_delta: number;
  expected_contribution: number | null;
  marginal_benefit: number;
  marginal_risk: number | null;
  capital_sources: CapitalSource[];
  required_action: string;
  opportunity_cost_note: string;
}

export interface CapitalRelease {
  ticker: string;
  amount: number;
  destinations: CapitalSource[];
}

export interface OpportunityCostHighlight {
  ticker: string;
  opportunity_score: number;
  reason: string;
}

export interface AllocationChange {
  ticker: string;
  action: PositionAction;
  current_weight: number;
  target_weight: number;
  capital_delta: number;
}

export interface CashWaiting {
  idle_cash_before: number;
  idle_cash_after: number;
  reason: string;
}

export interface CapitalAllocationPlan {
  as_of: string;
  ranking: RankedOpportunity[];
  queue: CapitalQueueEntry[];
  capital_released_today: CapitalRelease[];
  capital_recycled: CapitalFlow[];
  best_new_opportunities: RankedOpportunity[];
  highest_opportunity_cost: OpportunityCostHighlight[];
  allocation_changes: AllocationChange[];
  cash_waiting: CashWaiting;
  explanation: Explanation;
  provenance: Provenance;
}

// --- shadow_fund (GET /shadow-fund, GET /shadow-fund-history) -- the
// persistent virtual-portfolio state produced by shadow_fund/engine.py as
// a stage inside `agx run`, never computed on demand. See
// contracts/shadow_fund.schema.json / shadow_fund_history.schema.json. ---

export interface ShadowFundPosition {
  ticker: string;
  entry_date: string;
  average_cost: number;
  weight: number;
  target_weight: number;
  market_price: number;
  market_value: number;
  unrealized_pnl_pct: number | null;
  horizon: string;
  confidence: number;
  investment_thesis: string;
}

export interface ShadowFundClosedPosition {
  ticker: string;
  entry_date: string;
  exit_date: string;
  average_cost: number;
  exit_price: number;
  realized_pnl_pct: number;
}

export interface ShadowFundTransaction {
  id: string;
  date: string;
  ticker: string;
  action: PositionAction;
  weight_before: number;
  weight_after: number;
  weight_delta: number;
  price: number;
  cash_delta: number;
  transaction_cost: number;
  investment_thesis: string;
  confidence: number;
  provenance: Provenance;
}

export interface ShadowFundRiskMetrics {
  volatility_annualized_pct: number | null;
  max_drawdown_pct: number | null;
  sharpe_like_ratio: number | null;
  herfindahl_index: number | null;
  largest_position_pct: number | null;
  sample_days: number;
  sample_status: string;
}

export interface ShadowFundAttributionEntry {
  ticker: string;
  contribution_pct_of_total_gain: number | null;
  status: string;
}

export interface ShadowFundNavPoint {
  date: string;
  nav: number;
  cash: number;
  cash_pct: number;
  invested_pct: number;
  daily_return_pct: number | null;
  cumulative_return_pct: number;
  benchmark_nav: number;
  benchmark_cumulative_return_pct: number;
}

export interface ShadowFundPublicState {
  date: string;
  inception_date: string;
  nav: number;
  cash: number;
  cash_pct: number;
  invested_pct: number;
  daily_return_pct: number | null;
  cumulative_return_pct: number;
  benchmark_ticker: string;
  benchmark_nav: number;
  benchmark_cumulative_return_pct: number;
  excess_return_pct: number;
  open_positions: ShadowFundPosition[];
  closed_positions: ShadowFundClosedPosition[];
  transactions: ShadowFundTransaction[];
  capital_allocation_plan: CapitalAllocationPlan | null;
  risk: ShadowFundRiskMetrics;
  attribution: ShadowFundAttributionEntry[];
  provenance: Provenance;
}

export interface ShadowFundHistory {
  nav_series: ShadowFundNavPoint[];
  transactions: ShadowFundTransaction[];
}
