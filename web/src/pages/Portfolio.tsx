import { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { Badge, type BadgeVariant } from "../components/primitives/Badge";
import { Card } from "../components/primitives/Card";
import { DataTable } from "../components/primitives/DataTable";
import { Disclaimer } from "../components/primitives/Disclaimer";
import { Section } from "../components/primitives/Section";
import { StatTile } from "../components/primitives/StatTile";
import { EmptyState, ErrorState, LoadingState } from "../components/primitives/States";
import { dataProvider } from "../data/factory";
import { LiveDecisionsUnavailableError } from "../data/DataProvider";
import { useArtifact } from "../hooks/useArtifact";
import { useFormatters } from "../hooks/useFormatters";
import { usePortfolioPositions, type HeldPosition } from "../hooks/usePortfolioPositions";
import { formatPercent, titleCase } from "../lib/format";
import type { PositionAwareDecision } from "../types";
import styles from "./Portfolio.module.css";

const ACTION_VARIANT: Record<string, BadgeVariant> = {
  buy: "positive",
  increase_position: "positive",
  hold: "neutral",
  reduce_position: "warning",
  exit: "negative",
  no_action: "default",
};

function emptyRow(): HeldPosition {
  return { ticker: "", currentWeight: 0, averageCost: null };
}

/** Portfolio -- "is my capital allocated correctly?" Owns two things no
 * other screen does: editing the investor's own holdings, and the full,
 * position-aware six-way decision table those holdings produce (real,
 * on-demand `decision_service.DecisionService` calls -- see CLAUDE.md).
 * The summary numbers here are computed client-side from that same real
 * response (plus already-loaded market_state.sectors), never a second,
 * parallel autonomous computation. */
export function Portfolio() {
  const { t } = useTranslation("portfolio");
  const { t: tCommon } = useTranslation("common");
  const { formatDate } = useFormatters();
  const marketState = useArtifact((p) => p.getMarketState());
  const { positions: savedPositions, setPositions: savePositions, toPositionInputs } = usePortfolioPositions();

  const [rows, setRows] = useState<HeldPosition[]>(savedPositions.length > 0 ? savedPositions : [emptyRow()]);
  const [decisions, setDecisions] = useState<PositionAwareDecision[] | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<Error | null>(null);
  const [selectedTicker, setSelectedTicker] = useState<string | null>(null);

  const defaultDate = marketState.data?.as_of ?? new Date().toISOString().slice(0, 10);

  async function runDecide(nextRows: HeldPosition[]) {
    savePositions(nextRows);
    setLoading(true);
    setError(null);
    try {
      const positions = toPositionInputsFor(nextRows);
      const result = await dataProvider.postDecisions({ date: defaultDate, positions });
      setDecisions(result);
      setSelectedTicker(result[0]?.ticker ?? null);
    } catch (err) {
      setError(err instanceof Error ? err : new Error(String(err)));
    } finally {
      setLoading(false);
    }
  }

  function toPositionInputsFor(nextRows: HeldPosition[]) {
    const result: Record<string, { held: boolean; current_weight: number; average_cost: number | null }> = {};
    for (const row of nextRows) {
      const ticker = row.ticker.trim().toUpperCase();
      if (!ticker) continue;
      result[ticker] = { held: true, current_weight: row.currentWeight, average_cost: row.averageCost };
    }
    return result;
  }

  // Auto-fetch on first load if holdings were already saved from a prior visit.
  useEffect(() => {
    if (savedPositions.length > 0) {
      runDecide(savedPositions);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const selected = decisions?.find((d) => d.ticker === selectedTicker) ?? decisions?.[0] ?? null;
  const unavailable = error instanceof LiveDecisionsUnavailableError;

  const summary = useMemo(() => {
    if (!decisions || decisions.length === 0) return null;
    const held = decisions.filter((d) => d.target_weight > 0);
    const invested = held.reduce((sum, d) => sum + d.target_weight, 0);
    const cash = Math.max(0, 1 - invested);
    const herfindahl = held.reduce((sum, d) => sum + d.target_weight ** 2, 0);
    const sorted = [...held].sort((a, b) => b.target_weight - a.target_weight);
    const sectors = marketState.data?.sectors ?? {};
    const bySector = new Map<string, number>();
    for (const d of held) {
      const sector = sectors[d.ticker] ?? tCommon("table.noSector", { defaultValue: "Unclassified" });
      bySector.set(sector, (bySector.get(sector) ?? 0) + d.target_weight);
    }
    return {
      invested,
      cash,
      herfindahl,
      concentrated: herfindahl > 0.25,
      topPosition: sorted[0] ?? null,
      positionCount: held.length,
      sectors: [...bySector.entries()].sort((a, b) => b[1] - a[1]),
    };
  }, [decisions, marketState.data, tCommon]);

  return (
    <Section title={t("title")} description={t("description")}>
      <Disclaimer />

      <Card title={t("positions.title")} subtitle={t("positions.subtitle")}>
        <div className={styles.positionsTable}>
          <div className={styles.positionsHeader}>
            <span>{t("positions.ticker")}</span>
            <span>{t("positions.currentWeight")}</span>
            <span>{t("positions.averageCost")}</span>
            <span />
          </div>
          {rows.map((row, index) => (
            <div className={styles.positionsRow} key={index}>
              <input
                className={styles.input}
                value={row.ticker}
                placeholder={t("positions.tickerPlaceholder")}
                onChange={(e) => {
                  const next = [...rows];
                  next[index] = { ...row, ticker: e.target.value };
                  setRows(next);
                }}
              />
              <input
                className={styles.input}
                value={row.currentWeight || ""}
                placeholder="0.05"
                inputMode="decimal"
                onChange={(e) => {
                  const next = [...rows];
                  next[index] = { ...row, currentWeight: Number(e.target.value) || 0 };
                  setRows(next);
                }}
              />
              <input
                className={styles.input}
                value={row.averageCost ?? ""}
                placeholder={t("positions.optional")}
                inputMode="decimal"
                onChange={(e) => {
                  const next = [...rows];
                  const value = e.target.value;
                  next[index] = { ...row, averageCost: value === "" ? null : Number(value) };
                  setRows(next);
                }}
              />
              <button
                type="button"
                className={styles.removeButton}
                onClick={() => setRows(rows.filter((_, i) => i !== index))}
                aria-label={t("positions.remove")}
              >
                ×
              </button>
            </div>
          ))}
        </div>
        <div className={styles.actionsRow}>
          <button type="button" className={styles.secondaryButton} onClick={() => setRows([...rows, emptyRow()])}>
            {t("positions.addRow")}
          </button>
          <button type="button" className={styles.primaryButton} disabled={loading} onClick={() => runDecide(rows)}>
            {t("positions.getMyDecisions")}
          </button>
          <button type="button" className={styles.secondaryButton} disabled={loading} onClick={() => runDecide([])}>
            {t("positions.getFlatRead")}
          </button>
        </div>
      </Card>

      {loading && <LoadingState rows={4} />}

      {!loading && unavailable && <EmptyState title={t("unavailable.title")} detail={error?.message} icon="⛔" />}

      {!loading && error && !unavailable && (
        <ErrorState detail={error.message} onRetry={() => runDecide(rows)} />
      )}

      {!loading && !error && summary && (
        <Section title={t("summary.title")} description={t("summary.description")}>
          <div className={styles.statGrid}>
            <StatTile label={t("summary.cash")} value={formatPercent(summary.cash)} />
            <StatTile label={t("summary.invested")} value={formatPercent(summary.invested)} />
            <StatTile label={t("summary.positions")} value={summary.positionCount} />
            <StatTile
              label={t("summary.concentration")}
              value={summary.concentrated ? t("summary.concentrated") : t("summary.diversified")}
            />
            <StatTile
              label={t("summary.topPosition")}
              value={summary.topPosition ? `${summary.topPosition.ticker} (${formatPercent(summary.topPosition.target_weight)})` : "—"}
            />
          </div>
          {summary.sectors.length > 0 && (
            <div className={styles.sectorList}>
              {summary.sectors.map(([sector, weight]) => (
                <div key={sector} className={styles.sectorRow}>
                  <span className={styles.sectorName}>{sector}</span>
                  <span className="num">{formatPercent(weight)}</span>
                </div>
              ))}
            </div>
          )}
        </Section>
      )}

      {!loading && !error && decisions !== null && (
        <div className={styles.layout}>
          <Card title={t("results.title")} dense>
            <DataTable
              columns={[
                { key: "ticker", header: t("results.ticker"), render: (d: PositionAwareDecision) => d.ticker },
                {
                  key: "action",
                  header: t("results.action"),
                  render: (d: PositionAwareDecision) => (
                    <Badge variant={ACTION_VARIANT[d.action] ?? "default"}>{titleCase(d.action)}</Badge>
                  ),
                },
                {
                  key: "target",
                  header: t("results.targetWeight"),
                  align: "right",
                  render: (d: PositionAwareDecision) => formatPercent(d.target_weight),
                },
                {
                  key: "current",
                  header: t("results.currentWeight"),
                  align: "right",
                  render: (d: PositionAwareDecision) => formatPercent(d.current_weight),
                },
                {
                  key: "confidence",
                  header: t("results.confidence"),
                  align: "right",
                  render: (d: PositionAwareDecision) => formatPercent(d.confidence),
                },
                {
                  key: "review",
                  header: t("results.reviewDate"),
                  render: (d: PositionAwareDecision) => (d.expected_review_date ? formatDate(d.expected_review_date) : "—"),
                },
              ]}
              rows={decisions}
              getRowKey={(d) => d.ticker}
              onRowClick={(d) => setSelectedTicker(d.ticker)}
              emptyTitle={t("results.emptyTitle")}
              emptyDetail={t("results.emptyDetail")}
            />
          </Card>

          <Card title={selected ? t("detail.title", { ticker: selected.ticker }) : t("detail.select")} dense>
            {!selected && <EmptyState title={t("detail.select")} />}
            {selected && (
              <>
                <div className={styles.detailHeader}>
                  <Badge variant={ACTION_VARIANT[selected.action] ?? "default"}>{titleCase(selected.action)}</Badge>
                  {selected.abstained && <Badge variant="warning">{t("detail.abstained")}</Badge>}
                </div>

                <p className={styles.blockText}>{selected.investment_thesis}</p>

                <div className={styles.block}>
                  <div className={styles.blockTitle}>{t("detail.keyRisks")}</div>
                  {selected.key_risks.length === 0 ? (
                    <span className={styles.blockText}>{t("detail.none")}</span>
                  ) : (
                    <ul className={styles.bulletList}>
                      {selected.key_risks.map((r, i) => (
                        <li key={i}>{r}</li>
                      ))}
                    </ul>
                  )}
                </div>

                <div className={styles.block}>
                  <div className={styles.blockTitle}>{t("detail.contradictingEvidence")}</div>
                  {selected.contradicting_evidence.length === 0 ? (
                    <span className={styles.blockText}>{t("detail.none")}</span>
                  ) : (
                    <ul className={styles.bulletList}>
                      {selected.contradicting_evidence.map((r, i) => (
                        <li key={i}>{r}</li>
                      ))}
                    </ul>
                  )}
                </div>

                <div className={styles.block}>
                  <div className={styles.blockTitle}>{t("detail.activeCatalysts")}</div>
                  {selected.active_catalysts.length === 0 ? (
                    <span className={styles.blockText}>{t("detail.none")}</span>
                  ) : (
                    <ul className={styles.bulletList}>
                      {selected.active_catalysts.map((r, i) => (
                        <li key={i}>{r}</li>
                      ))}
                    </ul>
                  )}
                </div>

                <div className={styles.block}>
                  <div className={styles.blockTitle}>{t("detail.monitoringEvents")}</div>
                  {selected.monitoring_events.length === 0 ? (
                    <span className={styles.blockText}>{t("detail.none")}</span>
                  ) : (
                    <ul className={styles.bulletList}>
                      {selected.monitoring_events.map((r, i) => (
                        <li key={i}>{r}</li>
                      ))}
                    </ul>
                  )}
                </div>

                <div className={styles.block}>
                  <div className={styles.blockTitle}>{t("detail.invalidationConditions")}</div>
                  {selected.explanation.invalidation_conditions.length === 0 ? (
                    <span className={styles.blockText}>{t("detail.none")}</span>
                  ) : (
                    <ul className={styles.bulletList}>
                      {selected.explanation.invalidation_conditions.map((r, i) => (
                        <li key={i}>{r}</li>
                      ))}
                    </ul>
                  )}
                </div>

                <div className={styles.block}>
                  <div className={styles.blockTitle}>{t("detail.supportingEvidence")}</div>
                  {selected.explanation.supporting_evidence.length === 0 ? (
                    <span className={styles.blockText}>{t("detail.none")}</span>
                  ) : (
                    <ul className={styles.bulletList}>
                      {selected.explanation.supporting_evidence.map((r, i) => (
                        <li key={i}>{r}</li>
                      ))}
                    </ul>
                  )}
                </div>

                <Link className={styles.caseLink} to={`/cases/${selected.ticker}`}>
                  {t("detail.viewCase")} →
                </Link>
              </>
            )}
          </Card>
        </div>
      )}
    </Section>
  );
}
