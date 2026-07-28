import { useMemo, useRef, useState } from "react";
import { Link } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { Card } from "../components/primitives/Card";
import { Section } from "../components/primitives/Section";
import { EmptyState, ErrorState, LoadingState } from "../components/primitives/States";
import { useArtifact } from "../hooks/useArtifact";
import { useEnumLabel } from "../hooks/useEnumLabel";
import { computeForceLayout } from "../lib/forceLayout";
import { titleCase } from "../lib/format";
import type { GraphEdge, NodeType } from "../types";
import styles from "./KnowledgeGraphPage.module.css";

const NODE_COLOR: Record<NodeType, string> = {
  company: "#5b8def",
  sector: "#e0a030",
  market: "#34c77b",
  event: "#ef5350",
  hypothesis: "#8b90ea",
  experiment: "#4fc3d9",
  feature: "#c77dff",
  gene: "#7fd858",
  research_paper: "#f2a65a",
  prediction: "#6ee7e7",
  recommendation: "#f27ba0",
  knowledge: "#7ba3f2",
  dataset_snapshot: "#9aa0ab",
  research_finding: "#d4a5f2",
  macro_series: "#f2d24b",
};

const WIDTH = 1000;
const HEIGHT = 640;

/** The graph is a rendering of exactly what getKnowledgeGraph() returns
 * (itself a mechanical view over Provenance) -- no relationship is
 * invented here. Layout uses a small dependency-free force simulation
 * (lib/forceLayout.ts) rather than adding a graph-rendering library for
 * one page. */
export function KnowledgeGraphPage() {
  const { t } = useTranslation("knowledgeGraph");
  const label = useEnumLabel();
  const graph = useArtifact((p) => p.getKnowledgeGraph());
  const [query, setQuery] = useState("");
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [view, setView] = useState({ x: 0, y: 0, scale: 1 });
  const dragState = useRef<{ startX: number; startY: number; viewX: number; viewY: number } | null>(null);

  const nodes = graph.data?.nodes ?? [];
  const edges = graph.data?.edges ?? [];

  const positions = useMemo(
    () =>
      computeForceLayout(
        nodes.map((n) => n.id),
        edges.map((e) => ({ source: e.source_id, target: e.target_id })),
        WIDTH,
        HEIGHT,
      ),
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [nodes.length, edges.length],
  );

  const nodeById = useMemo(() => new Map(nodes.map((n) => [n.id, n])), [nodes]);
  const matchedIds = useMemo(() => {
    if (!query.trim()) return null;
    const q = query.toLowerCase();
    return new Set(nodes.filter((n) => n.label.toLowerCase().includes(q)).map((n) => n.id));
  }, [nodes, query]);

  const selected = selectedId ? nodeById.get(selectedId) ?? null : null;
  const selectedEdges: GraphEdge[] = selectedId
    ? edges.filter((e) => e.source_id === selectedId || e.target_id === selectedId)
    : [];

  const legendTypes = [...new Set(nodes.map((n) => n.node_type))];

  function onWheel(e: React.WheelEvent<SVGSVGElement>) {
    e.preventDefault();
    const delta = e.deltaY > 0 ? 0.9 : 1.1;
    setView((v) => ({ ...v, scale: Math.min(3, Math.max(0.3, v.scale * delta)) }));
  }

  function onMouseDown(e: React.MouseEvent<SVGSVGElement>) {
    dragState.current = { startX: e.clientX, startY: e.clientY, viewX: view.x, viewY: view.y };
  }

  function onMouseMove(e: React.MouseEvent<SVGSVGElement>) {
    if (!dragState.current) return;
    const dx = e.clientX - dragState.current.startX;
    const dy = e.clientY - dragState.current.startY;
    setView((v) => ({ ...v, x: dragState.current!.viewX + dx, y: dragState.current!.viewY + dy }));
  }

  function stopDrag() {
    dragState.current = null;
  }

  return (
    <Section title={t("title")} description={t("description")}>
      {graph.loading && <LoadingState rows={6} />}
      {graph.error && <ErrorState detail={graph.error.message} onRetry={graph.reload} />}
      {!graph.loading && !graph.error && nodes.length === 0 && (
        <EmptyState title={t("emptyTitle")} detail={t("emptyDetail")} />
      )}

      {!graph.loading && !graph.error && nodes.length > 0 && (
        <div className={styles.layout}>
          <div>
            <div className={styles.toolbar}>
              <input
                className={styles.searchInput}
                type="text"
                placeholder={t("searchPlaceholder")}
                value={query}
                onChange={(e) => setQuery(e.target.value)}
              />
              <span className={styles.hint}>{t("hint")}</span>
            </div>
            <div className={styles.canvasWrap}>
              <svg
                className={styles.svg}
                viewBox={`0 0 ${WIDTH} ${HEIGHT}`}
                onWheel={onWheel}
                onMouseDown={onMouseDown}
                onMouseMove={onMouseMove}
                onMouseUp={stopDrag}
                onMouseLeave={stopDrag}
              >
                <g transform={`translate(${view.x} ${view.y}) scale(${view.scale})`}>
                  {edges.map((e) => {
                    const a = positions.get(e.source_id);
                    const b = positions.get(e.target_id);
                    if (!a || !b) return null;
                    const dim = matchedIds ? !matchedIds.has(e.source_id) && !matchedIds.has(e.target_id) : false;
                    return (
                      <line
                        key={e.id}
                        x1={a.x}
                        y1={a.y}
                        x2={b.x}
                        y2={b.y}
                        className={dim ? styles.edgeDim : styles.edge}
                      />
                    );
                  })}
                  {nodes.map((n) => {
                    const pos = positions.get(n.id);
                    if (!pos) return null;
                    const dim = matchedIds ? !matchedIds.has(n.id) : false;
                    return (
                      <g key={n.id} onClick={() => setSelectedId(n.id)}>
                        <circle
                          cx={pos.x}
                          cy={pos.y}
                          r={n.id === selectedId ? 8 : 6}
                          fill={NODE_COLOR[n.node_type]}
                          opacity={dim ? 0.25 : 1}
                          className={n.id === selectedId ? `${styles.node} ${styles.nodeSelected}` : styles.node}
                        />
                        <text x={pos.x + 9} y={pos.y + 3} className={dim ? `${styles.nodeLabel} ${styles.nodeLabelDim}` : styles.nodeLabel}>
                          {n.label.length > 24 ? `${n.label.slice(0, 24)}…` : n.label}
                        </text>
                      </g>
                    );
                  })}
                </g>
              </svg>
              <div className={styles.legend}>
                {legendTypes.map((nodeType) => (
                  <span key={nodeType} className={styles.legendItem}>
                    <span className={styles.legendDot} style={{ background: NODE_COLOR[nodeType] }} />
                    {label("nodeType", nodeType)}
                  </span>
                ))}
              </div>
            </div>
          </div>

          <Card title={t("nodeDetail.title")} dense>
            {!selected && <EmptyState title={t("nodeDetail.emptyTitle")} detail={t("nodeDetail.emptyDetail")} />}
            {selected && (
              <div>
                <div className={styles.detailTitle}>{selected.label}</div>
                <div className={styles.detailMeta}>
                  {label("nodeType", selected.node_type)} · <span className="num">{selected.id}</span>
                </div>

                {selected.node_type === "company" && (
                  <Link to={`/company/${selected.id}`} style={{ color: "var(--accent-strong)", fontWeight: 600, fontSize: "var(--text-xs)" }}>
                    {t("nodeDetail.openWorkspace")} <span className="icon-forward" aria-hidden="true">→</span>
                  </Link>
                )}

                {Object.keys(selected.metadata).length > 0 && (
                  <>
                    <div className={styles.blockTitle} style={{ marginTop: "var(--space-4)" }}>
                      {t("nodeDetail.metadata")}
                    </div>
                    <div className={styles.metaTable}>
                      {Object.entries(selected.metadata).map(([k, v]) => (
                        <div key={k} className={styles.metaRow}>
                          <span className={styles.metaKey}>{titleCase(k)}</span>
                          <span className={styles.metaValue}>{String(v)}</span>
                        </div>
                      ))}
                    </div>
                  </>
                )}

                <div className={styles.blockTitle}>{t("nodeDetail.relationships", { count: selectedEdges.length })}</div>
                {selectedEdges.length === 0 ? (
                  <EmptyState title={t("nodeDetail.noConnectedEdges")} />
                ) : (
                  <div className={styles.edgeList}>
                    {selectedEdges.map((e) => {
                      const outgoing = e.source_id === selectedId;
                      const otherId = outgoing ? e.target_id : e.source_id;
                      const otherLabel = nodeById.get(otherId)?.label ?? otherId;
                      return (
                        <div key={e.id} className={styles.edgeRow}>
                          {/* Data-semantic direction (an actual graph-edge property, not a
                              "proceed forward" UI cue) -- never mirrored under RTL. */}
                          <span className="num" aria-hidden="true">{outgoing ? "→" : "←"}</span>{" "}
                          {label("eventRelationshipType", e.relationship)} {outgoing ? t("nodeDetail.edgeTo") : t("nodeDetail.edgeFrom")} <strong>{otherLabel}</strong>
                        </div>
                      );
                    })}
                  </div>
                )}
              </div>
            )}
          </Card>
        </div>
      )}
    </Section>
  );
}
