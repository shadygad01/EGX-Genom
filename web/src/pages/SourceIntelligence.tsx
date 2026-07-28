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
  const sourceTruth = useArtifact((p) => p.getSourceTruth());
  const [selectedId, setSelectedId] = useState<string | null>(null);

  const metricsById = new Map((sourceMetrics.data ?? []).map((m) => [m.source_id, m]));
  const collectorById = new Map((collectorStatus.data ?? []).map((c) => [c.source_id, c]));
  const truthById = new Map((sourceTruth.data ?? []).map((row) => [row.source_id, row]));
  const truthRows = sourceTruth.data ?? [];

  const sorted = [...(sourceRegistry.data ?? [])].sort((a, b) => a.priority - b.priority);
  const selected = sorted.find((s) => s.id === selectedId) ?? sorted[0] ?? null;
  const selectedMetrics = selected ? metricsById.get(selected.id) : undefined;
  const selectedCollector = selected ? collectorById.get(selected.id) : undefined;
  const effectiveCollected = selectedCollector?.status === "COLLECTED" || selectedCollector?.status === "DEGRADED" || selectedCollector?.status === "STANDBY";

  return (
    <Section
      title="شفافية المصادر"
      description="الصحة والتوفر والتغطية والحداثة والتأخر والتأهيل ودرجة التحقق لكل مصدر يتابعه AGX."
    >
      {sourceRegistry.loading && <LoadingState rows={4} />}
      {sourceRegistry.error && <ErrorState detail={sourceRegistry.error.message} onRetry={sourceRegistry.reload} />}

      {!sourceRegistry.loading && !sourceRegistry.error && (
        <>
          <div className={styles.grid}>
            <StatTile label="مصادر مسجلة" value={truthRows.length || sorted.length} />
            <StatTile label="مسموحة وقابلة للاستخدام" value={truthRows.filter((row) => row.legally_usable).length} />
            <StatTile label="أنتجت بيانات هذه الدورة" value={truthRows.filter((row) => row.produced_records > 0).length} />
            <StatTile label="وصلت لمسار القرار" value={truthRows.filter((row) => row.reached_decision_path).length} />
          </div>
          <div className={styles.layout}>
          <Card dense>
            <DataTable
              rows={sorted}
              getRowKey={(s) => s.id}
              onRowClick={(s) => setSelectedId(s.id)}
              emptyTitle="لا توجد مصادر مسجلة بعد"
              columns={[
                { key: "name", header: "المصدر", render: (s) => s.name },
                { key: "category", header: "الفئة", render: (s) => sourceTokenLabel(s.category) },
                { key: "status", header: "الحالة", render: (s) => collectorById.get(s.id)?.status === "COLLECTED" ? <Badge variant="positive">مدمج وجُمع</Badge> : collectorById.get(s.id)?.status === "STANDBY" ? <Badge variant="accent">مدمج واحتياطي</Badge> : <Badge variant={STATUS_VARIANT[s.status]}>{sourceTokenLabel(s.status)}</Badge> },
                { key: "integration", header: "التكامل", render: (s) => s.integrated_via ? `عبر ${s.integrated_via}` : (s.collector ?? "—") },
                { key: "lifecycle", header: "دورة الحياة", render: (s) => <Badge variant={LIFECYCLE_VARIANT[s.lifecycle_state]}>{sourceTokenLabel(s.lifecycle_state)}</Badge> },
                { key: "health", header: "الصحة", render: (s) => collectorById.get(s.id)?.status === "STANDBY" ? <Badge variant="accent">غير مقاس</Badge> : <Badge variant={HEALTH_VARIANT[s.health_status]}>{sourceTokenLabel(s.health_status)}</Badge> },
                { key: "decision", header: "مسار القرار", render: (s) => truthById.get(s.id)?.reached_decision_path ? <Badge variant="positive">وصل</Badge> : <Badge variant="neutral">لا سجلات صالحة</Badge> },
                {
                  key: "quality",
                  header: "درجة التحقق",
                  align: "right",
                  render: (s) => (s.data_quality_score != null ? formatPercent(s.data_quality_score) : "—"),
                },
              ]}
            />
          </Card>

          <Card title={selected ? selected.name : "تفاصيل المصدر"} dense>
            {!selected && <EmptyState title="لم يُحدد مصدر" detail="اختر صفًا لرؤية تفاصيل الصحة والسمعة." />}
            {selected && (
              <div>
                <div className={styles.detailHeader}>{selected.name}</div>
                <div className={styles.detailMeta}>
                  {sourceTokenLabel(selected.category)} · {selected.country} · الأولوية {selected.priority}
                </div>

                <div className={styles.badgeRow}>
                  <Badge variant={effectiveCollected ? (selectedCollector?.status === "COLLECTED" ? "positive" : selectedCollector?.status === "STANDBY" ? "accent" : "warning") : STATUS_VARIANT[selected.status]}>
                    {effectiveCollected ? titleCase(selectedCollector!.status) : titleCase(selected.status)}
                  </Badge>
                  <Badge variant={LIFECYCLE_VARIANT[selected.lifecycle_state]}>{titleCase(selected.lifecycle_state)}</Badge>
                  {selectedCollector?.status === "STANDBY"
                    ? <Badge variant="accent">غير مقاس</Badge>
                    : <Badge variant={HEALTH_VARIANT[selected.health_status]}>{titleCase(selected.health_status)}</Badge>}
                  <Badge variant={ACTIVATION_VARIANT[selected.activation_status]}>{titleCase(selected.activation_status)}</Badge>
                </div>

                <div className={styles.grid}>
                  <StatTile label="حديث" value={truthById.get(selected.id)?.fresh ? "نعم" : "لا"} />
                  <StatTile label="السجلات المنتجة" value={truthById.get(selected.id)?.produced_records ?? 0} />
                  <StatTile label="صالح قانونيًا" value={truthById.get(selected.id)?.legally_usable ? "نعم" : "لا"} />
                  <StatTile label="مؤيد مستقلًا" value={truthById.get(selected.id)?.corroborated ? "نعم" : "لا"} />
                  <StatTile label="الاكتشاف أو أول تشغيل" value={selectedMetrics?.first_run_at ? formatDate(selectedMetrics.first_run_at) : "—"} />
                  <StatTile label="آخر تشغيل" value={selectedMetrics?.last_run_at ? formatDate(selectedMetrics.last_run_at) : "—"} />
                  <StatTile label="إجمالي التشغيلات" value={selectedMetrics?.runs_total ?? 0} />
                  <StatTile label="مستندات آخر تشغيل" value={selectedCollector?.documents_fetched ?? "—"} />
                  <StatTile label="مدمج عبر" value={selected.integrated_via ?? selected.collector ?? "—"} />
                  <StatTile label="قدرات القرار" value={selected.integrated_capabilities.length ? selected.integrated_capabilities.map(sourceTokenLabel).join("، ") : "—"} />
                  <StatTile label="التأخر المتوقع" value={selected.expected_latency || "—"} />
                  <StatTile
                    label="درجة التحقق"
                    value={selected.data_quality_score != null ? formatPercent(selected.data_quality_score) : "—"}
                  />
                </div>

                <div className={styles.block}>
                  <div className={styles.blockTitle}>أبعاد السمعة</div>
                  {!selectedMetrics?.reputation ? (
                    <EmptyState title="لا توجد بيانات سمعة بعد" detail="تظهر أبعاد السمعة بعد تشغيل المصدر مرة واحدة على الأقل." />
                  ) : (
                    <>
                      {(
                        [
                          ["availability", "التوفر"],
                          ["coverage", "التغطية"],
                          ["freshness", "الحداثة"],
                          ["latency", "التأخر"],
                          ["accuracy", "الدقة"],
                          ["schema_stability", "ثبات البنية"],
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
                    <div className={styles.blockTitle}>ملاحظات</div>
                    <p className={styles.notes}>{selected.notes}</p>
                  </div>
                )}
              </div>
            )}
          </Card>
          </div>
        </>
      )}
    </Section>
  );
}

function sourceTokenLabel(value: string): string {
  const labels: Record<string, string> = {
    active: "نشط", candidate: "مرشح", probation: "اختباري", rejected: "مرفوض",
    healthy: "سليم", degraded: "متراجع", down: "متوقف", unknown: "غير معروف",
    implemented: "منفذ", planned: "مخطط", needs_key: "يحتاج مفتاحًا", tos_review: "مراجعة شروط الاستخدام",
    prices: "أسعار", macro: "اقتصاد كلي", news: "أخبار", disclosures: "إفصاحات",
    financials: "قوائم مالية", universe: "نطاق الأسهم", reference: "مرجعي",
    active_source: "مصدر نشط", monitoring: "مراقبة", retired: "مسحوب",
  };
  return labels[value.toLowerCase()] ?? titleCase(value);
}
