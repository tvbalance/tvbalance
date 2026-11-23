import { useTranslation } from "react-i18next";

import { useInventory, useLicense, useMe, type Tv } from "../../api/hooks";
import type { PolicyDoc } from "../../presets";
import { Button } from "../ui/button";
import { Field, Input, Switch } from "../ui/field";
import { IdList } from "./IdList";
import { weekdayName } from "./time";

const MAX_MINUTES = 24 * 60;
const DEFAULT_GROUP_MINUTES = 60;
const DEFAULT_ROLLOVER = 30;

type Group = NonNullable<PolicyDoc["app_budgets"]>[number];

/** Per-weekday budgets, app-group allowances and rollover: the Pro part of the Time tab. */
export function AdvancedBudgets({
  policy,
  tvs,
  onChange,
}: {
  policy: PolicyDoc;
  tvs: Tv[];
  onChange: (patch: Partial<PolicyDoc>) => void;
}) {
  const { t, i18n } = useTranslation();
  const me = useMe();
  const license = useLicense(me.data?.scopes.includes("admin") ?? false);
  const inventory = useInventory(tvs[0]?.id ?? null);
  const apps = (inventory.data?.apps ?? []).map((app) => ({
    id: app.id,
    label: app.name,
    icon: app.has_icon ? `api/v1/tvs/${tvs[0]?.id}/apps/${encodeURIComponent(app.id)}/icon` : undefined,
  }));

  const weekdays = policy.weekday_budget_minutes ?? {};
  const groups = policy.app_budgets ?? [];
  const rollover = policy.rollover_max_minutes;

  const setWeekday = (day: number, raw: string) => {
    const next = { ...weekdays };
    if (raw === "") delete next[day];
    else next[day] = Number(raw);
    onChange({ weekday_budget_minutes: next });
  };
  const setGroup = (index: number, patch: Partial<Group>) =>
    onChange({ app_budgets: groups.map((group, i) => (i === index ? { ...group, ...patch } : group)) });

  return (
    <div className="space-y-6">
      <div>
        <h3 className="font-semibold">{t("rules.advancedBudgets")}</h3>
        <p className="text-sm text-muted">{t("rules.advancedBudgetsHelp")}</p>
        {license.data?.tier === "free" ? (
          <p role="status" className="text-sm text-warn">
            {t("rules.advancedBudgetsPro")}
          </p>
        ) : null}
      </div>

      <section className="space-y-3">
        <h4 className="text-sm font-medium">{t("rules.weekdayBudgets")}</h4>
        <p className="text-sm text-muted">{t("rules.weekdayBudgetsHelp")}</p>
        <div className="grid gap-3 sm:grid-cols-2">
          {[0, 1, 2, 3, 4, 5, 6].map((day) => (
            <Field key={day} label={t("rules.weekdayBudget", { day: weekdayName(day, i18n.language) })}>
              {(props) => (
                <Input
                  {...props}
                  type="number"
                  min={0}
                  max={MAX_MINUTES}
                  placeholder={t("rules.sameAsDaily")}
                  value={weekdays[day] ?? ""}
                  onChange={(event) => setWeekday(day, event.target.value)}
                />
              )}
            </Field>
          ))}
        </div>
      </section>

      <section className="space-y-3">
        <h4 className="text-sm font-medium">{t("rules.appGroups")}</h4>
        <p className="text-sm text-muted">{t("rules.appGroupsHelp")}</p>
        {groups.map((group, index) => (
          <div key={index} className="space-y-3 rounded-lg border border-line p-3">
            <div className="grid gap-3 sm:grid-cols-2">
              <Field label={t("rules.groupName")}>
                {(props) => (
                  <Input
                    {...props}
                    value={group.name}
                    maxLength={40}
                    onChange={(event) => setGroup(index, { name: event.target.value })}
                  />
                )}
              </Field>
              <Field label={t("rules.groupMinutes")}>
                {(props) => (
                  <Input
                    {...props}
                    type="number"
                    min={0}
                    max={MAX_MINUTES}
                    value={group.minutes}
                    onChange={(event) => setGroup(index, { minutes: Number(event.target.value) })}
                  />
                )}
              </Field>
            </div>
            <IdList
              label={t("rules.groupApps", { name: group.name })}
              value={group.apps}
              choices={apps}
              onChange={(next) => setGroup(index, { apps: next })}
            />
            <Button
              variant="secondary"
              onClick={() => onChange({ app_budgets: groups.filter((_, i) => i !== index) })}
            >
              {t("rules.removeGroup", { name: group.name })}
            </Button>
          </div>
        ))}
        <Button
          variant="secondary"
          onClick={() =>
            onChange({
              app_budgets: [
                ...groups,
                { name: t("rules.newGroupName", { n: groups.length + 1 }), apps: [], minutes: DEFAULT_GROUP_MINUTES },
              ],
            })
          }
        >
          {t("rules.addGroup")}
        </Button>
      </section>

      <section className="space-y-3">
        <div className="flex items-center justify-between gap-4">
          <div>
            <h4 className="text-sm font-medium">{t("rules.rollover")}</h4>
            <p className="text-sm text-muted">{t("rules.rolloverHelp")}</p>
          </div>
          <Switch
            label={t("rules.rollover")}
            checked={rollover !== null && rollover !== undefined}
            onChange={(on) => onChange({ rollover_max_minutes: on ? DEFAULT_ROLLOVER : null })}
          />
        </div>
        {rollover !== null && rollover !== undefined ? (
          <Field label={t("rules.rolloverMax")}>
            {(props) => (
              <Input
                {...props}
                type="number"
                min={0}
                max={MAX_MINUTES}
                value={rollover}
                onChange={(event) => onChange({ rollover_max_minutes: Number(event.target.value) })}
              />
            )}
          </Field>
        ) : null}
      </section>
    </div>
  );
}
