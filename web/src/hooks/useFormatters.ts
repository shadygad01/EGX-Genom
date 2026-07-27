import { useTranslation } from "react-i18next";
import { formatDate, formatDateTime, formatRelativeToNow } from "../lib/format";

const LOCALE_BY_LANGUAGE: Record<string, string> = {
  en: "en-US",
  ar: "ar-EG",
};

/** Locale-bound versions of the calendar-date formatters in lib/format.ts,
 * so month names (etc.) follow the active UI language. Numeric/percent
 * formatters are deliberately NOT here -- digit glyphs stay Western in
 * every language, per this dashboard's financial-data convention, so
 * those keep using lib/format.ts's plain functions directly. */
export function useFormatters() {
  const { i18n } = useTranslation();
  const locale = LOCALE_BY_LANGUAGE[i18n.language] ?? "en-US";

  return {
    formatDate: (value: string | null | undefined) => formatDate(value, locale),
    formatDateTime: (value: string | null | undefined) => formatDateTime(value, locale),
    formatRelativeToNow: (value: string | null | undefined) => formatRelativeToNow(value, locale),
  };
}
