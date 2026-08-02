import { useState } from "react";
import { useTranslation } from "react-i18next";
import { Badge, type BadgeVariant } from "../components/primitives/Badge";
import { Card } from "../components/primitives/Card";
import { DataTable } from "../components/primitives/DataTable";
import { Meter } from "../components/primitives/Meter";
import { Section } from "../components/primitives/Section";
import { StatTile } from "../components/primitives/StatTile";
import { EmptyState, ErrorState, LoadingState } from "../components/primitives/States";
import { useArtifact } from "../hooks/useArtifact";
import { useEnumLabel } from "../hooks/useEnumLabel";
import { useFormatters } from "../hooks/useFormatters";
import { formatPercent } from "../lib/format";
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

const REPUTATION_DIMENSIONS = [
  ["availability", "availability"],
  ["coverage", "coverage"],
  ["freshness", "freshness"],
  ["latency", "latency"],
  ["accuracy", "accuracy"],
  ["schema_stability", "schemaStability"],
  ["correction_rate", "correctionRate"],
  ["duplicate_rate", "duplicateRate"],
  ["historical_usefulness", "historicalUsefulness"],
] as const;

/** Every active decision source -- health, availability, coverage,
 * freshness, latency, qualification, validation score, and (for a still-
 * PLANNED source) the weekly Discovery workflow's own evidenced attempt to
 * verify a real endpoint -- joined across the source registry, source
 * reputation metrics, the most recent collector run, and the discovery
 * report. */
export function SourceIntelligence() {
  const { t } = useTranslation("sourceIntelligence");
  const label = useEnumLabel();
  const { formatDate } = useFormatters();
  const sourceRegistry = useArtifact((p) => p.getSourceRegistry());
  const sourceMetrics = useArtifact((p) => p.getSourceMetrics());
  const collectorStatus = useArtifact((p) => p.getCollectorStatus());
  const discoveryReport = useArtifact((p) => p.getDiscoveryReport());
  const [selectedId, setSelectedId] = useState<string | null>(null);

  const metricsById = new Map((sourceMetrics.data ?? []).map((m) => [m.source_id, m]));
  const collectorById = new Map((collectorStatus.data ?? []).map((c) => [c.source_id, c]));
  const discoveryById = new Map((discoveryReport.data ?? []).map((d) => [d.source_id, d]));

  // Disabled/retired tombstones remain in the internal registry so a dead or
  // legally blocked source is not accidentally rediscovered. They are not an
  // investable-data source and therefore do not belong on the CIO workspace.
  const sorted = [...(sourceRegistry.data ?? [])]
    .filter((source) => source.status !== "disabled" && source.activation_status !== "retired")
    .sort((a, b) => a.priority - b.priority);
  const selected = sorted.find((s) => s.id === selectedId) ?? sorted[0] ?? null;
  const selectedMetrics = selected ? metricsById.get(selected.id) : undefined;
  const selectedCollector = selected ? collectorById.get(selected.id) : undefined;
  const selectedDiscovery = selected ? discoveryById.get(selected.id) : undefined;
  const effectiveCollected = selectedCollector?.status === "COLLECTED" || selectedCollector?.status === "DEGRADED" || selectedCollector?.status === "STANDBY";

  return (
    <Section title={t("title")} description={t("description")}>
      {sourceRegistry.loading && <LoadingState rows={4} />}
      {sourceRegistry.error && <ErrorState detail={sourceRegistry.error.message} onRetry={sourceRegistry.reload} />}

      {!sourceRegistry.loading && !sourceRegistry.error && (
        <div className={styles.layout}>
          <Card dense>
            <DataTable
              rows={sorted}
              getRowKey={(s) => s.id}
              onRowClick={(s) => setSelectedId(s.id)}
              emptyTitle={t("emptyTitle")}
              columns={[
                { key: "name", header: t("columns.source"), render: (s) => s.name },
                { key: "category", header: t("columns.category"), render: (s) => label("sourceCategory", s.category) },
                {
                  key: "status",
                  header: t("columns.status"),
                  render: (s) =>
                    collectorById.get(s.id)?.status === "COLLECTED" ? (
                      <Badge variant="positive">{t("columns.integratedCollected")}</Badge>
                    ) : collectorById.get(s.id)?.status === "STANDBY" ? (
                      <Badge variant="accent">{t("columns.integratedStandby")}</Badge>
                    ) : (
                      <Badge variant={STATUS_VARIANT[s.status]}>{label("sourceStatus", s.status)}</Badge>
                    ),
                },
                { key: "integration", header: t("columns.integration"), render: (s) => s.integrated_via ? t("columns.integratedVia", { name: s.integrated_via }) : (s.collector ?? "—") },
                { key: "lifecycle", header: t("columns.lifecycle"), render: (s) => <Badge variant={LIFECYCLE_VARIANT[s.lifecycle_state]}>{label("lifecycleState", s.lifecycle_state)}</Badge> },
                {
                  key: "health",
                  header: t("columns.health"),
                  render: (s) =>
                    collectorById.get(s.id)?.status === "STANDBY" ? (
                      <Badge variant="accent">{t("columns.notMeasured")}</Badge>
                    ) : (
                      <Badge variant={HEALTH_VARIANT[s.health_status]}>{label("healthStatus", s.health_status)}</Badge>
                    ),
                },
                {
                  key: "quality",
                  header: t("columns.validationScore"),
                  align: "right",
                  render: (s) => (s.data_quality_score != null ? <span className="num">{formatPercent(s.data_quality_score)}</span> : "—"),
                },
              ]}
            />
          </Card>

          <Card title={selected ? selected.name : t("detail.title")} dense>
            {!selected && <EmptyState title={t("detail.emptyTitle")} detail={t("detail.emptyDetail")} />}
            {selected && (
              <div>
                <div className={styles.detailHeader}>{selected.name}</div>
                <div className={styles.detailMeta}>
                  {t("detail.priorityMeta", { category: label("sourceCategory", selected.category), country: selected.country, priority: selected.priority })}
                </div>

                <div className={styles.badgeRow}>
                  <Badge variant={effectiveCollected ? (selectedCollector?.status === "COLLECTED" ? "positive" : selectedCollector?.status === "STANDBY" ? "accent" : "warning") : STATUS_VARIANT[selected.status]}>
                    {effectiveCollected ? label("collectorStatus", selectedCollector!.status) : label("sourceStatus", selected.status)}
                  </Badge>
                  <Badge variant={LIFECYCLE_VARIANT[selected.lifecycle_state]}>{label("lifecycleState", selected.lifecycle_state)}</Badge>
                  {selectedCollector?.status === "STANDBY" ? (
                    <Badge variant="accent">{t("columns.notMeasured")}</Badge>
                  ) : (
                    <Badge variant={HEALTH_VARIANT[selected.health_status]}>{label("healthStatus", selected.health_status)}</Badge>
                  )}
                  <Badge variant={ACTIVATION_VARIANT[selected.activation_status]}>{label("activationStatus", selected.activation_status)}</Badge>
                </div>

                <div className={styles.grid}>
                  <StatTile label={t("detail.discoveredFirstRun")} value={selectedMetrics?.first_run_at ? formatDate(selectedMetrics.first_run_at) : "—"} />
                  <StatTile label={t("detail.lastRun")} value={selectedMetrics?.last_run_at ? formatDate(selectedMetrics.last_run_at) : "—"} />
                  <StatTile label={t("detail.totalRuns")} value={selectedMetrics?.runs_total ?? 0} />
                  <StatTile label={t("detail.documentsLastRun")} value={selectedCollector?.documents_fetched ?? "—"} />
                  <StatTile label={t("detail.integratedVia")} value={selected.integrated_via ?? selected.collector ?? "—"} />
                  <StatTile label={t("detail.decisionCapabilities")} value={selected.integrated_capabilities.length ? selected.integrated_capabilities.map((c) => label("capability", c)).join(", ") : "—"} />
                  <StatTile label={t("detail.expectedLatency")} value={selected.expected_latency || "—"} />
                  <StatTile
                    label={t("detail.validationScore")}
                    value={selected.data_quality_score != null ? formatPercent(selected.data_quality_score) : "—"}
                  />
                  <StatTile
                    label={t("detail.compositeReputation")}
                    value={selectedMetrics?.reputation?.composite != null ? formatPercent(selectedMetrics.reputation.composite) : "—"}
                  />
                </div>

                <div className={styles.block}>
                  <div className={styles.blockTitle}>{t("reputation.title")}</div>
                  {!selectedMetrics?.reputation ? (
                    <EmptyState title={t("reputation.emptyTitle")} detail={t("reputation.emptyDetail")} />
                  ) : (
                    <>
                      {REPUTATION_DIMENSIONS.map(([key, labelKey]) => {
                        const value = selectedMetrics.reputation![key];
                        return (
                          <div key={key} className={styles.meterRow}>
                            <span className={styles.meterLabel}>{t(`reputation.${labelKey}`)}</span>
                            <span className={styles.meterTrack}>
                              <Meter value={value ?? 0} label={value != null ? formatPercent(value) : "—"} />
                            </span>
                          </div>
                        );
                      })}
                    </>
                  )}
                </div>

                {selectedDiscovery && (
                  <div className={styles.block}>
                    <div className={styles.blockTitle}>{t("discoveryEvidence.title")}</div>
                    <p className={styles.notes}>
                      {label("discoveryResult", selectedDiscovery.verification_result)}
                      {selectedDiscovery.from_cache ? t("discoveryEvidence.cachedResult") : ""} —{" "}
                      {selectedDiscovery.reason_for_failure ?? t("discoveryEvidence.endpointVerified")}
                    </p>
                    {selectedDiscovery.discovered_endpoints.length > 0 && (
                      <p className={styles.notes}>{t("discoveryEvidence.discovered", { endpoints: selectedDiscovery.discovered_endpoints.join(", ") })}</p>
                    )}
                    {selectedDiscovery.evidence.length > 0 && (
                      <p className={styles.notes}>{t("discoveryEvidence.evidence", { items: selectedDiscovery.evidence.join("; ") })}</p>
                    )}
                    <p className={styles.notes}>{selectedDiscovery.recommendation}</p>
                  </div>
                )}

                {selected.notes && (
                  <div className={styles.block}>
                    <div className={styles.blockTitle}>{t("notes.title")}</div>
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
