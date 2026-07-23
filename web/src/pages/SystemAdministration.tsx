import { Badge, type BadgeVariant } from "../components/primitives/Badge";
import { Card } from "../components/primitives/Card";
import { DataTable } from "../components/primitives/DataTable";
import { Section } from "../components/primitives/Section";
import { StatTile } from "../components/primitives/StatTile";
import { EmptyState, ErrorState, LoadingState } from "../components/primitives/States";
import { useArtifact } from "../hooks/useArtifact";
import { formatDateTime, formatNumber, titleCase } from "../lib/format";
import type { RunStatus, StageStatus } from "../types";
import styles from "./SystemAdministration.module.css";

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

/** Operational/infra view of the platform: runtime version and
 * configuration, artifact inventory, per-stage performance, replay
 * capability, and the raw execution log (with error/session detail
 * Mission Control's business-facing history omits). Logs streaming is an
 * honest gap -- no artifact carries raw log lines yet. */
export function SystemAdministration() {
  const executionReport = useArtifact((p) => p.getExecutionReport());
  const dashboardMetrics = useArtifact((p) => p.getDashboardMetrics());
  const runtimeMetrics = useArtifact((p) => p.getRuntimeMetrics());

  const artifactRows = Object.entries(dashboardMetrics.data?.artifacts ?? {}).sort(([a], [b]) => a.localeCompare(b));
  const stagesByDuration = [...(executionReport.data?.stages ?? [])].sort((a, b) => b.duration_seconds - a.duration_seconds);
  const runHistory = [...(runtimeMetrics.data ?? [])].sort((a, b) => (a.run_date < b.run_date ? 1 : -1));

  return (
    <>
      <Section title="Runtime & Versions" description="The pipeline version and mode behind the most recent execution.">
        {executionReport.loading && <LoadingState rows={2} />}
        {executionReport.error && <ErrorState detail={executionReport.error.message} onRetry={executionReport.reload} />}
        {!executionReport.loading && !executionReport.error && !executionReport.data && (
          <EmptyState title="No execution report yet" />
        )}
        {executionReport.data && (
          <div className={styles.grid}>
            <StatTile label="Pipeline Version" value={executionReport.data.pipeline_version} />
            <StatTile label="Execution Mode" value={titleCase(executionReport.data.execution_mode)} />
            <StatTile label="Overall Status" value={<Badge variant={STAGE_VARIANT[executionReport.data.overall_status]}>{titleCase(executionReport.data.overall_status)}</Badge>} />
            <StatTile label="Run Dates" value={executionReport.data.run_dates.length} />
            <StatTile label="Started" value={formatDateTime(executionReport.data.started_at)} />
            <StatTile label="Completed" value={formatDateTime(executionReport.data.completed_at)} />
            <StatTile label="Duration" value={`${formatNumber(executionReport.data.duration_seconds, 2)}s`} />
          </div>
        )}
      </Section>

      <div className={styles.twoCol}>
        <Card title="Configuration" subtitle="Where this run's artifacts were written, and which stages were skipped">
          {!executionReport.data && !dashboardMetrics.data ? (
            <EmptyState title="No configuration data yet" />
          ) : (
            <div>
              {dashboardMetrics.data && (
                <div className={styles.listItem}>
                  <strong>Dashboard directory:</strong> <span className={styles.path}>{dashboardMetrics.data.dashboard_dir}</span>
                </div>
              )}
              {executionReport.data && executionReport.data.skipped_stages.length > 0 && (
                <div className={styles.listItem}>
                  <strong>Skipped stages:</strong> {executionReport.data.skipped_stages.map((s) => titleCase(s)).join(", ")}
                </div>
              )}
              {executionReport.data && executionReport.data.skipped_stages.length === 0 && (
                <div className={styles.listItem}>No stages were skipped in the most recent run.</div>
              )}
            </div>
          )}
        </Card>

        <Card title="Replay">
          <EmptyState
            title={executionReport.data ? `Current mode: ${titleCase(executionReport.data.execution_mode)}` : "Not yet run"}
            detail="Replay mode re-executes the identical pipeline against already-archived RawDocuments from a prior run, proving the pipeline cannot distinguish live data from replayed data. No dedicated replay-history artifact exists separately from Execution History below."
          />
        </Card>
      </div>

      <Section title="Artifacts" description="Every dashboard artifact file written by the most recent run, and how many records it holds.">
        {dashboardMetrics.error && <ErrorState detail={dashboardMetrics.error.message} onRetry={dashboardMetrics.reload} />}
        {!dashboardMetrics.error && dashboardMetrics.data && (
          <StatTile label="Total Artifacts" value={dashboardMetrics.data.total_artifacts} caption={formatDateTime(dashboardMetrics.data.generated_at)} />
        )}
        <div style={{ marginTop: "var(--space-4)" }}>
          <DataTable
            rows={artifactRows}
            getRowKey={([name]) => name}
            emptyTitle="No artifacts recorded yet"
            columns={[
              { key: "name", header: "Artifact", render: ([name]) => name },
              { key: "count", header: "Records", align: "right", render: ([, count]) => formatNumber(count) },
            ]}
          />
        </div>
      </Section>

      <Section title="Performance" description="Every stage of the most recent execution, slowest first.">
        <DataTable
          rows={stagesByDuration}
          getRowKey={(s) => s.name}
          emptyTitle="No stage timing recorded yet"
          columns={[
            { key: "name", header: "Stage", render: (s) => titleCase(s.name) },
            { key: "status", header: "Status", render: (s) => <Badge variant={STAGE_VARIANT[s.status]}>{titleCase(s.status)}</Badge> },
            { key: "duration", header: "Duration", align: "right", render: (s) => `${formatNumber(s.duration_seconds, 3)}s` },
          ]}
        />
      </Section>

      <Section title="Execution History" description="Every research-cycle run, including error and session detail.">
        <DataTable
          rows={runHistory}
          getRowKey={(r) => r.id}
          emptyTitle="No runs recorded yet"
          columns={[
            { key: "date", header: "Run Date", render: (r) => r.run_date },
            { key: "status", header: "Status", render: (r) => <Badge variant={RUN_VARIANT[r.status]}>{titleCase(r.status)}</Badge> },
            { key: "session", header: "Session", render: (r) => r.session_id ?? "—" },
            { key: "error", header: "Error", render: (r) => r.error ?? "—" },
            { key: "completed", header: "Completed", align: "right", render: (r) => formatDateTime(r.completed_at) },
          ]}
        />
      </Section>

      <Card title="Logs">
        <EmptyState
          title="Not yet available"
          detail="No artifact carries raw log lines yet -- this section will populate once one exists, rather than fabricating a log stream."
        />
      </Card>
    </>
  );
}
