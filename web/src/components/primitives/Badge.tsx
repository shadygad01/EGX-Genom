import type { ReactNode } from "react";
import styles from "./Badge.module.css";

export type BadgeVariant = "positive" | "negative" | "warning" | "accent" | "neutral" | "default";

export interface BadgeProps {
  variant?: BadgeVariant;
  dot?: boolean;
  children: ReactNode;
}

/** Every status/category label in the app (health, lifecycle, severity,
 * horizon) renders through this -- one visual vocabulary for "state,"
 * never a one-off colored span per page. */
export function Badge({ variant = "default", dot, children }: BadgeProps) {
  return (
    <span className={`${styles.badge} ${styles[variant]}`}>
      {dot && <span className={styles.dot} aria-hidden="true" />}
      {children}
    </span>
  );
}
