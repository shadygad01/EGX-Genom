import { useParams } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { Badge, type BadgeVariant } from "../components/primitives/Badge";
import { Card } from "../components/primitives/Card";
import { DataTable } from "../components/primitives/DataTable";
import { Disclaimer } from "../components/primitives/Disclaimer";
import { Section } from "../components/primitives/Section";
import { StatTile } from "../components/primitives/StatTile";
import { EmptyState, ErrorState, LoadingState } from "../components/primitives/States";
import { useArtifact } from "../hooks/useArtifact";
import { useEnumLabel } from "../hooks/useEnumLabel";
import { useFormatters } from "../hooks/useFormatters";
import { dedupeEvidence, formatCompactNumber, formatNumber, formatPercent, formatSignedPercent, humanizeEvidence, titleCase } from "../lib/format";
import type { GeneStatus, KnowledgeStatus } from "../types";
import styles from "./CompanyWorkspace.module.css";

const KNOWLEDGE_VARIANT: Record<KnowledgeStatus, BadgeVariant> = {
  promoted: "positive",
  monitoring: "accent",
  retired: "neutral",
};

const GENE_VARIANT: Record<GeneStatus, BadgeVariant> = {
  promoted: "positive",
  monitoring: "accent",
  replaced: "warning",
  retired: "neutral",
};

/** The per-company deep-dive: every recommendation must be explainable, so
 * this page assembles everything AGX knows about one ticker from already-
 * exported artifacts -- no calculation happens here either. */
export function CompanyWorkspace() {
  const { t } = useTranslation("companyWorkspace");
  const { t: tCommon } = useTranslation("common");
  const label = useEnumLabel();
  const { formatDate, formatDateTime } = useFormatters();
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
  const latestFinancialPeriod = tickerStatements[0]?.period_end_date;
  const latestFinancials = tickerStatements.filter((f) => f.period_end_date === latestFinancialPeriod);
  const financialByItem = new Map(latestFinancials.map((f) => [f.line_item, f]));
  const revenueGrowth = financialByItem.get("revenue_growth_yoy")?.value;
  const ebitdaGrowth = financialByItem.get("ebitda_growth_yoy")?.value;
  const netMargin = financialByItem.get("net_margin")?.value;
  const leverage = financialByItem.get("net_debt_to_ebitda")?.value;
  const freeCashFlow = financialByItem.get("free_cash_flow")?.value;
  const fundamentalChecks: Array<boolean | undefined> = [
    revenueGrowth === undefined ? undefined : revenueGrowth > 0,
    ebitdaGrowth === undefined || revenueGrowth === undefined ? undefined : ebitdaGrowth >= revenueGrowth,
    netMargin === undefined ? undefined : netMargin > 0,
    leverage === undefined ? undefined : leverage <= 2,
    freeCashFlow === undefined ? undefined : freeCashFlow > 0,
  ];
  const availableChecks = fundamentalChecks.filter((check) => check !== undefined);
  const passedChecks = availableChecks.filter(Boolean).length;
  const fundamentalTone = availableChecks.length < 3
    ? "insufficient"
    : passedChecks >= 4
      ? "positive"
      : passedChecks >= 2
        ? "mixed"
        : "weak";

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
      <Disclaimer />

      <div className={styles.header}>
        <div className={styles.headerLeft}>
          <span className={`${styles.ticker} num`}>{ticker}</span>
          {companyName && <span className={styles.company}>{companyName}</span>}
        </div>
        <div className={styles.headerMeta}>
          {sector && <Badge variant="neutral">{sector}</Badge>}
        </div>
      </div>

      {loading && <LoadingState rows={4} />}

      <div className={styles.twoCol}>
        <Card title={t("thesis.title")}>
          {!recommendation && !recommendations.loading && (
            <EmptyState title={t("thesis.emptyTitle")} detail={t("thesis.emptyDetail")} />
          )}
          {recommendation && (
            <div>
              <div className={styles.grid}>
                <StatTile label={tCommon("table.confidence")} value={formatPercent(recommendation.confidence)} />
                <StatTile
                  label={tCommon("table.expReturn")}
                  value={formatSignedPercent(recommendation.combined_expected_return)}
                  deltaSign={recommendation.combined_expected_return >= 0 ? 1 : -1}
                />
                <StatTile label={tCommon("table.expRisk")} value={formatPercent(recommendation.combined_expected_risk)} />
              </div>

              <div className={styles.block}>
                <div className={styles.blockTitle}>{t("thesis.researchSummary")}</div>
                <p className={styles.blockText}>
                  {recommendation.explanation.why_this_stock} {recommendation.explanation.why_now}
                </p>
              </div>

              <div className={styles.block}>
                <div className={styles.blockTitle}>{t("thesis.riskSummary")}</div>
                <p className={styles.blockText}>{recommendation.explanation.why_not_others}</p>
              </div>

              <div className={styles.block}>
                <div className={styles.blockTitle}>{t("thesis.supportingEvidence")}</div>
                {recommendation.explanation.supporting_evidence.length === 0 ? (
                  <span className={styles.blockText}>{tCommon("states.noneRecorded")}</span>
                ) : (
                  <ul className={styles.bulletList}>
                    {dedupeEvidence(recommendation.explanation.supporting_evidence).map((e, i) => (
                      <li key={i}>{humanizeEvidence(e)}</li>
                    ))}
                  </ul>
                )}
              </div>

              <div className={styles.block}>
                <div className={styles.blockTitle}>{t("thesis.contradictingEvidence")}</div>
                {recommendation.explanation.invalidation_conditions.length === 0 ? (
                  <span className={styles.blockText}>{tCommon("states.noneRecorded")}</span>
                ) : (
                  <ul className={styles.bulletList}>
                    {recommendation.explanation.invalidation_conditions.map((e, i) => (
                      <li key={i}>{e}</li>
                    ))}
                  </ul>
                )}
              </div>

              <div className={styles.block}>
                <div className={styles.blockTitle}>{t("thesis.historicalSimilarCases")}</div>
                {recommendation.explanation.similar_historical_cases.length === 0 ? (
                  <span className={styles.blockText}>{tCommon("states.noneRecorded")}</span>
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

        <Card title={t("upcomingCatalysts.title")} subtitle={t("upcomingCatalysts.subtitle")}>
          {upcomingCatalysts.length === 0 ? (
            <EmptyState title={t("upcomingCatalysts.emptyTitle")} detail={t("upcomingCatalysts.emptyDetail")} />
          ) : (
            <div className={styles.list}>
              {upcomingCatalysts.map((ce, i) => (
                <div key={i} className={styles.listItem}>
                  <div className={styles.listItemHead}>
                    <span className={styles.listItemTitle}>{label("corporateEventType", ce.event_type)}</span>
                    <span className={styles.listItemMeta}>{formatDate(ce.event_date)}</span>
                  </div>
                  <span className={styles.listItemDetail}>{ce.description}</span>
                </div>
              ))}
            </div>
          )}
        </Card>
      </div>

      <Section title={t("knowledgeTimeline.title")} description={t("knowledgeTimeline.description")}>
        {knowledge.error && <ErrorState detail={knowledge.error.message} onRetry={knowledge.reload} />}
        {!knowledge.error && tickerKnowledge.length === 0 && !knowledge.loading && (
          <EmptyState title={t("knowledgeTimeline.emptyTitle")} detail={t("knowledgeTimeline.emptyDetail")} />
        )}
        {tickerKnowledge.length > 0 && (
          <div className={styles.list}>
            {tickerKnowledge.map((k) => (
              <div key={k.id} className={styles.listItem}>
                <div className={styles.listItemHead}>
                  <span className={`${styles.listItemTitle} num`}>{k.id}</span>
                  <span className={styles.listItemMeta}>{formatDate(k.discovery_date)}</span>
                </div>
                <div className={styles.badgeRow}>
                  <Badge variant={KNOWLEDGE_VARIANT[k.status]}>{label("knowledgeStatus", k.status)}</Badge>
                  <Badge variant="neutral">{label("horizon", k.horizon)}</Badge>
                  <Badge variant="neutral">{t("knowledgeTimeline.confidencePct", { value: formatPercent(k.confidence) })}</Badge>
                </div>
                <span className={styles.listItemDetail}>{k.economic_explanation}</span>
              </div>
            ))}
          </div>
        )}
      </Section>

      <div className={styles.twoCol}>
        <Card title={t("researchPapers.title")} subtitle={t("researchPapers.subtitle")}>
          {tickerPapers.length === 0 ? (
            <EmptyState title={t("researchPapers.emptyTitle")} detail={t("researchPapers.emptyDetail")} />
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

        <Card title={t("genes.title")} subtitle={t("genes.subtitle")}>
          {tickerGenes.length === 0 ? (
            <EmptyState title={t("genes.emptyTitle")} detail={t("genes.emptyDetail")} />
          ) : (
            <div className={styles.list}>
              {tickerGenes.map((g) => (
                <div key={g.id} className={styles.listItem}>
                  <div className={styles.listItemHead}>
                    <span className={`${styles.listItemTitle} num`}>
                      {t("genes.generationLabel", { id: g.id, generation: g.generation })}
                    </span>
                  </div>
                  <div className={styles.badgeRow}>
                    <Badge variant={GENE_VARIANT[g.status]}>{label("geneStatus", g.status)}</Badge>
                  </div>
                  {g.mutation_notes && <span className={styles.listItemDetail}>{g.mutation_notes}</span>}
                </div>
              ))}
            </div>
          )}
        </Card>
      </div>

      <Section title={t("financialStatements.title")} description={t("financialStatements.description")}>
        {latestFinancials.length > 0 && (
          <>
            <div className={styles.badgeRow}>
              <Badge variant={fundamentalTone === "positive" ? "positive" : fundamentalTone === "mixed" ? "warning" : fundamentalTone === "weak" ? "negative" : "neutral"}>
                {t(`financialStatements.assessment.${fundamentalTone}`)}
              </Badge>
              <span className={styles.listItemMeta}>{t("financialStatements.valuationRequired")}</span>
            </div>
            <div className={styles.grid}>
              {latestFinancials
                .filter((f) => ["revenue", "ebitda", "net_income", "free_cash_flow", "revenue_growth_yoy", "ebitda_growth_yoy", "net_margin", "net_debt_to_ebitda"].includes(f.line_item))
                .map((f) => (
                  <StatTile
                    key={f.line_item}
                    label={t(`financialStatements.items.${f.line_item}`, { defaultValue: titleCase(f.line_item) })}
                    value={["EGP", "USD"].includes(f.currency)
                      ? `${formatCompactNumber(f.value)} ${f.currency}`
                      : `${formatNumber(f.value, 1)}${f.currency}`}
                  />
                ))}
            </div>
          </>
        )}
        <DataTable
          rows={tickerStatements}
          getRowKey={(f, i) => `${f.period_end_date}-${f.statement_type}-${f.line_item}-${i}`}
          emptyTitle={t("financialStatements.emptyTitle")}
          emptyDetail={t("financialStatements.emptyDetail")}
          columns={[
            { key: "period", header: t("financialStatements.periodEnd"), render: (f) => formatDate(f.period_end_date) },
            { key: "type", header: t("financialStatements.type"), render: (f) => label("periodType", f.period_type) },
            {
              key: "statement",
              header: t("financialStatements.statement"),
              render: (f) => f.statement_type === "KEY_METRICS" ? t("financialStatements.keyMetrics") : label("statementType", f.statement_type),
            },
            {
              key: "item",
              header: t("financialStatements.lineItem"),
              render: (f) => t(`financialStatements.items.${f.line_item}`, { defaultValue: titleCase(f.line_item) }),
            },
            {
              key: "value",
              header: t("financialStatements.value"),
              align: "right",
              render: (f) => (
                <span className="num">
                  {["EGP", "USD"].includes(f.currency)
                    ? `${formatNumber(f.value)} ${f.currency}`
                    : `${formatNumber(f.value, 1)}${f.currency}`}
                </span>
              ),
            },
          ]}
        />
      </Section>

      <div className={styles.twoCol}>
        <Card title={t("corporateActions.title")} subtitle={t("corporateActions.subtitle")}>
          {pastActions.length === 0 ? (
            <EmptyState title={t("corporateActions.emptyTitle")} />
          ) : (
            <div className={styles.list}>
              {pastActions.map((ce, i) => (
                <div key={i} className={styles.listItem}>
                  <div className={styles.listItemHead}>
                    <span className={styles.listItemTitle}>{label("corporateEventType", ce.event_type)}</span>
                    <span className={styles.listItemMeta}>{formatDate(ce.event_date)}</span>
                  </div>
                  <span className={styles.listItemDetail}>{ce.description}</span>
                </div>
              ))}
            </div>
          )}
        </Card>

        <Card title={t("newsTimeline.title")} subtitle={t("newsTimeline.subtitle")}>
          {news.length === 0 ? (
            <EmptyState title={t("newsTimeline.emptyTitle")} />
          ) : (
            <div className={styles.list}>
              {news.map((n, i) => (
                <div key={i} className={styles.listItem}>
                  <div className={styles.listItemHead}>
                    {n.body?.startsWith("http") ? (
                      <a
                        className={styles.listItemTitle}
                        href={n.body}
                        target="_blank"
                        rel="noreferrer"
                      >
                        {n.headline}
                      </a>
                    ) : (
                      <span className={styles.listItemTitle}>{n.headline}</span>
                    )}
                    <span className={styles.listItemMeta}>{formatDateTime(n.published_at)}</span>
                  </div>
                  <span className={styles.listItemDetail}>{n.source}</span>
                </div>
              ))}
            </div>
          )}
        </Card>
      </div>

      <Card title={t("marketRegime.title")}>
        <EmptyState title={t("marketRegime.emptyTitle")} detail={t("marketRegime.emptyDetail")} />
      </Card>
    </>
  );
}
