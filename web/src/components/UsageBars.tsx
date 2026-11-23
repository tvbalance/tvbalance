import { useTranslation } from "react-i18next";

import type { Usage } from "../api/hooks";
import { currentLanguage } from "../i18n";

/** One CSS bar per day, scaled to the busiest day; no charting library needed. */
export function UsageBars({ usage }: { usage: Usage }) {
  const { t } = useTranslation();
  const language = currentLanguage();
  const days = [...usage.days].sort((a, b) => a.day.localeCompare(b.day));
  const busiest = Math.max(1, ...days.map((d) => d.watched_seconds));
  const compact = days.length > 14; // too many bars to label each one
  const weekday = new Intl.DateTimeFormat(language, {
    weekday: "short",
    timeZone: "UTC",
  });
  return (
    <ul
      aria-label={t("activity.usage")}
      className={`flex h-32 items-end ${compact ? "gap-px" : "gap-2"}`}
    >
      {days.map((d) => {
        const minutes = Math.round(d.watched_seconds / 60);
        return (
          <li
            key={d.day}
            className="flex h-full flex-1 flex-col items-center justify-end gap-1"
          >
            {compact ? null : (
              <span className="text-xs text-muted">{minutes}</span>
            )}
            <div
              role="img"
              aria-label={t("activity.dayUsage", { day: d.day, minutes })}
              className="w-full rounded-t bg-brand"
              style={{
                height: `${Math.max(2, (d.watched_seconds / busiest) * 100)}%`,
              }}
            />
            {compact ? null : (
              <span className="text-xs text-muted">
                {weekday.format(new Date(`${d.day}T00:00:00Z`))}
              </span>
            )}
          </li>
        );
      })}
    </ul>
  );
}
