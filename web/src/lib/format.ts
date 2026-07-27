// Shared, presentation-only formatting -- every page must format a percent,
// a date, or a signed return the same way. No calculation happens here,
// only how an already-computed number is displayed (rounding for display
// is not "computing a value the backend didn't produce").

export function formatPercent(value: number | null | undefined, digits = 1): string {
  if (value === null || value === undefined || Number.isNaN(value)) return "—";
  return `${(value * 100).toFixed(digits)}%`;
}

export function formatSignedPercent(value: number | null | undefined, digits = 2): string {
  if (value === null || value === undefined || Number.isNaN(value)) return "—";
  const pct = value * 100;
  const sign = pct > 0 ? "+" : "";
  return `${sign}${pct.toFixed(digits)}%`;
}

export function formatNumber(value: number | null | undefined, digits = 0): string {
  if (value === null || value === undefined || Number.isNaN(value)) return "—";
  return value.toLocaleString(undefined, { maximumFractionDigits: digits, minimumFractionDigits: digits });
}

export function formatCompactNumber(value: number | null | undefined): string {
  if (value === null || value === undefined || Number.isNaN(value)) return "—";
  return Intl.NumberFormat(undefined, { notation: "compact", maximumFractionDigits: 1 }).format(value);
}

// Calendar dates translate (month names, etc.) with the active UI language;
// digit glyphs and separators stay Western ("latn" numbering system) even in
// Arabic, matching this dashboard's financial-data convention -- see
// styles/global.css's `.num` for the same rule applied to numeric figures.
const DEFAULT_LOCALE = "en-US";

export function formatDate(value: string | null | undefined, locale: string = DEFAULT_LOCALE): string {
  if (!value) return "—";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return date.toLocaleDateString(locale, {
    year: "numeric",
    month: "short",
    day: "numeric",
    numberingSystem: "latn",
  });
}

export function formatDateTime(value: string | null | undefined, locale: string = DEFAULT_LOCALE): string {
  if (!value) return "—";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return date.toLocaleString(locale, {
    year: "numeric",
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
    numberingSystem: "latn",
  });
}

export function formatRelativeToNow(value: string | null | undefined, locale: string = DEFAULT_LOCALE): string {
  if (!value) return "—";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  const rtf = new Intl.RelativeTimeFormat(locale, { numeric: "auto", numberingSystem: "latn" } as Intl.RelativeTimeFormatOptions);
  const diffMs = Date.now() - date.getTime();
  const diffMinutes = Math.round(diffMs / 60000);
  if (Math.abs(diffMinutes) < 1) return rtf.format(0, "second");
  const diffHours = Math.round(diffMinutes / 60);
  if (Math.abs(diffHours) < 1) return rtf.format(-diffMinutes, "minute");
  const diffDays = Math.round(diffHours / 24);
  if (Math.abs(diffDays) < 1) return rtf.format(-diffHours, "hour");
  return rtf.format(-diffDays, "day");
}

export function titleCase(value: string): string {
  return value
    .split(/[_\s]+/)
    .filter(Boolean)
    .map((word) => word.charAt(0).toUpperCase() + word.slice(1).toLowerCase())
    .join(" ");
}

/** Semantic direction for a signed number -- what color/badge variant a
 * return, delta, or score change should use. Presentation, not a model. */
export function signOf(value: number | null | undefined): "positive" | "negative" | "neutral" {
  if (value === null || value === undefined || Number.isNaN(value) || value === 0) return "neutral";
  return value > 0 ? "positive" : "negative";
}
