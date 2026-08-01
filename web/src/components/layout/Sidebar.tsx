import { NavLink } from "react-router-dom";
import { useTranslation } from "react-i18next";
import styles from "./Sidebar.module.css";

interface NavItem {
  to: string;
  labelKey: string;
  icon: string;
}

// The 7-item Institutional Investment Operating System hierarchy, in
// investment-workflow order: decision first (CIO Desk), then portfolio
// state, then the evidence behind any one company, then what changed,
// then the wider environment, then internal research capability (never
// the default destination), then system configuration. Knowledge Graph
// and Source Intelligence remain real routes but are deliberately not
// top-level nav items -- they're reachable from Research (see
// ResearchCenter's "More Research Tools" links) since they're deeper
// internal-capability views, not investment-workflow destinations.
const NAV_ITEMS: NavItem[] = [
  { to: "/", labelKey: "nav.cioDesk", icon: "◆" },
  { to: "/portfolio", labelKey: "nav.portfolio", icon: "▣" },
  { to: "/cases", labelKey: "nav.investmentCases", icon: "◎" },
  { to: "/monitoring", labelKey: "nav.monitoring", icon: "◉" },
  { to: "/market", labelKey: "nav.market", icon: "▤" },
  { to: "/research", labelKey: "nav.research", icon: "⚗" },
  { to: "/settings", labelKey: "nav.settings", icon: "⚙" },
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
