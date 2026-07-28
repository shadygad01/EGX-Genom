import { useState } from "react";
import { Link } from "react-router-dom";
import { useTranslation } from "react-i18next";
import type { TFunction } from "i18next";
import { Badge, type BadgeVariant } from "../components/primitives/Badge";
import { Card } from "../components/primitives/Card";
import { DataTable } from "../components/primitives/DataTable";
import { Section } from "../components/primitives/Section";
import { StatTile } from "../components/primitives/StatTile";
import { EmptyState, ErrorState, LoadingState } from "../components/primitives/States";
import { useArtifact } from "../hooks/useArtifact";
import { useEnumLabel } from "../hooks/useEnumLabel";
import { useFormatters } from "../hooks/useFormatters";
import { formatPercent } from "../lib/format";
import type { Hypothesis, KnowledgeStatus } from "../types";
import styles from "./ResearchCenter.module.css";

const KNOWLEDGE_VARIANT: Record<KnowledgeStatus, BadgeVariant> = {
  promoted: "positive",
  monitoring: "accent",
  retired: "neutral",
};

function hypothesisStatus(
  h: Hypothesis,
  t: TFunction<"researchCenter">,
  label: (category: string, value: string | null | undefined) => string,
): { label: string; variant: BadgeVariant } {
  const lastStage = h.stage_history[h.stage_history.length - 1];
  if (lastStage && !lastStage.passed) {
    return { label: t("pipeline.failedAt", { stage: label("stageName", lastStage.stage_name) }), variant: "negative" };
  }
  if (h.stage_index >= h.pipeline.length) {
    return { label: t("pipeline.completedAllGates"), variant: "positive" };
  }
  return { label: t("pipeline.stageOf", { index: h.stage_index + 1, total: h.pipeline.length }), variant: "accent" };
}

/** Where a discovered relationship's whole lifecycle is visible: the
 * 8-gate hypothesis pipeline (covering "experiments," "validation queue,"
 * "active research," and "discovery history" -- all views over the same
 * Hypothesis stage_history), the knowledge store, and published papers.
 * Review Board detail is an honest gap: no repository persists past
 * BoardDecisions yet (see NEXT_MISSIONS.md). */
export function ResearchCenter() {
  const { t } = useTranslation("researchCenter");
  const label = useEnumLabel();
  const { formatDate, formatDateTime } = useFormatters();
  const hypotheses = useArtifact((p) => p.getHypotheses());
  const knowledge = useArtifact((p) => p.getKnowledge());
  const papers = useArtifact((p) => p.getPapers());
  const [selectedId, setSelectedId] = useState<string | null>(null);

  const allHypotheses = [...(hypotheses.data ?? [])].sort((a, b) => (a.created_at < b.created_at ? 1 : -1));
  const activeCount = allHypotheses.filter((h) => {
    const last = h.stage_history[h.stage_history.length - 1];
    return h.stage_index < h.pipeline.length && (!last || last.passed);
  }).length;
  const selected = allHypotheses.find((h) => h.id === selectedId) ?? allHypotheses[0] ?? null;

  const knowledgeByStatus = {
    promoted: (knowledge.data ?? []).filter((k) => k.status === "promoted").length,
    monitoring: (knowledge.data ?? []).filter((k) => k.status === "monitoring").length,
    retired: (knowledge.data ?? []).filter((k) => k.status === "retired").length,
  };
  const sortedKnowledge = [...(knowledge.data ?? [])].sort((a, b) => (a.discovery_date < b.discovery_date ? 1 : -1));
  const sortedPapers = [...(papers.data ?? [])].sort((a, b) => (a.published_at < b.published_at ? 1 : -1));

  return (
    <>
      <Section title={t("pipeline.title")} description={t("pipeline.description")}>
        {hypotheses.loading && <LoadingState rows={4} />}
        {hypotheses.error && <ErrorState detail={hypotheses.error.message} onRetry={hypotheses.reload} />}
        {!hypotheses.loading && !hypotheses.error && (
          <div className={styles.grid} style={{ marginBottom: "var(--space-4)" }}>
            <StatTile label={t("pipeline.totalHypotheses")} value={allHypotheses.length} />
            <StatTile label={t("pipeline.activeResearch")} value={activeCount} />
          </div>
        )}
        {!hypotheses.loading && !hypotheses.error && (
          <div className={styles.layout}>
            <Card dense>
              <DataTable
                rows={allHypotheses}
                getRowKey={(h) => h.id}
                onRowClick={(h) => setSelectedId(h.id)}
                emptyTitle={t("pipeline.emptyTitle")}
                emptyDetail={t("pipeline.emptyDetail")}
                columns={[
                  { key: "statement", header: t("pipeline.statement"), render: (h) => h.statement },
                  { key: "horizon", header: t("pipeline.horizon"), render: (h) => <Badge variant="neutral">{label("horizon", h.horizon)}</Badge> },
                  {
                    key: "status",
                    header: t("pipeline.status"),
                    render: (h) => {
                      const s = hypothesisStatus(h, t, label);
                      return <Badge variant={s.variant}>{s.label}</Badge>;
                    },
                  },
                  { key: "created", header: t("pipeline.created"), align: "right", render: (h) => formatDate(h.created_at) },
                ]}
              />
            </Card>

            <Card title={t("stageHistory.title")} dense>
              {!selected && <EmptyState title={t("stageHistory.emptyTitle")} detail={t("stageHistory.emptyDetail")} />}
              {selected && (
                <div>
                  <div className={styles.detailHeader}>{selected.statement}</div>
                  <div className={styles.detailMeta}>
                    {selected.created_by} · {formatDate(selected.created_at)} · <span className="num">{selected.affected_assets.join(", ")}</span>
                  </div>
                  {selected.stage_history.length === 0 ? (
                    <EmptyState title={t("stageHistory.noStagesYet")} />
                  ) : (
                    <div className={styles.stageList}>
                      {selected.stage_history.map((s, i) => (
                        <div key={i} className={styles.stageRow}>
                          <div>
                            <div className={styles.stageName}>{label("stageName", s.stage_name)}</div>
                            {s.notes && <div className={styles.stageNotes}>{s.notes}</div>}
                          </div>
                          <Badge variant={s.passed ? "positive" : "negative"}>{s.passed ? t("stageHistory.passed") : t("stageHistory.failed")}</Badge>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              )}
            </Card>
          </div>
        )}
      </Section>

      <Section title={t("knowledgeObjects.title")} description={t("knowledgeObjects.description")}>
        <div className={styles.grid} style={{ marginBottom: "var(--space-4)" }}>
          <StatTile label={t("knowledgeObjects.promoted")} value={knowledgeByStatus.promoted} />
          <StatTile label={t("knowledgeObjects.monitoring")} value={knowledgeByStatus.monitoring} />
          <StatTile label={t("knowledgeObjects.retired")} value={knowledgeByStatus.retired} />
        </div>
        {knowledge.error && <ErrorState detail={knowledge.error.message} onRetry={knowledge.reload} />}
        {!knowledge.error && (
          <DataTable
            rows={sortedKnowledge}
            getRowKey={(k) => k.id}
            emptyTitle={t("knowledgeObjects.emptyTitle")}
            columns={[
              {
                key: "assets",
                header: t("knowledgeObjects.assets"),
                render: (k) => (
                  <div className={styles.tickerLinks}>
                    {k.affected_assets.map((ticker) => (
                      <Link key={ticker} className={`${styles.tickerLink} num`} to={`/company/${ticker}`}>
                        {ticker}
                      </Link>
                    ))}
                  </div>
                ),
              },
              { key: "status", header: t("knowledgeObjects.status"), render: (k) => <Badge variant={KNOWLEDGE_VARIANT[k.status]}>{label("knowledgeStatus", k.status)}</Badge> },
              { key: "horizon", header: t("knowledgeObjects.horizon"), render: (k) => label("horizon", k.horizon) },
              { key: "confidence", header: t("knowledgeObjects.confidence"), align: "right", render: (k) => <span className="num">{formatPercent(k.confidence)}</span> },
              { key: "discovered", header: t("knowledgeObjects.discovered"), align: "right", render: (k) => formatDate(k.discovery_date) },
            ]}
          />
        )}
      </Section>

      <div className={styles.layout}>
        <Card title={t("papers.title")} subtitle={t("papers.subtitle")}>
          {papers.error && <ErrorState detail={papers.error.message} onRetry={papers.reload} />}
          {!papers.error && sortedPapers.length === 0 && <EmptyState title={t("papers.emptyTitle")} />}
          {sortedPapers.length > 0 && (
            <div className={styles.list}>
              {sortedPapers.map((p) => (
                <div key={p.id} className={styles.listItem}>
                  <div className={styles.listItemHead}>
                    <span className={styles.listItemTitle}>{p.title}</span>
                    <span className={styles.listItemMeta}>{formatDateTime(p.published_at)}</span>
                  </div>
                  <span className={styles.listItemDetail}>{p.conclusion}</span>
                </div>
              ))}
            </div>
          )}
        </Card>

        <Card title={t("reviewBoard.title")}>
          <EmptyState title={t("reviewBoard.emptyTitle")} detail={t("reviewBoard.emptyDetail")} />
        </Card>
      </div>
    </>
  );
}
