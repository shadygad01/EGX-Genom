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

// Backend evidence strings (ResearchFinding.evidence, threaded unchanged
// into KnowledgeObject/Explanation.supporting_evidence -- see
// orchestration/pipeline.py) are internal `snake_case_key=value` notation,
// e.g. "macro_correlation=0.532" or "directional_agreement=100.00%". That's
// the right format for a value every agent/gate can parse, but it reads as
// symbol noise to a person. This only reformats each inline `key=value` it
// finds (snake_case identifier + "=" + a run of non-whitespace/comma/paren
// characters) into "Key: value" -- it never touches surrounding free text
// (a headline, a stress-test note), so a value containing spaces just
// continues as plain text right after its label.
const EVIDENCE_KEY_VALUE = /\b([a-z][a-z0-9_]*)=([^\s,)]+)/g;

// Every persisted entity's id is `<prefix>_<12 hex chars>` (see
// domain/identifiers.new_id). KnowledgeWeightedHorizonModel.predict() and
// decision_engine.py both open an evidence line with one of these ids
// (e.g. "hyp_3f2a91bc7d4e v2: ..." or "event event_a1b2c3d4e5f6: ...") --
// real provenance, but meaningless to read. This only strips/relabels the
// leading id, it never drops the rest of the line.
const KNOWLEDGE_ID_PREFIX = /^[a-z]+_[0-9a-f]{8,}\s+v\d+:\s*/i;
const EVENT_ID_PREFIX = /^event\s+[a-z]+_[0-9a-f]{8,}:\s*/i;

// decision_engine.py also opens a per-horizon evidence line with the raw
// enum value ("micro: expected_return=...").
const HORIZON_PREFIX = /^(micro|swing|investment):\s*/i;

// Anything still lower_snake_case after the passes above is a bare
// identifier value with no "key=" attached -- e.g. an event's `.subtype`
// ("large_price_move", "macro_news") appended straight after its headline.
// Requires at least one underscore so it never touches an ordinary English
// word or a value the key=value pass already turned into "Key: value".
const BARE_SNAKE_TOKEN = /\b[a-z][a-z0-9]*(?:_[a-z0-9]+)+\b/g;

export function humanizeEvidence(text: string): string {
  let result = text
    .replace(KNOWLEDGE_ID_PREFIX, "Knowledge: ")
    .replace(EVENT_ID_PREFIX, "Event: ")
    .replace(HORIZON_PREFIX, (_match, horizon: string) => `${titleCase(horizon)}: `);
  result = result.replace(EVIDENCE_KEY_VALUE, (_match, key: string, value: string) => `${titleCase(key)}: ${value}`);
  result = result.replace(BARE_SNAKE_TOKEN, (match) => titleCase(match));
  return result;
}

/** Removes exact-duplicate lines while preserving first-seen order. The Meta
 * Decision Engine concatenates each horizon prediction's full evidence list
 * (meta/decision_engine.py) -- when the same knowledge or event supports
 * more than one horizon, its evidence lines are repeated verbatim in the
 * combined Recommendation. This is purely a render-time dedupe: it drops
 * repeats, it never merges or reworded distinct evidence. */
export function dedupeEvidence(evidence: readonly string[]): string[] {
  return Array.from(new Set(evidence));
}
