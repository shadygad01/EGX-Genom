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
  { to: "/", label: "الملخص الذكي", icon: "◆" },
  { to: "/opportunities", label: "مركز القرارات", icon: "◎" },
  { to: "/market", label: "تحليل السوق", icon: "▤" },
  { to: "/research", label: "مركز الأبحاث", icon: "⚗" },
  { to: "/knowledge-graph", label: "خريطة المعرفة", icon: "◈" },
  { to: "/mission-control", label: "مراقبة التشغيل", icon: "⌘" },
  { to: "/sources", label: "شفافية المصادر", icon: "⛁" },
  { to: "/admin", label: "إدارة النظام", icon: "⚙" },
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
      <div className={styles.footer}>EGX30 + EGX70 · للاستخدام البحثي فقط</div>
    </nav>
  );
}
