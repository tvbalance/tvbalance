import { useTranslation } from "react-i18next";

import type { PolicyDoc } from "../../presets";
import { Field, Input } from "../ui/field";

type Escalation = PolicyDoc["escalation"];

const FIELDS: { key: keyof Escalation; min: number }[] = [
  { key: "debounce", min: 0 },
  { key: "grace", min: 0 },
  { key: "power_off_cap", min: 1 },
  { key: "cap_window", min: 1 },
  { key: "cap_pause", min: 1 },
  { key: "message_repeat", min: 1 },
];

/** How firmly the Engine enforces a block; the defaults suit nearly everyone. */
export function AdvancedTab({
  escalation,
  onChange,
}: {
  escalation: Escalation;
  onChange: (escalation: Escalation) => void;
}) {
  const { t } = useTranslation();
  return (
    <div className="space-y-4">
      <p className="text-sm text-muted">{t("rules.advancedHelp")}</p>
      {FIELDS.map(({ key, min }) => (
        <Field key={key} label={t(`rules.escalation.${key}`)} hint={t(`rules.escalation.${key}Help`)}>
          {(props) => (
            <Input
              {...props}
              type="number"
              min={min}
              value={escalation[key]}
              onChange={(event) => onChange({ ...escalation, [key]: Number(event.target.value) })}
            />
          )}
        </Field>
      ))}
    </div>
  );
}
