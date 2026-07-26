import { useState } from "react";
import { Badge, type BadgeVariant } from "../components/primitives/Badge";
import { Card } from "../components/primitives/Card";
import { DataTable } from "../components/primitives/DataTable";
import { Meter } from "../components/primitives/Meter";
import { Section } from "../components/primitives/Section";
import { StatTile } from "../components/primitives/StatTile";
import { EmptyState, ErrorState, LoadingState } from "../components/primitives/States";
import { useArtifact } from "../hooks/useArtifact";
import { formatDate, formatPercent, titleCase } from "../lib/format";
import type { ActivationStatus, HealthStatus, LifecycleState, SourceStatus } from "../types";
import styles from "./SourceIntelligence.module.css";

const HEALTH_VARIANT: Record<HealthStatus, BadgeVariant> = {
  healthy: "positive",
  degraded: "warning",
  down: "negative",
  unknown: "neutral",
};

const LIFECYCLE_VARIANT: Record<LifecycleState, BadgeVariant> = {
  candidate: "neutral",
  quarantine: "negative",
  evaluation: "warning",
  trusted: "accent",
  core: "positive",
};

const STATUS_VARIANT: Record<SourceStatus, BadgeVariant> = {
  implemented: "positive",
  planned: "neutral",
  needs_key: "warning",
  tos_review: "warning",
  disabled: "negative",
};

const ACTIVATION_VARIANT: Record<ActivationStatus, BadgeVariant> = {
  active: "positive",
  paused: "warning",
  retired: "neutral",
};

/** Every source AGX knows about -- health, availability, coverage,
 * freshness, latency, qualification, and validation score, joined across
 * the source registry, source reputation metrics, and the most recent
 * collector run. */
export function SourceIntelligence() {
  const sourceRegistry = useArtifact((p) => p.getSourceRegistry());
  const sourceMetrics = useArtifact((p) => p.getSourceMetrics());
  const collectorStatus = useArtifact((p) => p.getCollectorStatus());
  const [selectedId, setSelectedId] = useState<string | null>(null);

  const metricsById = new Map((sourceMetrics.data ?? []).map((m) => [m.source_id, m]));
  const collectorById = new Map((collectorStatus.data ?? []).map((c) => [c.source_id, c]));

  const sorted = [...(sourceRegistry.data ?? [])].sort((a, b) => a.priority - b.priority);
  const selected = sorted.find((s) => s.id === selectedId) ?? sorted[0] ?? null;
  const selectedMetrics = selected ? metricsById.get(selected.id) : undefined;
  const selectedCollector = selected ? collectorById.get(selected.id) : undefined;
  const effectiveCollected = selectedCollector?.status === "COLLECTED" || selectedCollector?.status === "DEGRADED" || selectedCollector?.status === "STANDBY";

  return (
    <Section
      title="Source Intelligence"
      description="Health, availability, coverage, freshness, latency, qualification, and validation score for every source AGX tracks."
    >
      {sourceRegistry.loading && <LoadingState rows={4} />}
      {sourceRegistry.error && <ErrorState detail={sourceRegistry.error.message} onRetry={sourceRegistry.reload} />}

      {!sourceRegistry.loading && !sourceRegistry.error && (
        <div className={styles.layout}>
          <Card dense>
            <DataTable
              rows={sorted}
              getRowKey={(s) => s.id}
              onRowClick={(s) => setSelectedId(s.id)}
              emptyTitle="No sources registered yet"
              columns={[
                { key: "name", header: "Source", render: (s) => s.name },
                { key: "category", header: "Category", render: (s) => titleCase(s.category) },
                { key: "status", header: "Status", render: (s) => collectorById.get(s.id)?.status === "COLLECTED" ? <Badge variant="positive">Integrated / Collected</Badge> : collectorById.get(s.id)?.status === "STANDBY" ? <Badge variant="accent">Integrated / Standby</Badge> : <Badge variant={STATUS_VARIANT[s.status]}>{titleCase(s.status)}</Badge> },
                { key: "integration", header: "Integration", render: (s) => s.integrated_via ? `Via ${s.integrated_via}` : (s.collector ?? "—") },
                { key: "lifecycle", header: "Lifecycle", render: (s) => <Badge variant={LIFECYCLE_VARIANT[s.lifecycle_state]}>{titleCase(s.lifecycle_state)}</Badge> },
                { key: "health", header: "Health", render: (s) => collectorById.get(s.id)?.status === "STANDBY" ? <Badge variant="accent">Not Measured</Badge> : <Badge variant={HEALTH_VARIANT[s.health_status]}>{titleCase(s.health_status)}</Badge> },
                {
                  key: "quality",
                  header: "Validation Score",
                  align: "right",
                  render: (s) => (s.data_quality_score != null ? formatPercent(s.data_quality_score) : "—"),
                },
              ]}
            />
          </Card>

          <Card title={selected ? selected.name : "Source Detail"} dense>
            {!selected && <EmptyState title="No source selected" detail="Select a row to see its full health and reputation detail." />}
            {selected && (
              <div>
                <div className={styles.detailHeader}>{selected.name}</div>
                <div className={styles.detailMeta}>
                  {titleCase(selected.category)} · {selected.country} · priority {selected.priority}
                </div>

                <div className={styles.badgeRow}>
                  <Badge variant={effectiveCollected ? (selectedCollector?.status === "COLLECTED" ? "positive" : selectedCollector?.status === "STANDBY" ? "accent" : "warning") : STATUS_VARIANT[selected.status]}>
                    {effectiveCollected ? titleCase(selectedCollector!.status) : titleCase(selected.status)}
                  </Badge>
                  <Badge variant={LIFECYCLE_VARIANT[selected.lifecycle_state]}>{titleCase(selected.lifecycle_state)}</Badge>
                  {selectedCollector?.status === "STANDBY"
                    ? <Badge variant="accent">Not Measured</Badge>
                    : <Badge variant={HEALTH_VARIANT[selected.health_status]}>{titleCase(selected.health_status)}</Badge>}
                  <Badge variant={ACTIVATION_VARIANT[selected.activation_status]}>{titleCase(selected.activation_status)}</Badge>
                </div>

                <div className={styles.grid}>
                  <StatTile label="Discovered / First Run" value={selectedMetrics?.first_run_at ? formatDate(selectedMetrics.first_run_at) : "—"} />
                  <StatTile label="Last Run" value={selectedMetrics?.last_run_at ? formatDate(selectedMetrics.last_run_at) : "—"} />
                  <StatTile label="Total Runs" value={selectedMetrics?.runs_total ?? 0} />
                  <StatTile label="Documents (Last Run)" value={selectedCollector?.documents_fetched ?? "—"} />
                  <StatTile label="Integrated Via" value={selected.integrated_via ?? selected.collector ?? "—"} />
                  <StatTile label="Decision Capabilities" value={selected.integrated_capabilities.length ? selected.integrated_capabilities.map(titleCase).join(", ") : "—"} />
                  <StatTile label="Expected Latency" value={selected.expected_latency || "—"} />
                  <StatTile
                    label="Validation Score"
                    value={selected.data_quality_score != null ? formatPercent(selected.data_quality_score) : "—"}
                  />
                </div>

                <div className={styles.block}>
                  <div className={styles.blockTitle}>Reputation Dimensions</div>
                  {!selectedMetrics?.reputation ? (
                    <EmptyState title="No reputation data yet" detail="Reputation dimensions populate once this source has run at least once." />
                  ) : (
                    <>
                      {(
                        [
                          ["availability", "Availability"],
                          ["coverage", "Coverage"],
                          ["freshness", "Freshness"],
                          ["latency", "Latency"],
                          ["accuracy", "Accuracy"],
                          ["schema_stability", "Schema Stability"],
                        ] as const
                      ).map(([key, label]) => {
                        const value = selectedMetrics.reputation![key];
                        return (
                          <div key={key} className={styles.meterRow}>
                            <span className={styles.meterLabel}>{label}</span>
                            <span className={styles.meterTrack}>
                              <Meter value={value ?? 0} label={value != null ? formatPercent(value) : "—"} />
                            </span>
                          </div>
                        );
                      })}
                    </>
                  )}
                </div>

                {selected.notes && (
                  <div className={styles.block}>
                    <div className={styles.blockTitle}>Notes</div>
                    <p className={styles.notes}>{selected.notes}</p>
                  </div>
                )}
              </div>
            )}
          </Card>
        </div>
      )}
    </Section>
  );
}
