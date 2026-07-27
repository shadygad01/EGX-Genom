import { useState } from "react";
import { Link } from "react-router-dom";
import { Badge } from "../components/primitives/Badge";
import { Card } from "../components/primitives/Card";
import { DataTable } from "../components/primitives/DataTable";
import { Meter } from "../components/primitives/Meter";
import { Section } from "../components/primitives/Section";
import { StatTile } from "../components/primitives/StatTile";
import { EmptyState, ErrorState, LoadingState } from "../components/primitives/States";
import { useArtifact } from "../hooks/useArtifact";
import { formatDate, formatPercent, formatSignedPercent, titleCase } from "../lib/format";
import type {
  CorporateEvent,
  DecisionReadiness,
  Horizon,
  Recommendation,
  TickerDataGapReport,
} from "../types";
import styles from "./OpportunityCenter.module.css";

const HORIZON_ORDER: Horizon[] = ["micro", "swing", "investment"];
const LAYER_LABELS: Record<string, string> = {
  financials: "Financials",
  disclosures: "Disclosures",
  news: "News",
  macro: "Macro",
  knowledge: "Knowledge",
};

/** Every opportunity AGX currently sees, ranked by confidence -- the
 * mission's "heart of AGX." Selecting a row shows the full explanation
 * inline; "Open full research workspace" goes to the per-company deep
 * page (Company Research Workspace, a later milestone). */
export function OpportunityCenter() {
  const recommendations = useArtifact((p) => p.getRecommendations());
  const marketState = useArtifact((p) => p.getMarketState());
  const readiness = useArtifact((p) => p.getDecisionReadiness());
  const gapReport = useArtifact((p) => p.getTickerDataGapReport());
  const [selectedTicker, setSelectedTicker] = useState<string | null>(null);
  const [selectedGapTicker, setSelectedGapTicker] = useState<string | null>(null);

  const ranked = [...(recommendations.data ?? [])].sort((a, b) => b.confidence - a.confidence);
  const companyNames = marketState.data?.constituents ?? {};
  const selected = ranked.find((r) => r.ticker === selectedTicker) ?? ranked[0] ?? null;

  const catalystsForSelected: CorporateEvent[] = selected
    ? (marketState.data?.dataset_snapshot.corporate_events[selected.ticker] ?? [])
        .filter((ce) => (marketState.data ? ce.event_date >= marketState.data.as_of : true))
        .sort((a, b) => (a.event_date > b.event_date ? 1 : -1))
    : [];

  const gapReports = gapReport.data ?? [];
  const selectedGap = gapReports.find((g) => g.ticker === selectedGapTicker) ?? null;

  return (
    <Section
      title="Opportunity Center"
      description="Every opportunity AGX currently sees, ranked by confidence, with the evidence behind it."
    >
      {recommendations.loading && <LoadingState rows={4} />}
      {recommendations.error && <ErrorState detail={recommendations.error.message} onRetry={recommendations.reload} />}

      {!recommendations.loading && !recommendations.error && (
        <div className={styles.layout}>
          <Card dense>
            <DataTable
              rows={ranked}
              getRowKey={(r) => r.ticker}
              onRowClick={(r) => setSelectedTicker(r.ticker)}
              emptyTitle="No opportunities yet"
              emptyDetail="Recommendations appear once the Meta Decision Engine has combined horizon predictions."
              columns={[
                {
                  key: "ticker",
                  header: "Opportunity",
                  render: (r) => (
                    <div className={styles.tickerCell}>
                      <span className={styles.tickerCode}>{r.ticker}</span>
                      <span className={styles.tickerCompany}>{companyNames[r.ticker] ?? ""}</span>
                    </div>
                  ),
                },
                {
                  key: "confidence",
                  header: "Confidence",
                  render: (r) => <Meter value={r.confidence} label={formatPercent(r.confidence)} />,
                },
                {
                  key: "return",
                  header: "Exp. Return",
                  align: "right",
                  render: (r) => (
                    <span className="num" style={{ color: r.combined_expected_return >= 0 ? "var(--positive)" : "var(--negative)" }}>
                      {formatSignedPercent(r.combined_expected_return)}
                    </span>
                  ),
                },
                {
                  key: "risk",
                  header: "Exp. Risk",
                  align: "right",
                  render: (r) => <span className="num">{formatPercent(r.combined_expected_risk)}</span>,
                },
                {
                  key: "horizons",
                  header: "Horizons",
                  render: (r) => (
                    <div className={styles.horizonBadges}>
                      {HORIZON_ORDER.filter((h) => r.horizon_predictions[h]).map((h) => {
                        const prediction = r.horizon_predictions[h]!;
                        return (
                          <Badge
                            key={h}
                            variant={prediction.expected_return >= 0 ? "positive" : "negative"}
                            title={`${titleCase(h)}: ${formatSignedPercent(prediction.expected_return)} exp. return, ${formatPercent(prediction.confidence)} confidence`}
                          >
                            {titleCase(h)} {formatSignedPercent(prediction.expected_return)}
                          </Badge>
                        );
                      })}
                    </div>
                  ),
                },
              ]}
            />
          </Card>

          <Card title={selected ? `${selected.ticker} — Evidence` : "Evidence"} dense>
            {!selected && <EmptyState title="No opportunity selected" detail="Select a row to see its full explanation." />}
            {selected && <OpportunityDetail recommendation={selected} companyName={companyNames[selected.ticker]} catalysts={catalystsForSelected} />}
          </Card>
        </div>
      )}

      <div className={styles.layout}>
        <Card title="Decision Readiness" subtitle="Why AGX can research or must abstain for every ticker" dense>
          {readiness.loading && <LoadingState rows={4} />}
          {readiness.error && <ErrorState detail={readiness.error.message} onRetry={readiness.reload} />}
          {!readiness.loading && !readiness.error && (
            <DataTable<DecisionReadiness>
              rows={readiness.data ?? []}
              getRowKey={(row) => row.ticker}
              onRowClick={(row) => setSelectedGapTicker(row.ticker)}
              emptyTitle="No readiness assessment yet"
              emptyDetail="The production pipeline must run before evidence readiness can be assessed."
              columns={[
                { key: "ticker", header: "Ticker", render: (row) => <span className={styles.tickerCode}>{row.ticker}</span> },
                {
                  key: "status",
                  header: "Status",
                  render: (row) => (
                    <Badge variant={row.status === "ready" ? "positive" : row.status === "degraded" ? "warning" : "negative"}>
                      {titleCase(row.status)}
                    </Badge>
                  ),
                },
                { key: "decision", header: "Decision", render: (row) => titleCase(row.decision) },
                { key: "prices", header: "Prices", align: "right", render: (row) => <span className="num">{row.price_observations}</span> },
                { key: "financials", header: "Financial Periods", align: "right", render: (row) => <span className="num">{row.financial_periods}</span> },
                { key: "knowledge", header: "Knowledge", align: "right", render: (row) => <span className="num">{row.active_knowledge}</span> },
                { key: "blocker", header: "Primary Blocker", render: (row) => row.blockers[0] ?? "None" },
              ]}
            />
          )}
        </Card>

        <Card title={selectedGap ? `${selectedGap.ticker} — Data Coverage` : "Data Coverage"} dense>
          {gapReport.loading && <LoadingState rows={4} />}
          {gapReport.error && <ErrorState detail={gapReport.error.message} onRetry={gapReport.reload} />}
          {!gapReport.loading && !gapReport.error && !selectedGap && (
            <EmptyState
              title="No ticker selected"
              detail="Select a row in Decision Readiness to see its per-layer data-completeness breakdown."
            />
          )}
          {!gapReport.loading && !gapReport.error && selectedGap && <TickerGapDetail gap={selectedGap} />}
        </Card>
      </div>
    </Section>
  );
}

function TickerGapDetail({ gap }: { gap: TickerDataGapReport }) {
  return (
    <div>
      <div className={styles.detailStats}>
        <StatTile label="Overall Completeness" value={formatPercent(gap.overall_completeness_pct / 100)} />
        <StatTile label="Swing Ready" value={gap.swing_ready ? "Yes" : "No"} />
        <StatTile label="Investment Ready" value={gap.investment_ready ? "Yes" : "No"} />
      </div>

      <div className={styles.block}>
        <div className={styles.blockTitle}>Data Layers</div>
        <div className={styles.horizonGrid}>
          {gap.layers.map((layer) => (
            <div key={layer.layer} className={styles.horizonCard}>
              <div className={styles.horizonCardHeader}>
                <span className={styles.horizonCardTitle}>{LAYER_LABELS[layer.layer] ?? titleCase(layer.layer)}</span>
                <Meter value={layer.completeness_pct / 100} label={`${layer.completeness_pct}%`} />
              </div>
              <div className={styles.horizonCardStats}>
                <span className="num">{layer.count}</span>
                <span className={styles.horizonCardStatLabel}>of {layer.threshold} required</span>
              </div>
              {!layer.complete && (
                <p className={styles.horizonCardWhy}>Below the readiness threshold for this layer.</p>
              )}
            </div>
          ))}
        </div>
      </div>

      <div className={styles.block}>
        <div className={styles.blockTitle}>Blockers</div>
        {gap.blockers.length === 0 ? (
          <span className={styles.blockText}>None recorded.</span>
        ) : (
          <ul className={styles.bulletList}>
            {gap.blockers.map((b, i) => (
              <li key={i}>{b}</li>
            ))}
          </ul>
        )}
      </div>

      <div className={styles.block}>
        <div className={styles.blockTitle}>Next Actions</div>
        {gap.next_actions.length === 0 ? (
          <span className={styles.blockText}>None recorded.</span>
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
  const { explanation } = recommendation;
  return (
    <div>
      <div className={styles.detailHeader}>
        <span className={styles.detailTicker}>{recommendation.ticker}</span>
        {companyName && <span className={styles.detailCompany}>{companyName}</span>}
      </div>

      <div className={styles.detailStats}>
        <StatTile label="Confidence" value={formatPercent(recommendation.confidence)} />
        <StatTile
          label="Exp. Return"
          value={formatSignedPercent(recommendation.combined_expected_return)}
          deltaSign={recommendation.combined_expected_return >= 0 ? 1 : -1}
        />
        <StatTile label="Exp. Risk" value={formatPercent(recommendation.combined_expected_risk)} />
      </div>

      <div className={styles.block}>
        <div className={styles.blockTitle}>Horizon Breakdown</div>
        <div className={styles.horizonGrid}>
          {HORIZON_ORDER.map((h) => {
            const prediction = recommendation.horizon_predictions[h];
            return (
              <div key={h} className={styles.horizonCard}>
                <div className={styles.horizonCardHeader}>
                  <span className={styles.horizonCardTitle}>{titleCase(h)}</span>
                  {prediction ? (
                    <Meter value={prediction.confidence} label={formatPercent(prediction.confidence)} />
                  ) : (
                    <Badge variant="neutral">No signal</Badge>
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
                      <span className={styles.horizonCardStatLabel}>exp. return</span>
                      <span className="num">{formatPercent(prediction.expected_risk)}</span>
                      <span className={styles.horizonCardStatLabel}>exp. risk</span>
                    </div>
                    <p className={styles.horizonCardWhy}>
                      {prediction.explanation.why_this_stock} {prediction.explanation.why_now}
                    </p>
                  </>
                ) : (
                  <p className={styles.horizonCardWhy}>No model prediction for this horizon yet.</p>
                )}
              </div>
            );
          })}
        </div>
      </div>

      <div className={styles.block}>
        <div className={styles.blockTitle}>Research Summary</div>
        <p className={styles.blockText}>{explanation.why_this_stock} {explanation.why_now}</p>
      </div>

      <div className={styles.block}>
        <div className={styles.blockTitle}>Risk Summary</div>
        <p className={styles.blockText}>{explanation.why_not_others}</p>
      </div>

      <div className={styles.block}>
        <div className={styles.blockTitle}>Supporting Evidence</div>
        {explanation.supporting_evidence.length === 0 ? (
          <span className={styles.blockText}>None recorded.</span>
        ) : (
          <ul className={styles.bulletList}>
            {explanation.supporting_evidence.map((e, i) => (
              <li key={i}>{e}</li>
            ))}
          </ul>
        )}
      </div>

      <div className={styles.block}>
        <div className={styles.blockTitle}>Contradicting Evidence / Invalidation Conditions</div>
        {explanation.invalidation_conditions.length === 0 ? (
          <span className={styles.blockText}>None recorded.</span>
        ) : (
          <ul className={styles.bulletList}>
            {explanation.invalidation_conditions.map((e, i) => (
              <li key={i}>{e}</li>
            ))}
          </ul>
        )}
      </div>

      <div className={styles.block}>
        <div className={styles.blockTitle}>Historical Similar Cases</div>
        {explanation.similar_historical_cases.length === 0 ? (
          <span className={styles.blockText}>None recorded.</span>
        ) : (
          <ul className={styles.bulletList}>
            {explanation.similar_historical_cases.map((e, i) => (
              <li key={i}>{e}</li>
            ))}
          </ul>
        )}
      </div>

      <div className={styles.block}>
        <div className={styles.blockTitle}>Upcoming Catalysts</div>
        {catalysts.length === 0 ? (
          <span className={styles.blockText}>No scheduled catalysts.</span>
        ) : (
          <ul className={styles.bulletList}>
            {catalysts.map((c, i) => (
              <li key={i}>
                {formatDate(c.event_date)} — {titleCase(c.event_type)}: {c.description}
              </li>
            ))}
          </ul>
        )}
      </div>

      <Link className={styles.workspaceLink} to={`/company/${recommendation.ticker}`}>
        Open full research workspace →
      </Link>
    </div>
  );
}
