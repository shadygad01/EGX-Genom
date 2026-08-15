import { useTranslation } from "react-i18next";
import { Card } from "../components/primitives/Card";
import { Section } from "../components/primitives/Section";
import { StatTile } from "../components/primitives/StatTile";
import { EmptyState, ErrorState, LoadingState } from "../components/primitives/States";
import { useArtifact } from "../hooks/useArtifact";
import { useEnumLabel } from "../hooks/useEnumLabel";
import { useFormatters } from "../hooks/useFormatters";
import { formatNumber, formatPercent, formatSignedPercent, titleCase } from "../lib/format";
import type { CorporateEvent, MacroObservation } from "../types";
import styles from "./MarketIntelligence.module.css";

/** Market-wide context: universe composition, sector breakdown, the latest
 * macro observations AGX tracks, corporate actions across every covered
 * ticker, market breadth/liquidity (advance/decline, volume breadth --
 * `market_breadth.json`), and market regime (trend/volatility --
 * `market_regime.json`) -- both computed entirely in `market_memory`
 * through the platform's own return-adjustment rule, never here. */
export function MarketIntelligence() {
  const { t } = useTranslation("marketIntelligence");
  const label = useEnumLabel();
  const { formatDate } = useFormatters();
  const marketState = useArtifact((p) => p.getMarketState());
  const breadth = useArtifact((p) => p.getMarketBreadth());
  const regime = useArtifact((p) => p.getMarketRegime());
  const investmentCases = useArtifact((p) => p.getInvestmentCases());

  const sectors = marketState.data?.sectors ?? {};
  const constituents = marketState.data?.constituents ?? {};
  const universeTickers = Object.keys(constituents).sort();
  const classifiedTickers = new Set(Object.keys(sectors));
  const unclassifiedTickers = universeTickers.filter((ticker) => !classifiedTickers.has(ticker));
  const bySector = new Map<string, string[]>();
  for (const ticker of universeTickers) {
    const sector = sectors[ticker];
    if (sector) bySector.set(sector, [...(bySector.get(sector) ?? []), ticker]);
  }
  const marketAsOf = marketState.data?.as_of ?? null;
  const snapshotAgeDays = marketAsOf
    ? Math.max(0, Math.floor((Date.now() - new Date(`${marketAsOf}T00:00:00Z`).getTime()) / 86_400_000))
    : null;
  const freshnessEligible = snapshotAgeDays !== null && snapshotAgeDays <= 1;

  const latestMacro: { seriesId: string; observation: MacroObservation | null }[] = Object.entries(
    marketState.data?.dataset_snapshot.macro_series ?? {},
  ).map(([seriesId, observations]) => ({
    seriesId,
    observation: [...observations].sort((a, b) => (a.observation_date > b.observation_date ? -1 : 1))[0] ?? null,
  }));

  const asOf = marketState.data?.as_of ?? null;
  const allCorporateEvents: (CorporateEvent & { ticker: string })[] = Object.entries(
    marketState.data?.dataset_snapshot.corporate_events ?? {},
  ).flatMap(([ticker, events]) => events.map((e) => ({ ...e, ticker })));

  const upcoming = allCorporateEvents
    .filter((e) => (asOf ? e.event_date >= asOf : true))
    .sort((a, b) => (a.event_date > b.event_date ? 1 : -1))
    .slice(0, 10);
  const past = allCorporateEvents
    .filter((e) => (asOf ? e.event_date < asOf : false))
    .sort((a, b) => (a.event_date > b.event_date ? -1 : 1))
    .slice(0, 10);

  if (marketState.loading) return <LoadingState rows={4} />;
  if (marketState.error) return <ErrorState detail={marketState.error.message} onRetry={marketState.reload} />;

  return (
    <>
      <Section title={t("marketSummary.title")} description={t("marketSummary.description")}>
        {!marketState.data ? (
          <EmptyState title={t("marketSummary.emptyTitle")} detail={t("marketSummary.emptyDetail")} />
        ) : (
          <div className={styles.grid}>
            <StatTile label={t("marketSummary.asOf")} value={formatDate(marketState.data.as_of)} />
            <StatTile
              label={t("marketSummary.tradingSession")}
              value={marketState.data.trading_session.is_trading_day ? t("marketSummary.open") : t("marketSummary.closed")}
              caption={marketState.data.trading_session.holiday_name ?? undefined}
            />
            <StatTile label={t("marketSummary.constituents")} value={Object.keys(constituents).length} />
            <StatTile label={t("marketSummary.sectors")} value={bySector.size} />
          </div>
        )}
      </Section>

      {marketState.data && (
        <Card title={t("dataFreshness.title")} subtitle={t("dataFreshness.subtitle")}>
          <div className={styles.grid}>
            <StatTile label={t("dataFreshness.snapshotDate")} value={formatDate(marketState.data.as_of)} />
            <StatTile
              label={t("dataFreshness.age")}
              value={snapshotAgeDays === null ? "—" : t("dataFreshness.days", { count: snapshotAgeDays })}
            />
            <StatTile
              label={t("dataFreshness.status")}
              value={t(freshnessEligible ? "dataFreshness.researchOnly" : "dataFreshness.blocked")}
            />
          </div>
          <p className={styles.footnote}>
            {freshnessEligible ? t("dataFreshness.reviewBeforeExecution") : t("dataFreshness.notEligible")}
          </p>
        </Card>
      )}

      <div className={styles.twoCol}>
        <Card title={t("sectorComposition.title")} subtitle={t("sectorComposition.subtitle")}>
          {bySector.size === 0 ? (
            <EmptyState title={t("sectorComposition.emptyTitle")} />
          ) : (
            <div>
              {[...bySector.entries()].sort(([a], [b]) => a.localeCompare(b)).map(([sector, tickers]) => (
                <div key={sector} className={styles.sectorRow}>
                  <span className={styles.sectorName}>{sector}</span>
                  <span className={`${styles.sectorTickers} num`}>{tickers.join(", ")}</span>
                </div>
              ))}
              {unclassifiedTickers.length > 0 && (
                <div className={styles.sectorRow}>
                  <span className={styles.sectorName}>{t("sectorComposition.unclassified")}</span>
                  <span className={`${styles.sectorTickers} num`}>{unclassifiedTickers.join(", ")}</span>
                </div>
              )}
              <p className={styles.footnote}>
                {t("sectorComposition.coverage", {
                  classified: classifiedTickers.size,
                  universe: universeTickers.length,
                  unclassified: unclassifiedTickers.length,
                })}
              </p>
            </div>
          )}
        </Card>

        <Card title={t("macroDashboard.title")} subtitle={t("macroDashboard.subtitle")}>
          {latestMacro.length === 0 ? (
            <EmptyState title={t("macroDashboard.emptyTitle")} />
          ) : (
            <div className={styles.grid}>
              {latestMacro.map(({ seriesId, observation }) => (
                <StatTile
                  key={seriesId}
                  label={titleCase(seriesId)}
                  value={observation ? formatNumber(observation.value, 2) : "—"}
                  caption={observation ? formatDate(observation.observation_date) : t("macroDashboard.noObservations")}
                />
              ))}
            </div>
          )}
        </Card>
      </div>

      <div className={styles.twoCol}>
        <Card title={t("macroDecision.title")} subtitle={t("macroDecision.subtitle")}>
          {!investmentCases.data?.macro_overlay ? (
            <EmptyState title={t("macroDecision.empty")} />
          ) : (
            <div>
              <div className={styles.grid}>
                <StatTile label={t("macroDecision.decision")} value={t(`macroDecision.states.${investmentCases.data.macro_overlay.decision}`)} />
                <StatTile label={t("macroDecision.score")} value={formatSignedPercent(investmentCases.data.macro_overlay.score)} />
                <StatTile label={t("macroDecision.exposure")} value={formatPercent(investmentCases.data.macro_overlay.exposure_multiplier)} />
                <StatTile label={t("macroDecision.coverage")} value={formatPercent(investmentCases.data.macro_overlay.available_weight)} />
              </div>
              <div className={styles.list}>
                {investmentCases.data.macro_overlay.contributions.map((row) => (
                  <div className={styles.listItem} key={row.factor}>
                    <div className={styles.listItemHead}>
                      <span className={styles.listItemTitle}>{titleCase(row.factor)}</span>
                      <span className={styles.listItemMeta}>{formatPercent(row.effective_weight)}</span>
                    </div>
                    <span className={styles.listItemDetail}>
                      {t(`macroDecision.impacts.${row.impact}`)} · {formatSignedPercent(row.change_pct)} · {titleCase(row.series_id)}
                    </span>
                  </div>
                ))}
              </div>
            </div>
          )}
        </Card>

        <Card title={t("upcomingEvents.title")} subtitle={t("upcomingEvents.subtitle")}>
          {upcoming.length === 0 ? (
            <EmptyState title={t("upcomingEvents.emptyTitle")} detail={t("upcomingEvents.emptyDetail")} />
          ) : (
            <div className={styles.list}>
              {upcoming.map((e, i) => (
                <div key={i} className={styles.listItem}>
                  <div className={styles.listItemHead}>
                    <span className={styles.listItemTitle}><span className="num">{e.ticker}</span> — {label("corporateEventType", e.event_type)}</span>
                    <span className={styles.listItemMeta}>{formatDate(e.event_date)}</span>
                  </div>
                  <span className={styles.listItemDetail}>{e.description}</span>
                </div>
              ))}
            </div>
          )}
        </Card>

        <Card title={t("recentActions.title")} subtitle={t("recentActions.subtitle")}>
          {past.length === 0 ? (
            <EmptyState title={t("recentActions.emptyTitle")} />
          ) : (
            <div className={styles.list}>
              {past.map((e, i) => (
                <div key={i} className={styles.listItem}>
                  <div className={styles.listItemHead}>
                    <span className={styles.listItemTitle}><span className="num">{e.ticker}</span> — {label("corporateEventType", e.event_type)}</span>
                    <span className={styles.listItemMeta}>{formatDate(e.event_date)}</span>
                  </div>
                  <span className={styles.listItemDetail}>{e.description}</span>
                </div>
              ))}
            </div>
          )}
        </Card>
      </div>

      <div className={styles.twoCol}>
        <Card title={t("breadthLiquidity.title")} subtitle={t("breadthLiquidity.subtitle")}>
          {breadth.loading && <LoadingState rows={2} />}
          {breadth.error && <ErrorState detail={breadth.error.message} onRetry={breadth.reload} />}
          {!breadth.loading && !breadth.error && !breadth.data && (
            <EmptyState title={t("breadthLiquidity.emptyTitle")} detail={t("breadthLiquidity.emptyDetail")} />
          )}
          {breadth.data && (
            <>
              <div className={styles.grid}>
                <StatTile label={t("breadthLiquidity.advancers")} value={formatNumber(breadth.data.advancers)} />
                <StatTile label={t("breadthLiquidity.decliners")} value={formatNumber(breadth.data.decliners)} />
                <StatTile label={t("breadthLiquidity.unchanged")} value={formatNumber(breadth.data.unchanged)} />
                <StatTile
                  label={t("breadthLiquidity.advanceDeclineRatio")}
                  value={breadth.data.advance_decline_ratio == null ? "—" : formatNumber(breadth.data.advance_decline_ratio, 2)}
                />
                <StatTile
                  label={t("breadthLiquidity.averageReturn")}
                  value={formatSignedPercent((breadth.data.average_daily_return_pct ?? 0) / 100)}
                />
                <StatTile label={t("breadthLiquidity.aboveAverageVolume")} value={formatNumber(breadth.data.tickers_above_average_volume)} />
                <StatTile label={t("breadthLiquidity.belowAverageVolume")} value={formatNumber(breadth.data.tickers_below_average_volume)} />
              </div>
              <p className={styles.footnote}>
                {t("breadthLiquidity.coverage", {
                  withData: breadth.data.tickers_with_price_data,
                  universe: breadth.data.universe_count,
                })}
              </p>
            </>
          )}
        </Card>

        <Card title={t("marketRegime.title")} subtitle={t("marketRegime.subtitle")}>
          {regime.loading && <LoadingState rows={2} />}
          {regime.error && <ErrorState detail={regime.error.message} onRetry={regime.reload} />}
          {!regime.loading && !regime.error && !regime.data && (
            <EmptyState title={t("marketRegime.emptyTitle")} detail={t("marketRegime.emptyDetail")} />
          )}
          {regime.data && (
            <>
              <div className={styles.grid}>
                <StatTile label={t("marketRegime.trend")} value={label("marketTrend", regime.data.trend)} />
                <StatTile label={t("marketRegime.volatility")} value={label("volatilityLevel", regime.data.volatility)} />
                <StatTile
                  label={t("marketRegime.cumulativeReturn")}
                  value={
                    regime.data.cumulative_return_pct == null
                      ? "—"
                      : formatSignedPercent(regime.data.cumulative_return_pct / 100)
                  }
                />
                <StatTile
                  label={t("marketRegime.volatilityPct")}
                  value={regime.data.daily_volatility_pct == null ? "—" : formatSignedPercent(regime.data.daily_volatility_pct / 100)}
                />
              </div>
              <p className={styles.footnote}>
                {t("marketRegime.coverage", {
                  days: regime.data.trading_days_observed,
                  tickers: regime.data.tickers_with_sufficient_data,
                })}
              </p>
              {regime.data.reasons.length > 0 && (
                <ul className={styles.compactList}>
                  {regime.data.reasons.map((r, i) => (
                    <li key={i}>{r}</li>
                  ))}
                </ul>
              )}
            </>
          )}
        </Card>
      </div>
    </>
  );
}
