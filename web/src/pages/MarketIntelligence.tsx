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
      <Section title="ملخص السوق" description="نطاق الأسهم وجلسة التداول في آخر دورة بحث.">
        {!marketState.data ? (
          <EmptyState title="لا توجد حالة سوق بعد" detail="تظهر بعد تشغيل أول دورة بحث." />
        ) : (
          <div className={styles.grid}>
            <StatTile label="حتى تاريخ" value={formatDate(marketState.data.as_of)} />
            <StatTile
              label="جلسة التداول"
              value={marketState.data.trading_session.is_trading_day ? "مفتوحة" : "مغلقة"}
              caption={marketState.data.trading_session.holiday_name ?? undefined}
            />
            <StatTile label="الأسهم" value={Object.keys(constituents).length} />
            <StatTile label="القطاعات" value={bySector.size} />
          </div>
        )}
      </Section>

      <div className={styles.twoCol}>
        <Card title="توزيع القطاعات" subtitle="الأسهم المغطاة ذات القطاعات المعروفة">
          {bySector.size === 0 ? (
            <EmptyState title="لا توجد بيانات قطاعات بعد" />
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

        <Card title="لوحة الاقتصاد الكلي" subtitle="أحدث مشاهدة لكل سلسلة متابعة">
          {latestMacro.length === 0 ? (
            <EmptyState title="لا توجد بيانات اقتصاد كلي بعد" />
          ) : (
            <div className={styles.grid}>
              {latestMacro.map(({ seriesId, observation }) => (
                <StatTile
                  key={seriesId}
                  label={titleCase(seriesId)}
                  value={observation ? formatNumber(observation.value, 2) : "—"}
                  caption={observation ? formatDate(observation.observation_date) : "لا توجد مشاهدات"}
                />
              ))}
            </div>
          )}
        </Card>
      </div>

      <div className={styles.twoCol}>
        <Card title="الأرباح والإجراءات والإفصاحات القادمة" subtitle="الأحداث المجدولة عبر نطاق الأسهم المغطى">
          {upcoming.length === 0 ? (
            <EmptyState title="لا توجد أحداث مجدولة" detail="لا توجد أحداث مؤسسية قادمة معروفة لنطاق الأسهم المغطى." />
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

        <Card title="الإجراءات المؤسسية الأخيرة" subtitle="الأحداث المؤسسية السابقة عبر نطاق الأسهم المغطى">
          {past.length === 0 ? (
            <EmptyState title="لا توجد إجراءات مؤسسية مسجلة" />
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
        <Card title="اتساع السوق والسيولة">
          <EmptyState
            title="غير متاح بعد"
            detail="يتطلب اتساع السوق والسيولة ملفًا محسوبًا خلفيًا للأسهم الصاعدة والهابطة والحجم المعدل؛ لا تحسب الواجهة هذه القيم من الأسعار الخام."
          />
        </Card>

        <Card title="نظام السوق والمقارنة التاريخية">
          <EmptyState
            title="غير متاح بعد"
            detail="لا يوجد حتى الآن تصنيف لنظام السوق أو ملف مقارنة تاريخية من محرك البحث؛ سيظهر القسم عند إنتاجه."
          />
        </Card>
      </div>
    </>
  );
}
