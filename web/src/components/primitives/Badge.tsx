import type { ReactNode } from "react";
import styles from "./Badge.module.css";

export type BadgeVariant = "positive" | "negative" | "warning" | "accent" | "neutral" | "default";

export interface BadgeProps {
  variant?: BadgeVariant;
  dot?: boolean;
  title?: string;
  children: ReactNode;
}

/** Every status/category label in the app (health, lifecycle, severity,
 * horizon) renders through this -- one visual vocabulary for "state,"
 * never a one-off colored span per page. */
export function Badge({ variant = "default", dot, title, children }: BadgeProps) {
  return (
    <span className={`${styles.badge} ${styles[variant]}`} title={title}>
      {dot && <span className={styles.dot} aria-hidden="true" />}
      {children}
    </span>
  );
}
