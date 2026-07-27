import { Link, useNavigate } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { Badge, type BadgeVariant } from "../components/primitives/Badge";
import { Card } from "../components/primitives/Card";
import { DataTable } from "../components/primitives/DataTable";
import { Meter } from "../components/primitives/Meter";
import { Section } from "../components/primitives/Section";
import { StatTile } from "../components/primitives/StatTile";
import { EmptyState, ErrorState, LoadingState } from "../components/primitives/States";
import { useArtifact } from "../hooks/useArtifact";
import { useEnumLabel } from "../hooks/useEnumLabel";
import { useFormatters } from "../hooks/useFormatters";
import { formatSignedPercent, formatPercent, titleCase } from "../lib/format";
import type { CorporateEvent, Event, EventSeverity, KnowledgeStatus, NewsItem } from "../types";
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
  const { t } = useTranslation("aiBriefing");
  const { t: tCommon } = useTranslation("common");
  const label = useEnumLabel();
  const { formatDate, formatDateTime } = useFormatters();
  const navigate = useNavigate();
  const systemStatus = useArtifact((p) => p.getSystemStatus());
  const marketState = useArtifact((p) => p.getMarketState());
  const recommendations = useArtifact((p) => p.getRecommendations());
  const events = useArtifact((p) => p.getEvents());
  const knowledge = useArtifact((p) => p.getKnowledge());
  const papers = useArtifact((p) => p.getPapers());
  const investmentCases = useArtifact((p) => p.getInvestmentCases());
  const executionReport = useArtifact((p) => p.getExecutionReport());

  const topOpportunities = [...(recommendations.data ?? [])]
    .sort((a, b) => b.confidence - a.confidence)
    .slice(0, 5);

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
      <Section title={t("systemHealth.title")} description={t("systemHealth.description")}>
        {systemStatus.loading && <LoadingState rows={1} />}
        {systemStatus.error && <ErrorState detail={systemStatus.error.message} onRetry={systemStatus.reload} />}
        {systemStatus.data && (
          <div className={styles.statGrid}>
            <StatTile label={t("systemHealth.lastCycle")} value={formatDate(systemStatus.data.pipeline_run_date)} />
            <StatTile label={t("systemHealth.runs")} value={systemStatus.data.runs} />
            <StatTile
              label={t("systemHealth.succeeded")}
              value={systemStatus.data.succeeded}
              deltaSign={systemStatus.data.failed > 0 ? -1 : 1}
              delta={
                systemStatus.data.failed > 0
                  ? t("systemHealth.failedCount", { count: systemStatus.data.failed })
                  : t("systemHealth.allClear")
              }
            />
            <StatTile label={t("systemHealth.knowledgeObjects")} value={systemStatus.data.knowledge_objects} />
            {Object.entries(systemStatus.data.by_status).map(([status, count]) => (
              <StatTile key={status} label={label("knowledgeStatus", status)} value={count} />
            ))}
          </div>
        )}
      </Section>

      {executionReport.data && (
        <Section title={t("changesSinceYesterday.title")} description={t("changesSinceYesterday.description")}>
          <div className={styles.statGrid}>
            <StatTile
              label={t("changesSinceYesterday.knowledgeObjects")}
              value={executionReport.data.knowledge_after}
              deltaSign={Math.sign(executionReport.data.knowledge_after - executionReport.data.knowledge_before)}
              delta={t("changesSinceYesterday.sinceLastRun", {
                delta: `${executionReport.data.knowledge_after - executionReport.data.knowledge_before >= 0 ? "+" : ""}${
                  executionReport.data.knowledge_after - executionReport.data.knowledge_before
                }`,
              })}
            />
            <StatTile
              label={t("changesSinceYesterday.genes")}
              value={executionReport.data.genome_after}
              deltaSign={Math.sign(executionReport.data.genome_after - executionReport.data.genome_before)}
              delta={t("changesSinceYesterday.sinceLastRun", {
                delta: `${executionReport.data.genome_after - executionReport.data.genome_before >= 0 ? "+" : ""}${
                  executionReport.data.genome_after - executionReport.data.genome_before
                }`,
              })}
            />
            <StatTile
              label={t("changesSinceYesterday.events")}
              value={executionReport.data.events_after}
              deltaSign={Math.sign(executionReport.data.events_after - executionReport.data.events_before)}
              delta={t("changesSinceYesterday.sinceLastRun", {
                delta: `${executionReport.data.events_after - executionReport.data.events_before >= 0 ? "+" : ""}${
                  executionReport.data.events_after - executionReport.data.events_before
                }`,
              })}
            />
            <StatTile
              label={t("changesSinceYesterday.pipelineStatus")}
              value={label("stageStatus", executionReport.data.overall_status)}
            />
          </div>
          {executionReport.data.errors.length > 0 && (
            <div className={styles.list} style={{ marginTop: "var(--space-4)" }}>
              {executionReport.data.errors.map((e, i) => (
                <div key={i} className={styles.listItemDetail}>
                  <Badge variant="negative">{t("changesSinceYesterday.error")}</Badge> {e}
                </div>
              ))}
            </div>
          )}
        </Section>
      )}

      <Section title={t("marketSummary.title")} description={t("marketSummary.description")}>
        {marketState.loading && <LoadingState rows={1} />}
        {marketState.error && <ErrorState detail={marketState.error.message} onRetry={marketState.reload} />}
        {marketState.data === null && !marketState.loading && !marketState.error && (
          <EmptyState title={t("marketSummary.emptyTitle")} detail={t("marketSummary.emptyDetail")} />
        )}
        {marketState.data && (
          <div className={styles.statGrid}>
            <StatTile label={t("marketSummary.asOf")} value={formatDate(marketState.data.as_of)} />
            <StatTile
              label={t("marketSummary.tradingSession")}
              value={marketState.data.trading_session.is_trading_day ? t("marketSummary.open") : t("marketSummary.closed")}
              caption={marketState.data.trading_session.holiday_name ?? undefined}
            />
            <StatTile label={t("marketSummary.constituents")} value={Object.keys(marketState.data.constituents).length} />
            <StatTile label={t("marketSummary.sectors")} value={new Set(Object.values(marketState.data.sectors)).size} />
          </div>
        )}
      </Section>

      <div className={styles.twoCol}>
        <Card title={t("topOpportunities.title")} subtitle={t("topOpportunities.subtitle")}>
          {recommendations.loading && <LoadingState />}
          {recommendations.error && <ErrorState detail={recommendations.error.message} onRetry={recommendations.reload} />}
          {!recommendations.loading && !recommendations.error && (
            <DataTable
              rows={topOpportunities}
              getRowKey={(r) => r.ticker}
              onRowClick={(r) => navigate(`/company/${r.ticker}`)}
              emptyTitle={t("topOpportunities.emptyTitle")}
              emptyDetail={t("topOpportunities.emptyDetail")}
              columns={[
                {
                  key: "ticker",
                  header: tCommon("table.ticker"),
                  render: (r) => <span className="num" style={{ color: "var(--accent-strong)", fontWeight: 600 }}>{r.ticker}</span>,
                },
                { key: "confidence", header: tCommon("table.confidence"), render: (r) => <Meter value={r.confidence} label={formatPercent(r.confidence)} /> },
                {
                  key: "return",
                  header: tCommon("table.expReturn"),
                  align: "right",
                  render: (r) => (
                    <span className="num" style={{ color: r.combined_expected_return >= 0 ? "var(--positive)" : "var(--negative)" }}>
                      {formatSignedPercent(r.combined_expected_return)}
                    </span>
                  ),
                },
                { key: "risk", header: tCommon("table.expRisk"), align: "right", render: (r) => <span className="num">{formatPercent(r.combined_expected_risk)}</span> },
              ]}
            />
          )}
        </Card>

        <Card title={t("biggestRisks.title")} subtitle={t("biggestRisks.subtitle")}>
          {events.loading && <LoadingState />}
          {events.error && <ErrorState detail={events.error.message} onRetry={events.reload} />}
          {!events.loading && !events.error && elevatedEvents.length === 0 && (
            <EmptyState title={t("biggestRisks.emptyTitle")} detail={t("biggestRisks.emptyDetail")} />
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
                    <Badge variant={SEVERITY_VARIANT[e.severity]}>{label("eventSeverity", e.severity)}</Badge>
                    <Badge variant="neutral">{label("eventType", e.event_type)}</Badge>
                  </div>
                  <span className={styles.listItemDetail}>{titleCase(e.subtype)} · {label("eventStatus", e.status)}</span>
                </div>
              ))}
            </div>
          )}
        </Card>

        <Card title={t("mostImportantNews.title")} subtitle={t("mostImportantNews.subtitle")}>
          {marketState.loading && <LoadingState />}
          {!marketState.loading && news.length === 0 && (
            <EmptyState title={t("mostImportantNews.emptyTitle")} detail={t("mostImportantNews.emptyDetail")} />
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

        <Card title={t("upcomingCatalysts.title")} subtitle={t("upcomingCatalysts.subtitle")}>
          {marketState.loading && <LoadingState />}
          {!marketState.loading && upcomingCatalysts.length === 0 && (
            <EmptyState title={t("upcomingCatalysts.emptyTitle")} detail={t("upcomingCatalysts.emptyDetail")} />
          )}
          {upcomingCatalysts.length > 0 && (
            <div className={styles.list}>
              {upcomingCatalysts.map((ce, i) => (
                <div key={i} className={styles.listItem}>
                  <div className={styles.listItemHead}>
                    <span className={styles.listItemTitle}>
                      <span className="num">{ce.ticker}</span> — {label("corporateEventType", ce.event_type)}
                    </span>
                    <span className={styles.listItemMeta}>{formatDate(ce.event_date)}</span>
                  </div>
                  <span className={styles.listItemDetail}>{ce.description}</span>
                </div>
              ))}
            </div>
          )}
        </Card>

        <Card title={t("knowledgeChanges.title")} subtitle={t("knowledgeChanges.subtitle")}>
          {knowledge.loading && <LoadingState />}
          {knowledge.error && <ErrorState detail={knowledge.error.message} onRetry={knowledge.reload} />}
          {!knowledge.loading && !knowledge.error && recentKnowledge.length === 0 && (
            <EmptyState title={t("knowledgeChanges.emptyTitle")} detail={t("knowledgeChanges.emptyDetail")} />
          )}
          {recentKnowledge.length > 0 && (
            <div className={styles.list}>
              {recentKnowledge.map((k) => (
                <div key={k.id} className={styles.listItem}>
                  <div className={styles.listItemHead}>
                    <span className={`${styles.listItemTitle} num`}>{k.affected_assets.join(", ")}</span>
                    <span className={styles.listItemMeta}>{formatDate(k.discovery_date)}</span>
                  </div>
                  <div className={styles.badgeRow}>
                    <Badge variant={KNOWLEDGE_VARIANT[k.status]}>{label("knowledgeStatus", k.status)}</Badge>
                    <Badge variant="neutral">{label("horizon", k.horizon)}</Badge>
                  </div>
                  <span className={styles.listItemDetail}>{k.economic_explanation}</span>
                </div>
              ))}
            </div>
          )}
        </Card>

        <Card title={t("scientificDiscoveries.title")} subtitle={t("scientificDiscoveries.subtitle")}>
          {papers.loading && <LoadingState />}
          {papers.error && <ErrorState detail={papers.error.message} onRetry={papers.reload} />}
          {!papers.loading && !papers.error && recentPapers.length === 0 && (
            <EmptyState title={t("scientificDiscoveries.emptyTitle")} detail={t("scientificDiscoveries.emptyDetail")} />
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

      <Section title={t("portfolio.title")} description={t("portfolio.description")}>
        {investmentCases.loading && <LoadingState />}
        {investmentCases.error && <ErrorState detail={investmentCases.error.message} onRetry={investmentCases.reload} />}
        {!investmentCases.loading && !investmentCases.error && investmentCases.data?.portfolio == null && (
          <EmptyState title={t("portfolio.emptyTitle")} detail={t("portfolio.emptyDetail")} />
        )}
        {investmentCases.data?.portfolio && (
          <DataTable
            rows={investmentCases.data.portfolio.positions}
            getRowKey={(p) => p.ticker}
            columns={[
              {
                key: "ticker",
                header: tCommon("table.ticker"),
                render: (p) => (
                  <Link to={`/company/${p.ticker}`} className="num" style={{ color: "var(--accent-strong)", fontWeight: 600 }}>
                    {p.ticker}
                  </Link>
                ),
              },
              { key: "weight", header: t("portfolio.weight"), align: "right", render: (p) => <span className="num">{formatPercent(p.weight)}</span> },
              { key: "confidence", header: tCommon("table.confidence"), render: (p) => <Meter value={p.confidence} label={formatPercent(p.confidence)} /> },
              {
                key: "return",
                header: tCommon("table.expReturn"),
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
            <StatTile label={t("portfolio.cashWeight")} value={formatPercent(investmentCases.data.portfolio.cash_weight)} />
            <StatTile label={t("portfolio.positions")} value={investmentCases.data.portfolio.positions.length} />
          </div>
        )}
      </Section>
    </>
  );
}
