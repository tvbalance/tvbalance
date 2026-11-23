import type { TFunction } from "i18next";
import { useTranslation } from "react-i18next";

import type { EngineEvent, Tv } from "../api/hooks";
import { currentLanguage } from "../i18n";

const KNOWN = [
  "time_warning",
  "blocked",
  "redirected",
  "powered_off",
  "enforcement_paused",
  "enforcement_unavailable",
  "tv_reachable",
  "tv_unreachable",
  "pairing_lost",
  "tv_added",
  "tv_paired",
  "license_changed",
  "weekly_report",
];

/** Turns a stored event into one readable sentence; unknown types fall back to the raw type. */
export function describeEvent(t: TFunction, event: EngineEvent): string {
  if (!KNOWN.includes(event.type)) return event.type;
  const p = event.payload;
  const reason = typeof p.reason === "string" ? t(`tv.reason.${p.reason}`, { defaultValue: p.reason }) : "";
  const limit = typeof p.limit === "string" ? t(`tv.limit.${p.limit}`, { defaultValue: "" }) : "";
  return t(`activity.event.${event.type}`, { reason, limit, minutes: p.minutes_left ?? "" });
}

export function EventList({ events, tvs }: { events: EngineEvent[]; tvs: Tv[] }) {
  const { t } = useTranslation();
  const format = new Intl.DateTimeFormat(currentLanguage(), { dateStyle: "short", timeStyle: "short" });
  if (events.length === 0) return <p className="text-muted">{t("activity.noEvents")}</p>;
  return (
    <ul className="divide-y divide-line">
      {events.map((event) => (
        <li key={event.id} className="flex flex-wrap items-baseline gap-x-3 py-2 text-sm">
          <time dateTime={event.occurred_at} className="text-muted">
            {format.format(new Date(event.occurred_at))}
          </time>
          {event.tv_id ? (
            <span className="font-medium">{tvs.find((tv) => tv.id === event.tv_id)?.name ?? event.tv_id}</span>
          ) : null}
          <span>{describeEvent(t, event)}</span>
        </li>
      ))}
    </ul>
  );
}
