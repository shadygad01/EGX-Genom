import { Link, useNavigate } from "react-router-dom";
import { Badge, type BadgeVariant } from "../components/primitives/Badge";
import { Card } from "../components/primitives/Card";
import { DataTable } from "../components/primitives/DataTable";
import { Meter } from "../components/primitives/Meter";
import { Section } from "../components/primitives/Section";
import { StatTile } from "../components/primitives/StatTile";
import { EmptyState, ErrorState, LoadingState } from "../components/primitives/States";
import { useArtifact } from "../hooks/useArtifact";
import {
  formatDate,
  formatDateTime,
  formatSignedPercent,
  formatPercent,
  titleCase,
} from "../lib/format";
import type { CorporateEvent, Event, EventSeverity, HorizonDecision, KnowledgeStatus, NewsItem, Recommendation } from "../types";
import styles from "./AIBriefing.module.css";

const SEVERITY_VARIANT: Record<EventSeverity, BadgeVariant> = {
  critical: "negative",
  high: "negative",
  medium: "warning",
  low: "neutral",
};

const KNOWLEDGE_VARIANT: Record<KnowledgeStatus, BadgeVariant> = {
  promoted: "positive",
  monitoring: "accent",
  retired: "neutral",
};

/** The landing page and signature experience: everything a portfolio
 * manager needs to know before the market opens, generated entirely from
 * already-produced AGX artifacts -- no calculation happens on this page. */
export function AIBriefing() {
  const navigate = useNavigate();
  const systemStatus = useArtifact((p) => p.getSystemStatus());
  const marketState = useArtifact((p) => p.getMarketState());
  const recommendations = useArtifact((p) => p.getRecommendations());
  const events = useArtifact((p) => p.getEvents());
  const knowledge = useArtifact((p) => p.getKnowledge());
  const papers = useArtifact((p) => p.getPapers());
  const investmentCases = useArtifact((p) => p.getInvestmentCases());
  const executionReport = useArtifact((p) => p.getExecutionReport());
  const decisionPerformance = useArtifact((p) => p.getDecisionPerformance());
  const publicationGate = useArtifact((p) => p.getPublicationGate());

  const topOpportunities = publicationGate.data?.publication_ready ? [...(recommendations.data ?? [])]
    .filter((recommendation) => Object.values(recommendation.horizon_decisions).some(
      (decision) => decision?.publication_status === "publication_ready"
        && decision.action !== "abstain",
    ))
    .sort((a, b) => bestDecisionScore(b) - bestDecisionScore(a))
    .slice(0, 5) : [];

  const elevatedEvents = [...(events.data ?? [])]
    .filter((e) => e.severity === "high" || e.severity === "critical")
    .sort((a, b) => (a.event_date < b.event_date ? 1 : -1))
    .slice(0, 5);

  const news: NewsItem[] = [...(marketState.data?.dataset_snapshot.news ?? [])]
    .sort((a, b) => (a.published_at < b.published_at ? 1 : -1))
    .slice(0, 5);

  const asOf = marketState.data?.as_of ?? null;
  const upcomingCatalysts: CorporateEvent[] = Object.values(
    marketState.data?.dataset_snapshot.corporate_events ?? {},
  )
    .flat()
    .filter((ce) => (asOf ? ce.event_date >= asOf : true))
    .sort((a, b) => (a.event_date > b.event_date ? 1 : -1))
    .slice(0, 5);

  const recentKnowledge = [...(knowledge.data ?? [])]
    .sort((a, b) => (a.discovery_date < b.discovery_date ? 1 : -1))
    .slice(0, 5);

  const recentPapers = [...(papers.data ?? [])]
    .sort((a, b) => (a.published_at < b.published_at ? 1 : -1))
    .slice(0, 5);

  return (
    <>
      <Section
        title="ملخص القرار"
        description="ما الذي يمكن فعله الآن، لكل أفق، مع إثبات الأداء أو التصريح بعدم كفاية العينة."
      >
        <div role="alert" style={{ border: "1px solid var(--warning)", padding: "12px", marginBottom: "16px" }}>
          <strong>بحث فقط — بيانات تجريبية.</strong> لا توجد توصية صالحة للنشر قبل اجتياز بوابات البيانات الحية والمراجعة القانونية.
        </div>
        {publicationGate.data && (
          <Card
            title={publicationGate.data.publication_ready ? "بوابة النشر: مجتازة" : "بوابة النشر: محظورة"}
            subtitle={`آخر تقييم: ${formatDate(publicationGate.data.as_of)}`}
            dense
          >
            <ul>
              {publicationGate.data.checks.map((check) => (
                <li key={check.id}>
                  {check.passed ? "✓" : "✕"} {check.label}
                  {!check.passed && check.blocker ? ` — ${check.blocker}` : ""}
                </li>
              ))}
            </ul>
          </Card>
        )}
        {topOpportunities.length === 0 ? (
          <EmptyState title="امتناع" detail="لا توجد قرارات اجتازت بوابات الأدلة الحالية." />
        ) : (
          <DataTable
            rows={topOpportunities}
            getRowKey={(row) => row.ticker}
            columns={[
              { key: "ticker", header: "السهم", render: (row) => row.ticker },
              { key: "action", header: "القرار", render: (row) => bestDecision(row)?.action ?? "abstain" },
              { key: "horizon", header: "الأفق", render: (row) => bestDecision(row)?.horizon_window ?? "—" },
              { key: "valid", header: "صالح حتى", render: (row) => formatDate(bestDecision(row)?.valid_until ?? null) },
              { key: "score", header: "درجة المخاطر", align: "right", render: (row) => bestDecision(row)?.risk_adjusted_score.toFixed(2) ?? "—" },
            ]}
          />
        )}
        <Card title="إثبات الأداء" subtitle="لا تُعرض نسبة نجاح كدليل حتى تتوفر 30 نتيجة مقيمة على الأقل لكل أفق" dense>
          {decisionPerformance.loading && <LoadingState />}
          {!decisionPerformance.loading && (decisionPerformance.data ?? []).length === 0 && (
            <EmptyState title="لا يوجد سجل أداء بعد" detail="سيظهر الأداء بعد انتهاء صلاحية القرارات وتقييم نتائجها تلقائيًا." />
          )}
          {(decisionPerformance.data ?? []).length > 0 && (
            <DataTable
              rows={decisionPerformance.data ?? []}
              getRowKey={(row) => row.horizon}
              columns={[
                { key: "horizon", header: "الأفق", render: (row) => titleCase(row.horizon) },
                { key: "evaluated", header: "مقيّمة", align: "right", render: (row) => row.evaluated },
                { key: "hit", header: "نسبة التفوق", render: (row) => row.sample_status === "sufficient" && row.hit_rate != null ? formatPercent(row.hit_rate) : row.sample_status === "insufficient_benchmark" ? "المؤشر غير مكتمل" : "عينة غير كافية" },
                { key: "realized", header: "العائد المحقق", render: (row) => row.mean_realized_return != null ? formatSignedPercent(row.mean_realized_return) : "—" },
                { key: "excess", header: "فوق EGX30", render: (row) => row.sample_status === "sufficient" && row.mean_excess_return != null ? formatSignedPercent(row.mean_excess_return) : "—" },
              ]}
            />
          )}
        </Card>
      </Section>

      <Section
        title="صحة النظام"
        description="حالة تنفيذ خط الإنتاج في أحدث دورة بحث."
      >
        {systemStatus.loading && <LoadingState rows={1} />}
        {systemStatus.error && <ErrorState detail={systemStatus.error.message} onRetry={systemStatus.reload} />}
        {systemStatus.data && (
          <div className={styles.statGrid}>
            <StatTile label="آخر دورة" value={formatDate(systemStatus.data.pipeline_run_date)} />
            <StatTile label="مرات التشغيل" value={systemStatus.data.runs} />
            <StatTile
              label="الناجحة"
              value={systemStatus.data.succeeded}
              deltaSign={systemStatus.data.failed > 0 ? -1 : 1}
              delta={systemStatus.data.failed > 0 ? `${systemStatus.data.failed} فاشلة` : "كلها سليمة"}
            />
            <StatTile label="كائنات المعرفة" value={systemStatus.data.knowledge_objects} />
            {Object.entries(systemStatus.data.by_status).map(([status, count]) => (
              <StatTile key={status} label={titleCase(status)} value={count} />
            ))}
          </div>
        )}
      </Section>

      {executionReport.data && (
        <Section
          title="التغييرات منذ الدورة السابقة"
          description="صافي التغير في المعرفة والاكتشافات الناتج عن آخر تشغيل كامل."
        >
          <div className={styles.statGrid}>
            <StatTile
              label="كائنات المعرفة"
              value={executionReport.data.knowledge_after}
              deltaSign={Math.sign(executionReport.data.knowledge_after - executionReport.data.knowledge_before)}
              delta={`${executionReport.data.knowledge_after - executionReport.data.knowledge_before >= 0 ? "+" : ""}${
                executionReport.data.knowledge_after - executionReport.data.knowledge_before
              } منذ آخر تشغيل`}
            />
            <StatTile
              label="الجينات البحثية"
              value={executionReport.data.genome_after}
              deltaSign={Math.sign(executionReport.data.genome_after - executionReport.data.genome_before)}
              delta={`${executionReport.data.genome_after - executionReport.data.genome_before >= 0 ? "+" : ""}${
                executionReport.data.genome_after - executionReport.data.genome_before
              } منذ آخر تشغيل`}
            />
            <StatTile
              label="الأحداث"
              value={executionReport.data.events_after}
              deltaSign={Math.sign(executionReport.data.events_after - executionReport.data.events_before)}
              delta={`${executionReport.data.events_after - executionReport.data.events_before >= 0 ? "+" : ""}${
                executionReport.data.events_after - executionReport.data.events_before
              } منذ آخر تشغيل`}
            />
            <StatTile label="حالة خط الإنتاج" value={titleCase(executionReport.data.overall_status)} />
          </div>
          {executionReport.data.errors.length > 0 && (
            <div className={styles.list} style={{ marginTop: "var(--space-4)" }}>
              {executionReport.data.errors.map((e, i) => (
                <div key={i} className={styles.listItemDetail}>
                  <Badge variant="negative">خطأ</Badge> {e}
                </div>
              ))}
            </div>
          )}
        </Section>
      )}

      <Section title="ملخص السوق" description="جلسة التداول ونطاق الأسهم في آخر دورة.">
        {marketState.loading && <LoadingState rows={1} />}
        {marketState.error && <ErrorState detail={marketState.error.message} onRetry={marketState.reload} />}
        {marketState.data === null && !marketState.loading && !marketState.error && (
          <EmptyState title="لا توجد حالة سوق بعد" detail="تظهر بعد تشغيل أول دورة بحث." />
        )}
        {marketState.data && (
          <div className={styles.statGrid}>
            <StatTile label="حتى تاريخ" value={formatDate(marketState.data.as_of)} />
            <StatTile
              label="جلسة التداول"
              value={marketState.data.trading_session.is_trading_day ? "مفتوحة" : "مغلقة"}
              caption={marketState.data.trading_session.holiday_name ?? undefined}
            />
            <StatTile label="الأسهم" value={Object.keys(marketState.data.constituents).length} />
            <StatTile label="القطاعات" value={new Set(Object.values(marketState.data.sectors)).size} />
          </div>
        )}
      </Section>

      <div className={styles.twoCol}>
        <Card title="أبرز الفرص" subtitle="مرتبة حسب ثقة AGX">
          {recommendations.loading && <LoadingState />}
          {recommendations.error && <ErrorState detail={recommendations.error.message} onRetry={recommendations.reload} />}
          {!recommendations.loading && !recommendations.error && (
            <DataTable
              rows={topOpportunities}
              getRowKey={(r) => r.ticker}
              onRowClick={(r) => navigate(`/company/${r.ticker}`)}
              emptyTitle="لا توجد فرص بعد"
              emptyDetail="تظهر القرارات بعد أن يجمع محرك القرار تنبؤات الآفاق."
              columns={[
                {
                  key: "ticker",
                  header: "السهم",
                  render: (r) => <span style={{ color: "var(--accent-strong)", fontWeight: 600 }}>{r.ticker}</span>,
                },
                { key: "confidence", header: "الثقة", render: (r) => <Meter value={r.confidence} label={formatPercent(r.confidence)} /> },
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
                { key: "risk", header: "المخاطر المتوقعة", align: "right", render: (r) => <span className="num">{formatPercent(r.combined_expected_risk)}</span> },
              ]}
            />
          )}
        </Card>

        <Card title="أكبر المخاطر" subtitle="الأحداث عالية وحرجة الشدة قيد المتابعة">
          {events.loading && <LoadingState />}
          {events.error && <ErrorState detail={events.error.message} onRetry={events.reload} />}
          {!events.loading && !events.error && elevatedEvents.length === 0 && (
            <EmptyState title="لا توجد أحداث مرتفعة الشدة" detail="لا يوجد حاليًا حدث مصنف عاليًا أو حرجًا." />
          )}
          {elevatedEvents.length > 0 && (
            <div className={styles.list}>
              {elevatedEvents.map((e: Event) => (
                <div key={e.id} className={styles.listItem}>
                  <div className={styles.listItemHead}>
                    <span className={styles.listItemTitle}>
                      {e.entities.map((ent) => ent.display_name ?? ent.raw_mention).join(", ") || titleCase(e.subtype)}
                    </span>
                    <span className={styles.listItemMeta}>{formatDate(e.event_date)}</span>
                  </div>
                  <div className={styles.badgeRow}>
                    <Badge variant={SEVERITY_VARIANT[e.severity]}>{titleCase(e.severity)}</Badge>
                    <Badge variant="neutral">{titleCase(e.event_type)}</Badge>
                  </div>
                  <span className={styles.listItemDetail}>{titleCase(e.subtype)} · {titleCase(e.status)}</span>
                </div>
              ))}
            </div>
          )}
        </Card>

        <Card title="أهم الأخبار" subtitle="أحدث العناوين من المصادر التي يراقبها AGX">
          {marketState.loading && <LoadingState />}
          {!marketState.loading && news.length === 0 && (
            <EmptyState title="لا توجد أخبار بعد" detail="تظهر الأخبار بعد استيعابها في دورة جمع البيانات." />
          )}
          {news.length > 0 && (
            <div className={styles.list}>
              {news.map((n, i) => (
                <div key={i} className={styles.listItem}>
                  <div className={styles.listItemHead}>
                    <span className={styles.listItemTitle}>{n.headline}</span>
                    <span className={styles.listItemMeta}>{formatDateTime(n.published_at)}</span>
                  </div>
                  <span className={styles.listItemDetail}>
                    {n.source}
                    {n.tickers.length > 0 ? ` · ${n.tickers.join(", ")}` : ""}
                  </span>
                </div>
              ))}
            </div>
          )}
        </Card>

        <Card title="المحفزات القادمة" subtitle="الأحداث المؤسسية المجدولة من تاريخ آخر دورة فصاعدًا">
          {marketState.loading && <LoadingState />}
          {!marketState.loading && upcomingCatalysts.length === 0 && (
            <EmptyState title="لا توجد محفزات مجدولة" detail="لا توجد أحداث مؤسسية قادمة معروفة لنطاق الأسهم المغطى." />
          )}
          {upcomingCatalysts.length > 0 && (
            <div className={styles.list}>
              {upcomingCatalysts.map((ce, i) => (
                <div key={i} className={styles.listItem}>
                  <div className={styles.listItemHead}>
                    <span className={styles.listItemTitle}>{ce.ticker} — {titleCase(ce.event_type)}</span>
                    <span className={styles.listItemMeta}>{formatDate(ce.event_date)}</span>
                  </div>
                  <span className={styles.listItemDetail}>{ce.description}</span>
                </div>
              ))}
            </div>
          )}
        </Card>

        <Card title="تغييرات المعرفة" subtitle="أحدث كائنات المعرفة اكتشافًا أو تحديثًا">
          {knowledge.loading && <LoadingState />}
          {knowledge.error && <ErrorState detail={knowledge.error.message} onRetry={knowledge.reload} />}
          {!knowledge.loading && !knowledge.error && recentKnowledge.length === 0 && (
            <EmptyState title="لا توجد كائنات معرفة بعد" detail="تظهر المعرفة المرقّاة أو المراقبة هنا بعد اكتشافها." />
          )}
          {recentKnowledge.length > 0 && (
            <div className={styles.list}>
              {recentKnowledge.map((k) => (
                <div key={k.id} className={styles.listItem}>
                  <div className={styles.listItemHead}>
                    <span className={styles.listItemTitle}>{k.affected_assets.join(", ")}</span>
                    <span className={styles.listItemMeta}>{formatDate(k.discovery_date)}</span>
                  </div>
                  <div className={styles.badgeRow}>
                    <Badge variant={KNOWLEDGE_VARIANT[k.status]}>{titleCase(k.status)}</Badge>
                    <Badge variant="neutral">{titleCase(k.horizon)}</Badge>
                  </div>
                  <span className={styles.listItemDetail}>{k.economic_explanation}</span>
                </div>
              ))}
            </div>
          )}
        </Card>

        <Card title="الاكتشافات العلمية" subtitle="أحدث الأوراق البحثية المنشورة">
          {papers.loading && <LoadingState />}
          {papers.error && <ErrorState detail={papers.error.message} onRetry={papers.reload} />}
          {!papers.loading && !papers.error && recentPapers.length === 0 && (
            <EmptyState title="لا توجد أوراق بعد" detail="تُنتج الأوراق بعد ترقية فرضية إلى معرفة." />
          )}
          {recentPapers.length > 0 && (
            <div className={styles.list}>
              {recentPapers.map((p) => (
                <div key={p.id} className={styles.listItem}>
                  <div className={styles.listItemHead}>
                    <span className={styles.listItemTitle}>{p.title}</span>
                    <span className={styles.listItemMeta}>{formatDate(p.published_at)}</span>
                  </div>
                  <span className={styles.listItemDetail}>{p.conclusion}</span>
                </div>
              ))}
            </div>
          )}
        </Card>
      </div>

      <Section title="المحفظة" description="التخصيص الحالي على مستوى المحفظة إن كان محرك القرار قد أنتجه.">
        {investmentCases.loading && <LoadingState />}
        {investmentCases.error && <ErrorState detail={investmentCases.error.message} onRetry={investmentCases.reload} />}
        {!investmentCases.loading && !investmentCases.error && investmentCases.data?.portfolio == null && (
          <EmptyState title="لا يوجد تخصيص محفظة بعد" detail="يظهر التخصيص بعد تشغيل كامل لخط الإنتاج واجتياز بوابة النشر." />
        )}
        {investmentCases.data?.portfolio && (
          <DataTable
            rows={investmentCases.data.portfolio.positions}
            getRowKey={(p) => p.ticker}
            columns={[
              {
                key: "ticker",
                header: "السهم",
                render: (p) => (
                  <Link to={`/company/${p.ticker}`} style={{ color: "var(--accent-strong)", fontWeight: 600 }}>
                    {p.ticker}
                  </Link>
                ),
              },
              { key: "weight", header: "الوزن", align: "right", render: (p) => <span className="num">{formatPercent(p.weight)}</span> },
              { key: "confidence", header: "الثقة", render: (p) => <Meter value={p.confidence} label={formatPercent(p.confidence)} /> },
              {
                key: "return",
                header: "العائد المتوقع",
                align: "right",
                render: (p) => (
                  <span className="num" style={{ color: p.expected_return >= 0 ? "var(--positive)" : "var(--negative)" }}>
                    {formatSignedPercent(p.expected_return)}
                  </span>
                ),
              },
            ]}
          />
        )}
        {investmentCases.data?.portfolio && (
          <div className={styles.statGrid} style={{ marginTop: "var(--space-4)" }}>
            <StatTile label="وزن النقد" value={formatPercent(investmentCases.data.portfolio.cash_weight)} />
            <StatTile label="Positions" value={investmentCases.data.portfolio.positions.length} />
          </div>
        )}
      </Section>
    </>
  );
}

function bestDecision(recommendation: Recommendation): HorizonDecision | null {
  const decisions = Object.values(recommendation.horizon_decisions).filter(
    (decision): decision is HorizonDecision => Boolean(decision)
      && decision.publication_status === "publication_ready"
      && decision.action !== "abstain",
  );
  return decisions.reduce<HorizonDecision | null>(
    (best, decision) => !best || decision.risk_adjusted_score > best.risk_adjusted_score ? decision : best,
    null,
  );
}

function bestDecisionScore(recommendation: Recommendation): number {
  return bestDecision(recommendation)?.risk_adjusted_score ?? Number.NEGATIVE_INFINITY;
}
