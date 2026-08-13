import { useEffect, useState } from "react";
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
import type { CorporateEvent, DecisionReadiness, Horizon, MarketState, Recommendation, ResearchCandidate } from "../types";
import styles from "./InvestmentCases.module.css";

const HORIZON_ORDER: Horizon[] = ["micro", "swing", "investment"];
const SIX_MONTH_LOOKBACK_DAYS = 183;

function priceProximity(ticker: string, marketState: MarketState | null | undefined) {
  const history = marketState?.dataset_snapshot?.long_price_history?.[ticker] ?? marketState?.dataset_snapshot?.price_history?.[ticker] ?? [];
  const asOf = marketState?.as_of ? new Date(marketState.as_of) : new Date();
  const cutoff = new Date(asOf);
  cutoff.setDate(cutoff.getDate() - SIX_MONTH_LOOKBACK_DAYS);
  const window = history.filter((bar: { trade_date: string }) => new Date(bar.trade_date) >= cutoff && new Date(bar.trade_date) <= asOf);
  if (window.length === 0) return null;
  const latest = [...window].sort((a: { trade_date: string }, b: { trade_date: string }) => b.trade_date.localeCompare(a.trade_date))[0];
  const low = Math.min(...window.map((bar: { low: number; close: number }) => bar.low ?? bar.close));
  return { current: latest.close, low, distance: latest.close > 0 ? latest.close / low - 1 : null, observations: window.length };
}

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
  const researchCandidates = useArtifact((p) => p.getResearchCandidates());
  const marketState = useArtifact((p) => p.getMarketState());
  const [selectedTicker, setSelectedTicker] = useState<string | null>(null);
  const [horizonFilter, setHorizonFilter] = useState<Horizon | "all">("all");

  const ranked = [...(recommendations.data ?? [])]
    .filter((r) => horizonFilter === "all" || r.horizon_predictions[horizonFilter] != null)
    .sort((a, b) => {
      const returnA = horizonFilter === "all" ? a.combined_expected_return : (a.horizon_predictions[horizonFilter]?.expected_return ?? -100);
      const returnB = horizonFilter === "all" ? b.combined_expected_return : (b.horizon_predictions[horizonFilter]?.expected_return ?? -100);
      return returnB - returnA;
    });

  const companyNames = marketState.data?.constituents ?? {};
  const marketSnapshot = marketState.data;

  useEffect(() => {
    if (!marketSnapshot || typeof window === "undefined" || typeof Notification === "undefined") return;
    const notify = (ticker: string, companyName: string, distance: number) => {
      if (Notification.permission !== "granted") return;
      const key = `egx-low-alert:${ticker}:${new Date().toISOString().slice(0, 10)}`;
      if (window.localStorage.getItem(key)) return;
      window.localStorage.setItem(key, "1");
      new Notification(`EGX opportunity: ${ticker}`, {
        body: `${companyName || ticker} is ${formatPercent(distance)} above its six-month low.`,
        tag: key,
      });
    };
    const requestPermission = Notification.permission === "default" ? Notification.requestPermission() : Promise.resolve(Notification.permission);
    requestPermission.then((permission) => {
      if (permission !== "granted") return;
      Object.keys(companyNames).forEach((ticker) => {
        const proximity = priceProximity(ticker, marketSnapshot);
        if (proximity?.distance != null && proximity.distance <= 0.08) notify(ticker, companyNames[ticker] ?? "", proximity.distance);
      });
    }).catch(() => undefined);
  }, [marketSnapshot, companyNames]);

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

      <div style={{ display: "flex", gap: "var(--space-2)", marginBottom: "var(--space-3)", alignItems: "center" }}>
        <span style={{ fontSize: "0.85rem", fontWeight: 600, color: "var(--text-muted)" }}>{tCommon("table.horizonFilter") || "Horizon Filter"}:</span>
        <button
          className="btn"
          style={{ padding: "4px 12px", fontSize: "0.8rem", background: horizonFilter === "all" ? "var(--accent)" : "var(--surface-2)", color: horizonFilter === "all" ? "#fff" : "var(--text-main)" }}
          onClick={() => setHorizonFilter("all")}
        >
          All Horizons
        </button>
        {HORIZON_ORDER.map((h) => (
          <button
            key={h}
            className="btn"
            style={{ padding: "4px 12px", fontSize: "0.8rem", background: horizonFilter === h ? "var(--accent)" : "var(--surface-2)", color: horizonFilter === h ? "#fff" : "var(--text-main)" }}
            onClick={() => setHorizonFilter(h)}
          >
            {label("horizon", h)}
          </button>
        ))}
      </div>

      <Section title="Quantitative research candidates" description="Multi-model fair-value candidates ranked by expected return. These are watchlist items until every execution gate passes.">
        {researchCandidates.loading && <LoadingState rows={2} />}
        {!researchCandidates.loading && (
          <Card dense>
            <DataTable<ResearchCandidate>
              rows={researchCandidates.data ?? []}
              getRowKey={(row) => row.ticker}
              emptyTitle="No undervalued candidates"
              emptyDetail="No stock currently has a populated multi-model fair value below its latest price."
              columns={[
                { key: "ticker", header: "Ticker", render: (row) => <Link className="num" to={`/cases/${row.ticker}`}>{row.ticker}</Link> },
                { key: "price", header: "Price / Target", align: "right", render: (row) => <span className="num">{row.current_price.toFixed(2)} / {row.target_price.toFixed(2)}</span> },
                { key: "return", header: "Expected return", align: "right", render: (row) => <span className="num" style={{ color: "var(--positive)", fontWeight: 700 }}>{formatSignedPercent(row.expected_return)}</span> },
                { key: "time", header: "Target horizon", align: "right", render: (row) => <span className="num">{row.time_to_target_days}d</span> },
                { key: "confidence", header: "Evidence completeness", align: "right", render: (row) => <Meter value={row.confidence} label={formatPercent(row.confidence)} /> },
                { key: "status", header: "Decision status", render: (row) => <Badge variant="neutral" title={row.primary_blockers.join(" ")}>WATCHLIST — gated</Badge> },
              ]}
            />
          </Card>
        )}
      </Section>

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
                  key: "price",
                  header: "Price / 6M low",
                  align: "right",
                  render: (r) => {
                    const proximity = priceProximity(r.ticker, marketSnapshot);
                    if (!proximity) return <span className="num">—</span>;
                    return (
                      <div>
                        <span className="num">{proximity.current.toFixed(2)} / {proximity.low.toFixed(2)}</span>
                        <div style={{ fontSize: "0.72rem", color: proximity.distance != null && proximity.distance <= 0.08 ? "var(--warning)" : "var(--text-muted)" }}>
                          {proximity.distance == null ? "—" : `${(proximity.distance * 100).toFixed(1)}% above low`}
                        </div>
                      </div>
                    );
                  },
                },
                {
                  key: "fairValueGap",
                  header: "Fair value gap",
                  align: "right",
                  render: (r) => {
                    const valuation = readinessByTicker.get(r.ticker);
                    const gap = valuation?.price_vs_fair_value_pct;
                    if (gap == null) return <span className="num">—</span>;
                    return <span className="num" style={{ color: gap <= 0 ? "var(--positive)" : "var(--negative)", fontWeight: 700 }}>{formatSignedPercent(-gap)}</span>;
                  },
                },
                {
                  key: "return",
                  header: tCommon("table.expReturn"),
                  align: "right",
                  render: (r) => {
                    const val = horizonFilter === "all" ? r.combined_expected_return : (r.horizon_predictions[horizonFilter]?.expected_return ?? r.combined_expected_return);
                    return (
                      <span className="num" style={{ color: val >= 0 ? "var(--positive)" : "var(--negative)", fontWeight: 700 }}>
                        {formatSignedPercent(val)}
                      </span>
                    );
                  },
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
                  render: (r) => {
                    const readinessVal = readinessByTicker.get(r.ticker)?.valuation;
                    return (
                      <div className={styles.horizonBadges} style={{ gap: "4px", flexWrap: "wrap" }}>
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
                        {readinessVal?.dcf_per_share != null && (
                          <Badge variant="accent" title={`DCF Fair Value: ${readinessVal.dcf_per_share.toFixed(2)} EGP`}>
                            DCF: {readinessVal.dcf_per_share.toFixed(2)}
                          </Badge>
                        )}
                        {readinessVal?.ev_to_ebitda != null && (
                          <Badge variant="neutral" title={`EV/EBITDA: ${readinessVal.ev_to_ebitda.toFixed(1)}x`}>
                            EV/EBITDA: {readinessVal.ev_to_ebitda.toFixed(1)}x
                          </Badge>
                        )}
                        {readinessVal?.price_to_book != null && (
                          <Badge variant="neutral" title={`P/B: ${readinessVal.price_to_book.toFixed(2)}x`}>
                            P/B: {readinessVal.price_to_book.toFixed(2)}x
                          </Badge>
                        )}
                      </div>
                    );
                  },
                },
              ]}
            />
          </Card>

          <Card title={selected ? t("evidenceTitle", { ticker: selected.ticker }) : t("evidence")} dense>
            {!selected && <EmptyState title={t("noOpportunitySelected")} detail={t("selectRowDetail")} />}
            {selected && (
              <CasePreview
                recommendation={selected}
                companyName={companyNames[selected.ticker]}
                catalysts={catalystsForSelected}
                valuation={readinessByTicker.get(selected.ticker)?.valuation}
              />
            )}
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
  valuation,
}: {
  recommendation: Recommendation;
  companyName: string | undefined;
  catalysts: CorporateEvent[];
  valuation?: import("../types").ValuationMetrics | null;
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

      {valuation && (
        <div className={styles.block} style={{ background: "var(--surface-2)", padding: "var(--space-3)", borderRadius: "var(--radius-md)", marginBottom: "var(--space-3)" }}>
          <div className={styles.blockTitle}>Valuation & Quantitative Metrics</div>
          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(110px, 1fr))", gap: "var(--space-2)", marginTop: "var(--space-2)" }}>
            {valuation.weighted_fair_value != null && (
              <div>
                <span style={{ fontSize: "0.75rem", color: "var(--text-muted)", display: "block" }}>Fair Value</span>
                <strong className="num" style={{ fontSize: "0.95rem" }}>{valuation.weighted_fair_value.toFixed(2)} EGP</strong>
              </div>
            )}
            {valuation.dcf_per_share != null && (
              <div>
                <span style={{ fontSize: "0.75rem", color: "var(--text-muted)", display: "block" }}>DCF / Share</span>
                <strong className="num" style={{ fontSize: "0.95rem" }}>{valuation.dcf_per_share.toFixed(2)} EGP</strong>
              </div>
            )}
            {valuation.ev_to_ebitda != null && (
              <div>
                <span style={{ fontSize: "0.75rem", color: "var(--text-muted)", display: "block" }}>EV / EBITDA</span>
                <strong className="num" style={{ fontSize: "0.95rem" }}>{valuation.ev_to_ebitda.toFixed(1)}x</strong>
              </div>
            )}
            {valuation.price_to_book != null && (
              <div>
                <span style={{ fontSize: "0.75rem", color: "var(--text-muted)", display: "block" }}>P / B Ratio</span>
                <strong className="num" style={{ fontSize: "0.95rem" }}>{valuation.price_to_book.toFixed(2)}x</strong>
              </div>
            )}
            {valuation.market_pe != null && (
              <div>
                <span style={{ fontSize: "0.75rem", color: "var(--text-muted)", display: "block" }}>P / E Ratio</span>
                <strong className="num" style={{ fontSize: "0.95rem" }}>{valuation.market_pe.toFixed(1)}x</strong>
              </div>
            )}
          </div>
        </div>
      )}

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
