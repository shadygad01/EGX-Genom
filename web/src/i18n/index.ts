import i18n from "i18next";
import { initReactI18next } from "react-i18next";

import arCommon from "./locales/ar/common.json";
import arCioDesk from "./locales/ar/cioDesk.json";
import arPortfolio from "./locales/ar/portfolio.json";
import arInvestmentCases from "./locales/ar/investmentCases.json";
import arMonitoring from "./locales/ar/monitoring.json";
import arSettings from "./locales/ar/settings.json";
import arMarketIntelligence from "./locales/ar/marketIntelligence.json";
import arResearchCenter from "./locales/ar/researchCenter.json";
import arKnowledgeGraph from "./locales/ar/knowledgeGraph.json";
import arSourceIntelligence from "./locales/ar/sourceIntelligence.json";

import enCommon from "./locales/en/common.json";
import enCioDesk from "./locales/en/cioDesk.json";
import enPortfolio from "./locales/en/portfolio.json";
import enInvestmentCases from "./locales/en/investmentCases.json";
import enMonitoring from "./locales/en/monitoring.json";
import enSettings from "./locales/en/settings.json";
import enMarketIntelligence from "./locales/en/marketIntelligence.json";
import enResearchCenter from "./locales/en/researchCenter.json";
import enKnowledgeGraph from "./locales/en/knowledgeGraph.json";
import enSourceIntelligence from "./locales/en/sourceIntelligence.json";

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
    cioDesk: enCioDesk,
    portfolio: enPortfolio,
    investmentCases: enInvestmentCases,
    monitoring: enMonitoring,
    settings: enSettings,
    marketIntelligence: enMarketIntelligence,
    researchCenter: enResearchCenter,
    knowledgeGraph: enKnowledgeGraph,
    sourceIntelligence: enSourceIntelligence,
  },
  ar: {
    common: arCommon,
    cioDesk: arCioDesk,
    portfolio: arPortfolio,
    investmentCases: arInvestmentCases,
    monitoring: arMonitoring,
    settings: arSettings,
    marketIntelligence: arMarketIntelligence,
    researchCenter: arResearchCenter,
    knowledgeGraph: arKnowledgeGraph,
    sourceIntelligence: arSourceIntelligence,
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
