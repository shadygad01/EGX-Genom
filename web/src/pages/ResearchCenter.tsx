import { useState } from "react";
import { Link } from "react-router-dom";
import { Badge, type BadgeVariant } from "../components/primitives/Badge";
import { Card } from "../components/primitives/Card";
import { DataTable } from "../components/primitives/DataTable";
import { Section } from "../components/primitives/Section";
import { StatTile } from "../components/primitives/StatTile";
import { EmptyState, ErrorState, LoadingState } from "../components/primitives/States";
import { useArtifact } from "../hooks/useArtifact";
import { formatDate, formatDateTime, formatPercent, titleCase } from "../lib/format";
import type { Hypothesis, KnowledgeStatus } from "../types";
import styles from "./ResearchCenter.module.css";

const KNOWLEDGE_VARIANT: Record<KnowledgeStatus, BadgeVariant> = {
  promoted: "positive",
  monitoring: "accent",
  retired: "neutral",
};

function hypothesisStatus(h: Hypothesis): { label: string; variant: BadgeVariant } {
  const lastStage = h.stage_history[h.stage_history.length - 1];
  if (lastStage && !lastStage.passed) {
    return { label: `Failed at ${titleCase(lastStage.stage_name)}`, variant: "negative" };
  }
  if (h.stage_index >= h.pipeline.length) {
    return { label: "Completed all gates", variant: "positive" };
  }
  return { label: `Stage ${h.stage_index + 1} of ${h.pipeline.length}`, variant: "accent" };
}

/** Where a discovered relationship's whole lifecycle is visible: the
 * 8-gate hypothesis pipeline (covering "experiments," "validation queue,"
 * "active research," and "discovery history" -- all views over the same
 * Hypothesis stage_history), the knowledge store, and published papers.
 * Review Board detail is an honest gap: no repository persists past
 * BoardDecisions yet (see NEXT_MISSIONS.md). */
export function ResearchCenter() {
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
      <Section
        title="Hypothesis Pipeline"
        description="Discovery History, Active Research, and the Validation Queue are all this same 8-gate pipeline, viewed by stage."
      >
        {hypotheses.loading && <LoadingState rows={4} />}
        {hypotheses.error && <ErrorState detail={hypotheses.error.message} onRetry={hypotheses.reload} />}
        {!hypotheses.loading && !hypotheses.error && (
          <div className={styles.grid} style={{ marginBottom: "var(--space-4)" }}>
            <StatTile label="Total Hypotheses" value={allHypotheses.length} />
            <StatTile label="Active Research" value={activeCount} />
          </div>
        )}
        {!hypotheses.loading && !hypotheses.error && (
          <div className={styles.layout}>
            <Card dense>
              <DataTable
                rows={allHypotheses}
                getRowKey={(h) => h.id}
                onRowClick={(h) => setSelectedId(h.id)}
                emptyTitle="No hypotheses yet"
                emptyDetail="Hypotheses appear once an agent's research finding enters the validation pipeline."
                columns={[
                  { key: "statement", header: "Statement", render: (h) => h.statement },
                  { key: "horizon", header: "Horizon", render: (h) => <Badge variant="neutral">{titleCase(h.horizon)}</Badge> },
                  {
                    key: "status",
                    header: "Status",
                    render: (h) => {
                      const s = hypothesisStatus(h);
                      return <Badge variant={s.variant}>{s.label}</Badge>;
                    },
                  },
                  { key: "created", header: "Created", align: "right", render: (h) => formatDate(h.created_at) },
                ]}
              />
            </Card>

            <Card title={selected ? "Stage History" : "Stage History"} dense>
              {!selected && <EmptyState title="No hypothesis selected" detail="Select a row to see its full gate history." />}
              {selected && (
                <div>
                  <div className={styles.detailHeader}>{selected.statement}</div>
                  <div className={styles.detailMeta}>
                    {selected.created_by} · {formatDate(selected.created_at)} · {selected.affected_assets.join(", ")}
                  </div>
                  {selected.stage_history.length === 0 ? (
                    <EmptyState title="No stages evaluated yet" />
                  ) : (
                    <div className={styles.stageList}>
                      {selected.stage_history.map((s, i) => (
                        <div key={i} className={styles.stageRow}>
                          <div>
                            <div className={styles.stageName}>{titleCase(s.stage_name)}</div>
                            {s.notes && <div className={styles.stageNotes}>{s.notes}</div>}
                          </div>
                          <Badge variant={s.passed ? "positive" : "negative"}>{s.passed ? "Passed" : "Failed"}</Badge>
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

      <Section title="Knowledge Objects" description="Every knowledge object the validation pipeline has promoted, monitored, or retired.">
        <div className={styles.grid} style={{ marginBottom: "var(--space-4)" }}>
          <StatTile label="Promoted" value={knowledgeByStatus.promoted} />
          <StatTile label="Monitoring" value={knowledgeByStatus.monitoring} />
          <StatTile label="Retired" value={knowledgeByStatus.retired} />
        </div>
        {knowledge.error && <ErrorState detail={knowledge.error.message} onRetry={knowledge.reload} />}
        {!knowledge.error && (
          <DataTable
            rows={sortedKnowledge}
            getRowKey={(k) => k.id}
            emptyTitle="No knowledge objects yet"
            columns={[
              {
                key: "assets",
                header: "Assets",
                render: (k) => (
                  <div className={styles.tickerLinks}>
                    {k.affected_assets.map((t) => (
                      <Link key={t} className={styles.tickerLink} to={`/company/${t}`}>
                        {t}
                      </Link>
                    ))}
                  </div>
                ),
              },
              { key: "status", header: "Status", render: (k) => <Badge variant={KNOWLEDGE_VARIANT[k.status]}>{titleCase(k.status)}</Badge> },
              { key: "horizon", header: "Horizon", render: (k) => titleCase(k.horizon) },
              { key: "confidence", header: "Confidence", align: "right", render: (k) => formatPercent(k.confidence) },
              { key: "discovered", header: "Discovered", align: "right", render: (k) => formatDate(k.discovery_date) },
            ]}
          />
        )}
      </Section>

      <div className={styles.layout}>
        <Card title="Scientific Papers" subtitle="Every paper published from promoted knowledge">
          {papers.error && <ErrorState detail={papers.error.message} onRetry={papers.reload} />}
          {!papers.error && sortedPapers.length === 0 && <EmptyState title="No papers yet" />}
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

        <Card title="Review Board">
          <EmptyState
            title="Not yet available"
            detail="No repository persists past ScientificReviewBoard decisions yet -- this section will populate once one exists (see docs/TECHNICAL_DEBT.md), never a fabricated review history."
          />
        </Card>
      </div>
    </>
  );
}
