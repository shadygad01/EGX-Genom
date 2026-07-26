import { NavLink } from "react-router-dom";
import styles from "./Sidebar.module.css";

interface NavItem {
  to: string;
  label: string;
  icon: string;
}

// The 9 sections, in the mission's canonical order -- AI Briefing is the
// landing page (index route), everything else is a first-class nav entry.
const NAV_ITEMS: NavItem[] = [
  { to: "/", label: "AI Briefing", icon: "◆" },
  { to: "/opportunities", label: "Opportunity Center", icon: "◎" },
  { to: "/market", label: "Market Intelligence", icon: "▤" },
  { to: "/research", label: "Research Center", icon: "⚗" },
  { to: "/knowledge-graph", label: "Knowledge Graph", icon: "◈" },
  { to: "/mission-control", label: "Mission Control", icon: "⌘" },
  { to: "/sources", label: "Source Intelligence", icon: "⛁" },
  { to: "/admin", label: "System Administration", icon: "⚙" },
];

export function Sidebar() {
  return (
    <nav className={styles.sidebar} aria-label="Main navigation">
      <div className={styles.brand}>
        <span className={styles.brandMark} aria-hidden="true">A</span>
        <span className={styles.brandText}>AGX Research</span>
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
            {item.label}
          </NavLink>
        ))}
      </div>
      <div className={styles.footer}>EGX30 + EGX70 · Research Only</div>
    </nav>
  );
}
