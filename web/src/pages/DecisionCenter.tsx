import { useState } from "react";
import { useTranslation } from "react-i18next";
import { Badge, type BadgeVariant } from "../components/primitives/Badge";
import { Card } from "../components/primitives/Card";
import { DataTable } from "../components/primitives/DataTable";
import { Disclaimer } from "../components/primitives/Disclaimer";
import { Section } from "../components/primitives/Section";
import { EmptyState, ErrorState, LoadingState } from "../components/primitives/States";
import { dataProvider } from "../data/factory";
import { DecisionCenterUnavailableError } from "../data/DataProvider";
import { useArtifact } from "../hooks/useArtifact";
import { useFormatters } from "../hooks/useFormatters";
import { formatPercent, titleCase } from "../lib/format";
import type { PositionAwareDecision, PositionInput } from "../types";
import styles from "./DecisionCenter.module.css";

const ACTION_VARIANT: Record<string, BadgeVariant> = {
  buy: "positive",
  increase_position: "positive",
  hold: "neutral",
  reduce_position: "warning",
  exit: "negative",
  no_action: "default",
};

interface PositionRow {
  key: string;
  ticker: string;
  currentWeight: string;
  averageCost: string;
}

function emptyRow(): PositionRow {
  return { key: crypto.randomUUID(), ticker: "", currentWeight: "", averageCost: "" };
}

function toPositions(rows: PositionRow[]): Record<string, PositionInput> {
  const positions: Record<string, PositionInput> = {};
  for (const row of rows) {
    const ticker = row.ticker.trim().toUpperCase();
    if (!ticker) continue;
    const weight = Number(row.currentWeight);
    const cost = Number(row.averageCost);
    positions[ticker] = {
      held: true,
      current_weight: Number.isFinite(weight) && row.currentWeight !== "" ? weight : 0,
      average_cost: Number.isFinite(cost) && row.averageCost !== "" ? cost : null,
    };
  }
  return positions;
}

/** The mission's primary output, made queryable: a real, on-demand call to
 * `decision_service.DecisionService` (via POST /decisions) for a six-way
 * Buy/Increase Position/Hold/Reduce Position/Exit/No Action decision per
 * ticker, complete with target weight, thesis, risks, contradicting
 * evidence, catalysts, monitoring status and review date. Deliberately not
 * a static dashboard artifact -- it depends on the investor's own holdings,
 * which this platform never autonomously discovers (see CLAUDE.md's
 * decision_service rules) -- so it only works against a live api/ instance;
 * StaticJsonProvider honestly reports that rather than fabricating a result. */
export function DecisionCenter() {
  const { t } = useTranslation("decisionCenter");
  const { formatDate } = useFormatters();
  const marketState = useArtifact((p) => p.getMarketState());
  const [rows, setRows] = useState<PositionRow[]>([emptyRow()]);
  const [decisions, setDecisions] = useState<PositionAwareDecision[] | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<Error | null>(null);
  const [selectedTicker, setSelectedTicker] = useState<string | null>(null);

  const defaultDate = marketState.data?.as_of ?? new Date().toISOString().slice(0, 10);

  async function runDecide(positions: Record<string, PositionInput>) {
    setLoading(true);
    setError(null);
    try {
      const result = await dataProvider.postDecisions({ date: defaultDate, positions });
      setDecisions(result);
      setSelectedTicker(result[0]?.ticker ?? null);
    } catch (err) {
      setError(err instanceof Error ? err : new Error(String(err)));
    } finally {
      setLoading(false);
    }
  }

  const selected = decisions?.find((d) => d.ticker === selectedTicker) ?? decisions?.[0] ?? null;
  const unavailable = error instanceof DecisionCenterUnavailableError;

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
            <div className={styles.positionsRow} key={row.key}>
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
                value={row.currentWeight}
                placeholder="0.05"
                inputMode="decimal"
                onChange={(e) => {
                  const next = [...rows];
                  next[index] = { ...row, currentWeight: e.target.value };
                  setRows(next);
                }}
              />
              <input
                className={styles.input}
                value={row.averageCost}
                placeholder={t("positions.optional")}
                inputMode="decimal"
                onChange={(e) => {
                  const next = [...rows];
                  next[index] = { ...row, averageCost: e.target.value };
                  setRows(next);
                }}
              />
              <button
                type="button"
                className={styles.removeButton}
                onClick={() => setRows(rows.filter((r) => r.key !== row.key))}
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
          <button
            type="button"
            className={styles.primaryButton}
            disabled={loading}
            onClick={() => runDecide(toPositions(rows))}
          >
            {t("positions.getMyDecisions")}
          </button>
          <button type="button" className={styles.secondaryButton} disabled={loading} onClick={() => runDecide({})}>
            {t("positions.getFlatRead")}
          </button>
        </div>
      </Card>

      {loading && <LoadingState rows={4} />}

      {!loading && unavailable && (
        <EmptyState title={t("unavailable.title")} detail={error?.message} icon="⛔" />
      )}

      {!loading && error && !unavailable && (
        <ErrorState detail={error.message} onRetry={() => runDecide(toPositions(rows))} />
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
              </>
            )}
          </Card>
        </div>
      )}
    </Section>
  );
}
