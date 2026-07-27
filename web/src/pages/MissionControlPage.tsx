import { useTranslation } from "react-i18next";
import type { TFunction } from "i18next";
import { Badge, type BadgeVariant } from "../components/primitives/Badge";
import { Card } from "../components/primitives/Card";
import { DataTable } from "../components/primitives/DataTable";
import { Section } from "../components/primitives/Section";
import { StatTile } from "../components/primitives/StatTile";
import { EmptyState, ErrorState, LoadingState } from "../components/primitives/States";
import { useArtifact } from "../hooks/useArtifact";
import { useEnumLabel } from "../hooks/useEnumLabel";
import { useFormatters } from "../hooks/useFormatters";
import { formatNumber, formatPercent } from "../lib/format";
import type { CollectorStatusRow, DiscoveryOutcome, GeneStatus, HealthStatus, RunStatus, StageStatus } from "../types";
import styles from "./MissionControlPage.module.css";

const DISCOVERY_RESULT_VARIANT: Record<string, BadgeVariant> = {
  verified_reachable: "positive",
  not_targeted: "neutral",
  no_reachable_domain: "negative",
  homepage_unreachable: "negative",
  no_candidates_discovered: "warning",
  legality_blocked: "warning",
  not_verified: "neutral",
};

const STAGE_VARIANT: Record<StageStatus, BadgeVariant> = {
  succeeded: "positive",
  partial: "warning",
  failed: "negative",
  skipped: "neutral",
};

const RUN_VARIANT: Record<RunStatus, BadgeVariant> = {
  succeeded: "positive",
  failed: "negative",
  skipped_non_trading: "neutral",
};

const HEALTH_VARIANT: Record<HealthStatus, BadgeVariant> = {
  healthy: "positive",
  degraded: "warning",
  down: "negative",
  unknown: "neutral",
};

const STATUS_VARIANT: Record<CollectorStatusRow["status"], BadgeVariant> = {
  COLLECTED: "positive",
  DEGRADED: "warning",
  STANDBY: "accent",
  FAILED: "negative",
  UNAVAILABLE: "neutral",
};

const GENE_VARIANT: Record<GeneStatus, BadgeVariant> = {
  promoted: "positive",
  monitoring: "accent",
  replaced: "warning",
  retired: "neutral",
};

/** `collector_status.json` carries per-record-type counts (price bars,
 * macro observations, news, corporate events, index constituents,
 * financial statement line items) that a single summed "Yield" number
 * otherwise hides -- e.g. a source producing prices but zero news, or
 * vice versa. Only non-zero categories are shown, so a single-purpose
 * source's row stays short. */
function describeYieldBreakdown(row: CollectorStatusRow, t: TFunction<"missionControl">): string {
  const parts: string[] = [
    row.price_bars_written && t("collectors.yieldParts.price", { count: formatNumber(row.price_bars_written) }),
    row.macro_observations_written && t("collectors.yieldParts.macro", { count: formatNumber(row.macro_observations_written) }),
    row.news_items_written && t("collectors.yieldParts.news", { count: formatNumber(row.news_items_written) }),
    row.corporate_events_written && t("collectors.yieldParts.corporateActions", { count: formatNumber(row.corporate_events_written) }),
    row.index_constituents_written && t("collectors.yieldParts.index", { count: formatNumber(row.index_constituents_written) }),
    row.financial_statement_line_items_written &&
      t("collectors.yieldParts.financials", { count: formatNumber(row.financial_statement_line_items_written) }),
  ].filter((part): part is string => Boolean(part));
  return parts.length ? parts.join(" · ") : "—";
}

/** Everything an operator needs to know about the platform itself:
 * current mission status, pipeline health stage-by-stage, collector
 * output, knowledge/genome status, source health, execution history,
 * current blockers, and the weekly Discovery workflow's own verification
 * report -- all composed from existing artifacts. */
export function MissionControlPage() {
  const { t } = useTranslation("missionControl");
  const label = useEnumLabel();
  const { formatDate, formatDateTime } = useFormatters();
  const missionStatus = useArtifact((p) => p.getMissionStatus());
  const executionReport = useArtifact((p) => p.getExecutionReport());
  const systemStatus = useArtifact((p) => p.getSystemStatus());
  const collectorStatus = useArtifact((p) => p.getCollectorStatus());
  const genes = useArtifact((p) => p.getGenes());
  const sourceRegistry = useArtifact((p) => p.getSourceRegistry());
  const runtimeMetrics = useArtifact((p) => p.getRuntimeMetrics());
  const acquisitionDecisions = useArtifact((p) => p.getAcquisitionDecisions());
  const discoveryReport = useArtifact((p) => p.getDiscoveryReport());
  const discoveryMetrics = useArtifact((p) => p.getDiscoveryMetrics());

  const geneCounts = {
    promoted: (genes.data ?? []).filter((g) => g.status === "promoted").length,
    monitoring: (genes.data ?? []).filter((g) => g.status === "monitoring").length,
    replaced: (genes.data ?? []).filter((g) => g.status === "replaced").length,
    retired: (genes.data ?? []).filter((g) => g.status === "retired").length,
  };

  const sourceHealthCounts: Record<HealthStatus, number> = { healthy: 0, degraded: 0, down: 0, unknown: 0 };
  for (const s of sourceRegistry.data ?? []) sourceHealthCounts[s.health_status] += 1;
  const implementedCount = (sourceRegistry.data ?? []).filter((s) => s.status === "implemented").length;
  const collectedCount = (collectorStatus.data ?? []).filter((s) => s.status === "COLLECTED").length;
  const degradedCount = (collectorStatus.data ?? []).filter((s) => s.status === "DEGRADED").length;
  const standbyCount = (collectorStatus.data ?? []).filter((s) => s.status === "STANDBY").length;
  const failedCount = (collectorStatus.data ?? []).filter((s) => s.status === "FAILED").length;
  const unavailableCount = (collectorStatus.data ?? []).filter((s) => s.status === "UNAVAILABLE").length;

  const runHistory = [...(runtimeMetrics.data ?? [])].sort((a, b) => (a.run_date < b.run_date ? 1 : -1));

  return (
    <>
      <Section title={t("missionStatus.title")} description={t("missionStatus.description")}>
        {missionStatus.loading && <LoadingState rows={2} />}
        {missionStatus.error && <ErrorState detail={missionStatus.error.message} onRetry={missionStatus.reload} />}
        {!missionStatus.loading && !missionStatus.error && !missionStatus.data && (
          <EmptyState title={t("missionStatus.emptyTitle")} detail={t("missionStatus.emptyDetail")} />
        )}
        {missionStatus.data && (
          <div className={styles.grid}>
            <StatTile label={t("missionStatus.pipelineStatus")} value={<Badge variant={STAGE_VARIANT[missionStatus.data.pipeline_status]}>{label("stageStatus", missionStatus.data.pipeline_status)}</Badge>} />
            <StatTile label={t("missionStatus.pipelineVersion")} value={<span className="num">{missionStatus.data.pipeline_version}</span>} />
            <StatTile label={t("missionStatus.executionMode")} value={label("executionMode", missionStatus.data.current_execution_mode)} />
            <StatTile label={t("missionStatus.duration")} value={<span className="num">{formatNumber(missionStatus.data.execution_duration_seconds, 2)}s</span>} />
            <StatTile label={t("missionStatus.totalExecutions")} value={missionStatus.data.total_executions} />
            <StatTile label={t("missionStatus.lastSuccessfulRun")} value={formatDate(missionStatus.data.last_successful_pipeline_at)} />
            <StatTile label={t("missionStatus.lastFailedRun")} value={formatDate(missionStatus.data.last_failed_pipeline_at)} />
          </div>
        )}
      </Section>

      <Section title={t("pipelineHealth.title")} description={t("pipelineHealth.description")}>
        {executionReport.loading && <LoadingState rows={3} />}
        {executionReport.error && <ErrorState detail={executionReport.error.message} onRetry={executionReport.reload} />}
        {!executionReport.loading && !executionReport.error && !executionReport.data && (
          <EmptyState title={t("pipelineHealth.emptyTitle")} />
        )}
        {executionReport.data && (
          <DataTable
            rows={executionReport.data.stages}
            getRowKey={(s) => s.name}
            emptyTitle={t("pipelineHealth.emptyTitleStages")}
            columns={[
              { key: "name", header: t("pipelineHealth.stage"), render: (s) => label("stageName", s.name) },
              { key: "status", header: t("pipelineHealth.status"), render: (s) => <Badge variant={STAGE_VARIANT[s.status]}>{label("stageStatus", s.status)}</Badge> },
              { key: "duration", header: t("pipelineHealth.duration"), align: "right", render: (s) => <span className="num">{formatNumber(s.duration_seconds, 2)}s</span> },
              { key: "detail", header: t("pipelineHealth.detail"), render: (s) => s.detail },
              { key: "warnings", header: t("pipelineHealth.warnings"), align: "right", render: (s) => s.warnings.length },
            ]}
          />
        )}
      </Section>

      <div className={styles.twoCol}>
        <Card title={t("knowledgeStatus.title")} subtitle={t("knowledgeStatus.subtitle")}>
          {systemStatus.data ? (
            <div className={styles.grid}>
              <StatTile label={t("knowledgeStatus.total")} value={systemStatus.data.knowledge_objects} />
              {Object.entries(systemStatus.data.by_status).map(([status, count]) => (
                <StatTile key={status} label={label("knowledgeStatus", status)} value={count} />
              ))}
            </div>
          ) : (
            <EmptyState title={t("knowledgeStatus.emptyTitle")} />
          )}
        </Card>

        <Card title={t("genomeStatus.title")} subtitle={t("genomeStatus.subtitle")}>
          {(genes.data ?? []).length === 0 ? (
            <EmptyState title={t("genomeStatus.emptyTitle")} />
          ) : (
            <div className={styles.grid}>
              <StatTile label={t("genomeStatus.total")} value={genes.data!.length} />
              <StatTile label={t("genomeStatus.promoted")} value={geneCounts.promoted} />
              <StatTile label={t("genomeStatus.monitoring")} value={geneCounts.monitoring} />
              <StatTile label={t("genomeStatus.replaced")} value={geneCounts.replaced} />
              <StatTile label={t("genomeStatus.retired")} value={geneCounts.retired} />
            </div>
          )}
        </Card>
      </div>

      <Section title={t("collectors.title")} description={t("collectors.description")}>
        <div className={styles.grid}>
          <StatTile label={t("collectors.catalogued")} value={(sourceRegistry.data ?? []).length} />
          <StatTile label={t("collectors.collected")} value={collectedCount} />
          <StatTile label={t("collectors.degraded")} value={degradedCount} />
          <StatTile label={t("collectors.wiredStandby")} value={standbyCount} />
          <StatTile label={t("collectors.failed")} value={failedCount} />
          <StatTile label={t("collectors.notYetWired")} value={unavailableCount} />
        </div>
        {collectorStatus.loading && <LoadingState rows={3} />}
        {collectorStatus.error && <ErrorState detail={collectorStatus.error.message} onRetry={collectorStatus.reload} />}
        {!collectorStatus.loading && !collectorStatus.error && (
          <DataTable
            rows={collectorStatus.data ?? []}
            getRowKey={(c) => c.source_id}
            emptyTitle={t("collectors.emptyTitle")}
            columns={[
              { key: "source", header: t("collectors.source"), render: (c) => <span className="num">{c.source_id}</span> },
              {
                key: "status",
                header: t("collectors.status"),
                render: (c) => <Badge variant={STATUS_VARIANT[c.status]}>{label("collectorStatus", c.status)}</Badge>,
              },
              {
                key: "health",
                header: t("collectors.health"),
                render: (c) => c.status === "STANDBY"
                  ? <Badge variant="accent">{t("collectors.notMeasured")}</Badge>
                  : (c.health_status ? <Badge variant={HEALTH_VARIANT[c.health_status]}>{label("healthStatus", c.health_status)}</Badge> : "—"),
              },
              {
                key: "connection",
                header: t("collectors.connected"),
                render: (c) => c.status === "STANDBY"
                  ? <Badge variant="neutral">{t("collectors.notRun")}</Badge>
                  : <Badge variant={c.connection_success ? "positive" : "negative"}>{c.connection_success ? t("collectors.yes") : t("collectors.no")}</Badge>,
              },
              {
                key: "parsed",
                header: t("collectors.parsed"),
                render: (c) => c.status === "STANDBY"
                  ? <Badge variant="neutral">{t("collectors.notRun")}</Badge>
                  : <Badge variant={c.parse_success ? "positive" : "negative"}>{c.parse_success ? t("collectors.yes") : t("collectors.no")}</Badge>,
              },
              { key: "yield", header: t("collectors.yield"), align: "right", render: (c) => <span className="num">{formatNumber(c.yield)}</span> },
              { key: "breakdown", header: t("collectors.breakdown"), render: (c) => describeYieldBreakdown(c, t) },
              { key: "events", header: t("collectors.events"), align: "right", render: (c) => <span className="num">{formatNumber(c.events_produced)}</span> },
              { key: "docs", header: t("collectors.documents"), align: "right", render: (c) => <span className="num">{formatNumber(c.documents_fetched)}</span> },
              {
                key: "withheld",
                header: t("collectors.withheld"),
                align: "right",
                render: (c) => (c.batches_withheld > 0 ? <Badge variant="warning">{formatNumber(c.batches_withheld)}</Badge> : "0"),
              },
              { key: "reputation", header: t("collectors.reputation"), align: "right", render: (c) => (c.reputation_score != null ? formatPercent(c.reputation_score) : "—") },
              { key: "quality", header: t("collectors.quality"), align: "right", render: (c) => (c.data_quality_score != null ? formatPercent(c.data_quality_score) : "—") },
              { key: "reason", header: t("collectors.reason"), render: (c) => c.reason ?? "—" },
            ]}
          />
        )}
      </Section>

      <div className={styles.twoCol}>
        <Card title={t("sourceHealth.title")} subtitle={t("sourceHealth.subtitle")}>
          {(sourceRegistry.data ?? []).length === 0 ? (
            <EmptyState title={t("sourceHealth.emptyTitle")} />
          ) : (
            <div className={styles.grid}>
              <StatTile label={t("sourceHealth.implemented")} value={implementedCount} />
              <StatTile label={t("sourceHealth.healthy")} value={sourceHealthCounts.healthy} />
              <StatTile label={t("sourceHealth.degraded")} value={sourceHealthCounts.degraded} />
              <StatTile label={t("sourceHealth.down")} value={sourceHealthCounts.down} />
            </div>
          )}
        </Card>

        <Card title={t("currentBlockers.title")}>
          {!executionReport.data || (executionReport.data.errors.length === 0 && executionReport.data.warnings.length === 0) ? (
            <EmptyState title={t("currentBlockers.emptyTitle")} detail={t("currentBlockers.emptyDetail")} />
          ) : (
            <div className={styles.list}>
              {executionReport.data.errors.map((e, i) => (
                <div key={`e-${i}`} className={styles.listItem}>
                  <Badge variant="negative">{t("currentBlockers.error")}</Badge> {e}
                </div>
              ))}
              {executionReport.data.warnings.map((w, i) => (
                <div key={`w-${i}`} className={styles.listItem}>
                  <Badge variant="warning">{t("currentBlockers.warning")}</Badge> {w}
                </div>
              ))}
            </div>
          )}
        </Card>
      </div>

      <Section title={t("executionHistory.title")} description={t("executionHistory.description")}>
        <DataTable
          rows={runHistory}
          getRowKey={(r) => r.id}
          emptyTitle={t("executionHistory.emptyTitle")}
          columns={[
            { key: "date", header: t("executionHistory.runDate"), render: (r) => formatDate(r.run_date) },
            { key: "status", header: t("executionHistory.status"), render: (r) => <Badge variant={RUN_VARIANT[r.status]}>{label("runStatus", r.status)}</Badge> },
            { key: "hypotheses", header: t("executionHistory.hypotheses"), align: "right", render: (r) => r.hypotheses },
            { key: "promoted", header: t("executionHistory.promoted"), align: "right", render: (r) => r.promoted },
            { key: "completed", header: t("executionHistory.completed"), align: "right", render: (r) => formatDateTime(r.completed_at) },
          ]}
        />
      </Section>

      <Section title={t("acquisitionDecisions.title")} description={t("acquisitionDecisions.description")}>
        {acquisitionDecisions.loading && <LoadingState rows={3} />}
        {acquisitionDecisions.error && (
          <ErrorState detail={acquisitionDecisions.error.message} onRetry={acquisitionDecisions.reload} />
        )}
        {!acquisitionDecisions.loading && !acquisitionDecisions.error && (
          <DataTable
            rows={acquisitionDecisions.data ?? []}
            getRowKey={(d) => d.capability}
            emptyTitle={t("acquisitionDecisions.emptyTitle")}
            columns={[
              { key: "capability", header: t("acquisitionDecisions.capability"), render: (d) => label("capability", d.capability) },
              {
                key: "status",
                header: t("acquisitionDecisions.status"),
                render: (d) => (
                  <Badge variant={d.succeeded ? "positive" : "neutral"}>
                    {d.succeeded ? t("acquisitionDecisions.satisfied") : t("acquisitionDecisions.unsatisfied")}
                  </Badge>
                ),
              },
              {
                key: "selected",
                header: t("acquisitionDecisions.selectedStrategy"),
                render: (d) => (d.selected_source_ids.length ? <span className="num">{d.selected_source_ids.join(", ")}</span> : "—"),
              },
              {
                key: "attempts",
                header: t("acquisitionDecisions.strategiesConsidered"),
                align: "right",
                render: (d) => d.attempts.length,
              },
              {
                key: "top",
                header: t("acquisitionDecisions.topRankedStrategy"),
                render: (d) =>
                  d.attempts[0] ? <span className="num">{d.attempts[0].source_id} ({label("capabilityStrategyOutcome", d.attempts[0].outcome)})</span> : "—",
              },
            ]}
          />
        )}
      </Section>

      <Section title={t("weeklyDiscovery.title")} description={t("weeklyDiscovery.description")}>
        {discoveryMetrics.data && (
          <div className={styles.grid}>
            <StatTile label={t("weeklyDiscovery.sourcesInReport")} value={discoveryMetrics.data.sources_in_report} />
            <StatTile label={t("weeklyDiscovery.verifiedReachable")} value={discoveryMetrics.data.sources_verified_reachable} />
            <StatTile label={t("weeklyDiscovery.checkedFresh")} value={discoveryMetrics.data.sources_checked_fresh_this_run} />
            <StatTile label={t("weeklyDiscovery.servedFromCache")} value={discoveryMetrics.data.sources_served_from_cache} />
            <StatTile label={t("weeklyDiscovery.lastRun")} value={formatDateTime(discoveryMetrics.data.finished_at)} />
          </div>
        )}
        {discoveryReport.loading && <LoadingState rows={3} />}
        {discoveryReport.error && <ErrorState detail={discoveryReport.error.message} onRetry={discoveryReport.reload} />}
        {!discoveryReport.loading && !discoveryReport.error && (
          <DataTable
            rows={discoveryReport.data ?? []}
            getRowKey={(r) => r.source_id}
            emptyTitle={t("weeklyDiscovery.emptyTitle")}
            emptyDetail={t("weeklyDiscovery.emptyDetail")}
            columns={[
              { key: "source", header: t("weeklyDiscovery.source"), render: (r: DiscoveryOutcome) => <span className="num">{r.source_id}</span> },
              {
                key: "result",
                header: t("weeklyDiscovery.result"),
                render: (r) => (
                  <Badge variant={DISCOVERY_RESULT_VARIANT[r.verification_result] ?? "neutral"}>
                    {label("discoveryResult", r.verification_result)}
                  </Badge>
                ),
              },
              { key: "endpoint", header: t("weeklyDiscovery.endpoint"), render: (r) => <span className="num">{r.discovered_endpoints[0] ?? "—"}</span> },
              { key: "confidence", header: t("weeklyDiscovery.confidence"), align: "right", render: (r) => formatPercent(r.confidence) },
              {
                key: "cache",
                header: t("weeklyDiscovery.cache"),
                render: (r) => (r.from_cache ? <Badge variant="accent">{t("weeklyDiscovery.cached")}</Badge> : <Badge variant="neutral">{t("weeklyDiscovery.fresh")}</Badge>),
              },
              { key: "recommendation", header: t("weeklyDiscovery.recommendation"), render: (r) => r.recommendation },
            ]}
          />
        )}
      </Section>
    </>
  );
}
