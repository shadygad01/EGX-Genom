import { useMemo, useState } from "react";
import { useTranslation } from "react-i18next";
import { Badge } from "../components/primitives/Badge";
import { Card } from "../components/primitives/Card";
import { DataTable } from "../components/primitives/DataTable";
import { Section } from "../components/primitives/Section";
import { StatTile } from "../components/primitives/StatTile";
import { EmptyState, ErrorState, LoadingState } from "../components/primitives/States";
import { useArtifact } from "../hooks/useArtifact";
import { useEnumLabel } from "../hooks/useEnumLabel";
import { useFormatters } from "../hooks/useFormatters";
import { formatPercent, formatSignedPercent, titleCase } from "../lib/format";
import type { WarningCategory } from "../types";
import styles from "./Monitoring.module.css";

const WARNING_VARIANT: Record<string, "warningCritical" | "warningWarning" | "warningInfo"> = {
  critical: "warningCritical",
  warning: "warningWarning",
  info: "warningInfo",
};

const WARNING_CATEGORIES: WarningCategory[] = [
  "broken_thesis",
  "macro_risk_increased",
  "catalyst_expired",
  "liquidity_deterioration",
  "portfolio_concentration",
  "review_required",
];

/** Monitoring -- "what changed since my last decision?" Full warnings
 * list (filterable by category), the pipeline's own reported deltas since
 * the last run, and the two real change timelines that already exist
 * (knowledge revisions, recorded decisions) but previously only appeared
 * buried inside the old AI Briefing research feed. */
export function Monitoring() {
  const { t } = useTranslation("monitoring");
  const { t: tCommon } = useTranslation("common");
  const label = useEnumLabel();
  const { formatDate } = useFormatters();

  const warnings = useArtifact((p) => p.getWarnings());
  const executionReport = useArtifact((p) => p.getExecutionReport());
  const knowledge = useArtifact((p) => p.getKnowledge());
  const decisionHistory = useArtifact((p) => p.getDecisionHistory());
  const shadowFund = useArtifact((p) => p.getShadowFund());
  const shadowFundHistory = useArtifact((p) => p.getShadowFundHistory());

  const [categoryFilter, setCategoryFilter] = useState<WarningCategory | "all">("all");

  const filteredWarnings = useMemo(() => {
    const all = warnings.data?.warnings ?? [];
    return categoryFilter === "all" ? all : all.filter((w) => w.category === categoryFilter);
  }, [warnings.data, categoryFilter]);

  const recentKnowledge = [...(knowledge.data ?? [])]
    .sort((a, b) => (a.discovery_date < b.discovery_date ? 1 : -1))
    .slice(0, 15);

  const recentDecisions = [...(decisionHistory.data ?? [])]
    .sort((a, b) => (a.as_of < b.as_of ? 1 : -1))
    .slice(0, 20);

  const recentTransactions = [...(shadowFundHistory.data?.transactions ?? [])]
    .sort((a, b) => (a.date < b.date ? 1 : -1))
    .slice(0, 20);

  return (
    <>
      <Section title={t("warnings.title")} description={t("warnings.description")}>
        <div className={styles.filterRow}>
          <button
            type="button"
            className={`${styles.filterButton} ${categoryFilter === "all" ? styles.filterButtonActive : ""}`}
            onClick={() => setCategoryFilter("all")}
          >
            {t("warnings.filterAll")}
          </button>
          {WARNING_CATEGORIES.map((category) => (
            <button
              key={category}
              type="button"
              className={`${styles.filterButton} ${categoryFilter === category ? styles.filterButtonActive : ""}`}
              onClick={() => setCategoryFilter(category)}
            >
              {label("warningCategory", category)}
            </button>
          ))}
        </div>

        {warnings.loading && <LoadingState rows={3} />}
        {warnings.error && <ErrorState detail={warnings.error.message} onRetry={warnings.reload} />}
        {!warnings.loading && !warnings.error && filteredWarnings.length === 0 && (
          <EmptyState title={t("warnings.emptyTitle")} detail={t("warnings.emptyDetail")} />
        )}
        {filteredWarnings.length > 0 && (
          <div className={styles.warningsList}>
            {filteredWarnings.map((w, i) => (
              <div key={i} className={`${styles.warningItem} ${styles[WARNING_VARIANT[w.severity]]}`}>
                <div className={styles.warningHead}>
                  <span className={styles.warningTitle}>{w.title}</span>
                  <Badge variant={w.severity === "critical" ? "negative" : w.severity === "warning" ? "warning" : "neutral"}>
                    {label("warningCategory", w.category)}
                  </Badge>
                </div>
                <span className={styles.warningDetail}>{w.detail}</span>
              </div>
            ))}
          </div>
        )}
      </Section>

      <Section title={t("shadowFund.title")} description={t("shadowFund.description")}>
        {shadowFund.loading && <LoadingState rows={3} />}
        {shadowFund.error && <ErrorState detail={shadowFund.error.message} onRetry={shadowFund.reload} />}
        {!shadowFund.loading && !shadowFund.error && !shadowFund.data && (
          <EmptyState title={t("shadowFund.emptyTitle")} detail={t("shadowFund.emptyDetail")} />
        )}
        {shadowFund.data && (
          <>
            <div className={styles.statGrid}>
              <StatTile label={t("shadowFund.nav")} value={shadowFund.data.nav.toFixed(2)} />
              <StatTile
                label={t("shadowFund.cumulativeReturn")}
                value={formatSignedPercent(shadowFund.data.cumulative_return_pct)}
              />
              <StatTile
                label={t("shadowFund.benchmarkReturn")}
                value={formatSignedPercent(shadowFund.data.benchmark_cumulative_return_pct)}
              />
              <StatTile
                label={t("shadowFund.excessReturn")}
                value={formatSignedPercent(shadowFund.data.excess_return_pct)}
              />
              <StatTile label={t("shadowFund.cashAllocation")} value={formatPercent(shadowFund.data.cash_pct)} />
            </div>
            <div className={styles.statGrid} style={{ marginTop: "var(--space-3)" }}>
              <StatTile
                label={t("shadowFund.volatility")}
                value={
                  shadowFund.data.risk.sample_status === "sufficient"
                    ? formatPercent(shadowFund.data.risk.volatility_annualized_pct)
                    : t("shadowFund.insufficientSample", { days: shadowFund.data.risk.sample_days })
                }
              />
              <StatTile
                label={t("shadowFund.maxDrawdown")}
                value={
                  shadowFund.data.risk.max_drawdown_pct != null
                    ? formatSignedPercent(shadowFund.data.risk.max_drawdown_pct)
                    : "—"
                }
              />
              <StatTile
                label={t("shadowFund.sharpeLike")}
                value={shadowFund.data.risk.sharpe_like_ratio != null ? shadowFund.data.risk.sharpe_like_ratio.toFixed(2) : "—"}
              />
            </div>

            <Card title={t("shadowFund.openPositions.title")} dense>
              {shadowFund.data.open_positions.length === 0 && (
                <EmptyState
                  title={t("shadowFund.openPositions.emptyTitle")}
                  detail={t("shadowFund.openPositions.emptyDetail")}
                />
              )}
              {shadowFund.data.open_positions.length > 0 && (
                <DataTable
                  rows={shadowFund.data.open_positions}
                  getRowKey={(p) => p.ticker}
                  columns={[
                    { key: "ticker", header: tCommon("table.ticker"), render: (p) => <span className="num">{p.ticker}</span> },
                    { key: "weight", header: tCommon("table.weight"), align: "right", render: (p) => formatPercent(p.weight) },
                    { key: "entryDate", header: t("shadowFund.openPositions.entryDate"), render: (p) => formatDate(p.entry_date) },
                    { key: "avgCost", header: t("shadowFund.openPositions.avgCost"), align: "right", render: (p) => p.average_cost.toFixed(2) },
                    { key: "marketPrice", header: t("shadowFund.openPositions.marketPrice"), align: "right", render: (p) => p.market_price.toFixed(2) },
                    {
                      key: "unrealizedPnl",
                      header: t("shadowFund.openPositions.unrealizedPnl"),
                      align: "right",
                      render: (p) => (p.unrealized_pnl_pct != null ? formatSignedPercent(p.unrealized_pnl_pct) : "—"),
                    },
                  ]}
                />
              )}
            </Card>

            <Card title={t("shadowFund.transactions.title")} dense>
              {recentTransactions.length === 0 && (
                <EmptyState
                  title={t("shadowFund.transactions.emptyTitle")}
                  detail={t("shadowFund.transactions.emptyDetail")}
                />
              )}
              {recentTransactions.length > 0 && (
                <DataTable
                  rows={recentTransactions}
                  getRowKey={(txn) => txn.id}
                  columns={[
                    { key: "date", header: t("shadowFund.transactions.date"), render: (txn) => formatDate(txn.date) },
                    { key: "ticker", header: tCommon("table.ticker"), render: (txn) => <span className="num">{txn.ticker}</span> },
                    { key: "action", header: tCommon("table.decision"), render: (txn) => titleCase(txn.action) },
                    {
                      key: "weightBefore",
                      header: t("shadowFund.transactions.weightBefore"),
                      align: "right",
                      render: (txn) => formatPercent(txn.weight_before),
                    },
                    {
                      key: "weightAfter",
                      header: t("shadowFund.transactions.weightAfter"),
                      align: "right",
                      render: (txn) => formatPercent(txn.weight_after),
                    },
                    { key: "price", header: t("shadowFund.transactions.price"), align: "right", render: (txn) => txn.price.toFixed(2) },
                  ]}
                />
              )}
            </Card>
          </>
        )}
      </Section>

      {executionReport.data && (
        <Section title={t("sinceLastRun.title")} description={t("sinceLastRun.description")}>
          <div className={styles.statGrid}>
            <StatTile
              label={t("sinceLastRun.knowledgeObjects")}
              value={executionReport.data.knowledge_after}
              deltaSign={Math.sign(executionReport.data.knowledge_after - executionReport.data.knowledge_before)}
              delta={t("sinceLastRun.delta", {
                delta: `${executionReport.data.knowledge_after - executionReport.data.knowledge_before >= 0 ? "+" : ""}${
                  executionReport.data.knowledge_after - executionReport.data.knowledge_before
                }`,
              })}
            />
            <StatTile
              label={t("sinceLastRun.genes")}
              value={executionReport.data.genome_after}
              deltaSign={Math.sign(executionReport.data.genome_after - executionReport.data.genome_before)}
              delta={t("sinceLastRun.delta", {
                delta: `${executionReport.data.genome_after - executionReport.data.genome_before >= 0 ? "+" : ""}${
                  executionReport.data.genome_after - executionReport.data.genome_before
                }`,
              })}
            />
            <StatTile
              label={t("sinceLastRun.events")}
              value={executionReport.data.events_after}
              deltaSign={Math.sign(executionReport.data.events_after - executionReport.data.events_before)}
              delta={t("sinceLastRun.delta", {
                delta: `${executionReport.data.events_after - executionReport.data.events_before >= 0 ? "+" : ""}${
                  executionReport.data.events_after - executionReport.data.events_before
                }`,
              })}
            />
            <StatTile label={t("sinceLastRun.pipelineStatus")} value={label("stageStatus", executionReport.data.overall_status)} />
          </div>
          {executionReport.data.errors.length > 0 && (
            <div className={styles.list} style={{ marginTop: "var(--space-4)" }}>
              {executionReport.data.errors.map((e, i) => (
                <div key={i} className={styles.listItemDetail}>
                  <Badge variant="negative">{t("sinceLastRun.error")}</Badge> {e}
                </div>
              ))}
            </div>
          )}
        </Section>
      )}

      <Section title={t("knowledgeChanges.title")} description={t("knowledgeChanges.description")}>
        {knowledge.loading && <LoadingState rows={3} />}
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
                  <Badge variant={k.status === "retired" ? "neutral" : k.status === "monitoring" ? "accent" : "positive"}>
                    {label("knowledgeStatus", k.status)}
                  </Badge>
                  <Badge variant="neutral">{label("horizon", k.horizon)}</Badge>
                </div>
                <span className={styles.listItemDetail}>{k.economic_explanation}</span>
              </div>
            ))}
          </div>
        )}
      </Section>

      <Section title={t("decisionChanges.title")} description={t("decisionChanges.description")}>
        {decisionHistory.loading && <LoadingState rows={3} />}
        {decisionHistory.error && <ErrorState detail={decisionHistory.error.message} onRetry={decisionHistory.reload} />}
        {!decisionHistory.loading && !decisionHistory.error && recentDecisions.length === 0 && (
          <EmptyState title={t("decisionChanges.emptyTitle")} detail={t("decisionChanges.emptyDetail")} />
        )}
        {recentDecisions.length > 0 && (
          <Card dense>
            <DataTable
              rows={recentDecisions}
              getRowKey={(d) => `${d.id}-${d.version}`}
              columns={[
                { key: "ticker", header: tCommon("table.ticker"), render: (d) => <span className="num">{d.ticker}</span> },
                { key: "asOf", header: t("decisionChanges.asOf"), render: (d) => formatDate(d.as_of) },
                { key: "horizon", header: t("decisionChanges.horizon"), render: (d) => label("horizon", d.horizon) },
                { key: "action", header: tCommon("table.decision"), render: (d) => label("decision", d.action) },
                {
                  key: "realized",
                  header: t("decisionChanges.realizedReturn"),
                  align: "right",
                  render: (d) => (d.realized_return != null ? formatSignedPercent(d.realized_return) : "—"),
                },
              ]}
            />
          </Card>
        )}
      </Section>
    </>
  );
}
