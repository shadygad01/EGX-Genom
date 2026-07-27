import i18n from "i18next";
import { initReactI18next } from "react-i18next";

import arCommon from "./locales/ar/common.json";
import arAiBriefing from "./locales/ar/aiBriefing.json";
import arOpportunityCenter from "./locales/ar/opportunityCenter.json";
import arCompanyWorkspace from "./locales/ar/companyWorkspace.json";
import arMarketIntelligence from "./locales/ar/marketIntelligence.json";
import arResearchCenter from "./locales/ar/researchCenter.json";
import arKnowledgeGraph from "./locales/ar/knowledgeGraph.json";
import arMissionControl from "./locales/ar/missionControl.json";
import arSourceIntelligence from "./locales/ar/sourceIntelligence.json";
import arSystemAdministration from "./locales/ar/systemAdministration.json";

import enCommon from "./locales/en/common.json";
import enAiBriefing from "./locales/en/aiBriefing.json";
import enOpportunityCenter from "./locales/en/opportunityCenter.json";
import enCompanyWorkspace from "./locales/en/companyWorkspace.json";
import enMarketIntelligence from "./locales/en/marketIntelligence.json";
import enResearchCenter from "./locales/en/researchCenter.json";
import enKnowledgeGraph from "./locales/en/knowledgeGraph.json";
import enMissionControl from "./locales/en/missionControl.json";
import enSourceIntelligence from "./locales/en/sourceIntelligence.json";
import enSystemAdministration from "./locales/en/systemAdministration.json";

export const SUPPORTED_LANGUAGES = ["en", "ar"] as const;
export type SupportedLanguage = (typeof SUPPORTED_LANGUAGES)[number];

export const LANGUAGE_STORAGE_KEY = "agx-language";

export const RTL_LANGUAGES: SupportedLanguage[] = ["ar"];

export function directionFor(language: string): "rtl" | "ltr" {
  return RTL_LANGUAGES.includes(language as SupportedLanguage) ? "rtl" : "ltr";
}

function detectInitialLanguage(): SupportedLanguage {
  if (typeof window === "undefined") return "en";
  const stored = window.localStorage.getItem(LANGUAGE_STORAGE_KEY);
  if (stored === "en" || stored === "ar") return stored;
  return navigator.language?.toLowerCase().startsWith("ar") ? "ar" : "en";
}

const resources = {
  en: {
    common: enCommon,
    aiBriefing: enAiBriefing,
    opportunityCenter: enOpportunityCenter,
    companyWorkspace: enCompanyWorkspace,
    marketIntelligence: enMarketIntelligence,
    researchCenter: enResearchCenter,
    knowledgeGraph: enKnowledgeGraph,
    missionControl: enMissionControl,
    sourceIntelligence: enSourceIntelligence,
    systemAdministration: enSystemAdministration,
  },
  ar: {
    common: arCommon,
    aiBriefing: arAiBriefing,
    opportunityCenter: arOpportunityCenter,
    companyWorkspace: arCompanyWorkspace,
    marketIntelligence: arMarketIntelligence,
    researchCenter: arResearchCenter,
    knowledgeGraph: arKnowledgeGraph,
    missionControl: arMissionControl,
    sourceIntelligence: arSourceIntelligence,
    systemAdministration: arSystemAdministration,
  },
};

void i18n.use(initReactI18next).init({
  resources,
  lng: detectInitialLanguage(),
  fallbackLng: "en",
  defaultNS: "common",
  ns: Object.keys(resources.en),
  interpolation: { escapeValue: false },
  returnNull: false,
});

if (typeof document !== "undefined") {
  const applyDocumentDirection = (language: string) => {
    document.documentElement.lang = language;
    document.documentElement.dir = directionFor(language);
  };
  applyDocumentDirection(i18n.language);
  i18n.on("languageChanged", applyDocumentDirection);
}

export function setLanguage(language: SupportedLanguage): void {
  void i18n.changeLanguage(language);
  if (typeof window !== "undefined") {
    window.localStorage.setItem(LANGUAGE_STORAGE_KEY, language);
  }
}

export default i18n;
