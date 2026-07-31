import { useMemo, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { Badge, type BadgeVariant } from "../components/primitives/Badge";
import { Card } from "../components/primitives/Card";
import { DataTable } from "../components/primitives/DataTable";
import { Disclaimer } from "../components/primitives/Disclaimer";
import { Meter } from "../components/primitives/Meter";
import { Section } from "../components/primitives/Section";
import { StatTile } from "../components/primitives/StatTile";
import { EmptyState, ErrorState, LoadingState } from "../components/primitives/States";
import { useArtifact } from "../hooks/useArtifact";
import { useEnumLabel } from "../hooks/useEnumLabel";
import { useFormatters } from "../hooks/useFormatters";
import { formatSignedPercent, formatPercent, titleCase } from "../lib/format";
import type { CorporateEvent, DecisionReadiness, Event, EventSeverity, Horizon, KnowledgeStatus, NewsItem, Recommendation } from "../types";
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

const HORIZONS: Horizon[] = ["micro", "swing", "investment"];

type DecisionBoardRow = {
  ticker: string;
  company: string;
  readiness: DecisionReadiness | null;
  recommendation: Recommendation | null;
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
  const universe = useArtifact((p) => p.getUniverse());
  const readiness = useArtifact((p) => p.getDecisionReadiness());
  const publicationGate = useArtifact((p) => p.getPublicationGate());
  const decisionPerformance = useArtifact((p) => p.getDecisionPerformance());
  const [decisionSearch, setDecisionSearch] = useState("");
  const [decisionFilter, setDecisionFilter] = useState<"all" | "actionable" | "watch" | "abstain">("all");

  const decisionRows = useMemo<DecisionBoardRow[]>(() => {
    const recommendationByTicker = new Map((recommendations.data ?? []).map((row) => [row.ticker, row]));
    const readinessByTicker = new Map((readiness.data ?? []).map((row) => [row.ticker, row]));
    const tickers = universe.data?.tickers ?? Array.from(new Set([
      ...readinessByTicker.keys(),
      ...recommendationByTicker.keys(),
    ])).sort();
    const query = decisionSearch.trim().toLocaleLowerCase();

    return tickers.map((ticker) => ({
      ticker,
      company: universe.data?.constituents[ticker] ?? marketState.data?.constituents[ticker] ?? "",
      readiness: readinessByTicker.get(ticker) ?? null,
      recommendation: recommendationByTicker.get(ticker) ?? null,
    })).filter((row) => {
      const decisions = Object.values(row.recommendation?.horizon_decisions ?? {}).filter(Boolean);
      const hasAction = decisions.some((decision) => decision!.action === "buy_candidate" && decision!.publication_status === "publication_ready");
      const hasWatch = decisions.some((decision) => decision!.action === "watch") || row.readiness?.status === "degraded";
      const matchesFilter = decisionFilter === "all"
        || (decisionFilter === "actionable" && hasAction)
        || (decisionFilter === "watch" && hasWatch)
        || (decisionFilter === "abstain" && !hasAction && !hasWatch);
      return matchesFilter && (!query || `${row.ticker} ${row.company}`.toLocaleLowerCase().includes(query));
    }).sort((a, b) => {
      const rank = (row: DecisionBoardRow) => row.readiness?.status === "ready" ? 0 : row.readiness?.status === "degraded" ? 1 : 2;
      return rank(a) - rank(b) || a.ticker.localeCompare(b.ticker);
    });
  }, [decisionFilter, decisionSearch, marketState.data, readiness.data, recommendations.data, universe.data]);

  const actionableCount = decisionRows.filter((row) => Object.values(row.recommendation?.horizon_decisions ?? {})
    .some((decision) => decision?.action === "buy_candidate" && decision.publication_status === "publication_ready")).length;
  const coveredCount = (readiness.data ?? []).filter((row) => row.status !== "blocked").length;

  const topOpportunities = [...(recommendations.data ?? [])]
    .sort((a, b) => b.combined_expected_return - a.combined_expected_return)
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
      <Disclaimer />

      <Section title={t("decisionBoard.title")} description={t("decisionBoard.description")}>
        <div className={`${styles.decisionBanner} ${publicationGate.data?.publication_ready ? styles.decisionBannerReady : styles.decisionBannerBlocked}`}>
          <div>
            <span className={styles.decisionEyebrow}>{t("decisionBoard.portfolioStance")}</span>
            <strong>{actionableCount > 0 && publicationGate.data?.publication_ready ? t("decisionBoard.selectiveRisk") : t("decisionBoard.cashAndWait")}</strong>
          </div>
          <div className={styles.decisionStats}>
            <StatTile label={t("decisionBoard.universe")} value={universe.data?.count ?? decisionRows.length} />
            <StatTile label={t("decisionBoard.actionable")} value={actionableCount} />
            <StatTile label={t("decisionBoard.researchable")} value={coveredCount} />
            <StatTile label={t("decisionBoard.marketAsOf")} value={formatDate(marketState.data?.as_of ?? null)} />
          </div>
        </div>

        {publicationGate.data && !publicationGate.data.publication_ready && (
          <Card title={t("decisionBoard.gateBlocked")} subtitle={t("decisionBoard.gateSubtitle", { date: formatDate(publicationGate.data.as_of) })} dense>
            <ul className={styles.compactList}>
              {publicationGate.data.checks.filter((check) => !check.passed).map((check) => (
                <li key={check.id}>{check.label}{check.blocker ? ` — ${check.blocker}` : ""}</li>
              ))}
            </ul>
          </Card>
        )}

        <div className={styles.decisionToolbar}>
          <input
            className={styles.searchInput}
            aria-label={t("decisionBoard.search")}
            placeholder={t("decisionBoard.searchPlaceholder")}
            value={decisionSearch}
            onChange={(event) => setDecisionSearch(event.target.value)}
          />
          <select
            className={styles.filterSelect}
            aria-label={t("decisionBoard.filter")}
            value={decisionFilter}
            onChange={(event) => setDecisionFilter(event.target.value as typeof decisionFilter)}
          >
            <option value="all">{t("decisionBoard.filters.all")}</option>
            <option value="actionable">{t("decisionBoard.filters.actionable")}</option>
            <option value="watch">{t("decisionBoard.filters.watch")}</option>
            <option value="abstain">{t("decisionBoard.filters.abstain")}</option>
          </select>
          <span className={styles.rowCount}>{t("decisionBoard.rows", { count: decisionRows.length })}</span>
        </div>

        {(universe.loading || readiness.loading || recommendations.loading) && <LoadingState rows={6} />}
        {!universe.loading && !readiness.loading && !recommendations.loading && (
          <DataTable
            rows={decisionRows}
            getRowKey={(row) => row.ticker}
            onRowClick={(row) => navigate(`/company/${row.ticker}`)}
            emptyTitle={t("decisionBoard.noRows")}
            emptyDetail={t("decisionBoard.noRowsDetail")}
            columns={[
              { key: "ticker", header: tCommon("table.ticker"), render: (row) => <div className={styles.tickerCell}><span className={`${styles.tickerCode} num`}>{row.ticker}</span><span className={styles.tickerRationale}>{row.company}</span></div> },
              { key: "status", header: tCommon("table.status"), render: (row) => <Badge variant={row.readiness?.status === "ready" ? "positive" : row.readiness?.status === "degraded" ? "warning" : "negative"}>{row.readiness?.status ? label("readinessStatus", row.readiness.status) : t("decisionBoard.notAssessed")}</Badge> },
              ...HORIZONS.map((horizon) => ({
                key: horizon,
                header: label("horizon", horizon),
                render: (row: DecisionBoardRow) => {
                  const decision = row.recommendation?.horizon_decisions?.[horizon];
                  if (!decision) return <span className={styles.abstainCell}>{t("decisionBoard.abstain")}</span>;
                  return <div className={styles.horizonDecision}><Badge variant={decision.action === "buy_candidate" ? "positive" : decision.action === "watch" ? "warning" : "neutral"}>{label("decision", decision.action)}</Badge><span>{formatSignedPercent(decision.expected_return)}</span></div>;
                },
              })),
              { key: "blocker", header: t("decisionBoard.primaryBlocker"), render: (row) => <span className={styles.blockerText}>{row.readiness?.blockers[0] ?? t("decisionBoard.noValidatedDecision")}</span> },
            ]}
          />
        )}

        <Card title={t("decisionBoard.performanceTitle")} subtitle={t("decisionBoard.performanceSubtitle")} dense>
          {decisionPerformance.loading && <LoadingState />}
          {!decisionPerformance.loading && (decisionPerformance.data ?? []).length === 0 && <EmptyState title={t("decisionBoard.noPerformance")} detail={t("decisionBoard.noPerformanceDetail")} />}
          {(decisionPerformance.data ?? []).length > 0 && <DataTable rows={decisionPerformance.data ?? []} getRowKey={(row) => row.horizon} columns={[
            { key: "horizon", header: t("decisionBoard.horizon"), render: (row) => label("horizon", row.horizon) },
            { key: "evaluated", header: t("decisionBoard.evaluated"), align: "right", render: (row) => row.evaluated },
            { key: "hit", header: t("decisionBoard.hitRate"), render: (row) => row.sample_status === "sufficient" && row.hit_rate != null ? formatPercent(row.hit_rate) : t("decisionBoard.insufficientSample") },
            { key: "return", header: t("decisionBoard.realizedReturn"), render: (row) => row.mean_realized_return != null ? formatSignedPercent(row.mean_realized_return) : "—" },
          ]} />}
        </Card>
      </Section>

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
              emptyDetail={
                systemStatus.data && systemStatus.data.knowledge_objects > 0
                  ? t("topOpportunities.emptyDetailMonitoring", { count: systemStatus.data.knowledge_objects })
                  : t("topOpportunities.emptyDetail")
              }
              columns={[
                {
                  key: "ticker",
                  header: tCommon("table.ticker"),
                  render: (r) => (
                    <div className={styles.tickerCell}>
                      <span className={`${styles.tickerCode} num`}>{r.ticker}</span>
                      {r.explanation.why_this_stock && (
                        <span className={styles.tickerRationale}>{r.explanation.why_this_stock}</span>
                      )}
                    </div>
                  ),
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
          <EmptyState
            title={t("portfolio.emptyTitle")}
            detail={
              systemStatus.data && systemStatus.data.knowledge_objects > 0
                ? t("portfolio.emptyDetailMonitoring", { count: systemStatus.data.knowledge_objects })
                : t("portfolio.emptyDetail")
            }
          />
        )}
        {investmentCases.data?.portfolio?.explanation.why_this_stock && (
          <p className={styles.portfolioRationale}>
            <span className={styles.portfolioRationaleLabel}>{t("portfolio.rationale")}</span>
            {investmentCases.data.portfolio.explanation.why_this_stock}
          </p>
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
    </>
  );
}
