import i18n from "i18next";
import LanguageDetector from "i18next-browser-languagedetector";
import { initReactI18next } from "react-i18next";

import de from "./locales/de.json";
import en from "./locales/en.json";
import es from "./locales/es.json";
import fr from "./locales/fr.json";
import it from "./locales/it.json";

export const SUPPORTED_LANGUAGES = ["en", "it", "de", "fr", "es"] as const;

export type Language = (typeof SUPPORTED_LANGUAGES)[number];

/** Each language in its own name, so it can be found whatever the current one is. */
export const LANGUAGE_NAMES: Record<Language, string> = {
  en: "English",
  it: "Italiano",
  de: "Deutsch",
  fr: "Français",
  es: "Español",
};

/** The supported language closest to what i18next detected (e.g. "it-IT" gives "it"). */
export function currentLanguage(): Language {
  const base = i18n.language.slice(0, 2) as Language;
  return SUPPORTED_LANGUAGES.includes(base) ? base : "en";
}

void i18n
  .use(LanguageDetector)
  .use(initReactI18next)
  .init({
    resources: {
      en: { translation: en },
      it: { translation: it },
      de: { translation: de },
      fr: { translation: fr },
      es: { translation: es },
    },
    fallbackLng: "en",
    supportedLngs: [...SUPPORTED_LANGUAGES],
    nonExplicitSupportedLngs: true,
    interpolation: { escapeValue: false },
    detection: { order: ["localStorage", "navigator"], caches: ["localStorage"] },
  });

export default i18n;
