import { useTranslation } from "react-i18next";
import styles from "./Disclaimer.module.css";

/** A non-dismissible, always-visible notice on every page that shows a
 * concrete investment decision (opportunities, a portfolio, a single
 * company's thesis) -- AGX is a research scaffold, not a licensed
 * investment advisor, and its output is not a substitute for one. */
export function Disclaimer() {
  const { t } = useTranslation("common");
  return (
    <div className={styles.banner} role="note">
      <span className={styles.icon} aria-hidden="true">⚠</span>
      <span>{t("disclaimer.text")}</span>
    </div>
  );
}
