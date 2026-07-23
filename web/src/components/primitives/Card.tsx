import type { ReactNode } from "react";
import styles from "./Card.module.css";

export interface CardProps {
  title?: ReactNode;
  subtitle?: ReactNode;
  actions?: ReactNode;
  dense?: boolean;
  children: ReactNode;
  className?: string;
}

/** The base surface every panel on every page is built from -- one visual
 * language for "a bounded piece of information," never a bespoke div per
 * page. */
export function Card({ title, subtitle, actions, dense, children, className }: CardProps) {
  return (
    <section className={[styles.card, dense ? styles.dense : "", className ?? ""].join(" ").trim()}>
      {(title || actions) && (
        <div className={styles.header}>
          <div className={styles.titleGroup}>
            {title && <h3 className={styles.title}>{title}</h3>}
            {subtitle && <p className={styles.subtitle}>{subtitle}</p>}
          </div>
          {actions && <div className={styles.actions}>{actions}</div>}
        </div>
      )}
      {children}
    </section>
  );
}
