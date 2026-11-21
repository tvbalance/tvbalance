import { useTranslation } from "react-i18next";

import { LANGUAGE_NAMES, SUPPORTED_LANGUAGES, type Language } from "../i18n";
import { Field, Select } from "./ui/field";

/** The browser's own time zone, the best default for a family at home. */
export function browserTimezone(): string {
  return Intl.DateTimeFormat().resolvedOptions().timeZone || "UTC";
}

function timezones(selected: string): string[] {
  const all =
    typeof Intl.supportedValuesOf === "function" ? Intl.supportedValuesOf("timeZone") : [];
  return all.includes(selected) ? all : [selected, ...all];
}

export function RegionFields({
  language,
  timezone,
  onLanguage,
  onTimezone,
}: {
  language: Language;
  timezone: string;
  onLanguage: (language: Language) => void;
  onTimezone: (timezone: string) => void;
}) {
  const { t } = useTranslation();
  return (
    <>
      <Field label={t("region.language")}>
        {(props) => (
          <Select
            {...props}
            value={language}
            onChange={(event) => onLanguage(event.target.value as Language)}
          >
            {SUPPORTED_LANGUAGES.map((code) => (
              <option key={code} value={code} lang={code}>
                {LANGUAGE_NAMES[code]}
              </option>
            ))}
          </Select>
        )}
      </Field>
      <Field label={t("region.timezone")} hint={t("region.timezoneHint")}>
        {(props) => (
          <Select {...props} value={timezone} onChange={(event) => onTimezone(event.target.value)}>
            {timezones(timezone).map((zone) => (
              <option key={zone} value={zone}>
                {zone}
              </option>
            ))}
          </Select>
        )}
      </Field>
    </>
  );
}
