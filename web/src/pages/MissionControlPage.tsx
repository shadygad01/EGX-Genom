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
  const collectedCount = (collectorStatus.data ?? []).filter((s) => s.status === "COLLECTED").length;
  const degradedCount = (collectorStatus.data ?? []).filter((s) => s.status === "DEGRADED").length;
  const standbyCount = (collectorStatus.data ?? []).filter((s) => s.status === "STANDBY").length;
  const failedCount = (collectorStatus.data ?? []).filter((s) => s.status === "FAILED").length;
  const unavailableCount = (collectorStatus.data ?? []).filter((s) => s.status === "UNAVAILABLE").length;

  const runHistory = [...(runtimeMetrics.data ?? [])].sort((a, b) => (a.run_date < b.run_date ? 1 : -1));

  return (
    <>
      <Section title="حالة المهمة" description="حالة خط الإنتاج وفق أحدث تحديث لمراقبة التشغيل.">
        {missionStatus.loading && <LoadingState rows={2} />}
        {missionStatus.error && <ErrorState detail={missionStatus.error.message} onRetry={missionStatus.reload} />}
        {!missionStatus.loading && !missionStatus.error && !missionStatus.data && (
          <EmptyState title="لا توجد حالة للمهمة بعد" detail="تظهر بعد تشغيل خط الإنتاج الكامل." />
        )}
        {missionStatus.data && (
          <div className={styles.grid}>
            <StatTile label="حالة الخط" value={<Badge variant={STAGE_VARIANT[missionStatus.data.pipeline_status]}>{runtimeTokenLabel(missionStatus.data.pipeline_status)}</Badge>} />
            <StatTile label="إصدار الخط" value={missionStatus.data.pipeline_version} />
            <StatTile label="وضع التنفيذ" value={runtimeTokenLabel(missionStatus.data.current_execution_mode)} />
            <StatTile label="المدة" value={`${formatNumber(missionStatus.data.execution_duration_seconds, 2)} ث`} />
            <StatTile label="إجمالي التنفيذات" value={missionStatus.data.total_executions} />
            <StatTile label="آخر تشغيل ناجح" value={formatDate(missionStatus.data.last_successful_pipeline_at)} />
            <StatTile label="آخر تشغيل فاشل" value={formatDate(missionStatus.data.last_failed_pipeline_at)} />
          </div>
        )}
      </Section>

      <Section title="صحة خط الإنتاج" description="كل مرحلة من أحدث تنفيذ بالترتيب.">
        {executionReport.loading && <LoadingState rows={3} />}
        {executionReport.error && <ErrorState detail={executionReport.error.message} onRetry={executionReport.reload} />}
        {!executionReport.loading && !executionReport.error && !executionReport.data && (
          <EmptyState title="لا يوجد تقرير تنفيذ بعد" />
        )}
        {executionReport.data && (
          <DataTable
            rows={executionReport.data.stages}
            getRowKey={(s) => s.name}
            emptyTitle="لا توجد مراحل مسجلة"
            columns={[
              { key: "name", header: "المرحلة", render: (s) => runtimeTokenLabel(s.name) },
              { key: "status", header: "الحالة", render: (s) => <Badge variant={STAGE_VARIANT[s.status]}>{runtimeTokenLabel(s.status)}</Badge> },
              { key: "duration", header: "المدة", align: "right", render: (s) => `${formatNumber(s.duration_seconds, 2)} ث` },
              { key: "detail", header: "التفاصيل", render: (s) => s.detail },
              { key: "warnings", header: "التحذيرات", align: "right", render: (s) => s.warnings.length },
            ]}
          />
        )}
      </Section>

      <div className={styles.twoCol}>
        <Card title="حالة المعرفة" subtitle="كائنات المعرفة حسب دورة الحياة">
          {systemStatus.data ? (
            <div className={styles.grid}>
              <StatTile label="الإجمالي" value={systemStatus.data.knowledge_objects} />
              {Object.entries(systemStatus.data.by_status).map(([status, count]) => (
                <StatTile key={status} label={runtimeTokenLabel(status)} value={count} />
              ))}
            </div>
          ) : (
            <EmptyState title="لا توجد حالة معرفة بعد" />
          )}
        </Card>

        <Card title="حالة الجينوم" subtitle="الجينات حسب دورة الحياة">
          {(genes.data ?? []).length === 0 ? (
            <EmptyState title="لا توجد جينات بعد" />
          ) : (
            <div className={styles.grid}>
              <StatTile label="الإجمالي" value={genes.data!.length} />
              <StatTile label="مرقّاة" value={geneCounts.promoted} />
              <StatTile label="تحت المراقبة" value={geneCounts.monitoring} />
              <StatTile label="مستبدلة" value={geneCounts.replaced} />
              <StatTile label="مسحوبة" value={geneCounts.retired} />
            </div>
          )}
        </Card>
      </div>

      <Section title="جامعو البيانات" description="ناتج أحدث تشغيل جمع لكل مصدر.">
        <div className={styles.grid}>
          <StatTile label="مفهرسة" value={(sourceRegistry.data ?? []).length} />
          <StatTile label="جُمعت" value={collectedCount} />
          <StatTile label="متراجعة" value={degradedCount} />
          <StatTile label="احتياطية موصلة" value={standbyCount} />
          <StatTile label="فاشلة" value={failedCount} />
          <StatTile label="غير موصلة" value={unavailableCount} />
        </div>
        {collectorStatus.loading && <LoadingState rows={3} />}
        {collectorStatus.error && <ErrorState detail={collectorStatus.error.message} onRetry={collectorStatus.reload} />}
        {!collectorStatus.loading && !collectorStatus.error && (
          <DataTable
            rows={collectorStatus.data ?? []}
            getRowKey={(c) => c.source_id}
            emptyTitle="لا توجد تشغيلات جمع بعد"
            columns={[
              { key: "source", header: "المصدر", render: (c) => c.source_id },
              {
                key: "status",
                header: "الحالة",
                render: (c) => <Badge variant={STATUS_VARIANT[c.status]}>{runtimeTokenLabel(c.status)}</Badge>,
              },
              {
                key: "health",
                header: "الصحة",
                render: (c) => c.status === "STANDBY"
                  ? <Badge variant="accent">غير مقاس</Badge>
                  : (c.health_status ? <Badge variant={HEALTH_VARIANT[c.health_status]}>{runtimeTokenLabel(c.health_status)}</Badge> : "—"),
              },
              {
                key: "connection",
                header: "الاتصال",
                render: (c) => c.status === "STANDBY"
                  ? <Badge variant="neutral">لم يعمل</Badge>
                  : <Badge variant={c.connection_success ? "positive" : "negative"}>{c.connection_success ? "نعم" : "لا"}</Badge>,
              },
              {
                key: "parsed",
                header: "التحليل",
                render: (c) => c.status === "STANDBY"
                  ? <Badge variant="neutral">لم يعمل</Badge>
                  : <Badge variant={c.parse_success ? "positive" : "negative"}>{c.parse_success ? "نعم" : "لا"}</Badge>,
              },
              { key: "yield", header: "الناتج", align: "right", render: (c) => formatNumber(c.yield) },
              { key: "events", header: "الأحداث", align: "right", render: (c) => formatNumber(c.events_produced) },
              { key: "docs", header: "المستندات", align: "right", render: (c) => formatNumber(c.documents_fetched) },
              { key: "quality", header: "الجودة", align: "right", render: (c) => (c.data_quality_score != null ? formatPercent(c.data_quality_score) : "—") },
              { key: "reason", header: "السبب", render: (c) => c.reason ?? "—" },
            ]}
          />
        )}
      </Section>

      <div className={styles.twoCol}>
        <Card title="صحة المصادر" subtitle="ملخص سجل المصادر الكامل؛ راجع شفافية المصادر للتفاصيل">
          {(sourceRegistry.data ?? []).length === 0 ? (
            <EmptyState title="لا يوجد سجل مصادر بعد" />
          ) : (
            <div className={styles.grid}>
              <StatTile label="منفذة" value={implementedCount} />
              <StatTile label="سليمة" value={sourceHealthCounts.healthy} />
              <StatTile label="متراجعة" value={sourceHealthCounts.degraded} />
              <StatTile label="متوقفة" value={sourceHealthCounts.down} />
            </div>
          )}
        </Card>

        <Card title="العوائق الحالية">
          {!executionReport.data || (executionReport.data.errors.length === 0 && executionReport.data.warnings.length === 0) ? (
            <EmptyState title="لا توجد عوائق" detail="لم يسجل أحدث تنفيذ أخطاء أو تحذيرات." />
          ) : (
            <div className={styles.list}>
              {executionReport.data.errors.map((e, i) => (
                <div key={`e-${i}`} className={styles.listItem}>
                  <Badge variant="negative">خطأ</Badge> {e}
                </div>
              ))}
              {executionReport.data.warnings.map((w, i) => (
                <div key={`w-${i}`} className={styles.listItem}>
                  <Badge variant="warning">تحذير</Badge> {w}
                </div>
              ))}
            </div>
          )}
        </Card>
      </div>

      <Section title="سجل التنفيذ" description="كل تشغيل مسجل لدورة البحث.">
        <DataTable
          rows={runHistory}
          getRowKey={(r) => r.id}
          emptyTitle="لا توجد تشغيلات مسجلة بعد"
          columns={[
            { key: "date", header: "تاريخ التشغيل", render: (r) => formatDate(r.run_date) },
            { key: "status", header: "الحالة", render: (r) => <Badge variant={RUN_VARIANT[r.status]}>{runtimeTokenLabel(r.status)}</Badge> },
            { key: "hypotheses", header: "الفرضيات", align: "right", render: (r) => r.hypotheses },
            { key: "promoted", header: "المرقّاة", align: "right", render: (r) => r.promoted },
            { key: "completed", header: "اكتمل", align: "right", render: (r) => formatDateTime(r.completed_at) },
          ]}
        />
      </Section>

      <Section
        title="قرارات الحصول على البيانات"
        description="استراتيجيات المصادر المرتبة لكل قدرة في هذا التشغيل: ما المصدر المختار ولماذا تخطى النظام البدائل أو فشلت أو لم تنتج سجلات صالحة."
      >
        {acquisitionDecisions.loading && <LoadingState rows={3} />}
        {acquisitionDecisions.error && (
          <ErrorState detail={acquisitionDecisions.error.message} onRetry={acquisitionDecisions.reload} />
        )}
        {!acquisitionDecisions.loading && !acquisitionDecisions.error && (
          <DataTable
            rows={acquisitionDecisions.data ?? []}
            getRowKey={(d) => d.capability}
            emptyTitle="لا توجد قرارات حصول على البيانات بعد"
            columns={[
              { key: "capability", header: "القدرة", render: (d) => runtimeTokenLabel(d.capability) },
              {
                key: "status",
                header: "الحالة",
                render: (d) => (
                  <Badge variant={d.succeeded ? "positive" : "neutral"}>
                    {d.succeeded ? "مستوفاة" : "غير مستوفاة"}
                  </Badge>
                ),
              },
              {
                key: "selected",
                header: "الاستراتيجية المختارة",
                render: (d) => (d.selected_source_ids.length ? d.selected_source_ids.join(", ") : "—"),
              },
              {
                key: "attempts",
                header: "الاستراتيجيات المدروسة",
                align: "right",
                render: (d) => d.attempts.length,
              },
              {
                key: "top",
                header: "أعلى استراتيجية ترتيبًا",
                render: (d) =>
                  d.attempts[0] ? `${d.attempts[0].source_id} (${runtimeTokenLabel(d.attempts[0].outcome)})` : "—",
              },
            ]}
          />
        )}
      </Section>
    </>
  );
}

function runtimeTokenLabel(value: string): string {
  const labels: Record<string, string> = {
    succeeded: "ناجح", failed: "فاشل", partial: "جزئي", skipped: "متخطى",
    collected: "جُمع", degraded: "متراجع", standby: "احتياطي", unavailable: "غير متاح",
    healthy: "سليم", down: "متوقف", unknown: "غير معروف",
    promoted: "مرقّاة", monitoring: "تحت المراقبة", retired: "مسحوبة", replaced: "مستبدلة",
    live: "حي", mock: "تجريبي", replay: "إعادة تشغيل",
    usable: "صالح", empty: "فارغ", skipped_candidate: "بديل متخطى", fetch_failed: "فشل الجلب",
    price_history: "سجل الأسعار", macro_context: "سياق الاقتصاد الكلي", news: "الأخبار",
    corporate_events: "الأحداث المؤسسية", financial_statements: "القوائم المالية", universe: "نطاق الأسهم",
  };
  return labels[value.toLowerCase()] ?? titleCase(value);
}
