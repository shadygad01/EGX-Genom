import { useLocation } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { Badge } from "../primitives/Badge";
import { useArtifact } from "../../hooks/useArtifact";
import { useFormatters } from "../../hooks/useFormatters";
import { LanguageToggle } from "./LanguageToggle";
import styles from "./TopBar.module.css";

const PAGE_TITLE_KEYS: Record<string, string> = {
  "/": "nav.aiBriefing",
  "/opportunities": "nav.opportunityCenter",
  "/market": "nav.marketIntelligence",
  "/research": "nav.researchCenter",
  "/knowledge-graph": "nav.knowledgeGraph",
  "/mission-control": "nav.missionControl",
  "/sources": "nav.sourceIntelligence",
  "/admin": "nav.systemAdministration",
};

/** Global status strip -- pipeline health, always visible, so a portfolio
 * manager never wonders whether what they're reading is stale. */
export function TopBar() {
  const { t } = useTranslation("common");
  const { formatRelativeToNow } = useFormatters();
  const location = useLocation();
  const { data: status } = useArtifact((p) => p.getSystemStatus());

  const hasFailures = (status?.failed ?? 0) > 0;
  const titleKey = PAGE_TITLE_KEYS[location.pathname];
  const title = titleKey
    ? t(titleKey)
    : location.pathname.startsWith("/company/")
      ? t("nav.companyWorkspace")
      : t("app.fallbackTitle");

  return (
    <header className={styles.topbar}>
      <span className={styles.title}>{title}</span>
      <div className={styles.status}>
        {status && (
          <>
            <Badge variant={hasFailures ? "warning" : "positive"} dot>
              {hasFailures ? t("topbar.degraded") : t("topbar.nominal")}
            </Badge>
            <span className={styles.timestamp}>
              {t("topbar.lastCycle", { time: formatRelativeToNow(status.pipeline_run_date) })}
            </span>
          </>
        )}
        <LanguageToggle />
      </div>
    </header>
  );
}
