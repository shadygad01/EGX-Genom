import type { ReactNode } from "react";
import styles from "./Section.module.css";

export interface SectionProps {
  title: string;
  description?: string;
  actions?: ReactNode;
  children: ReactNode;
}

/** Page-level grouping with a heading -- distinct from Card (a bounded
 * panel): a Section groups one or more Cards under one business question. */
export function Section({ title, description, actions, children }: SectionProps) {
  return (
    <section className={styles.section}>
      <div className={styles.header}>
        <div className={styles.headerText}>
          <h2 className={styles.title}>{title}</h2>
          {description && <p className={styles.description}>{description}</p>}
        </div>
        {actions && <div className={styles.actions}>{actions}</div>}
      </div>
      {children}
    </section>
  );
}
