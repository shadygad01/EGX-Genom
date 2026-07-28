import { useParams } from "react-router-dom";
import { Badge, type BadgeVariant } from "../components/primitives/Badge";
import { Card } from "../components/primitives/Card";
import { DataTable } from "../components/primitives/DataTable";
import { Section } from "../components/primitives/Section";
import { EmptyState, ErrorState, LoadingState } from "../components/primitives/States";
import { useArtifact } from "../hooks/useArtifact";
import {
  formatDate,
  formatDateTime,
  formatNumber,
  formatPercent,
  formatSignedPercent,
  titleCase,
} from "../lib/format";
import type { GeneStatus, Horizon, HorizonDecision, KnowledgeStatus } from "../types";
import styles from "./CompanyWorkspace.module.css";

const KNOWLEDGE_VARIANT: Record<KnowledgeStatus, BadgeVariant> = {
  promoted: "positive",
  monitoring: "accent",
  retired: "neutral",
};

const HORIZON_ORDER: Horizon[] = ["micro", "swing", "investment"];

const GENE_VARIANT: Record<GeneStatus, BadgeVariant> = {
  promoted: "positive",
  monitoring: "accent",
  replaced: "warning",
  retired: "neutral",
};

function actionLabel(action: HorizonDecision["action"]): string {
  return {
    buy_candidate: "مرشح شراء مشروط",
    watch: "راقب",
    avoid: "تجنب",
    abstain: "امتناع",
  }[action];
}

function horizonLabel(horizon: Horizon): string {
  return { micro: "قصير", swing: "متوسط", investment: "طويل" }[horizon];
}

/** The per-company deep-dive: every recommendation must be explainable, so
 * this page assembles everything AGX knows about one ticker from already-
 * exported artifacts -- no calculation happens here either. */
export function CompanyWorkspace() {
  const { ticker = "" } = useParams<{ ticker: string }>();

  const marketState = useArtifact((p) => p.getMarketState());
  const recommendations = useArtifact((p) => p.getRecommendations());
  const knowledge = useArtifact((p) => p.getKnowledge());
  const financialStatements = useArtifact((p) => p.getFinancialStatements());
  const papers = useArtifact((p) => p.getPapers());
  const genes = useArtifact((p) => p.getGenes());

  const companyName = marketState.data?.constituents[ticker];
  const sector = marketState.data?.sectors[ticker];
  const asOf = marketState.data?.as_of ?? null;

  const recommendation = recommendations.data?.find((r) => r.ticker === ticker) ?? null;

  const tickerKnowledge = (knowledge.data ?? [])
    .filter((k) => k.affected_assets.includes(ticker))
    .sort((a, b) => (a.discovery_date < b.discovery_date ? 1 : -1));
  const tickerKnowledgeIds = new Set(tickerKnowledge.map((k) => k.id));

  const tickerPapers = (papers.data ?? [])
    .filter((p) => tickerKnowledgeIds.has(p.knowledge_id))
    .sort((a, b) => (a.published_at < b.published_at ? 1 : -1));

  const tickerGenes = (genes.data ?? []).filter((g) => tickerKnowledgeIds.has(g.knowledge_id));

  const tickerStatements = (financialStatements.data ?? [])
    .filter((f) => f.ticker === ticker)
    .sort((a, b) => (a.period_end_date > b.period_end_date ? -1 : 1));

  const allCorporateEvents = marketState.data?.dataset_snapshot.corporate_events[ticker] ?? [];
  const pastActions = allCorporateEvents
    .filter((ce) => (asOf ? ce.event_date < asOf : false))
    .sort((a, b) => (a.event_date > b.event_date ? -1 : 1));
  const upcomingCatalysts = allCorporateEvents
    .filter((ce) => (asOf ? ce.event_date >= asOf : true))
    .sort((a, b) => (a.event_date > b.event_date ? 1 : -1));

  const news = (marketState.data?.dataset_snapshot.news ?? [])
    .filter((n) => n.tickers.includes(ticker))
    .sort((a, b) => (a.published_at < b.published_at ? 1 : -1));

  const loading = marketState.loading || recommendations.loading || knowledge.loading;

  return (
    <>
      <div className={styles.header}>
        <div className={styles.headerLeft}>
          <span className={styles.ticker}>{ticker}</span>
          {companyName && <span className={styles.company}>{companyName}</span>}
        </div>
        <div className={styles.headerMeta}>
          {sector && <Badge variant="neutral">{sector}</Badge>}
        </div>
      </div>

      {loading && <LoadingState rows={4} />}

      <div className={styles.twoCol}>
        <Card title="القرار حسب الأفق">
          {!recommendation && !recommendations.loading && (
            <EmptyState
              title="لا يوجد قرار نشط"
              detail="لا يملك AGX قرارًا حاليًا لهذا السهم؛ قد لا يكون اجتاز التحقق أو لا توجد معرفة مؤيدة كافية."
            />
          )}
          {recommendation && (
            <div>
              {HORIZON_ORDER.map((horizon) => recommendation.horizon_decisions[horizon])
                .filter((decision): decision is HorizonDecision => Boolean(decision))
                .map((decision) => (
                  <div className={styles.block} key={decision.horizon}>
                    <div className={styles.blockTitle}>
                      {horizonLabel(decision.horizon)} — {actionLabel(decision.action)}
                    </div>
                    <p className={styles.blockText}>
                      الحالة: {decision.publication_status === "publication_ready" ? "قابل للنشر" : "بحث فقط — لا تنفذ"}
                      {" · "}صالح حتى {formatDate(decision.valid_until)}
                    </p>
                    <p className={styles.blockText}>
                      عائد {formatSignedPercent(decision.expected_return)} · مخاطر {formatPercent(decision.expected_risk)} · ثقة {formatPercent(decision.confidence)}
                    </p>
                    <p className={styles.blockText}>شرط الدخول: {decision.entry_condition}</p>
                    {decision.entry_value !== null && (
                      <p className={styles.blockText}>
                        سعر الدخول الأقصى: {decision.entry_value.toFixed(2)} جنيه · إبطال أسفل {decision.invalidation_value?.toFixed(2)} جنيه
                      </p>
                    )}
                    <p className={styles.blockText}>موعد المراجعة: {decision.review_condition}</p>
                    <p className={styles.blockText}>
                      حد المخاطر: {decision.publication_status === "publication_ready" ? formatPercent(decision.max_position_pct) : "0%"}
                    </p>
                    {decision.invalidation_conditions.length > 0 && (
                      <ul className={styles.bulletList}>
                        {decision.invalidation_conditions.map((condition) => <li key={condition}>{condition}</li>)}
                      </ul>
                    )}
                  </div>
                ))}

              <div className={styles.block}>
                <div className={styles.blockTitle}>ملخص البحث</div>
                <p className={styles.blockText}>
                  {recommendation.explanation.why_this_stock} {recommendation.explanation.why_now}
                </p>
              </div>

              <div className={styles.block}>
                <div className={styles.blockTitle}>ملخص المخاطر</div>
                <p className={styles.blockText}>{recommendation.explanation.why_not_others}</p>
              </div>

              <div className={styles.block}>
                <div className={styles.blockTitle}>الأدلة المؤيدة</div>
                {recommendation.explanation.supporting_evidence.length === 0 ? (
                  <span className={styles.blockText}>لا توجد أدلة مسجلة.</span>
                ) : (
                  <ul className={styles.bulletList}>
                    {recommendation.explanation.supporting_evidence.map((e, i) => (
                      <li key={i}>{e}</li>
                    ))}
                  </ul>
                )}
              </div>

              <div className={styles.block}>
                <div className={styles.blockTitle}>مراجع الأدلة القابلة للتتبع</div>
                {recommendation.explanation.evidence_refs.length === 0 ? (
                  <span className={styles.blockText}>لا توجد مراجع؛ لا يُعامل الملخص كقرار قابل للنشر.</span>
                ) : (
                  <ul className={styles.bulletList}>
                    {recommendation.explanation.evidence_refs.map((ref, i) => (
                      <li key={`${ref.kind}-${ref.ref_id}-${i}`}>
                        {ref.kind}: <code>{ref.ref_id}</code>{ref.ref_version !== null ? ` · الإصدار: ${ref.ref_version}` : ""}
                      </li>
                    ))}
                  </ul>
                )}
              </div>

              <div className={styles.block}>
                <div className={styles.blockTitle}>الأدلة المخالفة وشروط الإبطال</div>
                {recommendation.explanation.invalidation_conditions.length === 0 ? (
                  <span className={styles.blockText}>لا توجد شروط مسجلة.</span>
                ) : (
                  <ul className={styles.bulletList}>
                    {recommendation.explanation.invalidation_conditions.map((e, i) => (
                      <li key={i}>{e}</li>
                    ))}
                  </ul>
                )}
              </div>

              <div className={styles.block}>
                <div className={styles.blockTitle}>الحالات التاريخية المشابهة</div>
                {recommendation.explanation.similar_historical_cases.length === 0 ? (
                  <span className={styles.blockText}>لا توجد حالات مسجلة.</span>
                ) : (
                  <ul className={styles.bulletList}>
                    {recommendation.explanation.similar_historical_cases.map((e, i) => (
                      <li key={i}>{e}</li>
                    ))}
                  </ul>
                )}
              </div>
            </div>
          )}
        </Card>

        <Card title="المحفزات القادمة" subtitle="الأحداث المؤسسية المجدولة من تاريخ آخر دورة فصاعدًا">
          {upcomingCatalysts.length === 0 ? (
            <EmptyState title="لا توجد محفزات مجدولة" detail="لا توجد أحداث مؤسسية قادمة معروفة لهذا السهم." />
          ) : (
            <div className={styles.list}>
              {upcomingCatalysts.map((ce, i) => (
                <div key={i} className={styles.listItem}>
                  <div className={styles.listItemHead}>
                    <span className={styles.listItemTitle}>{titleCase(ce.event_type)}</span>
                    <span className={styles.listItemMeta}>{formatDate(ce.event_date)}</span>
                  </div>
                  <span className={styles.listItemDetail}>{ce.description}</span>
                </div>
              ))}
            </div>
          )}
        </Card>
      </div>

      <Section title="الخط الزمني للمعرفة" description="كائنات المعرفة التي تسمي هذا السهم أصلًا متأثرًا.">
        {knowledge.error && <ErrorState detail={knowledge.error.message} onRetry={knowledge.reload} />}
        {!knowledge.error && tickerKnowledge.length === 0 && !knowledge.loading && (
          <EmptyState title="لا توجد كائنات معرفة بعد" detail="لا توجد معرفة مرقّاة أو مراقبة تسمي هذا السهم." />
        )}
        {tickerKnowledge.length > 0 && (
          <div className={styles.list}>
            {tickerKnowledge.map((k) => (
              <div key={k.id} className={styles.listItem}>
                <div className={styles.listItemHead}>
                  <span className={styles.listItemTitle}>{k.id}</span>
                  <span className={styles.listItemMeta}>{formatDate(k.discovery_date)}</span>
                </div>
                <div className={styles.badgeRow}>
                  <Badge variant={KNOWLEDGE_VARIANT[k.status]}>{titleCase(k.status)}</Badge>
                  <Badge variant="neutral">{titleCase(k.horizon)}</Badge>
                  <Badge variant="neutral">ثقة {formatPercent(k.confidence)}</Badge>
                </div>
                <span className={styles.listItemDetail}>{k.economic_explanation}</span>
              </div>
            ))}
          </div>
        )}
      </Section>

      <div className={styles.twoCol}>
        <Card title="الأوراق البحثية" subtitle="الأوراق المنشورة من معرفة مرتبطة بهذا السهم">
          {tickerPapers.length === 0 ? (
            <EmptyState title="لا توجد أوراق بعد" detail="لا توجد ورقة منشورة قابلة للتتبع إلى معرفة هذا السهم." />
          ) : (
            <div className={styles.list}>
              {tickerPapers.map((p) => (
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

        <Card title="الجينات البحثية" subtitle="تسلسل معرفة هذا السهم وتغيرها بمرور الوقت">
          {tickerGenes.length === 0 ? (
            <EmptyState title="لا توجد جينات بعد" detail="لا يوجد تسلسل جيني بحثي لمعرفة هذا السهم." />
          ) : (
            <div className={styles.list}>
              {tickerGenes.map((g) => (
                <div key={g.id} className={styles.listItem}>
                  <div className={styles.listItemHead}>
                    <span className={styles.listItemTitle}>{g.id} · الجيل {g.generation}</span>
                  </div>
                  <div className={styles.badgeRow}>
                    <Badge variant={GENE_VARIANT[g.status]}>{titleCase(g.status)}</Badge>
                  </div>
                  {g.mutation_notes && <span className={styles.listItemDetail}>{g.mutation_notes}</span>}
                </div>
              ))}
            </div>
          )}
        </Card>
      </div>

      <Section title="القوائم المالية" description="البنود المالية المجمعة لهذا السهم.">
        <DataTable
          rows={tickerStatements}
          getRowKey={(f, i) => `${f.period_end_date}-${f.statement_type}-${f.line_item}-${i}`}
          emptyTitle="لم تُجمع قوائم مالية"
          emptyDetail="مسار الجمع مبني لكنه غير مرتبط بعد بمصدر إفصاحات حي ومتحقق منه."
          columns={[
            { key: "period", header: "نهاية الفترة", render: (f) => formatDate(f.period_end_date) },
            { key: "type", header: "النوع", render: (f) => titleCase(f.period_type) },
            { key: "statement", header: "القائمة", render: (f) => titleCase(f.statement_type) },
            { key: "item", header: "البند", render: (f) => titleCase(f.line_item) },
            {
              key: "value",
              header: "القيمة",
              align: "right",
              render: (f) => (
                <span className="num">
                  {formatNumber(f.value)} {f.currency}
                </span>
              ),
            },
          ]}
        />
      </Section>

      <div className={styles.twoCol}>
        <Card title="الإجراءات المؤسسية" subtitle="الأحداث المؤسسية السابقة لهذا السهم">
          {pastActions.length === 0 ? (
            <EmptyState title="لا توجد إجراءات مؤسسية مسجلة" />
          ) : (
            <div className={styles.list}>
              {pastActions.map((ce, i) => (
                <div key={i} className={styles.listItem}>
                  <div className={styles.listItemHead}>
                    <span className={styles.listItemTitle}>{titleCase(ce.event_type)}</span>
                    <span className={styles.listItemMeta}>{formatDate(ce.event_date)}</span>
                  </div>
                  <span className={styles.listItemDetail}>{ce.description}</span>
                </div>
              ))}
            </div>
          )}
        </Card>

        <Card title="الخط الزمني للأخبار" subtitle="العناوين التي تذكر هذا السهم">
          {news.length === 0 ? (
            <EmptyState title="لا توجد أخبار بعد" />
          ) : (
            <div className={styles.list}>
              {news.map((n, i) => (
                <div key={i} className={styles.listItem}>
                  <div className={styles.listItemHead}>
                    <span className={styles.listItemTitle}>{n.headline}</span>
                    <span className={styles.listItemMeta}>{formatDateTime(n.published_at)}</span>
                  </div>
                  <span className={styles.listItemDetail}>{n.source}</span>
                </div>
              ))}
            </div>
          )}
        </Card>
      </div>

      <Card title="نظام السوق والتعرض للاقتصاد الكلي">
        <EmptyState
          title="غير متاح بعد"
          detail="لا يوجد حتى الآن تصنيف لنظام السوق أو تعرض للاقتصاد الكلي لكل سهم؛ سيظهر القسم عندما ينتجه محرك البحث دون اختلاق بيانات."
        />
      </Card>
    </>
  );
}
