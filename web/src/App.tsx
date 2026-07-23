import { useEffect, useState } from "react";
import { dataProvider as defaultDataProvider, type DashboardDataProvider } from "./data";
import type { KnowledgeObject } from "./types";

export interface AppProps {
  /** Defaults to the module-level provider selected by VITE_DATA_PROVIDER
   * (see web/src/data/factory.ts) -- overridable for tests, never for
   * ordinary use, so components never hardcode which provider they talk to. */
  provider?: DashboardDataProvider;
}

export function App({ provider = defaultDataProvider }: AppProps) {
  const [knowledge, setKnowledge] = useState<KnowledgeObject[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    provider
      .getKnowledge()
      .then(setKnowledge)
      .catch((err: unknown) => setError(err instanceof Error ? err.message : String(err)));
  }, [provider]);

  return (
    <main style={{ fontFamily: "system-ui, sans-serif", padding: "2rem", maxWidth: 1100, margin: "0 auto" }}>
      <h1>AGX Knowledge Base</h1>
      <p style={{ color: "#555" }}>
        Promoted, statistically validated knowledge objects currently in Monitoring or Promoted
        status. This is a minimal read-only viewer over a{" "}
        <code>DashboardDataProvider</code> (static JSON artifacts or a hosted{" "}
        <code>api/</code>, per configuration) — see <code>docs/ARCHITECTURE.md</code>.
      </p>

      {error && <p style={{ color: "crimson" }}>Error loading knowledge: {error}</p>}
      {!error && knowledge === null && <p>Loading…</p>}
      {knowledge !== null && knowledge.length === 0 && <p>No knowledge objects have been promoted yet.</p>}

      {knowledge !== null && knowledge.length > 0 && (
        <table style={{ width: "100%", borderCollapse: "collapse" }}>
          <thead>
            <tr style={{ textAlign: "left", borderBottom: "2px solid #ddd" }}>
              <th style={cellStyle}>ID</th>
              <th style={cellStyle}>Assets</th>
              <th style={cellStyle}>Horizon</th>
              <th style={cellStyle}>Status</th>
              <th style={cellStyle}>Confidence</th>
              <th style={cellStyle}>Expected Return</th>
              <th style={cellStyle}>Expected Risk</th>
              <th style={cellStyle}>Explanation</th>
            </tr>
          </thead>
          <tbody>
            {knowledge.map((k) => (
              <tr key={k.id} style={{ borderBottom: "1px solid #eee" }}>
                <td style={cellStyle}>{k.id}</td>
                <td style={cellStyle}>{k.affected_assets.join(", ")}</td>
                <td style={cellStyle}>{k.horizon}</td>
                <td style={cellStyle}>{k.status}</td>
                <td style={cellStyle}>{(k.confidence * 100).toFixed(0)}%</td>
                <td style={cellStyle}>{(k.expected_return * 100).toFixed(2)}%</td>
                <td style={cellStyle}>{(k.expected_risk * 100).toFixed(2)}%</td>
                <td style={{ ...cellStyle, maxWidth: 360 }}>{k.economic_explanation}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </main>
  );
}

const cellStyle: React.CSSProperties = { padding: "0.5rem 0.75rem", verticalAlign: "top" };
