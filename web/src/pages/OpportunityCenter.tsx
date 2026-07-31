import { useState } from "react";
import { Link } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { Badge } from "../components/primitives/Badge";
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
import { dedupeEvidence, formatPercent, formatSignedPercent, humanizeEvidence } from "../lib/format";
import type {
  CorporateEvent,
  DecisionReadiness,
  Horizon,
  ReadinessStatus,
  Recommendation,
  TickerDataGapReport,
} from "../types";
import styles from "./OpportunityCenter.module.css";

const HORIZON_ORDER: Horizon[] = ["micro", "swing", "investment"];

// Closest to a decision first: a ticker AGX can already act on outranks
// one that's merely degraded, which outranks one still fully blocked.
const READINESS_RANK: Record<ReadinessStatus, number> = { ready: 0, degraded: 1, blocked: 2 };

/** Every opportunity AGX currently sees, ranked by expected return
 * (highest to lowest) -- the mission's "heart of AGX." Selecting a row
 * shows the full explanation inline; "Open full research workspace" goes
 * to the per-company deep page (Company Research Workspace, a later
 * milestone). */
export function OpportunityCenter() {
  const { t } = useTranslation("opportunityCenter");
  const { t: tCommon } = useTranslation("common");
  const label = useEnumLabel();
  const { formatDate } = useFormatters();
  const recommendations = useArtifact((p) => p.getRecommendations());
  const marketState = useArtifact((p) => p.getMarketState());
  const readiness = useArtifact((p) => p.getDecisionReadiness());
  const gapReport = useArtifact((p) => p.getTickerDataGapReport());
  const [selectedTicker, setSelectedTicker] = useState<string | null>(null);
  const [selectedGapTicker, setSelectedGapTicker] = useState<string | null>(null);

  const ranked = [...(recommendations.data ?? [])].sort(
    (a, b) => b.combined_expected_return - a.combined_expected_return,
  );
  const companyNames = marketState.data?.constituents ?? {};
  const selected = ranked.find((r) => r.ticker === selectedTicker) ?? ranked[0] ?? null;

  const catalystsForSelected: CorporateEvent[] = selected
    ? (marketState.data?.dataset_snapshot.corporate_events[selected.ticker] ?? [])
        .filter((ce) => (marketState.data ? ce.event_date >= marketState.data.as_of : true))
        .sort((a, b) => (a.event_date > b.event_date ? 1 : -1))
    : [];

  const gapReports = gapReport.data ?? [];
  const selectedGap = gapReports.find((g) => g.ticker === selectedGapTicker) ?? null;

  // Readiness closest to an actual decision first (ready, then degraded,
  // then blocked), not backend insertion order -- a user scanning this
  // table wants the tickers nearest to "researchable" at the top.
  const rankedReadiness = [...(readiness.data ?? [])].sort((a, b) => {
    const rank = READINESS_RANK[a.status] - READINESS_RANK[b.status];
    return rank !== 0 ? rank : a.ticker.localeCompare(b.ticker);
  });

  return (
    <Section title={t("title")} description={t("description")}>
      <Disclaimer />
      {recommendations.loading && <LoadingState rows={4} />}
      {recommendations.error && <ErrorState detail={recommendations.error.message} onRetry={recommendations.reload} />}

      {!recommendations.loading && !recommendations.error && (
        <div className={styles.layout}>
          <Card dense>
            <DataTable
              rows={ranked}
              getRowKey={(r) => r.ticker}
              onRowClick={(r) => setSelectedTicker(r.ticker)}
              emptyTitle={t("emptyTitle")}
              emptyDetail={t("emptyDetail")}
              columns={[
                {
                  key: "ticker",
                  header: t("columns.opportunity"),
                  render: (r) => (
                    <div className={styles.tickerCell}>
                      <span className={`${styles.tickerCode} num`}>{r.ticker}</span>
                      <span className={styles.tickerCompany}>{companyNames[r.ticker] ?? ""}</span>
                    </div>
                  ),
                },
                {
                  key: "confidence",
                  header: tCommon("table.confidence"),
                  render: (r) => <Meter value={r.confidence} label={formatPercent(r.confidence)} />,
                },
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
                {
                  key: "risk",
                  header: tCommon("table.expRisk"),
                  align: "right",
                  render: (r) => <span className="num">{formatPercent(r.combined_expected_risk)}</span>,
                },
                {
                  key: "horizons",
                  header: t("columns.horizons"),
                  render: (r) => (
                    <div className={styles.horizonBadges}>
                      {HORIZON_ORDER.filter((h) => r.horizon_predictions[h]).map((h) => {
                        const prediction = r.horizon_predictions[h]!;
                        return (
                          <Badge
                            key={h}
                            variant={prediction.expected_return >= 0 ? "positive" : "negative"}
                            title={t("badgeTitle", {
                              horizon: label("horizon", h),
                              return: formatSignedPercent(prediction.expected_return),
                              confidence: formatPercent(prediction.confidence),
                            })}
                          >
                            {label("horizon", h)} <span className="num">{formatSignedPercent(prediction.expected_return)}</span>
                          </Badge>
                        );
                      })}
                    </div>
                  ),
                },
              ]}
            />
          </Card>

          <Card title={selected ? t("evidenceTitle", { ticker: selected.ticker }) : t("evidence")} dense>
            {!selected && <EmptyState title={t("noOpportunitySelected")} detail={t("selectRowDetail")} />}
            {selected && <OpportunityDetail recommendation={selected} companyName={companyNames[selected.ticker]} catalysts={catalystsForSelected} />}
          </Card>
        </div>
      )}

      <div className={styles.layout}>
        <Card title={t("decisionReadiness.title")} subtitle={t("decisionReadiness.subtitle")} dense>
          {readiness.loading && <LoadingState rows={4} />}
          {readiness.error && <ErrorState detail={readiness.error.message} onRetry={readiness.reload} />}
          {!readiness.loading && !readiness.error && (
            <DataTable<DecisionReadiness>
              rows={rankedReadiness}
              getRowKey={(row) => row.ticker}
              onRowClick={(row) => setSelectedGapTicker(row.ticker)}
              emptyTitle={t("decisionReadiness.emptyTitle")}
              emptyDetail={t("decisionReadiness.emptyDetail")}
              columns={[
                { key: "ticker", header: tCommon("table.ticker"), render: (row) => <span className={`${styles.tickerCode} num`}>{row.ticker}</span> },
                {
                  key: "status",
                  header: tCommon("table.status"),
                  render: (row) => (
                    <Badge variant={row.status === "ready" ? "positive" : row.status === "degraded" ? "warning" : "negative"}>
                      {label("readinessStatus", row.status)}
                    </Badge>
                  ),
                },
                { key: "decision", header: tCommon("table.decision"), render: (row) => label("decision", row.decision) },
                { key: "prices", header: t("columns.prices"), align: "right", render: (row) => <span className="num">{row.price_observations}</span> },
                { key: "financials", header: t("columns.financialPeriods"), align: "right", render: (row) => <span className="num">{row.financial_periods}</span> },
                { key: "knowledge", header: t("columns.knowledge"), align: "right", render: (row) => <span className="num">{row.active_knowledge}</span> },
                {
                  key: "fairValueGap",
                  header: t("columns.fairValueGap"),
                  align: "right",
                  render: (row) =>
                    row.price_vs_fair_value_pct == null ? (
                      <span className="num">{t("columns.noFairValue")}</span>
                    ) : (
                      <span
                        className="num"
                        style={{ color: row.price_vs_fair_value_pct > 0 ? "var(--negative)" : "var(--positive)" }}
                      >
                        {formatSignedPercent(row.price_vs_fair_value_pct)}
                      </span>
                    ),
                },
                { key: "blocker", header: t("columns.primaryBlocker"), render: (row) => row.blockers[0] ?? t("columns.none") },
              ]}
            />
          )}
        </Card>

        <Card title={selectedGap ? t("dataCoverage.titleForTicker", { ticker: selectedGap.ticker }) : t("dataCoverage.title")} dense>
          {gapReport.loading && <LoadingState rows={4} />}
          {gapReport.error && <ErrorState detail={gapReport.error.message} onRetry={gapReport.reload} />}
          {!gapReport.loading && !gapReport.error && !selectedGap && (
            <EmptyState title={t("dataCoverage.noTickerSelected")} detail={t("dataCoverage.selectRowDetail")} />
          )}
          {!gapReport.loading && !gapReport.error && selectedGap && <TickerGapDetail gap={selectedGap} />}
        </Card>
      </div>
    </Section>
  );
}

function TickerGapDetail({ gap }: { gap: TickerDataGapReport }) {
  const { t } = useTranslation("opportunityCenter");
  const { t: tCommon } = useTranslation("common");
  return (
    <div>
      <div className={styles.detailStats}>
        <StatTile label={t("dataCoverage.overallCompleteness")} value={formatPercent(gap.overall_completeness_pct / 100)} />
        <StatTile label={t("dataCoverage.swingReady")} value={gap.swing_ready ? t("dataCoverage.yes") : t("dataCoverage.no")} />
        <StatTile label={t("dataCoverage.investmentReady")} value={gap.investment_ready ? t("dataCoverage.yes") : t("dataCoverage.no")} />
      </div>

      <div className={styles.block}>
        <div className={styles.blockTitle}>{t("dataCoverage.dataLayers")}</div>
        <div className={styles.horizonGrid}>
          {gap.layers.map((layer) => (
            <div key={layer.layer} className={styles.horizonCard}>
              <div className={styles.horizonCardHeader}>
                <span className={styles.horizonCardTitle}>{t(`layers.${layer.layer}`, { defaultValue: layer.layer })}</span>
                <Meter value={layer.completeness_pct / 100} label={`${layer.completeness_pct}%`} />
              </div>
              <div className={styles.horizonCardStats}>
                <span className="num">{layer.count}</span>
                <span className={styles.horizonCardStatLabel}>{t("dataCoverage.ofRequired", { threshold: layer.threshold })}</span>
              </div>
              {!layer.complete && (
                <p className={styles.horizonCardWhy}>{t("dataCoverage.belowThreshold")}</p>
              )}
            </div>
          ))}
        </div>
      </div>

      <div className={styles.block}>
        <div className={styles.blockTitle}>{tCommon("table.blockers")}</div>
        {gap.blockers.length === 0 ? (
          <span className={styles.blockText}>{tCommon("states.noneRecorded")}</span>
        ) : (
          <ul className={styles.bulletList}>
            {gap.blockers.map((b, i) => (
              <li key={i}>{b}</li>
            ))}
          </ul>
        )}
      </div>

      <div className={styles.block}>
        <div className={styles.blockTitle}>{tCommon("table.nextActions")}</div>
        {gap.next_actions.length === 0 ? (
          <span className={styles.blockText}>{tCommon("states.noneRecorded")}</span>
        ) : (
          <ul className={styles.bulletList}>
            {gap.next_actions.map((a, i) => (
              <li key={i}>{a}</li>
            ))}
          </ul>
        )}
      </div>
    </div>
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
  const { t } = useTranslation("opportunityCenter");
  const { t: tCommon } = useTranslation("common");
  const label = useEnumLabel();
  const { formatDate } = useFormatters();
  const { explanation } = recommendation;
  return (
    <div>
      <div className={styles.detailHeader}>
        <span className={`${styles.detailTicker} num`}>{recommendation.ticker}</span>
        {companyName && <span className={styles.detailCompany}>{companyName}</span>}
      </div>

      <div className={styles.detailStats}>
        <StatTile label={tCommon("table.confidence")} value={formatPercent(recommendation.confidence)} />
        <StatTile
          label={tCommon("table.expReturn")}
          value={formatSignedPercent(recommendation.combined_expected_return)}
          deltaSign={recommendation.combined_expected_return >= 0 ? 1 : -1}
        />
        <StatTile label={tCommon("table.expRisk")} value={formatPercent(recommendation.combined_expected_risk)} />
      </div>

      <div className={styles.block}>
        <div className={styles.blockTitle}>{t("detail.horizonBreakdown")}</div>
        <div className={styles.horizonGrid}>
          {HORIZON_ORDER.map((h) => {
            const prediction = recommendation.horizon_predictions[h];
            return (
              <div key={h} className={styles.horizonCard}>
                <div className={styles.horizonCardHeader}>
                  <span className={styles.horizonCardTitle}>{label("horizon", h)}</span>
                  {prediction ? (
                    <Meter value={prediction.confidence} label={formatPercent(prediction.confidence)} />
                  ) : (
                    <Badge variant="neutral">{tCommon("table.noSignal")}</Badge>
                  )}
                </div>
                {prediction ? (
                  <>
                    <div className={styles.horizonCardStats}>
                      <span
                        className="num"
                        style={{ color: prediction.expected_return >= 0 ? "var(--positive)" : "var(--negative)" }}
                      >
                        {formatSignedPercent(prediction.expected_return)}
                      </span>
                      <span className={styles.horizonCardStatLabel}>{t("detail.expReturnShort")}</span>
                      <span className="num">{formatPercent(prediction.expected_risk)}</span>
                      <span className={styles.horizonCardStatLabel}>{t("detail.expRiskShort")}</span>
                    </div>
                    <p className={styles.horizonCardWhy}>
                      {prediction.explanation.why_this_stock} {prediction.explanation.why_now}
                    </p>
                  </>
                ) : (
                  <p className={styles.horizonCardWhy}>{t("detail.noModelPrediction")}</p>
                )}
              </div>
            );
          })}
        </div>
      </div>

      <div className={styles.block}>
        <div className={styles.blockTitle}>{t("detail.researchSummary")}</div>
        <p className={styles.blockText}>{explanation.why_this_stock} {explanation.why_now}</p>
      </div>

      <div className={styles.block}>
        <div className={styles.blockTitle}>{t("detail.riskSummary")}</div>
        <p className={styles.blockText}>{explanation.why_not_others}</p>
      </div>

      <div className={styles.block}>
        <div className={styles.blockTitle}>{t("detail.supportingEvidence")}</div>
        {explanation.supporting_evidence.length === 0 ? (
          <span className={styles.blockText}>{tCommon("states.noneRecorded")}</span>
        ) : (
          <ul className={styles.bulletList}>
            {dedupeEvidence(explanation.supporting_evidence).map((e, i) => (
              <li key={i}>{humanizeEvidence(e)}</li>
            ))}
          </ul>
        )}
      </div>

      <div className={styles.block}>
        <div className={styles.blockTitle}>{t("detail.contradictingEvidence")}</div>
        {explanation.invalidation_conditions.length === 0 ? (
          <span className={styles.blockText}>{tCommon("states.noneRecorded")}</span>
        ) : (
          <ul className={styles.bulletList}>
            {explanation.invalidation_conditions.map((e, i) => (
              <li key={i}>{e}</li>
            ))}
          </ul>
        )}
      </div>

      <div className={styles.block}>
        <div className={styles.blockTitle}>{t("detail.historicalSimilarCases")}</div>
        {explanation.similar_historical_cases.length === 0 ? (
          <span className={styles.blockText}>{tCommon("states.noneRecorded")}</span>
        ) : (
          <ul className={styles.bulletList}>
            {explanation.similar_historical_cases.map((e, i) => (
              <li key={i}>{e}</li>
            ))}
          </ul>
        )}
      </div>

      <div className={styles.block}>
        <div className={styles.blockTitle}>{t("detail.upcomingCatalysts")}</div>
        {catalysts.length === 0 ? (
          <span className={styles.blockText}>{t("detail.noScheduledCatalysts")}</span>
        ) : (
          <ul className={styles.bulletList}>
            {catalysts.map((c, i) => (
              <li key={i}>
                {t("detail.catalystLine", {
                  date: formatDate(c.event_date),
                  eventType: label("corporateEventType", c.event_type),
                  description: c.description,
                })}
              </li>
            ))}
          </ul>
        )}
      </div>

      <Link className={styles.workspaceLink} to={`/company/${recommendation.ticker}`}>
        {t("detail.openWorkspace")} <span className="icon-forward" aria-hidden="true">→</span>
      </Link>
    </div>
  );
}
