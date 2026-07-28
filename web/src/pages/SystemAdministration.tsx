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
      <Section title="التشغيل والإصدارات" description="إصدار خط الإنتاج ووضع أحدث تنفيذ.">
        {executionReport.loading && <LoadingState rows={2} />}
        {executionReport.error && <ErrorState detail={executionReport.error.message} onRetry={executionReport.reload} />}
        {!executionReport.loading && !executionReport.error && !executionReport.data && (
          <EmptyState title="لا يوجد تقرير تنفيذ بعد" />
        )}
        {executionReport.data && (
          <div className={styles.grid}>
            <StatTile label="إصدار الخط" value={executionReport.data.pipeline_version} />
            <StatTile label="وضع التنفيذ" value={adminTokenLabel(executionReport.data.execution_mode)} />
            <StatTile label="الحالة العامة" value={<Badge variant={STAGE_VARIANT[executionReport.data.overall_status]}>{adminTokenLabel(executionReport.data.overall_status)}</Badge>} />
            <StatTile label="تواريخ التشغيل" value={executionReport.data.run_dates.length} />
            <StatTile label="بدأ" value={formatDateTime(executionReport.data.started_at)} />
            <StatTile label="اكتمل" value={formatDateTime(executionReport.data.completed_at)} />
            <StatTile label="المدة" value={`${formatNumber(executionReport.data.duration_seconds, 2)} ث`} />
          </div>
        )}
      </Section>

      <div className={styles.twoCol}>
        <Card title="الإعدادات" subtitle="مكان كتابة ملفات هذا التشغيل والمراحل المتخطاة">
          {!executionReport.data && !dashboardMetrics.data ? (
            <EmptyState title="لا توجد بيانات إعدادات بعد" />
          ) : (
            <div>
              {dashboardMetrics.data && (
                <div className={styles.listItem}>
                  <strong>مجلد اللوحة:</strong> <span className={styles.path}>{dashboardMetrics.data.dashboard_dir}</span>
                </div>
              )}
              {executionReport.data && executionReport.data.skipped_stages.length > 0 && (
                <div className={styles.listItem}>
                  <strong>المراحل المتخطاة:</strong> {executionReport.data.skipped_stages.map(adminTokenLabel).join("، ")}
                </div>
              )}
              {executionReport.data && executionReport.data.skipped_stages.length === 0 && (
                <div className={styles.listItem}>لم تُتخط أي مرحلة في أحدث تشغيل.</div>
              )}
            </div>
          )}
        </Card>

        <Card title="إعادة التشغيل">
          <EmptyState
            title={executionReport.data ? `الوضع الحالي: ${adminTokenLabel(executionReport.data.execution_mode)}` : "لم يعمل بعد"}
            detail="يعيد وضع الإعادة تنفيذ الخط نفسه على المستندات الخام المؤرشفة من تشغيل سابق. لا يوجد سجل إعادة مستقل عن سجل التنفيذ أدناه."
          />
        </Card>
      </div>

      <Section title="ملفات النتائج" description="كل ملف لوحة كتبه أحدث تشغيل وعدد السجلات التي يحتويها.">
        {dashboardMetrics.error && <ErrorState detail={dashboardMetrics.error.message} onRetry={dashboardMetrics.reload} />}
        {!dashboardMetrics.error && dashboardMetrics.data && (
          <StatTile label="إجمالي الملفات" value={dashboardMetrics.data.total_artifacts} caption={formatDateTime(dashboardMetrics.data.generated_at)} />
        )}
        <div style={{ marginTop: "var(--space-4)" }}>
          <DataTable
            rows={artifactRows}
            getRowKey={([name]) => name}
            emptyTitle="لا توجد ملفات نتائج مسجلة بعد"
            columns={[
              { key: "name", header: "الملف", render: ([name]) => name },
              { key: "count", header: "السجلات", align: "right", render: ([, count]) => formatNumber(count) },
            ]}
          />
        </div>
      </Section>

      <Section title="الأداء" description="مراحل أحدث تنفيذ مرتبة من الأبطأ.">
        <DataTable
          rows={stagesByDuration}
          getRowKey={(s) => s.name}
          emptyTitle="لم تُسجل أزمنة مراحل بعد"
          columns={[
            { key: "name", header: "المرحلة", render: (s) => adminTokenLabel(s.name) },
            { key: "status", header: "الحالة", render: (s) => <Badge variant={STAGE_VARIANT[s.status]}>{adminTokenLabel(s.status)}</Badge> },
            { key: "duration", header: "المدة", align: "right", render: (s) => `${formatNumber(s.duration_seconds, 3)} ث` },
          ]}
        />
      </Section>

      <Section title="سجل التنفيذ" description="كل تشغيل لدورة البحث مع تفاصيل الخطأ والجلسة.">
        <DataTable
          rows={runHistory}
          getRowKey={(r) => r.id}
          emptyTitle="لا توجد تشغيلات مسجلة بعد"
          columns={[
            { key: "date", header: "تاريخ التشغيل", render: (r) => r.run_date },
            { key: "status", header: "الحالة", render: (r) => <Badge variant={RUN_VARIANT[r.status]}>{adminTokenLabel(r.status)}</Badge> },
            { key: "session", header: "الجلسة", render: (r) => r.session_id ?? "—" },
            { key: "error", header: "الخطأ", render: (r) => r.error ?? "—" },
            { key: "completed", header: "اكتمل", align: "right", render: (r) => formatDateTime(r.completed_at) },
          ]}
        />
      </Section>

      <Card title="السجلات النصية">
        <EmptyState
          title="غير متاح بعد"
          detail="لا يحمل أي ملف سطور السجل الخام بعد؛ سيظهر القسم عند وجود سجل حقيقي بدل اختلاق تدفق سجلات."
        />
      </Card>
    </>
  );
}

function adminTokenLabel(value: string): string {
  const labels: Record<string, string> = {
    succeeded: "ناجح", partial: "جزئي", failed: "فاشل", skipped: "متخطى",
    skipped_non_trading: "تخطي يوم غير متداول", live: "حي", mock: "تجريبي", replay: "إعادة تشغيل",
    entry_point: "نقطة الدخول", source_registry: "سجل المصادر", collector_execution: "تنفيذ الجمع",
    research_pipeline: "خط البحث", investment_case_generator: "مولد الحالة الاستثمارية",
    dashboard_artifact_generator: "مولد ملفات اللوحة", mission_control_update: "تحديث مراقبة التشغيل",
  };
  return labels[value.toLowerCase()] ?? titleCase(value);
}
