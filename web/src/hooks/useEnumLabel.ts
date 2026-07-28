import { useTranslation } from "react-i18next";
import { titleCase } from "../lib/format";

/** Translates a closed-vocabulary backend enum value (status, severity,
 * horizon, stage name, ...) via `common.json`'s `enums.<category>.<value>`
 * key, falling back to the existing English `titleCase()` behavior when no
 * translation is registered -- so an enum this dashboard hasn't explicitly
 * covered yet degrades to readable English instead of a raw/missing key or
 * a fabricated guess at an Arabic term. Free-form backend-generated text
 * (explanations, headlines, notes) never goes through this -- only a
 * genuinely closed set of values declared in web/src/types.ts. */
export function useEnumLabel() {
  const { t, i18n } = useTranslation("common");
  return (category: string, value: string | null | undefined): string => {
    if (!value) return "—";
    if (i18n.language !== "ar") return titleCase(value);
    // Backend enums aren't uniformly cased (most are lowercase Python Enum
    // values; a few plain-`str` fields like financial-statement period/
    // statement type are upper snake case) -- normalize so one dictionary
    // key set covers both without duplicating entries per casing.
    return t(`enums.${category}.${value.toLowerCase()}`, { defaultValue: titleCase(value) });
  };
}
