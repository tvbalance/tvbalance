import { useState } from "react";
import { useTranslation } from "react-i18next";

import type { Tv } from "../../api/hooks";
import type { PolicyDoc } from "../../presets";
import { Button } from "../ui/button";
import { Field, Input, Switch } from "../ui/field";
import { AdvancedBudgets } from "./AdvancedBudgets";

const DEFAULT_BUDGET = 120;
const MAX_MINUTES = 24 * 60;

export function TimeTab({
  policy,
  tvs,
  onChange,
}: {
  policy: PolicyDoc;
  tvs: Tv[];
  onChange: (patch: Partial<PolicyDoc>) => void;
}) {
  const { t } = useTranslation();
  const [warning, setWarning] = useState("");
  const budget = policy.daily_budget_minutes;
  const warnings = [...policy.warn_at_minutes].sort((a, b) => b - a);

  const addWarning = () => {
    const minutes = Number(warning);
    if (!Number.isInteger(minutes) || minutes <= 0 || warnings.includes(minutes)) return;
    onChange({ warn_at_minutes: [...warnings, minutes].sort((a, b) => b - a) });
    setWarning("");
  };

  return (
    <div className="space-y-6">
      <section className="space-y-3">
        <div className="flex items-center justify-between gap-4">
          <div>
            <h3 className="font-semibold">{t("rules.budget")}</h3>
            <p className="text-sm text-muted">{t("rules.budgetHelp")}</p>
          </div>
          <Switch
            label={t("rules.budget")}
            checked={budget !== null && budget !== undefined}
            onChange={(on) => onChange({ daily_budget_minutes: on ? DEFAULT_BUDGET : null })}
          />
        </div>
        {budget !== null && budget !== undefined ? (
          <Field label={t("rules.budgetMinutes")}>
            {(props) => (
              <Input
                {...props}
                type="number"
                min={0}
                max={MAX_MINUTES}
                value={budget}
                onChange={(event) => onChange({ daily_budget_minutes: Number(event.target.value) })}
              />
            )}
          </Field>
        ) : null}
      </section>

      <section className="space-y-3">
        <h3 className="font-semibold">{t("rules.warnings")}</h3>
        <p className="text-sm text-muted">{t("rules.warningsHelp")}</p>
        <ul className="flex flex-wrap gap-2">
          {warnings.map((minutes) => (
            <li
              key={minutes}
              className="flex items-center gap-1 rounded-full border border-line py-1 pl-3 pr-1 text-sm"
            >
              {t("actions.minutes", { minutes })}
              <button
                type="button"
                aria-label={t("rules.removeWarning", { minutes })}
                className="min-h-8 min-w-8 rounded-full hover:bg-page"
                onClick={() => onChange({ warn_at_minutes: warnings.filter((m) => m !== minutes) })}
              >
                ✕
              </button>
            </li>
          ))}
        </ul>
        <div className="flex items-end gap-2">
          <div className="flex-1">
            <Field label={t("rules.warningMinutes")}>
              {(props) => (
                <Input
                  {...props}
                  type="number"
                  min={1}
                  value={warning}
                  onChange={(event) => setWarning(event.target.value)}
                />
              )}
            </Field>
          </div>
          <Button variant="secondary" onClick={addWarning}>
            {t("rules.addWarning")}
          </Button>
        </div>
      </section>

      <AdvancedBudgets policy={policy} tvs={tvs} onChange={onChange} />
    </div>
  );
}
