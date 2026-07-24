import { Badge, type BadgeVariant } from "../components/primitives/Badge";
import { Card } from "../components/primitives/Card";
import { DataTable } from "../components/primitives/DataTable";
import { Section } from "../components/primitives/Section";
import { StatTile } from "../components/primitives/StatTile";
import { EmptyState, ErrorState, LoadingState } from "../components/primitives/States";
import { useArtifact } from "../hooks/useArtifact";
import { formatDate, formatDateTime, formatNumber, formatPercent, titleCase } from "../lib/format";
import type { CollectorStatusRow, GeneStatus, HealthStatus, RunStatus, StageStatus } from "../types";
import styles from "./MissionControlPage.module.css";

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
  FAILED: "negative",
  UNAVAILABLE: "neutral",
};

const GENE_VARIANT: Record<GeneStatus, BadgeVariant> = {
  promoted: "positive",
  monitoring: "accent",
  replaced: "warning",
  retired: "neutral",
};

/** Everything an operator needs to know about the platform itself:
 * current mission status, pipeline health stage-by-stage, collector
 * output, knowledge/genome status, source health, execution history, and
 * current blockers -- all composed from existing artifacts. Discovery
 * Engine detail is an honest gap: acquisition_intelligence has no
 * dashboard export yet. */
export function MissionControlPage() {
  const missionStatus = useArtifact((p) => p.getMissionStatus());
  const executionReport = useArtifact((p) => p.getExecutionReport());
  const systemStatus = useArtifact((p) => p.getSystemStatus());
  const collectorStatus = useArtifact((p) => p.getCollectorStatus());
  const genes = useArtifact((p) => p.getGenes());
  const sourceRegistry = useArtifact((p) => p.getSourceRegistry());
  const runtimeMetrics = useArtifact((p) => p.getRuntimeMetrics());
  const acquisitionDecisions = useArtifact((p) => p.getAcquisitionDecisions());

  const geneCounts = {
    promoted: (genes.data ?? []).filter((g) => g.status === "promoted").length,
    monitoring: (genes.data ?? []).filter((g) => g.status === "monitoring").length,
    replaced: (genes.data ?? []).filter((g) => g.status === "replaced").length,
    retired: (genes.data ?? []).filter((g) => g.status === "retired").length,
  };

  const sourceHealthCounts: Record<HealthStatus, number> = { healthy: 0, degraded: 0, down: 0, unknown: 0 };
  for (const s of sourceRegistry.data ?? []) sourceHealthCounts[s.health_status] += 1;
  const implementedCount = (sourceRegistry.data ?? []).filter((s) => s.status === "implemented").length;

  const runHistory = [...(runtimeMetrics.data ?? [])].sort((a, b) => (a.run_date < b.run_date ? 1 : -1));

  return (
    <>
      <Section title="Mission Status" description="The current production pipeline's status, per the most recent Mission Control update.">
        {missionStatus.loading && <LoadingState rows={2} />}
        {missionStatus.error && <ErrorState detail={missionStatus.error.message} onRetry={missionStatus.reload} />}
        {!missionStatus.loading && !missionStatus.error && !missionStatus.data && (
          <EmptyState title="No mission status yet" detail="Available once the full production pipeline (agx run) executes." />
        )}
        {missionStatus.data && (
          <div className={styles.grid}>
            <StatTile label="Pipeline Status" value={<Badge variant={STAGE_VARIANT[missionStatus.data.pipeline_status]}>{titleCase(missionStatus.data.pipeline_status)}</Badge>} />
            <StatTile label="Pipeline Version" value={missionStatus.data.pipeline_version} />
            <StatTile label="Execution Mode" value={titleCase(missionStatus.data.current_execution_mode)} />
            <StatTile label="Duration" value={`${formatNumber(missionStatus.data.execution_duration_seconds, 2)}s`} />
            <StatTile label="Total Executions" value={missionStatus.data.total_executions} />
            <StatTile label="Last Successful Run" value={formatDate(missionStatus.data.last_successful_pipeline_at)} />
            <StatTile label="Last Failed Run" value={formatDate(missionStatus.data.last_failed_pipeline_at)} />
          </div>
        )}
      </Section>

      <Section title="Pipeline Health" description="Every stage of the most recent execution, in order.">
        {executionReport.loading && <LoadingState rows={3} />}
        {executionReport.error && <ErrorState detail={executionReport.error.message} onRetry={executionReport.reload} />}
        {!executionReport.loading && !executionReport.error && !executionReport.data && (
          <EmptyState title="No execution report yet" />
        )}
        {executionReport.data && (
          <DataTable
            rows={executionReport.data.stages}
            getRowKey={(s) => s.name}
            emptyTitle="No stages recorded"
            columns={[
              { key: "name", header: "Stage", render: (s) => titleCase(s.name) },
              { key: "status", header: "Status", render: (s) => <Badge variant={STAGE_VARIANT[s.status]}>{titleCase(s.status)}</Badge> },
              { key: "duration", header: "Duration", align: "right", render: (s) => `${formatNumber(s.duration_seconds, 2)}s` },
              { key: "detail", header: "Detail", render: (s) => s.detail },
              { key: "warnings", header: "Warnings", align: "right", render: (s) => s.warnings.length },
            ]}
          />
        )}
      </Section>

      <div className={styles.twoCol}>
        <Card title="Knowledge Status" subtitle="Knowledge objects by lifecycle status">
          {systemStatus.data ? (
            <div className={styles.grid}>
              <StatTile label="Total" value={systemStatus.data.knowledge_objects} />
              {Object.entries(systemStatus.data.by_status).map(([status, count]) => (
                <StatTile key={status} label={titleCase(status)} value={count} />
              ))}
            </div>
          ) : (
            <EmptyState title="No knowledge status yet" />
          )}
        </Card>

        <Card title="Genome Status" subtitle="Genes by lifecycle status">
          {(genes.data ?? []).length === 0 ? (
            <EmptyState title="No genes yet" />
          ) : (
            <div className={styles.grid}>
              <StatTile label="Total" value={genes.data!.length} />
              <StatTile label="Promoted" value={geneCounts.promoted} />
              <StatTile label="Monitoring" value={geneCounts.monitoring} />
              <StatTile label="Replaced" value={geneCounts.replaced} />
              <StatTile label="Retired" value={geneCounts.retired} />
            </div>
          )}
        </Card>
      </div>

      <Section title="Collectors" description="Output of each source's most recent collection run.">
        {collectorStatus.loading && <LoadingState rows={3} />}
        {collectorStatus.error && <ErrorState detail={collectorStatus.error.message} onRetry={collectorStatus.reload} />}
        {!collectorStatus.loading && !collectorStatus.error && (
          <DataTable
            rows={collectorStatus.data ?? []}
            getRowKey={(c) => c.source_id}
            emptyTitle="No collector runs yet"
            columns={[
              { key: "source", header: "Source", render: (c) => c.source_id },
              {
                key: "status",
                header: "Status",
                render: (c) => <Badge variant={STATUS_VARIANT[c.status]}>{titleCase(c.status)}</Badge>,
              },
              {
                key: "health",
                header: "Health",
                render: (c) => (c.health_status ? <Badge variant={HEALTH_VARIANT[c.health_status]}>{titleCase(c.health_status)}</Badge> : "—"),
              },
              {
                key: "connection",
                header: "Connected",
                render: (c) => <Badge variant={c.connection_success ? "positive" : "negative"}>{c.connection_success ? "Yes" : "No"}</Badge>,
              },
              {
                key: "parsed",
                header: "Parsed",
                render: (c) => <Badge variant={c.parse_success ? "positive" : "negative"}>{c.parse_success ? "Yes" : "No"}</Badge>,
              },
              { key: "yield", header: "Yield", align: "right", render: (c) => formatNumber(c.yield) },
              { key: "events", header: "Events", align: "right", render: (c) => formatNumber(c.events_produced) },
              { key: "docs", header: "Documents", align: "right", render: (c) => formatNumber(c.documents_fetched) },
              { key: "quality", header: "Quality", align: "right", render: (c) => (c.data_quality_score != null ? formatPercent(c.data_quality_score) : "—") },
              { key: "reason", header: "Reason", render: (c) => c.reason ?? "—" },
            ]}
          />
        )}
      </Section>

      <div className={styles.twoCol}>
        <Card title="Source Health" subtitle="Rollup across the full source registry -- see Source Intelligence for per-source detail">
          {(sourceRegistry.data ?? []).length === 0 ? (
            <EmptyState title="No source registry yet" />
          ) : (
            <div className={styles.grid}>
              <StatTile label="Implemented" value={implementedCount} />
              <StatTile label="Healthy" value={sourceHealthCounts.healthy} />
              <StatTile label="Degraded" value={sourceHealthCounts.degraded} />
              <StatTile label="Down" value={sourceHealthCounts.down} />
            </div>
          )}
        </Card>

        <Card title="Current Blockers">
          {!executionReport.data || (executionReport.data.errors.length === 0 && executionReport.data.warnings.length === 0) ? (
            <EmptyState title="No blockers" detail="The most recent execution reported no errors or warnings." />
          ) : (
            <div className={styles.list}>
              {executionReport.data.errors.map((e, i) => (
                <div key={`e-${i}`} className={styles.listItem}>
                  <Badge variant="negative">Error</Badge> {e}
                </div>
              ))}
              {executionReport.data.warnings.map((w, i) => (
                <div key={`w-${i}`} className={styles.listItem}>
                  <Badge variant="warning">Warning</Badge> {w}
                </div>
              ))}
            </div>
          )}
        </Card>
      </div>

      <Section title="Execution History" description="Every research-cycle run recorded.">
        <DataTable
          rows={runHistory}
          getRowKey={(r) => r.id}
          emptyTitle="No runs recorded yet"
          columns={[
            { key: "date", header: "Run Date", render: (r) => formatDate(r.run_date) },
            { key: "status", header: "Status", render: (r) => <Badge variant={RUN_VARIANT[r.status]}>{titleCase(r.status)}</Badge> },
            { key: "hypotheses", header: "Hypotheses", align: "right", render: (r) => r.hypotheses },
            { key: "promoted", header: "Promoted", align: "right", render: (r) => r.promoted },
            { key: "completed", header: "Completed", align: "right", render: (r) => formatDateTime(r.completed_at) },
          ]}
        />
      </Section>

      <Section
        title="Acquisition Decisions"
        description="Every capability's ranked acquisition strategies this run -- which source was selected, and why every other candidate was skipped, failed, or produced nothing usable. A capability is never tied to one website: this is the runtime Acquisition Decision Engine's own record of the fallback chain it evaluated."
      >
        {acquisitionDecisions.loading && <LoadingState rows={3} />}
        {acquisitionDecisions.error && (
          <ErrorState detail={acquisitionDecisions.error.message} onRetry={acquisitionDecisions.reload} />
        )}
        {!acquisitionDecisions.loading && !acquisitionDecisions.error && (
          <DataTable
            rows={acquisitionDecisions.data ?? []}
            getRowKey={(d) => d.capability}
            emptyTitle="No acquisition decisions yet"
            columns={[
              { key: "capability", header: "Capability", render: (d) => titleCase(d.capability) },
              {
                key: "status",
                header: "Status",
                render: (d) => (
                  <Badge variant={d.succeeded ? "positive" : "neutral"}>
                    {d.succeeded ? "Satisfied" : "Unsatisfied"}
                  </Badge>
                ),
              },
              {
                key: "selected",
                header: "Selected Strategy",
                render: (d) => (d.selected_source_ids.length ? d.selected_source_ids.join(", ") : "—"),
              },
              {
                key: "attempts",
                header: "Strategies Considered",
                align: "right",
                render: (d) => d.attempts.length,
              },
              {
                key: "top",
                header: "Top-Ranked Strategy",
                render: (d) =>
                  d.attempts[0] ? `${d.attempts[0].source_id} (${titleCase(d.attempts[0].outcome)})` : "—",
              },
            ]}
          />
        )}
      </Section>
    </>
  );
}
