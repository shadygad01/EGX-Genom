// Mirrors agx_research.knowledge.schema.KnowledgeObject (research/src/agx_research/knowledge/schema.py).
// This is a read-only view type — the API never constructs or mutates knowledge objects,
// it only serves what the Python research engine has already promoted and persisted.
//
// Kept in sync with contracts/knowledge_object.schema.json (regenerated via
// `uv run python research/scripts/export_schemas.py`) — CI fails if that file drifts
// from the pydantic schema, which is the forcing function to update this file too.

export type Horizon = "micro" | "swing" | "investment";

export type KnowledgeStatus = "promoted" | "monitoring" | "retired";

export interface PerformanceRecord {
  as_of: string;
  realized_return: number;
  notes: string;
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
