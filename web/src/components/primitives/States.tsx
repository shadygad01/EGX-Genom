import { useTranslation } from "react-i18next";
import styles from "./States.module.css";

export interface EmptyStateProps {
  title: string;
  detail?: string;
  icon?: string;
}

/** Nothing to show yet -- an honest "no data," never a fabricated placeholder. */
export function EmptyState({ title, detail, icon = "○" }: EmptyStateProps) {
  return (
    <div className={styles.state} role="status">
      <span className={styles.icon} aria-hidden="true">{icon}</span>
      <span className={styles.title}>{title}</span>
      {detail && <span className={styles.detail}>{detail}</span>}
    </div>
  );
}

export interface ErrorStateProps {
  title?: string;
  detail?: string;
  onRetry?: () => void;
}

export function ErrorState({ title, detail, onRetry }: ErrorStateProps) {
  const { t } = useTranslation("common");
  return (
    <div className={styles.state} role="alert">
      <span className={styles.icon} aria-hidden="true">⚠</span>
      <span className={styles.errorTitle}>{title ?? t("states.somethingWrong")}</span>
      {detail && <span className={styles.detail}>{detail}</span>}
      {onRetry && (
        <button type="button" onClick={onRetry} className={styles.retryButton}>
          {t("states.retry")}
        </button>
      )}
    </div>
  );
}

export interface LoadingStateProps {
  label?: string;
  rows?: number;
}

/** Skeleton block(s), not a spinner -- preserves layout while data loads. */
export function LoadingState({ label, rows = 3 }: LoadingStateProps) {
  const { t } = useTranslation("common");
  return (
    <div className={styles.skeletonWrap} role="status" aria-label={label ?? t("states.loading")}>
      {Array.from({ length: rows }, (_, i) => (
        <div key={i} className={styles.skeletonBlock} style={{ height: "1.5rem" }} />
      ))}
    </div>
  );
}
