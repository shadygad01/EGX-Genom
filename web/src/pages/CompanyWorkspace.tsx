import { useParams } from "react-router-dom";
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
  formatNumber,
  formatPercent,
  formatSignedPercent,
  titleCase,
} from "../lib/format";
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
        <Card title="Current Investment Thesis">
          {!recommendation && !recommendations.loading && (
            <EmptyState
              title="No active recommendation"
              detail="AGX has no current recommendation for this ticker -- it may not yet have cleared the validation pipeline, or no supporting knowledge exists."
            />
          )}
          {recommendation && (
            <div>
              <div className={styles.grid}>
                <StatTile label="Confidence" value={formatPercent(recommendation.confidence)} />
                <StatTile
                  label="Exp. Return"
                  value={formatSignedPercent(recommendation.combined_expected_return)}
                  deltaSign={recommendation.combined_expected_return >= 0 ? 1 : -1}
                />
                <StatTile label="Exp. Risk" value={formatPercent(recommendation.combined_expected_risk)} />
              </div>

              <div className={styles.block}>
                <div className={styles.blockTitle}>Research Summary</div>
                <p className={styles.blockText}>
                  {recommendation.explanation.why_this_stock} {recommendation.explanation.why_now}
                </p>
              </div>

              <div className={styles.block}>
                <div className={styles.blockTitle}>Risk Summary</div>
                <p className={styles.blockText}>{recommendation.explanation.why_not_others}</p>
              </div>

              <div className={styles.block}>
                <div className={styles.blockTitle}>Supporting Evidence</div>
                {recommendation.explanation.supporting_evidence.length === 0 ? (
                  <span className={styles.blockText}>None recorded.</span>
                ) : (
                  <ul className={styles.bulletList}>
                    {recommendation.explanation.supporting_evidence.map((e, i) => (
                      <li key={i}>{e}</li>
                    ))}
                  </ul>
                )}
              </div>

              <div className={styles.block}>
                <div className={styles.blockTitle}>Contradicting Evidence / Invalidation Conditions</div>
                {recommendation.explanation.invalidation_conditions.length === 0 ? (
                  <span className={styles.blockText}>None recorded.</span>
                ) : (
                  <ul className={styles.bulletList}>
                    {recommendation.explanation.invalidation_conditions.map((e, i) => (
                      <li key={i}>{e}</li>
                    ))}
                  </ul>
                )}
              </div>

              <div className={styles.block}>
                <div className={styles.blockTitle}>Historical Similar Cases</div>
                {recommendation.explanation.similar_historical_cases.length === 0 ? (
                  <span className={styles.blockText}>None recorded.</span>
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

        <Card title="Upcoming Catalysts" subtitle="Scheduled corporate events on or after the last cycle date">
          {upcomingCatalysts.length === 0 ? (
            <EmptyState title="No scheduled catalysts" detail="No known corporate events are upcoming for this ticker." />
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

      <Section title="Knowledge Timeline" description="Knowledge objects that name this ticker as an affected asset.">
        {knowledge.error && <ErrorState detail={knowledge.error.message} onRetry={knowledge.reload} />}
        {!knowledge.error && tickerKnowledge.length === 0 && !knowledge.loading && (
          <EmptyState title="No knowledge objects yet" detail="No promoted or monitored knowledge names this ticker." />
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
                  <Badge variant="neutral">{formatPercent(k.confidence)} confidence</Badge>
                </div>
                <span className={styles.listItemDetail}>{k.economic_explanation}</span>
              </div>
            ))}
          </div>
        )}
      </Section>

      <div className={styles.twoCol}>
        <Card title="Research Papers" subtitle="Papers published from knowledge naming this ticker">
          {tickerPapers.length === 0 ? (
            <EmptyState title="No papers yet" detail="No published research paper traces back to this ticker's knowledge." />
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

        <Card title="Genes" subtitle="Lineage of this ticker's knowledge as it mutates over time">
          {tickerGenes.length === 0 ? (
            <EmptyState title="No genes yet" detail="No gene lineage exists for this ticker's knowledge." />
          ) : (
            <div className={styles.list}>
              {tickerGenes.map((g) => (
                <div key={g.id} className={styles.listItem}>
                  <div className={styles.listItemHead}>
                    <span className={styles.listItemTitle}>{g.id} · gen {g.generation}</span>
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

      <Section title="Financial Statements" description="Line items collected for this ticker.">
        <DataTable
          rows={tickerStatements}
          getRowKey={(f, i) => `${f.period_end_date}-${f.statement_type}-${f.line_item}-${i}`}
          emptyTitle="No financial statements collected"
          emptyDetail="Financial statement collection is built but not yet wired to a live, verified filing source (see docs/TECHNICAL_DEBT.md)."
          columns={[
            { key: "period", header: "Period End", render: (f) => formatDate(f.period_end_date) },
            { key: "type", header: "Type", render: (f) => titleCase(f.period_type) },
            { key: "statement", header: "Statement", render: (f) => titleCase(f.statement_type) },
            { key: "item", header: "Line Item", render: (f) => titleCase(f.line_item) },
            {
              key: "value",
              header: "Value",
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
        <Card title="Corporate Actions" subtitle="Past corporate events for this ticker">
          {pastActions.length === 0 ? (
            <EmptyState title="No corporate actions recorded" />
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

        <Card title="News Timeline" subtitle="Headlines mentioning this ticker">
          {news.length === 0 ? (
            <EmptyState title="No news yet" />
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

      <Card title="Market Regime & Macro Exposure">
        <EmptyState
          title="Not yet available"
          detail="No market regime classification or per-ticker macro-exposure artifact exists yet upstream -- this section will populate once the research engine produces one, per the platform's anti-fabrication principle."
        />
      </Card>
    </>
  );
}
