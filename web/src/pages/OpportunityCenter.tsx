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
import type { CorporateEvent, Horizon, Recommendation } from "../types";
import styles from "./OpportunityCenter.module.css";

const HORIZON_ORDER: Horizon[] = ["micro", "swing", "investment"];

/** Every opportunity AGX currently sees, ranked by confidence -- the
 * mission's "heart of AGX." Selecting a row shows the full explanation
 * inline; "Open full research workspace" goes to the per-company deep
 * page (Company Research Workspace, a later milestone). */
export function OpportunityCenter() {
  const recommendations = useArtifact((p) => p.getRecommendations());
  const marketState = useArtifact((p) => p.getMarketState());
  const [selectedTicker, setSelectedTicker] = useState<string | null>(null);

  const ranked = [...(recommendations.data ?? [])].sort((a, b) => b.confidence - a.confidence);
  const companyNames = marketState.data?.constituents ?? {};
  const selected = ranked.find((r) => r.ticker === selectedTicker) ?? ranked[0] ?? null;

  const catalystsForSelected: CorporateEvent[] = selected
    ? (marketState.data?.dataset_snapshot.corporate_events[selected.ticker] ?? [])
        .filter((ce) => (marketState.data ? ce.event_date >= marketState.data.as_of : true))
        .sort((a, b) => (a.event_date > b.event_date ? 1 : -1))
    : [];

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
                      {HORIZON_ORDER.filter((h) => r.horizon_predictions[h]).map((h) => (
                        <Badge key={h} variant="neutral">
                          {titleCase(h)}
                        </Badge>
                      ))}
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
    </Section>
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
