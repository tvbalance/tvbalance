import { useState } from "react";
import { useTranslation } from "react-i18next";

import type { PolicyDoc } from "../../presets";
import { Button } from "../ui/button";
import { Field, Input, Select } from "../ui/field";
import { weekdayName } from "./time";
import { WindowList, type Window } from "./WindowList";

const DAYS = [0, 1, 2, 3, 4, 5, 6];
const COPY_TARGETS: Record<string, number[]> = {
  weekdays: [0, 1, 2, 3, 4],
  weekend: [5, 6],
  all: DAYS,
};

type Schedule = PolicyDoc["schedule"];

export function ScheduleTab({
  schedule,
  onChange,
}: {
  schedule: Schedule;
  onChange: (schedule: Schedule) => void;
}) {
  const { t, i18n } = useTranslation();
  const [newDate, setNewDate] = useState("");

  const setDay = (day: number, windows: Window[]) => {
    const next = { ...schedule.windows };
    if (windows.length === 0) delete next[String(day)];
    else next[String(day)] = windows;
    onChange({ ...schedule, windows: next });
  };
  const copy = (from: number, target: string) => {
    const source = schedule.windows[String(from)] ?? [];
    const next = { ...schedule.windows };
    for (const day of COPY_TARGETS[target]) {
      if (day === from) continue;
      if (source.length === 0) delete next[String(day)];
      else next[String(day)] = source;
    }
    onChange({ ...schedule, windows: next });
  };
  const setSpecial = (date: string, windows: Window[] | null) => {
    const next = { ...schedule.special_days };
    if (windows === null) delete next[date];
    else next[date] = windows;
    onChange({ ...schedule, special_days: next });
  };

  return (
    <div className="space-y-6">
      <p className="text-sm text-muted">{t("rules.scheduleHelp")}</p>
      {DAYS.map((day) => {
        const name = weekdayName(day, i18n.language);
        return (
          <fieldset key={day} className="space-y-2 rounded-lg border border-line p-3">
            <legend className="px-1 font-medium capitalize">{name}</legend>
            <WindowList
              label={name}
              windows={schedule.windows[String(day)] ?? []}
              onChange={(windows) => setDay(day, windows)}
            />
            <Select
              aria-label={t("rules.copyFrom", { day: name })}
              value=""
              onChange={(event) => event.target.value && copy(day, event.target.value)}
            >
              <option value="">{t("rules.copyTo")}</option>
              <option value="weekdays">{t("rules.copyWeekdays")}</option>
              <option value="weekend">{t("rules.copyWeekend")}</option>
              <option value="all">{t("rules.copyAll")}</option>
            </Select>
          </fieldset>
        );
      })}

      <section aria-labelledby="special-days" className="space-y-3">
        <h3 id="special-days" className="text-lg font-semibold">
          {t("rules.specialDays")}
        </h3>
        <p className="text-sm text-muted">{t("rules.specialDaysHelp")}</p>
        {Object.entries(schedule.special_days)
          .sort(([a], [b]) => a.localeCompare(b))
          .map(([date, windows]) => (
            <fieldset key={date} className="space-y-2 rounded-lg border border-line p-3">
              <legend className="px-1 font-medium">{date}</legend>
              <WindowList label={date} windows={windows} onChange={(next) => setSpecial(date, next)} />
              <Button variant="danger" onClick={() => setSpecial(date, null)}>
                {t("rules.removeDay", { date })}
              </Button>
            </fieldset>
          ))}
        <div className="flex items-end gap-2">
          <div className="flex-1">
            <Field label={t("rules.specialDate")}>
              {(props) => (
                <Input
                  {...props}
                  type="date"
                  value={newDate}
                  onChange={(event) => setNewDate(event.target.value)}
                />
              )}
            </Field>
          </div>
          <Button
            variant="secondary"
            disabled={!newDate || newDate in schedule.special_days}
            onClick={() => {
              setSpecial(newDate, []);
              setNewDate("");
            }}
          >
            {t("rules.addSpecialDay")}
          </Button>
        </div>
      </section>
    </div>
  );
}
