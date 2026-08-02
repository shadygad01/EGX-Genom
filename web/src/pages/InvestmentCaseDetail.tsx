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
import type { DecisionAction, GeneStatus, Horizon, KnowledgeStatus } from "../types";
import styles from "./InvestmentCaseDetail.module.css";

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

const DECISION_VARIANT: Record<DecisionAction, BadgeVariant> = {
  buy_candidate: "positive",
  watch: "warning",
  avoid: "negative",
  abstain: "neutral",
};

const HORIZONS: Horizon[] = ["micro", "swing", "investment"];

function formatFinancialLineItem(lineItem: string, value: number, currency: string): string {
  if (lineItem.includes("yield")) return `${formatNumber(value, 2)}%`;
  if (lineItem === "market_beta") return formatNumber(value, 2);
  if (lineItem.endsWith("_pe") || lineItem.endsWith("_pb")) {
    return `${formatNumber(value, 2)}x`;
  }
  if (lineItem === "shares_outstanding") return formatCompactNumber(value);
  return ["EGP", "USD"].includes(currency)
    ? `${formatCompactNumber(value)} ${currency}`
    : `${formatNumber(value, 1)}${currency}`;
}

/** Investment Case -- "why should I own this company?" The page begins
 * with the decision, not charts: Decision / Target Allocation / Horizon /
 * Confidence first, then thesis, then every layer of supporting evidence,
 * ending with the deepest research history (per the mission's Decision →
 * Investment Case → Evidence → Research hierarchy). Every section reuses
 * an already-exported artifact -- nothing is computed here that isn't
 * already a real field somewhere in `recommendations.json`/
 * `knowledge.json`/`decision_readiness.json`/`decision_history.json`/
 * `genes.json`/`financial_statements.json`/`market_state.json`. */
export function InvestmentCaseDetail() {
  const { t } = useTranslation("investmentCases");
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
  const investmentCases = useArtifact((p) => p.getInvestmentCases());
  const decisionReadiness = useArtifact((p) => p.getDecisionReadiness());
  const decisionHistory = useArtifact((p) => p.getDecisionHistory());

  const companyName = marketState.data?.constituents[ticker];
  const sector = marketState.data?.sectors[ticker];
  const asOf = marketState.data?.as_of ?? null;

  const recommendation = recommendations.data?.find((r) => r.ticker === ticker) ?? null;
  const investmentDecision = recommendation?.horizon_decisions.investment ?? null;
  const modelPosition = investmentCases.data?.portfolio?.positions.find((p) => p.ticker === ticker) ?? null;
  const readiness = decisionReadiness.data?.find((r) => r.ticker === ticker) ?? null;
  const tickerHistory = (decisionHistory.data ?? [])
    .filter((d) => d.ticker === ticker)
    .sort((a, b) => (a.as_of < b.as_of ? 1 : -1));

  const tickerKnowledge = (knowledge.data ?? [])
    .filter((k) => k.affected_assets.includes(ticker))
    .sort((a, b) => (a.discovery_date < b.discovery_date ? 1 : -1));
  const tickerKnowledgeIds = new Set(tickerKnowledge.map((k) => k.id));
  const macroKnowledge = tickerKnowledge.filter((k) => k.creator_agent === "macro_agent");
  const monitoringKnowledge = tickerKnowledge.filter((k) => k.status === "monitoring");

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

      {!loading && !recommendation && (
        <EmptyState title={t("caseDetail.noCaseTitle")} detail={t("caseDetail.noCaseDetail")} />
      )}

      {investmentDecision && (
        <div
          className={styles.decisionHeader}
          style={{ borderInlineStartColor: investmentDecision.action === "buy_candidate" ? "var(--positive)" : investmentDecision.action === "avoid" ? "var(--negative)" : "var(--warning)" }}
        >
          <div className={styles.decisionHeaderAction}>
            <span className={styles.blockTitle}>{t("caseDetail.decision")}</span>
            <Badge variant={DECISION_VARIANT[investmentDecision.action]}>{label("decision", investmentDecision.action)}</Badge>
          </div>
          <div className={styles.decisionHeaderStats}>
            <StatTile
              label={t("caseDetail.targetAllocation")}
              value={modelPosition ? formatPercent(modelPosition.weight) : t("caseDetail.notInModelPortfolio")}
            />
            <StatTile label={t("caseDetail.horizon")} value={label("horizon", "investment")} />
            <StatTile label={tCommon("table.confidence")} value={formatPercent(investmentDecision.confidence)} />
            <StatTile label={t("caseDetail.reviewBy")} value={formatDate(investmentDecision.valid_until)} />
          </div>
        </div>
      )}

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
                <div className={styles.blockTitle}>{t("thesis.investmentThesis")}</div>
                <p className={styles.blockText}>
                  {recommendation.explanation.why_this_stock} {recommendation.explanation.why_now}
                </p>
              </div>

              <div className={styles.block}>
                <div className={styles.blockTitle}>{t("thesis.risks")}</div>
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

      <div className={styles.twoCol}>
        <Card title={t("macroContext.title")} subtitle={t("macroContext.subtitle")}>
          {macroKnowledge.length === 0 ? (
            <EmptyState title={t("macroContext.emptyTitle")} />
          ) : (
            <div className={styles.list}>
              {macroKnowledge.map((k) => (
                <div key={k.id} className={styles.listItem}>
                  <span className={styles.listItemDetail}>{k.economic_explanation}</span>
                </div>
              ))}
            </div>
          )}
        </Card>

        <Card title={t("qualityAssessment.title")} subtitle={t("qualityAssessment.subtitle")}>
          {latestFinancials.length === 0 ? (
            <EmptyState title={t("qualityAssessment.emptyTitle")} detail={t("qualityAssessment.emptyDetail")} />
          ) : (
            <>
              <Badge variant={fundamentalTone === "positive" ? "positive" : fundamentalTone === "mixed" ? "warning" : fundamentalTone === "weak" ? "negative" : "neutral"}>
                {t(`qualityAssessment.assessment.${fundamentalTone}`)}
              </Badge>
              <div className={styles.grid} style={{ marginTop: "var(--space-3)" }}>
                {latestFinancials
                  .filter((f) => ["revenue_growth_yoy", "ebitda_growth_yoy", "net_margin", "net_debt_to_ebitda"].includes(f.line_item))
                  .map((f) => (
                    <StatTile key={f.line_item} label={titleCase(f.line_item)} value={formatNumber(f.value, 2)} />
                  ))}
              </div>
            </>
          )}
        </Card>
      </div>

      <Section title={t("valuation.title")} description={t("valuation.description")}>
        {decisionReadiness.loading && <LoadingState rows={1} />}
        {!decisionReadiness.loading && !readiness?.valuation?.latest_financial_period && !readiness?.valuation?.latest_market_snapshot_date && (
          <EmptyState title={t("valuation.emptyTitle")} detail={t("valuation.emptyDetail")} />
        )}
        {readiness?.valuation && (readiness.valuation.latest_financial_period || readiness.valuation.latest_market_snapshot_date) && (
          <div className={styles.grid}>
            <StatTile
              label={t("valuation.priceVsFairValue")}
              value={readiness.price_vs_fair_value_pct != null ? formatSignedPercent(readiness.price_vs_fair_value_pct) : "—"}
              deltaSign={readiness.price_vs_fair_value_pct != null ? (readiness.price_vs_fair_value_pct > 0 ? -1 : 1) : undefined}
            />
            <StatTile label={t("valuation.fairValue")} value={readiness.valuation.weighted_fair_value != null ? formatNumber(readiness.valuation.weighted_fair_value, 2) : "—"} />
            <StatTile label={t("valuation.dcf")} value={readiness.valuation.dcf_per_share != null ? formatNumber(readiness.valuation.dcf_per_share, 2) : "—"} />
            <StatTile label={t("valuation.enterpriseValue")} value={readiness.valuation.enterprise_value != null ? formatCompactNumber(readiness.valuation.enterprise_value) : "—"} />
            <StatTile label={t("valuation.ebitda")} value={readiness.valuation.ebitda != null ? formatCompactNumber(readiness.valuation.ebitda) : "—"} />
            <StatTile label={t("valuation.evEbitda")} value={readiness.valuation.ev_to_ebitda != null ? `${formatNumber(readiness.valuation.ev_to_ebitda, 2)}x` : "—"} />
            <StatTile label={t("valuation.priceBook")} value={readiness.valuation.price_to_book != null ? `${formatNumber(readiness.valuation.price_to_book, 2)}x` : "—"} />
            <StatTile label={t("valuation.marketPe")} value={readiness.valuation.market_pe != null ? `${formatNumber(readiness.valuation.market_pe, 2)}x` : "—"} />
            <StatTile label={t("valuation.marketCap")} value={readiness.valuation.market_cap != null ? formatCompactNumber(readiness.valuation.market_cap) : "—"} />
            <StatTile label={t("valuation.dividendYield")} value={readiness.valuation.dividend_yield != null ? `${formatNumber(readiness.valuation.dividend_yield, 2)}%` : "—"} />
            <StatTile label={t("valuation.beta")} value={readiness.valuation.beta != null ? formatNumber(readiness.valuation.beta, 2) : "—"} />
          </div>
        )}
      </Section>

      <Section title={t("executionPlan.title")} description={t("executionPlan.description")}>
        {!investmentDecision && <EmptyState title={t("executionPlan.emptyTitle")} />}
        {investmentDecision && (
          <div className={styles.executionGrid}>
            <div className={styles.executionItem}>
              <div className={styles.executionLabel}>{t("executionPlan.entryCondition")}</div>
              <div className={styles.executionValue}>{investmentDecision.entry_condition || t("executionPlan.notApplicable")}</div>
            </div>
            <div className={styles.executionItem}>
              <div className={styles.executionLabel}>{t("executionPlan.invalidationCondition")}</div>
              <div className={styles.executionValue}>
                {investmentDecision.invalidation_operator !== "not_applicable" && investmentDecision.invalidation_value != null
                  ? `${label("priceConditionOperator", investmentDecision.invalidation_operator)} ${formatNumber(investmentDecision.invalidation_value, 2)}`
                  : t("executionPlan.notApplicable")}
              </div>
            </div>
            <div className={styles.executionItem}>
              <div className={styles.executionLabel}>{t("executionPlan.reviewCondition")}</div>
              <div className={styles.executionValue}>{investmentDecision.review_condition || t("executionPlan.notApplicable")}</div>
            </div>
          </div>
        )}
        {investmentDecision && investmentDecision.invalidation_conditions.length > 0 && (
          <div className={styles.block}>
            <div className={styles.blockTitle}>{t("executionPlan.namedInvalidationConditions")}</div>
            <ul className={styles.bulletList}>
              {investmentDecision.invalidation_conditions.map((c, i) => (
                <li key={i}>{c}</li>
              ))}
            </ul>
          </div>
        )}
      </Section>

      <Section title={t("monitoringPlan.title")} description={t("monitoringPlan.description")}>
        {monitoringKnowledge.length === 0 ? (
          <EmptyState title={t("monitoringPlan.emptyTitle")} detail={t("monitoringPlan.emptyDetail")} />
        ) : (
          <div className={styles.list}>
            {monitoringKnowledge.map((k) => (
              <div key={k.id} className={styles.listItem}>
                <div className={styles.listItemHead}>
                  <span className={`${styles.listItemTitle} num`}>{k.id}</span>
                  <Badge variant="accent">{label("knowledgeStatus", k.status)}</Badge>
                </div>
                <span className={styles.listItemDetail}>{k.economic_explanation}</span>
              </div>
            ))}
          </div>
        )}
      </Section>

      <Section title={t("decisionHistory.title")} description={t("decisionHistory.description")}>
        {decisionHistory.loading && <LoadingState rows={2} />}
        {!decisionHistory.loading && tickerHistory.length === 0 && (
          <EmptyState title={t("decisionHistory.emptyTitle")} detail={t("decisionHistory.emptyDetail")} />
        )}
        {tickerHistory.length > 0 && (
          <DataTable
            rows={tickerHistory}
            getRowKey={(d) => `${d.id}-${d.version}`}
            columns={[
              { key: "asOf", header: t("decisionHistory.asOf"), render: (d) => formatDate(d.as_of) },
              { key: "horizon", header: t("decisionHistory.horizon"), render: (d) => label("horizon", d.horizon) },
              { key: "action", header: tCommon("table.decision"), render: (d) => label("decision", d.action) },
              { key: "outcome", header: t("decisionHistory.outcome"), render: (d) => label("outcomeStatus", d.outcome_status) },
              {
                key: "realized",
                header: t("decisionHistory.realizedReturn"),
                align: "right",
                render: (d) => (d.realized_return != null ? formatSignedPercent(d.realized_return) : "—"),
              },
            ]}
          />
        )}
      </Section>

      <Section title={t("evidenceTimeline.title")} description={t("evidenceTimeline.description")}>
        {knowledge.error && <ErrorState detail={knowledge.error.message} onRetry={knowledge.reload} />}
        {!knowledge.error && tickerKnowledge.length === 0 && !knowledge.loading && (
          <EmptyState title={t("evidenceTimeline.emptyTitle")} detail={t("evidenceTimeline.emptyDetail")} />
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
                  <Badge variant="neutral">{t("evidenceTimeline.confidencePct", { value: formatPercent(k.confidence) })}</Badge>
                </div>
                <span className={styles.listItemDetail}>{k.economic_explanation}</span>
              </div>
            ))}
          </div>
        )}
      </Section>

      <Section title={t("learningHistory.title")} description={t("learningHistory.description")}>
        {tickerGenes.length === 0 ? (
          <EmptyState title={t("learningHistory.emptyTitle")} detail={t("learningHistory.emptyDetail")} />
        ) : (
          <div className={styles.list}>
            {tickerGenes.map((g) => (
              <div key={g.id} className={styles.listItem}>
                <div className={styles.listItemHead}>
                  <span className={`${styles.listItemTitle} num`}>
                    {t("learningHistory.generationLabel", { id: g.id, generation: g.generation })}
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
      </Section>

      <Section title={t("research.title")} description={t("research.description")}>
        <div className={styles.twoCol}>
          <Card title={t("research.papers.title")} subtitle={t("research.papers.subtitle")}>
            {tickerPapers.length === 0 ? (
              <EmptyState title={t("research.papers.emptyTitle")} />
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

          <Card title={t("research.news.title")} subtitle={t("research.news.subtitle")}>
            {news.length === 0 ? (
              <EmptyState title={t("research.news.emptyTitle")} />
            ) : (
              <div className={styles.list}>
                {news.map((n, i) => (
                  <div key={i} className={styles.listItem}>
                    <div className={styles.listItemHead}>
                      {n.body?.startsWith("http") ? (
                        <a className={styles.listItemTitle} href={n.body} target="_blank" rel="noreferrer">
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

        <Card title={t("research.financials.title")} subtitle={t("research.financials.subtitle")}>
          <DataTable
            rows={tickerStatements}
            getRowKey={(f, i) => `${f.period_end_date}-${f.statement_type}-${f.line_item}-${i}`}
            emptyTitle={t("research.financials.emptyTitle")}
            emptyDetail={t("research.financials.emptyDetail")}
            columns={[
              { key: "period", header: t("research.financials.periodEnd"), render: (f) => formatDate(f.period_end_date) },
              { key: "item", header: t("research.financials.lineItem"), render: (f) => titleCase(f.line_item) },
              {
                key: "value",
                header: t("research.financials.value"),
                align: "right",
                render: (f) => (
                  <span className="num">
                    {formatFinancialLineItem(f.line_item, f.value, f.currency)}
                  </span>
                ),
              },
            ]}
          />
        </Card>

        <Card title={t("research.corporateActions.title")} subtitle={t("research.corporateActions.subtitle")}>
          {pastActions.length === 0 ? (
            <EmptyState title={t("research.corporateActions.emptyTitle")} />
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
      </Section>
    </>
  );
}
