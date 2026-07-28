import { useTranslation } from "react-i18next";
import { setLanguage, type SupportedLanguage } from "../../i18n";
import styles from "./LanguageToggle.module.css";

/** Switches the whole dashboard (text + layout direction) between English
 * and Arabic. Persisted to localStorage; see i18n/index.ts. */
export function LanguageToggle() {
  const { t, i18n } = useTranslation("common");
  const current = i18n.language as SupportedLanguage;

  return (
    <div className={styles.wrap} role="group" aria-label={t("language.toggleLabel")}>
      <button
        type="button"
        className={`${styles.option} ${current === "en" ? styles.optionActive : ""}`}
        onClick={() => setLanguage("en")}
        aria-pressed={current === "en"}
      >
        {t("language.en")}
      </button>
      <button
        type="button"
        className={`${styles.option} ${current === "ar" ? styles.optionActive : ""}`}
        onClick={() => setLanguage("ar")}
        aria-pressed={current === "ar"}
      >
        {t("language.ar")}
      </button>
    </div>
  );
}
