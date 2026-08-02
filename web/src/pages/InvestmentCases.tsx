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
import type { CorporateEvent, DecisionReadiness, Horizon, Recommendation } from "../types";
import styles from "./InvestmentCases.module.css";

const HORIZON_ORDER: Horizon[] = ["micro", "swing", "investment"];

/** Investment Cases -- "why should I own this company?" answered for
 * every ticker AGX currently sees, ranked by expected return. Selecting a
 * row previews the evidence inline; "Open full Investment Case" goes to
 * the per-ticker deep page with the full Decision/Allocation/Horizon/
 * Confidence header and all 19 mandated sections. */
export function InvestmentCases() {
  const { t } = useTranslation("investmentCases");
  const { t: tCommon } = useTranslation("common");
  const label = useEnumLabel();
  const { formatDate } = useFormatters();
  const recommendations = useArtifact((p) => p.getRecommendations());
  const readiness = useArtifact((p) => p.getDecisionReadiness());
  const marketState = useArtifact((p) => p.getMarketState());
  const [selectedTicker, setSelectedTicker] = useState<string | null>(null);

  const ranked = [...(recommendations.data ?? [])].sort(
    (a, b) => b.combined_expected_return - a.combined_expected_return,
  );
  const companyNames = marketState.data?.constituents ?? {};
  const selected = ranked.find((r) => r.ticker === selectedTicker) ?? ranked[0] ?? null;
  const recommendationByTicker = new Map(ranked.map((row) => [row.ticker, row]));
  const readinessByTicker = new Map((readiness.data ?? []).map((row) => [row.ticker, row]));
  const universeRows = Object.keys(companyNames)
    .map((ticker) => ({
      ticker,
      recommendation: recommendationByTicker.get(ticker) ?? null,
      readiness: readinessByTicker.get(ticker) ?? null,
    }))
    .sort((a, b) => {
      const ar = a.recommendation?.combined_expected_return;
      const br = b.recommendation?.combined_expected_return;
      if (ar != null && br != null) return br - ar;
      if (ar != null) return -1;
      if (br != null) return 1;
      return a.ticker.localeCompare(b.ticker);
    })
    .map((row, index) => ({ ...row, rank: index + 1 }));

  const catalystsForSelected: CorporateEvent[] = selected
    ? (marketState.data?.dataset_snapshot.corporate_events[selected.ticker] ?? [])
        .filter((ce) => (marketState.data ? ce.event_date >= marketState.data.as_of : true))
        .sort((a, b) => (a.event_date > b.event_date ? 1 : -1))
    : [];

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
            {selected && <CasePreview recommendation={selected} companyName={companyNames[selected.ticker]} catalysts={catalystsForSelected} />}
          </Card>
        </div>
      )}

      <Section title={t("universe.title")} description={t("universe.description")}>
        {(marketState.loading || readiness.loading) && <LoadingState rows={6} />}
        {!marketState.loading && !readiness.loading && (
          <Card dense>
            <DataTable
              rows={universeRows}
              getRowKey={(row) => row.ticker}
              emptyTitle={t("universe.empty")}
              columns={[
                {
                  key: "rank",
                  header: t("universe.rank"),
                  align: "right",
                  render: (row) => <span className="num">{row.rank}</span>,
                },
                {
                  key: "ticker",
                  header: t("columns.opportunity"),
                  render: (row) => <Link className="num" to={`/cases/${row.ticker}`}>{row.ticker}</Link>,
                },
                ...HORIZON_ORDER.map((horizon) => ({
                  key: horizon,
                  header: label("horizon", horizon),
                  render: (row: { ticker: string; recommendation: Recommendation | null; readiness: DecisionReadiness | null }) => {
                    const decision = row.recommendation?.horizon_decisions[horizon];
                    const prediction = row.recommendation?.horizon_predictions[horizon];
                    return (
                      <Badge variant={decision?.action === "buy_candidate" ? "positive" : decision?.action === "avoid" ? "negative" : decision?.action === "watch" ? "warning" : "neutral"}>
                        {label("decision", decision?.action ?? "abstain")}
                        {prediction ? ` ${formatSignedPercent(prediction.expected_return)}` : ""}
                      </Badge>
                    );
                  },
                })),
                {
                  key: "coverage",
                  header: t("universe.coverage"),
                  render: (row) => <span className="num">{row.readiness ? `${row.readiness.ready_horizons.length}/3` : "0/3"}</span>,
                },
                {
                  key: "blocker",
                  header: t("universe.blocker"),
                  render: (row) => row.readiness?.blockers[0] ?? t("universe.none"),
                },
              ]}
            />
          </Card>
        )}
      </Section>
    </Section>
  );
}

function CasePreview({
  recommendation,
  companyName,
  catalysts,
}: {
  recommendation: Recommendation;
  companyName: string | undefined;
  catalysts: CorporateEvent[];
}) {
  const { t } = useTranslation("investmentCases");
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
                  <div className={styles.horizonCardStats}>
                    <span
                      className="num"
                      style={{ color: prediction.expected_return >= 0 ? "var(--positive)" : "var(--negative)" }}
                    >
                      {formatSignedPercent(prediction.expected_return)}
                    </span>
                    <span className={styles.horizonCardStatLabel}>{t("detail.expReturnShort")}</span>
                  </div>
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
        <div className={styles.blockTitle}>{t("detail.supportingEvidence")}</div>
        {explanation.supporting_evidence.length === 0 ? (
          <span className={styles.blockText}>{tCommon("states.noneRecorded")}</span>
        ) : (
          <ul className={styles.bulletList}>
            {dedupeEvidence(explanation.supporting_evidence).slice(0, 4).map((e, i) => (
              <li key={i}>{humanizeEvidence(e)}</li>
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
            {catalysts.slice(0, 3).map((c, i) => (
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

      <Link className={styles.workspaceLink} to={`/cases/${recommendation.ticker}`}>
        {t("detail.openCase")} <span className="icon-forward" aria-hidden="true">→</span>
      </Link>
    </div>
  );
}
