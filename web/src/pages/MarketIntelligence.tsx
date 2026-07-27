import { useTranslation } from "react-i18next";
import { Card } from "../components/primitives/Card";
import { Section } from "../components/primitives/Section";
import { StatTile } from "../components/primitives/StatTile";
import { EmptyState, ErrorState, LoadingState } from "../components/primitives/States";
import { useArtifact } from "../hooks/useArtifact";
import { useEnumLabel } from "../hooks/useEnumLabel";
import { useFormatters } from "../hooks/useFormatters";
import { formatNumber, titleCase } from "../lib/format";
import type { CorporateEvent, MacroObservation } from "../types";
import styles from "./MarketIntelligence.module.css";

/** Market-wide context: universe composition, sector breakdown, the latest
 * macro observations AGX tracks, and corporate actions across every
 * covered ticker. Breadth/liquidity/regime need a backend-computed
 * artifact this platform doesn't produce yet -- shown as honest gaps
 * rather than a frontend-side calculation from raw price bars, which
 * CLAUDE.md's own return-adjustment rule forbids doing outside `data/`. */
export function MarketIntelligence() {
  const { t } = useTranslation("marketIntelligence");
  const label = useEnumLabel();
  const { formatDate } = useFormatters();
  const marketState = useArtifact((p) => p.getMarketState());

  const sectors = marketState.data?.sectors ?? {};
  const constituents = marketState.data?.constituents ?? {};
  const bySector = new Map<string, string[]>();
  for (const [ticker, sector] of Object.entries(sectors)) {
    bySector.set(sector, [...(bySector.get(sector) ?? []), ticker]);
  }

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

      <div className={styles.twoCol}>
        <Card title={t("sectorComposition.title")} subtitle={t("sectorComposition.subtitle")}>
          {bySector.size === 0 ? (
            <EmptyState title={t("sectorComposition.emptyTitle")} />
          ) : (
            <div>
              {[...bySector.entries()].map(([sector, tickers]) => (
                <div key={sector} className={styles.sectorRow}>
                  <span className={styles.sectorName}>{sector}</span>
                  <span className={`${styles.sectorTickers} num`}>{tickers.join(", ")}</span>
                </div>
              ))}
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
        <Card title={t("breadthLiquidity.title")}>
          <EmptyState title={t("breadthLiquidity.emptyTitle")} detail={t("breadthLiquidity.emptyDetail")} />
        </Card>

        <Card title={t("marketRegime.title")}>
          <EmptyState title={t("marketRegime.emptyTitle")} detail={t("marketRegime.emptyDetail")} />
        </Card>
      </div>
    </>
  );
}
