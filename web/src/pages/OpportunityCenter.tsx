import { useState } from "react";
import { Link } from "react-router-dom";
import { Badge } from "../components/primitives/Badge";
import { Card } from "../components/primitives/Card";
import { DataTable } from "../components/primitives/DataTable";
import { Meter } from "../components/primitives/Meter";
import { Section } from "../components/primitives/Section";
import { StatTile } from "../components/primitives/StatTile";
import { EmptyState, ErrorState, LoadingState } from "../components/primitives/States";
import { useArtifact } from "../hooks/useArtifact";
import { formatDate, formatPercent, formatSignedPercent, titleCase } from "../lib/format";
import type { CorporateEvent, DecisionReadiness, Horizon, HorizonDecision, Recommendation, TickerDataGapReport } from "../types";
import styles from "./OpportunityCenter.module.css";

const HORIZON_ORDER: Horizon[] = ["micro", "swing", "investment"];

/** Every opportunity AGX currently sees, ranked by confidence -- the
 * mission's "heart of AGX." Selecting a row shows the full explanation
 * inline; "Open full research workspace" goes to the per-company deep
 * page (Company Research Workspace, a later milestone). */
export function OpportunityCenter() {
  const recommendations = useArtifact((p) => p.getRecommendations());
  const marketState = useArtifact((p) => p.getMarketState());
  const readiness = useArtifact((p) => p.getDecisionReadiness());
  const dataGaps = useArtifact((p) => p.getTickerDataGapReport());
  const [selectedTicker, setSelectedTicker] = useState<string | null>(null);

  const ranked = [...(recommendations.data ?? [])].sort(
    (a, b) => bestDecisionScore(b) - bestDecisionScore(a),
  );
  const companyNames = marketState.data?.constituents ?? {};
  const selected = ranked.find((r) => r.ticker === selectedTicker) ?? ranked[0] ?? null;

  const catalystsForSelected: CorporateEvent[] = selected
    ? (marketState.data?.dataset_snapshot.corporate_events[selected.ticker] ?? [])
        .filter((ce) => (marketState.data ? ce.event_date >= marketState.data.as_of : true))
        .sort((a, b) => (a.event_date > b.event_date ? 1 : -1))
    : [];

  return (
    <Section
      title="مركز القرارات"
      description="قرارات بحثية مستقلة لكل أفق، مرتبة بالعائد المعدل بالمخاطر والثقة."
    >
      <div role="alert" style={{ border: "1px solid var(--warning)", padding: "12px", marginBottom: "16px" }}>
        <strong>بيانات تجريبية — ليست توصية استثمارية حالية.</strong>{" "}
        لا يصبح أي قرار صالحًا للنشر قبل بيانات حية موثقة ومراجعة قانونية مستقلة.
      </div>
      {recommendations.loading && <LoadingState rows={4} />}
      {recommendations.error && <ErrorState detail={recommendations.error.message} onRetry={recommendations.reload} />}

      {!recommendations.loading && !recommendations.error && (
        <div className={styles.layout}>
          <Card dense>
            <DataTable
              rows={ranked}
              getRowKey={(r) => r.ticker}
              onRowClick={(r) => setSelectedTicker(r.ticker)}
              emptyTitle="لا توجد قرارات بحثية بعد"
              emptyDetail="يمتنع النظام عند نقص الأدلة بدل اختلاق توصية."
              columns={[
                {
                  key: "ticker",
                  header: "السهم",
                  render: (r) => (
                    <div className={styles.tickerCell}>
                      <span className={styles.tickerCode}>{r.ticker}</span>
                      <span className={styles.tickerCompany}>{companyNames[r.ticker] ?? ""}</span>
                    </div>
                  ),
                },
                {
                  key: "confidence",
                  header: "الثقة",
                  render: (r) => <Meter value={r.confidence} label={formatPercent(r.confidence)} />,
                },
                {
                  key: "return",
                  header: "العائد المتوقع",
                  align: "right",
                  render: (r) => (
                    <span className="num" style={{ color: r.combined_expected_return >= 0 ? "var(--positive)" : "var(--negative)" }}>
                      {formatSignedPercent(r.combined_expected_return)}
                    </span>
                  ),
                },
                {
                  key: "risk",
                  header: "المخاطر المتوقعة",
                  align: "right",
                  render: (r) => <span className="num">{formatPercent(r.combined_expected_risk)}</span>,
                },
                {
                  key: "horizons",
                  header: "الآفاق",
                  render: (r) => (
                    <div className={styles.horizonBadges}>
                      {HORIZON_ORDER.filter((h) => r.horizon_predictions[h]).map((h) => (
                        <Badge key={h} variant="neutral">
                          {titleCase(h)}
                        </Badge>
                      ))}
                    </div>
                  ),
                },
              ]}
            />
          </Card>

          <Card title={selected ? `${selected.ticker} — القرار والأدلة` : "القرار والأدلة"} dense>
            {!selected && <EmptyState title="لم يُحدد سهم" detail="اختر صفًا لرؤية القرار وأدلته كاملة." />}
            {selected && <OpportunityDetail recommendation={selected} companyName={companyNames[selected.ticker]} catalysts={catalystsForSelected} />}
          </Card>
        </div>
      )}

      <Card title="جاهزية القرار" subtitle="لماذا يستطيع AGX البحث أو يجب عليه الامتناع لكل سهم" dense>
        {readiness.loading && <LoadingState rows={4} />}
        {readiness.error && <ErrorState detail={readiness.error.message} onRetry={readiness.reload} />}
        {!readiness.loading && !readiness.error && (
          <DataTable<DecisionReadiness>
            rows={readiness.data ?? []}
            getRowKey={(row) => row.ticker}
            emptyTitle="لا يوجد تقييم جاهزية بعد"
            emptyDetail="يجب تشغيل خط الإنتاج قبل قياس جاهزية الأدلة."
            columns={[
              { key: "ticker", header: "السهم", render: (row) => <span className={styles.tickerCode}>{row.ticker}</span> },
              {
                key: "status",
                header: "الحالة",
                render: (row) => (
                  <Badge variant={row.status === "ready" ? "positive" : row.status === "degraded" ? "warning" : "negative"}>
                    {readinessStatusLabel(row.status)}
                  </Badge>
                ),
              },
              { key: "decision", header: "القرار", render: (row) => row.decision === "researchable" ? "قابل للبحث" : "امتناع" },
              { key: "prices", header: "الأسعار", align: "right", render: (row) => <span className="num">{row.price_observations}</span> },
              { key: "financials", header: "الفترات المالية", align: "right", render: (row) => <span className="num">{row.financial_periods}</span> },
              { key: "knowledge", header: "المعرفة", align: "right", render: (row) => <span className="num">{row.active_knowledge}</span> },
              { key: "blocker", header: "العائق الأساسي", render: (row) => row.blockers[0] ?? "لا يوجد" },
            ]}
          />
        )}
      </Card>

      <Card title="فجوات البيانات حسب السهم" subtitle="ما ينقص القرار تحديدًا، وما الإجراء المجاني التالي" dense>
        {dataGaps.loading && <LoadingState rows={4} />}
        {dataGaps.error && <ErrorState detail={dataGaps.error.message} onRetry={dataGaps.reload} />}
        {!dataGaps.loading && !dataGaps.error && (
          <DataTable<TickerDataGapReport>
            rows={dataGaps.data ?? []}
            getRowKey={(row) => row.ticker}
            emptyTitle="لا يوجد تقرير فجوات بعد"
            emptyDetail="شغّل خط الإنتاج لإنشاء قياس اكتمال مستقل لكل سهم."
            columns={[
              { key: "ticker", header: "السهم", render: (row) => <span className={styles.tickerCode}>{row.ticker}</span> },
              { key: "overall", header: "الاكتمال", render: (row) => <Meter value={row.overall_completeness_pct / 100} label={`${row.overall_completeness_pct.toFixed(0)}%`} /> },
              { key: "layers", header: "الطبقات الناقصة", render: (row) => row.layers.filter((layer) => !layer.complete).map((layer) => layerLabel(layer.layer)).join("، ") || "لا شيء" },
              { key: "horizons", header: "الأفق الجاهز", render: (row) => row.ready_horizons.map(horizonLabel).join("، ") || "امتناع" },
              { key: "action", header: "الإجراء التالي", render: (row) => row.next_actions[0] ?? "لا إجراء" },
            ]}
          />
        )}
      </Card>
    </Section>
  );
}

function OpportunityDetail({
  recommendation,
  companyName,
  catalysts,
}: {
  recommendation: Recommendation;
  companyName: string | undefined;
  catalysts: CorporateEvent[];
}) {
  const { explanation } = recommendation;
  return (
    <div>
      <div className={styles.detailHeader}>
        <span className={styles.detailTicker}>{recommendation.ticker}</span>
        {companyName && <span className={styles.detailCompany}>{companyName}</span>}
      </div>

      <div className={styles.detailStats}>
        <StatTile label="Confidence" value={formatPercent(recommendation.confidence)} />
        <StatTile
          label="Exp. Return"
          value={formatSignedPercent(recommendation.combined_expected_return)}
          deltaSign={recommendation.combined_expected_return >= 0 ? 1 : -1}
        />
        <StatTile label="Exp. Risk" value={formatPercent(recommendation.combined_expected_risk)} />
      </div>

      <div className={styles.block}>
        <div className={styles.blockTitle}>ماذا أفعل الآن؟</div>
        {HORIZON_ORDER.map((horizon) => recommendation.horizon_decisions[horizon])
          .filter((decision): decision is HorizonDecision => Boolean(decision))
          .map((decision) => (
            <div key={decision.horizon} style={{ borderBottom: "1px solid var(--border)", padding: "10px 0" }}>
              <strong>{actionLabel(decision.action)} — {horizonLabel(decision.horizon)}</strong>
              <div>{decision.horizon_window} · صالح حتى {formatDate(decision.valid_until)}</div>
              <div>
                عائد {formatSignedPercent(decision.expected_return)} · مخاطر {formatPercent(decision.expected_risk)} ·
                ثقة {formatPercent(decision.confidence)}
              </div>
              <div>{decision.entry_condition}</div>
              {decision.entry_value !== null && (
                <div>الدخول ≤ {decision.entry_value.toFixed(2)} جنيه · الإبطال &lt; {decision.invalidation_value?.toFixed(2)} جنيه</div>
              )}
              <div>المراجعة: {decision.review_condition}</div>
              <div>
                حد المخاطر: {decision.publication_status === "publication_ready"
                  ? formatPercent(decision.max_position_pct)
                  : "0% — غير قابل للتنفيذ"}
              </div>
              {decision.publication_status === "research_only" && <Badge variant="warning">بحث فقط</Badge>}
            </div>
          ))}
      </div>

      <div className={styles.block}>
        <div className={styles.blockTitle}>ملخص البحث</div>
        <p className={styles.blockText}>{explanation.why_this_stock} {explanation.why_now}</p>
      </div>

      <div className={styles.block}>
        <div className={styles.blockTitle}>ملخص المخاطر</div>
        <p className={styles.blockText}>{explanation.why_not_others}</p>
      </div>

      <div className={styles.block}>
        <div className={styles.blockTitle}>الأدلة المؤيدة</div>
        {explanation.supporting_evidence.length === 0 ? (
          <span className={styles.blockText}>لا توجد أدلة مسجلة.</span>
        ) : (
          <ul className={styles.bulletList}>
            {explanation.supporting_evidence.map((e, i) => (
              <li key={i}>{e}</li>
            ))}
          </ul>
        )}
      </div>

      <div className={styles.block}>
        <div className={styles.blockTitle}>مراجع الأدلة القابلة للتتبع</div>
        {explanation.evidence_refs.length === 0 ? (
          <span className={styles.blockText}>لا توجد مراجع؛ لا يُعامل الملخص كقرار قابل للنشر.</span>
        ) : (
          <ul className={styles.bulletList}>
            {explanation.evidence_refs.map((ref, i) => (
              <li key={`${ref.kind}-${ref.ref_id}-${i}`}>
                النوع: {evidenceKindLabel(ref.kind)} · المعرّف: <code>{ref.ref_id}</code>
                {ref.ref_version !== null ? ` · الإصدار: ${ref.ref_version}` : ""}
              </li>
            ))}
          </ul>
        )}
      </div>

      <div className={styles.block}>
        <div className={styles.blockTitle}>الأدلة المخالفة وشروط الإبطال</div>
        {explanation.invalidation_conditions.length === 0 ? (
          <span className={styles.blockText}>لا توجد شروط مسجلة.</span>
        ) : (
          <ul className={styles.bulletList}>
            {explanation.invalidation_conditions.map((e, i) => (
              <li key={i}>{e}</li>
            ))}
          </ul>
        )}
      </div>

      <div className={styles.block}>
        <div className={styles.blockTitle}>الحالات التاريخية المشابهة</div>
        {explanation.similar_historical_cases.length === 0 ? (
          <span className={styles.blockText}>لا توجد حالات مسجلة.</span>
        ) : (
          <ul className={styles.bulletList}>
            {explanation.similar_historical_cases.map((e, i) => (
              <li key={i}>{e}</li>
            ))}
          </ul>
        )}
      </div>

      <div className={styles.block}>
        <div className={styles.blockTitle}>المحفزات القادمة</div>
        {catalysts.length === 0 ? (
          <span className={styles.blockText}>لا توجد محفزات مجدولة.</span>
        ) : (
          <ul className={styles.bulletList}>
            {catalysts.map((c, i) => (
              <li key={i}>
                {formatDate(c.event_date)} — {titleCase(c.event_type)}: {c.description}
              </li>
            ))}
          </ul>
        )}
      </div>

      <Link className={styles.workspaceLink} to={`/company/${recommendation.ticker}`}>
        افتح مساحة البحث الكاملة ←
      </Link>
    </div>
  );
}

function layerLabel(layer: TickerDataGapReport["layers"][number]["layer"]): string {
  return ({ financials: "القوائم المالية", disclosures: "الإفصاحات", news: "الأخبار", macro: "الاقتصاد الكلي", knowledge: "المعرفة المختبرة" })[layer];
}

function readinessStatusLabel(status: DecisionReadiness["status"]): string {
  return ({ ready: "جاهز", degraded: "ناقص", blocked: "محظور" })[status];
}

function evidenceKindLabel(kind: string): string {
  return ({ knowledge: "معرفة مختبرة", prediction: "تنبؤ", dataset_snapshot: "لقطة بيانات", event: "حدث", raw_document: "مستند خام", source: "مصدر" } as Record<string, string>)[kind] ?? kind;
}

function bestDecisionScore(recommendation: Recommendation): number {
  const decisions = Object.values(recommendation.horizon_decisions).filter(
    (decision): decision is HorizonDecision => Boolean(decision),
  );
  return decisions.length
    ? Math.max(...decisions.map((decision) => decision.risk_adjusted_score))
    : Number.NEGATIVE_INFINITY;
}

function actionLabel(action: HorizonDecision["action"]): string {
  return {
    buy_candidate: "مرشح شراء مشروط",
    watch: "راقب",
    avoid: "تجنب",
    abstain: "امتناع",
  }[action];
}

function horizonLabel(horizon: Horizon): string {
  return { micro: "قصير", swing: "متوسط", investment: "استثماري" }[horizon];
}
