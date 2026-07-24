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
      <Section
        title="System Health"
        description="Pipeline execution status as of the most recent research cycle."
      >
        {systemStatus.loading && <LoadingState rows={1} />}
        {systemStatus.error && <ErrorState detail={systemStatus.error.message} onRetry={systemStatus.reload} />}
        {systemStatus.data && (
          <div className={styles.statGrid}>
            <StatTile label="Last Cycle" value={formatDate(systemStatus.data.pipeline_run_date)} />
            <StatTile label="Runs" value={systemStatus.data.runs} />
            <StatTile
              label="Succeeded"
              value={systemStatus.data.succeeded}
              deltaSign={systemStatus.data.failed > 0 ? -1 : 1}
              delta={systemStatus.data.failed > 0 ? `${systemStatus.data.failed} failed` : "all clear"}
            />
            <StatTile label="Knowledge Objects" value={systemStatus.data.knowledge_objects} />
            {Object.entries(systemStatus.data.by_status).map(([status, count]) => (
              <StatTile key={status} label={titleCase(status)} value={count} />
            ))}
          </div>
        )}
      </Section>

      {executionReport.data && (
        <Section
          title="Changes Since Yesterday"
          description="Net movement in knowledge and discoveries produced by the last full pipeline execution."
        >
          <div className={styles.statGrid}>
            <StatTile
              label="Knowledge Objects"
              value={executionReport.data.knowledge_after}
              deltaSign={Math.sign(executionReport.data.knowledge_after - executionReport.data.knowledge_before)}
              delta={`${executionReport.data.knowledge_after - executionReport.data.knowledge_before >= 0 ? "+" : ""}${
                executionReport.data.knowledge_after - executionReport.data.knowledge_before
              } since last run`}
            />
            <StatTile
              label="Genes"
              value={executionReport.data.genome_after}
              deltaSign={Math.sign(executionReport.data.genome_after - executionReport.data.genome_before)}
              delta={`${executionReport.data.genome_after - executionReport.data.genome_before >= 0 ? "+" : ""}${
                executionReport.data.genome_after - executionReport.data.genome_before
              } since last run`}
            />
            <StatTile
              label="Events"
              value={executionReport.data.events_after}
              deltaSign={Math.sign(executionReport.data.events_after - executionReport.data.events_before)}
              delta={`${executionReport.data.events_after - executionReport.data.events_before >= 0 ? "+" : ""}${
                executionReport.data.events_after - executionReport.data.events_before
              } since last run`}
            />
            <StatTile label="Pipeline Status" value={titleCase(executionReport.data.overall_status)} />
          </div>
          {executionReport.data.errors.length > 0 && (
            <div className={styles.list} style={{ marginTop: "var(--space-4)" }}>
              {executionReport.data.errors.map((e, i) => (
                <div key={i} className={styles.listItemDetail}>
                  <Badge variant="negative">Error</Badge> {e}
                </div>
              ))}
            </div>
          )}
        </Section>
      )}

      <Section title="Market Summary" description="Trading session and universe snapshot as of the last cycle.">
        {marketState.loading && <LoadingState rows={1} />}
        {marketState.error && <ErrorState detail={marketState.error.message} onRetry={marketState.reload} />}
        {marketState.data === null && !marketState.loading && !marketState.error && (
          <EmptyState title="No market state yet" detail="Available once the first research cycle runs." />
        )}
        {marketState.data && (
          <div className={styles.statGrid}>
            <StatTile label="As Of" value={formatDate(marketState.data.as_of)} />
            <StatTile
              label="Trading Session"
              value={marketState.data.trading_session.is_trading_day ? "Open" : "Closed"}
              caption={marketState.data.trading_session.holiday_name ?? undefined}
            />
            <StatTile label="Constituents" value={Object.keys(marketState.data.constituents).length} />
            <StatTile label="Sectors" value={new Set(Object.values(marketState.data.sectors)).size} />
          </div>
        )}
      </Section>

      <div className={styles.twoCol}>
        <Card title="Top Opportunities" subtitle="Ranked by AGX confidence">
          {recommendations.loading && <LoadingState />}
          {recommendations.error && <ErrorState detail={recommendations.error.message} onRetry={recommendations.reload} />}
          {!recommendations.loading && !recommendations.error && (
            <DataTable
              rows={topOpportunities}
              getRowKey={(r) => r.ticker}
              onRowClick={(r) => navigate(`/company/${r.ticker}`)}
              emptyTitle="No opportunities yet"
              emptyDetail="Recommendations appear once the Meta Decision Engine has combined horizon predictions."
              columns={[
                {
                  key: "ticker",
                  header: "Ticker",
                  render: (r) => <span style={{ color: "var(--accent-strong)", fontWeight: 600 }}>{r.ticker}</span>,
                },
                { key: "confidence", header: "Confidence", render: (r) => <Meter value={r.confidence} label={formatPercent(r.confidence)} /> },
                {
                  key: "return",
                  header: "Exp. Return",
                  align: "right",
                  render: (r) => (
                    <span className="num" style={{ color: r.combined_expected_return >= 0 ? "var(--positive)" : "var(--negative)" }}>
                      {formatSignedPercent(r.combined_expected_return)}
                    </span>
                  ),
                },
                { key: "risk", header: "Exp. Risk", align: "right", render: (r) => <span className="num">{formatPercent(r.combined_expected_risk)}</span> },
              ]}
            />
          )}
        </Card>

        <Card title="Biggest Risks" subtitle="High and critical severity events currently on watch">
          {events.loading && <LoadingState />}
          {events.error && <ErrorState detail={events.error.message} onRetry={events.reload} />}
          {!events.loading && !events.error && elevatedEvents.length === 0 && (
            <EmptyState title="No elevated-severity events" detail="Nothing rated high or critical severity right now." />
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

        <Card title="Most Important News" subtitle="Latest headlines from AGX's monitored sources">
          {marketState.loading && <LoadingState />}
          {!marketState.loading && news.length === 0 && (
            <EmptyState title="No news yet" detail="News items appear once a collection cycle ingests them." />
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

        <Card title="Upcoming Catalysts" subtitle="Scheduled corporate events on or after the last cycle date">
          {marketState.loading && <LoadingState />}
          {!marketState.loading && upcomingCatalysts.length === 0 && (
            <EmptyState title="No scheduled catalysts" detail="No known corporate events are upcoming for the covered universe." />
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

        <Card title="Knowledge Changes" subtitle="Most recently discovered or updated knowledge objects">
          {knowledge.loading && <LoadingState />}
          {knowledge.error && <ErrorState detail={knowledge.error.message} onRetry={knowledge.reload} />}
          {!knowledge.loading && !knowledge.error && recentKnowledge.length === 0 && (
            <EmptyState title="No knowledge objects yet" detail="Promoted or monitored knowledge will appear here once discovered." />
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

        <Card title="Scientific Discoveries" subtitle="Most recently published research papers">
          {papers.loading && <LoadingState />}
          {papers.error && <ErrorState detail={papers.error.message} onRetry={papers.reload} />}
          {!papers.loading && !papers.error && recentPapers.length === 0 && (
            <EmptyState title="No papers yet" detail="Papers are produced once a hypothesis is promoted to knowledge." />
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

      <Section title="Portfolio" description="Current portfolio-level recommendation, if the Meta Decision Engine has produced one.">
        {investmentCases.loading && <LoadingState />}
        {investmentCases.error && <ErrorState detail={investmentCases.error.message} onRetry={investmentCases.reload} />}
        {!investmentCases.loading && !investmentCases.error && investmentCases.data?.portfolio == null && (
          <EmptyState title="No portfolio recommendation yet" detail="A portfolio recommendation appears once produced by a full pipeline run." />
        )}
        {investmentCases.data?.portfolio && (
          <DataTable
            rows={investmentCases.data.portfolio.positions}
            getRowKey={(p) => p.ticker}
            columns={[
              {
                key: "ticker",
                header: "Ticker",
                render: (p) => (
                  <Link to={`/company/${p.ticker}`} style={{ color: "var(--accent-strong)", fontWeight: 600 }}>
                    {p.ticker}
                  </Link>
                ),
              },
              { key: "weight", header: "Weight", align: "right", render: (p) => <span className="num">{formatPercent(p.weight)}</span> },
              { key: "confidence", header: "Confidence", render: (p) => <Meter value={p.confidence} label={formatPercent(p.confidence)} /> },
              {
                key: "return",
                header: "Exp. Return",
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
            <StatTile label="Cash Weight" value={formatPercent(investmentCases.data.portfolio.cash_weight)} />
            <StatTile label="Positions" value={investmentCases.data.portfolio.positions.length} />
          </div>
        )}
      </Section>
    </>
  );
}
