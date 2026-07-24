import styles from "./Meter.module.css";

export interface MeterProps {
  value: number; // 0-1
  variant?: "positive" | "negative" | "warning" | "accent" | "neutral";
  label?: string;
}

/** A confidence/score bar -- the visual unit for "how sure is AGX," reused
 * across Opportunity Center, Research Center, and Source Intelligence. */
export function Meter({ value, variant = "accent", label }: MeterProps) {
  const clamped = Math.max(0, Math.min(1, value));
  return (
    <div className={styles.wrap}>
      <div className={styles.track} role="progressbar" aria-valuenow={Math.round(clamped * 100)} aria-valuemin={0} aria-valuemax={100}>
        <div className={`${styles.fill} ${styles[variant]}`} style={{ width: `${clamped * 100}%` }} />
      </div>
      {label !== undefined && <span className={styles.label}>{label}</span>}
    </div>
  );
}
