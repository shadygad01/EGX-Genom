import { useTranslation } from "react-i18next";
import { Badge, type BadgeVariant } from "../components/primitives/Badge";
import { Card } from "../components/primitives/Card";
import { DataTable } from "../components/primitives/DataTable";
import { Section } from "../components/primitives/Section";
import { StatTile } from "../components/primitives/StatTile";
import { EmptyState, ErrorState, LoadingState } from "../components/primitives/States";
import { useArtifact } from "../hooks/useArtifact";
import { useEnumLabel } from "../hooks/useEnumLabel";
import { useFormatters } from "../hooks/useFormatters";
import { formatNumber } from "../lib/format";
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
  const { t } = useTranslation("systemAdministration");
  const label = useEnumLabel();
  const { formatDateTime } = useFormatters();
  const executionReport = useArtifact((p) => p.getExecutionReport());
  const dashboardMetrics = useArtifact((p) => p.getDashboardMetrics());
  const runtimeMetrics = useArtifact((p) => p.getRuntimeMetrics());

  const artifactRows = Object.entries(dashboardMetrics.data?.artifacts ?? {}).sort(([a], [b]) => a.localeCompare(b));
  const stagesByDuration = [...(executionReport.data?.stages ?? [])].sort((a, b) => b.duration_seconds - a.duration_seconds);
  const runHistory = [...(runtimeMetrics.data ?? [])].sort((a, b) => (a.run_date < b.run_date ? 1 : -1));

  return (
    <>
      <Section title={t("runtime.title")} description={t("runtime.description")}>
        {executionReport.loading && <LoadingState rows={2} />}
        {executionReport.error && <ErrorState detail={executionReport.error.message} onRetry={executionReport.reload} />}
        {!executionReport.loading && !executionReport.error && !executionReport.data && (
          <EmptyState title={t("runtime.emptyTitle")} />
        )}
        {executionReport.data && (
          <div className={styles.grid}>
            <StatTile label={t("runtime.pipelineVersion")} value={<span className="num">{executionReport.data.pipeline_version}</span>} />
            <StatTile label={t("runtime.executionMode")} value={label("executionMode", executionReport.data.execution_mode)} />
            <StatTile label={t("runtime.overallStatus")} value={<Badge variant={STAGE_VARIANT[executionReport.data.overall_status]}>{label("stageStatus", executionReport.data.overall_status)}</Badge>} />
            <StatTile label={t("runtime.runDates")} value={executionReport.data.run_dates.length} />
            <StatTile label={t("runtime.started")} value={formatDateTime(executionReport.data.started_at)} />
            <StatTile label={t("runtime.completed")} value={formatDateTime(executionReport.data.completed_at)} />
            <StatTile label={t("runtime.duration")} value={<span className="num">{`${formatNumber(executionReport.data.duration_seconds, 2)}s`}</span>} />
          </div>
        )}
      </Section>

      <div className={styles.twoCol}>
        <Card title={t("configuration.title")} subtitle={t("configuration.subtitle")}>
          {!executionReport.data && !dashboardMetrics.data ? (
            <EmptyState title={t("configuration.emptyTitle")} />
          ) : (
            <div>
              {dashboardMetrics.data && (
                <div className={styles.listItem}>
                  <strong>{t("configuration.dashboardDirectory")}</strong> <span className={styles.path}>{dashboardMetrics.data.dashboard_dir}</span>
                </div>
              )}
              {executionReport.data && executionReport.data.skipped_stages.length > 0 && (
                <div className={styles.listItem}>
                  <strong>{t("configuration.skippedStages")}</strong> {executionReport.data.skipped_stages.map((s) => label("stageName", s)).join(", ")}
                </div>
              )}
              {executionReport.data && executionReport.data.skipped_stages.length === 0 && (
                <div className={styles.listItem}>{t("configuration.noSkippedStages")}</div>
              )}
            </div>
          )}
        </Card>

        <Card title={t("replay.title")}>
          <EmptyState
            title={executionReport.data ? t("replay.currentMode", { mode: label("executionMode", executionReport.data.execution_mode) }) : t("replay.notYetRun")}
            detail={t("replay.detail")}
          />
        </Card>
      </div>

      <Section title={t("artifacts.title")} description={t("artifacts.description")}>
        {dashboardMetrics.error && <ErrorState detail={dashboardMetrics.error.message} onRetry={dashboardMetrics.reload} />}
        {!dashboardMetrics.error && dashboardMetrics.data && (
          <StatTile label={t("artifacts.totalArtifacts")} value={dashboardMetrics.data.total_artifacts} caption={formatDateTime(dashboardMetrics.data.generated_at)} />
        )}
        <div style={{ marginTop: "var(--space-4)" }}>
          <DataTable
            rows={artifactRows}
            getRowKey={([name]) => name}
            emptyTitle={t("artifacts.emptyTitle")}
            columns={[
              { key: "name", header: t("artifacts.artifact"), render: ([name]) => name },
              { key: "count", header: t("artifacts.records"), align: "right", render: ([, count]) => <span className="num">{formatNumber(count)}</span> },
            ]}
          />
        </div>
      </Section>

      <Section title={t("performance.title")} description={t("performance.description")}>
        <DataTable
          rows={stagesByDuration}
          getRowKey={(s) => s.name}
          emptyTitle={t("performance.emptyTitle")}
          columns={[
            { key: "name", header: t("performance.stage"), render: (s) => label("stageName", s.name) },
            { key: "status", header: t("performance.status"), render: (s) => <Badge variant={STAGE_VARIANT[s.status]}>{label("stageStatus", s.status)}</Badge> },
            { key: "duration", header: t("performance.duration"), align: "right", render: (s) => <span className="num">{`${formatNumber(s.duration_seconds, 3)}s`}</span> },
          ]}
        />
      </Section>

      <Section title={t("executionHistory.title")} description={t("executionHistory.description")}>
        <DataTable
          rows={runHistory}
          getRowKey={(r) => r.id}
          emptyTitle={t("executionHistory.emptyTitle")}
          columns={[
            { key: "date", header: t("executionHistory.runDate"), render: (r) => <span className="num">{r.run_date}</span> },
            { key: "status", header: t("executionHistory.status"), render: (r) => <Badge variant={RUN_VARIANT[r.status]}>{label("runStatus", r.status)}</Badge> },
            { key: "session", header: t("executionHistory.session"), render: (r) => r.session_id ?? "—" },
            { key: "error", header: t("executionHistory.error"), render: (r) => r.error ?? "—" },
            { key: "completed", header: t("executionHistory.completed"), align: "right", render: (r) => formatDateTime(r.completed_at) },
          ]}
        />
      </Section>

      <Card title={t("logs.title")}>
        <EmptyState
          title={t("logs.notYetAvailable")}
          detail={t("logs.detail")}
        />
      </Card>
    </>
  );
}
