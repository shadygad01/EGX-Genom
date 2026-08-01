import { NavLink } from "react-router-dom";
import { useTranslation } from "react-i18next";
import styles from "./Sidebar.module.css";

interface NavItem {
  to: string;
  labelKey: string;
  icon: string;
}

// The 9 sections, in the mission's canonical order -- AI Briefing is the
// landing page (index route), everything else is a first-class nav entry.
const NAV_ITEMS: NavItem[] = [
  { to: "/", labelKey: "nav.aiBriefing", icon: "◆" },
  { to: "/decisions", labelKey: "nav.decisionCenter", icon: "⚖" },
  { to: "/opportunities", labelKey: "nav.opportunityCenter", icon: "◎" },
  { to: "/market", labelKey: "nav.marketIntelligence", icon: "▤" },
  { to: "/research", labelKey: "nav.researchCenter", icon: "⚗" },
  { to: "/knowledge-graph", labelKey: "nav.knowledgeGraph", icon: "◈" },
  { to: "/mission-control", labelKey: "nav.missionControl", icon: "⌘" },
  { to: "/sources", labelKey: "nav.sourceIntelligence", icon: "⛁" },
  { to: "/admin", labelKey: "nav.systemAdministration", icon: "⚙" },
];

export function Sidebar() {
  const { t } = useTranslation("common");
  return (
    <nav className={styles.sidebar} aria-label={t("a11y.mainNavigation")}>
      <div className={styles.brand}>
        <span className={styles.brandMark} aria-hidden="true">A</span>
        <span className={styles.brandText}>{t("app.brand")}</span>
      </div>
      <div className={styles.nav}>
        {NAV_ITEMS.map((item) => (
          <NavLink
            key={item.to}
            to={item.to}
            end={item.to === "/"}
            className={({ isActive }) => `${styles.link} ${isActive ? styles.linkActive : ""}`}
          >
            <span className={styles.icon} aria-hidden="true">{item.icon}</span>
            {t(item.labelKey)}
          </NavLink>
        ))}
      </div>
      <div className={styles.footer}>{t("app.footer")}</div>
    </nav>
  );
}
