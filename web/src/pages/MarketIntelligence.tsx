import { Card } from "../components/primitives/Card";
import { Section } from "../components/primitives/Section";
import { StatTile } from "../components/primitives/StatTile";
import { EmptyState, ErrorState, LoadingState } from "../components/primitives/States";
import { useArtifact } from "../hooks/useArtifact";
import { formatDate, formatNumber, titleCase } from "../lib/format";
import type { CorporateEvent, MacroObservation } from "../types";
import styles from "./MarketIntelligence.module.css";

/** Market-wide context: universe composition, sector breakdown, the latest
 * macro observations AGX tracks, and corporate actions across every
 * covered ticker. Breadth/liquidity/regime need a backend-computed
 * artifact this platform doesn't produce yet -- shown as honest gaps
 * rather than a frontend-side calculation from raw price bars, which
 * CLAUDE.md's own return-adjustment rule forbids doing outside `data/`. */
export function MarketIntelligence() {
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
      <Section title="Market Summary" description="Universe and trading session snapshot as of the last research cycle.">
        {!marketState.data ? (
          <EmptyState title="No market state yet" detail="Available once the first research cycle runs." />
        ) : (
          <div className={styles.grid}>
            <StatTile label="As Of" value={formatDate(marketState.data.as_of)} />
            <StatTile
              label="Trading Session"
              value={marketState.data.trading_session.is_trading_day ? "Open" : "Closed"}
              caption={marketState.data.trading_session.holiday_name ?? undefined}
            />
            <StatTile label="Constituents" value={Object.keys(constituents).length} />
            <StatTile label="Sectors" value={bySector.size} />
          </div>
        )}
      </Section>

      <div className={styles.twoCol}>
        <Card title="Sector Composition" subtitle="Covered constituents with known sectors">
          {bySector.size === 0 ? (
            <EmptyState title="No sector data yet" />
          ) : (
            <div>
              {[...bySector.entries()].map(([sector, tickers]) => (
                <div key={sector} className={styles.sectorRow}>
                  <span className={styles.sectorName}>{sector}</span>
                  <span className={styles.sectorTickers}>{tickers.join(", ")}</span>
                </div>
              ))}
            </div>
          )}
        </Card>

        <Card title="Macro Dashboard" subtitle="Latest observation per tracked macro series">
          {latestMacro.length === 0 ? (
            <EmptyState title="No macro data yet" />
          ) : (
            <div className={styles.grid}>
              {latestMacro.map(({ seriesId, observation }) => (
                <StatTile
                  key={seriesId}
                  label={titleCase(seriesId)}
                  value={observation ? formatNumber(observation.value, 2) : "—"}
                  caption={observation ? formatDate(observation.observation_date) : "No observations"}
                />
              ))}
            </div>
          )}
        </Card>
      </div>

      <div className={styles.twoCol}>
        <Card title="Upcoming Earnings, Corporate Actions & Disclosures" subtitle="Scheduled events across the covered universe">
          {upcoming.length === 0 ? (
            <EmptyState title="No scheduled events" detail="No known corporate events are upcoming for the covered universe." />
          ) : (
            <div className={styles.list}>
              {upcoming.map((e, i) => (
                <div key={i} className={styles.listItem}>
                  <div className={styles.listItemHead}>
                    <span className={styles.listItemTitle}>{e.ticker} — {titleCase(e.event_type)}</span>
                    <span className={styles.listItemMeta}>{formatDate(e.event_date)}</span>
                  </div>
                  <span className={styles.listItemDetail}>{e.description}</span>
                </div>
              ))}
            </div>
          )}
        </Card>

        <Card title="Recent Corporate Actions" subtitle="Past corporate events across the covered universe">
          {past.length === 0 ? (
            <EmptyState title="No corporate actions recorded" />
          ) : (
            <div className={styles.list}>
              {past.map((e, i) => (
                <div key={i} className={styles.listItem}>
                  <div className={styles.listItemHead}>
                    <span className={styles.listItemTitle}>{e.ticker} — {titleCase(e.event_type)}</span>
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
        <Card title="Market Breadth & Liquidity">
          <EmptyState
            title="Not yet available"
            detail="Breadth and liquidity require a backend-computed artifact (advancers/decliners, adjusted volume) this platform doesn't export yet -- the frontend never computes returns from raw price bars directly, per the platform's data.adjustments rule."
          />
        </Card>

        <Card title="Market Regime & Historical Comparison">
          <EmptyState
            title="Not yet available"
            detail="No market regime classification or historical-comparison artifact exists upstream yet. This section will populate once the research engine produces one."
          />
        </Card>
      </div>
    </>
  );
}
