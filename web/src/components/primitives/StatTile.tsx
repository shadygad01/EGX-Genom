import type { ReactNode } from "react";
import { signOf } from "../../lib/format";
import styles from "./StatTile.module.css";

export interface StatTileProps {
  label: string;
  value: ReactNode;
  delta?: string;
  deltaSign?: number | null;
  caption?: string;
}

/** One number, labeled, with an optional signed delta -- the unit every
 * "at a glance" dashboard row (briefing, mission control, market
 * intelligence) is built from. */
export function StatTile({ label, value, delta, deltaSign, caption }: StatTileProps) {
  const sign = deltaSign === undefined ? "neutral" : signOf(deltaSign);
  return (
    <div className={styles.tile}>
      <span className={styles.label}>{label}</span>
      <div className={styles.valueRow}>
        <span className={styles.value}>{value}</span>
        {delta && <span className={`${styles.delta} ${styles[sign]}`}>{delta}</span>}
      </div>
      {caption && <span className={styles.caption}>{caption}</span>}
    </div>
  );
}
