import { useState } from "react";
import { useTranslation } from "react-i18next";

import { Button } from "../ui/button";
import { Field, Input, Select } from "../ui/field";

export interface Choice {
  id: string;
  label: string;
  /** A same-origin URL for an icon, when the TV has one. */
  icon?: string;
}

function Icon({ choice }: { choice: Choice }) {
  const [broken, setBroken] = useState(false);
  if (choice.icon && !broken) {
    return (
      <img
        src={choice.icon}
        alt=""
        className="size-6 rounded"
        onError={() => setBroken(true)}
      />
    );
  }
  return (
    <span
      aria-hidden="true"
      className="flex size-6 items-center justify-center rounded bg-page text-xs font-semibold"
    >
      {choice.label.slice(0, 1).toUpperCase()}
    </span>
  );
}

/**
 * A list of ids (apps, inputs or channels) shown with their names when the TV's inventory is
 * known. Ids the inventory does not know are still listed, and new ones can be typed when
 * there is no inventory (the TV is offline).
 */
export function IdList({
  label,
  value,
  choices,
  onChange,
}: {
  label: string;
  value: string[];
  choices: Choice[];
  onChange: (value: string[]) => void;
}) {
  const { t } = useTranslation();
  const [typed, setTyped] = useState("");
  const byId = new Map(choices.map((choice) => [choice.id, choice]));
  const available = choices.filter((choice) => !value.includes(choice.id));

  const add = (id: string) => {
    const clean = id.trim();
    if (clean && !value.includes(clean)) onChange([...value, clean]);
  };

  return (
    <div className="space-y-2">
      <h4 className="text-sm font-medium">{label}</h4>
      {value.length === 0 ? <p className="text-sm text-muted">{t("rules.listEmpty")}</p> : null}
      <ul className="flex flex-wrap gap-2">
        {value.map((id) => {
          const choice = byId.get(id) ?? { id, label: id };
          return (
            <li
              key={id}
              className="flex items-center gap-2 rounded-full border border-line py-1 pl-2 pr-1 text-sm"
            >
              <Icon choice={choice} />
              {choice.label}
              <button
                type="button"
                aria-label={t("rules.removeItem", { name: choice.label })}
                className="min-h-8 min-w-8 rounded-full hover:bg-page"
                onClick={() => onChange(value.filter((other) => other !== id))}
              >
                ✕
              </button>
            </li>
          );
        })}
      </ul>
      {available.length > 0 ? (
        <Select
          aria-label={t("rules.addTo", { list: label })}
          value=""
          onChange={(event) => event.target.value && add(event.target.value)}
        >
          <option value="">{t("rules.addPlaceholder")}</option>
          {available.map((choice) => (
            <option key={choice.id} value={choice.id}>
              {choice.label}
            </option>
          ))}
        </Select>
      ) : null}
      <div className="flex items-end gap-2">
        <div className="flex-1">
          <Field label={t("rules.addById", { list: label })}>
            {(props) => (
              <Input {...props} value={typed} onChange={(event) => setTyped(event.target.value)} />
            )}
          </Field>
        </div>
        <Button
          variant="secondary"
          disabled={typed.trim() === ""}
          onClick={() => {
            add(typed);
            setTyped("");
          }}
        >
          {t("rules.add")}
        </Button>
      </div>
    </div>
  );
}
