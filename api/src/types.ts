// Mirrors agx_research.knowledge.schema.KnowledgeObject (research/src/agx_research/knowledge/schema.py).
// This is a read-only view type — the API never constructs or mutates knowledge objects,
// it only serves what the Python research engine has already promoted and persisted.

export type Horizon = "micro" | "swing" | "investment";

export type KnowledgeStatus = "promoted" | "monitoring" | "retired";

export interface PerformanceRecord {
  as_of: string;
  realized_return: number;
  notes: string;
}

export interface KnowledgeObject {
  id: string;
  version: number;
  discovery_date: string;
  creator_agent: string;
  supporting_evidence: string[];
  confidence: number;
  statistical_strength: number;
  economic_explanation: string;
  affected_assets: string[];
  horizon: Horizon;
  expected_return: number;
  expected_risk: number;
  status: KnowledgeStatus;
  performance_history: PerformanceRecord[];
  retired_at: string | null;
  retirement_reason: string | null;
}
