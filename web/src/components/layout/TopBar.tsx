import { useLocation } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { Badge } from "../primitives/Badge";
import { useArtifact } from "../../hooks/useArtifact";
import { useFormatters } from "../../hooks/useFormatters";
import { LanguageToggle } from "./LanguageToggle";
import styles from "./TopBar.module.css";

const PAGE_TITLE_KEYS: Record<string, string> = {
  "/": "nav.cioDesk",
  "/portfolio": "nav.portfolio",
  "/cases": "nav.investmentCases",
  "/monitoring": "nav.monitoring",
  "/market": "nav.market",
  "/research": "nav.research",
  "/knowledge-graph": "nav.knowledgeGraph",
  "/sources": "nav.sourceIntelligence",
  "/settings": "nav.settings",
};

/** Global status strip -- pipeline health, always visible, so a portfolio
 * manager never wonders whether what they're reading is stale.
 *
 * `status.pipeline_run_date` is the research/decision data's as-of date
 * (`_latest_successful_as_of()` on the backend), not the automation's own
 * execution timestamp (`status.generated_at`) -- on a real EGX
 * non-trading day (Fri/Sat) the pipeline can run successfully today and
 * still honestly report yesterday's date here, since there is no new
 * trading session to reflect. The label says "Data as of", not "Last
 * run", specifically so this reads as current market data, not a stalled
 * automation (AD-67 made this scenario reachable in production; a prior
 * "Last cycle" label read as exactly that false alarm). */
export function TopBar() {
  const { t } = useTranslation("common");
  const { formatRelativeToNow } = useFormatters();
  const location = useLocation();
  const { data: status } = useArtifact((p) => p.getSystemStatus());

  const hasFailures = (status?.failed ?? 0) > 0;
  const titleKey = PAGE_TITLE_KEYS[location.pathname];
  const title = titleKey
    ? t(titleKey)
    : location.pathname.startsWith("/cases/")
      ? t("nav.investmentCaseDetail")
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
              {t("topbar.dataAsOf", { time: formatRelativeToNow(status.pipeline_run_date) })}
            </span>
          </>
        )}
        <LanguageToggle />
      </div>
    </header>
  );
}
