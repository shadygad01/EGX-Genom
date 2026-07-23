import { useLocation } from "react-router-dom";
import { Badge } from "../primitives/Badge";
import { useArtifact } from "../../hooks/useArtifact";
import { formatRelativeToNow } from "../../lib/format";
import styles from "./TopBar.module.css";

const PAGE_TITLES: Record<string, string> = {
  "/": "AI Briefing",
  "/opportunities": "Opportunity Center",
  "/market": "Market Intelligence",
  "/research": "Research Center",
  "/knowledge-graph": "Knowledge Graph",
  "/mission-control": "Mission Control",
  "/sources": "Source Intelligence",
  "/admin": "System Administration",
};

function titleForPath(pathname: string): string {
  if (PAGE_TITLES[pathname]) return PAGE_TITLES[pathname];
  if (pathname.startsWith("/company/")) return "Company Research Workspace";
  return "AGX Research";
}

/** Global status strip -- pipeline health, always visible, so a portfolio
 * manager never wonders whether what they're reading is stale. */
export function TopBar() {
  const location = useLocation();
  const { data: status } = useArtifact((p) => p.getSystemStatus());

  const hasFailures = (status?.failed ?? 0) > 0;

  return (
    <header className={styles.topbar}>
      <span className={styles.title}>{titleForPath(location.pathname)}</span>
      <div className={styles.status}>
        {status && (
          <>
            <Badge variant={hasFailures ? "warning" : "positive"} dot>
              {hasFailures ? "Degraded" : "Nominal"}
            </Badge>
            <span className={styles.timestamp}>
              Last cycle {formatRelativeToNow(status.pipeline_run_date)}
            </span>
          </>
        )}
      </div>
    </header>
  );
}
