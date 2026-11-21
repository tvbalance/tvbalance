import { useTranslation } from "react-i18next";

import type { PolicyDoc } from "../../presets";
import { Button } from "../ui/button";
import { Input } from "../ui/field";
import { fromInput, toInput } from "./time";

export type Window = PolicyDoc["schedule"]["windows"][string][number];

const DEFAULT_WINDOW: Window = { start: "16:00:00", end: "20:00:00" };

/** The time windows of one day (or one special date), each with a start and an end. */
export function WindowList({
  label,
  windows,
  onChange,
}: {
  label: string;
  windows: Window[];
  onChange: (windows: Window[]) => void;
}) {
  const { t } = useTranslation();
  const edit = (index: number, patch: Partial<Window>) =>
    onChange(windows.map((w, i) => (i === index ? { ...w, ...patch } : w)));
  return (
    <div className="space-y-2">
      {windows.length === 0 ? <p className="text-sm text-muted">{t("rules.noWindows")}</p> : null}
      {windows.map((window, index) => (
        <div key={index} className="space-y-1">
          <div className="flex flex-wrap items-center gap-2">
            <Input
              type="time"
              className="w-auto"
              aria-label={t("rules.windowStart", { day: label, n: index + 1 })}
              value={toInput(window.start)}
              onChange={(event) => edit(index, { start: fromInput(event.target.value) })}
            />
            <span aria-hidden="true">–</span>
            <Input
              type="time"
              className="w-auto"
              aria-label={t("rules.windowEnd", { day: label, n: index + 1 })}
              value={toInput(window.end)}
              onChange={(event) => edit(index, { end: fromInput(event.target.value) })}
            />
            <Button
              variant="ghost"
              aria-label={t("rules.removeWindow", { day: label, n: index + 1 })}
              onClick={() => onChange(windows.filter((_, i) => i !== index))}
            >
              ✕
            </Button>
          </div>
          {window.end <= window.start ? (
            <p className="text-sm text-muted">{t("rules.overnight")}</p>
          ) : null}
        </div>
      ))}
      <Button
        variant="secondary"
        aria-label={t("rules.addWindowFor", { day: label })}
        onClick={() => onChange([...windows, DEFAULT_WINDOW])}
      >
        {t("rules.addWindow")}
      </Button>
    </div>
  );
}
