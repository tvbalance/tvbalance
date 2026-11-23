import type { TFunction } from "i18next";
import { useTranslation } from "react-i18next";

import {
  useContentUsage,
  useInventory,
  useWeeklyReport,
  type Inventory,
  type WeeklyReport as Report,
} from "../api/hooks";
import { ApiError } from "../api/http";
import { currentLanguage } from "../i18n";
import { UsageBars } from "./UsageBars";
import { Card } from "./ui/card";

const TOP = 8;

/** The name the TV gives an app, input or channel; the raw id when the TV is unreachable. */
function contentName(
  inventory: Inventory | undefined,
  kind: string,
  id: string,
): string {
  if (kind === "app")
    return inventory?.apps.find((app) => app.id === id)?.name ?? id;
  if (kind === "input")
    return inventory?.inputs.find((input) => input.id === id)?.label ?? id;
  return inventory?.channels.find((channel) => channel.id === id)?.name ?? id;
}

function duration(t: TFunction, seconds: number): string {
  const minutes = Math.round(seconds / 60);
  return t("activity.duration", {
    h: Math.floor(minutes / 60),
    m: minutes % 60,
  });
}

/** The most watched apps, inputs and channels of one TV, as proportional bars. */
export function ContentBars({ tvId, days }: { tvId: string; days: number }) {
  const { t } = useTranslation();
  const used = useContentUsage(tvId, days);
  const inventory = useInventory(tvId);
  const items = (used.data?.items ?? []).slice(0, TOP);
  if (!used.data) return null;
  if (items.length === 0)
    return <p className="text-sm text-muted">{t("activity.noContent")}</p>;
  const busiest = Math.max(1, ...items.map((item) => item.seconds));
  return (
    <div className="space-y-2">
      <h3 className="text-sm font-medium">{t("activity.content")}</h3>
      <ul className="space-y-2">
        {items.map((item) => {
          const name = contentName(inventory.data, item.kind, item.id);
          const minutes = Math.round(item.seconds / 60);
          return (
            <li key={`${item.kind}:${item.id}`} className="space-y-1 text-sm">
              <div className="flex justify-between gap-2">
                <span className="truncate">{name}</span>
                <span className="text-muted">
                  {t("activity.minutesShort", { minutes })}
                </span>
              </div>
              <div
                role="img"
                aria-label={t("activity.contentMinutes", { name, minutes })}
                className="h-1.5 rounded bg-brand"
                style={{
                  width: `${Math.max(2, (item.seconds / busiest) * 100)}%`,
                }}
              />
            </li>
          );
        })}
      </ul>
    </div>
  );
}

function TvReport({ tv }: { tv: Report["tvs"][number] }) {
  const { t } = useTranslation();
  const inventory = useInventory(tv.tv_id);
  const usage = {
    tv_id: tv.tv_id,
    limited: false,
    days: tv.days.map((d) => ({
      day: d.day,
      watched_seconds: d.seconds,
      bonus_minutes: 0,
    })),
  };
  return (
    <Card className="space-y-3">
      <h3 className="text-lg font-semibold">{tv.tv_name}</h3>
      <p>
        {t("activity.report.total", {
          duration: duration(t, tv.total_seconds),
        })}
        {" · "}
        {t("activity.report.blocks", { blocks: tv.blocks })}
      </p>
      <UsageBars usage={usage} />
      {tv.top_content.length > 0 ? (
        <ul className="text-sm">
          {tv.top_content.map((item) => (
            <li
              key={`${item.kind}:${item.id}`}
              className="flex justify-between gap-2"
            >
              <span className="truncate">
                {contentName(inventory.data, item.kind, item.id)}
              </span>
              <span className="text-muted">{duration(t, item.seconds)}</span>
            </li>
          ))}
        </ul>
      ) : null}
    </Card>
  );
}

/** How much each TV was watched last week; a Pro feature, so the Free plan sees a notice. */
export function WeeklyReport() {
  const { t } = useTranslation();
  const report = useWeeklyReport();
  if (report.isPending) return <p role="status">{t("auth.loading")}</p>;
  if (
    report.error instanceof ApiError &&
    report.error.code === "requires_pro"
  ) {
    return (
      <p role="status" className="text-sm text-warn">
        {t("activity.report.requiresPro")}
      </p>
    );
  }
  if (!report.data) return <p role="alert">{t("auth.error")}</p>;
  const day = new Intl.DateTimeFormat(currentLanguage(), {
    dateStyle: "medium",
    timeZone: "UTC",
  });
  const first = day.format(new Date(`${report.data.first}T00:00:00Z`));
  const last = day.format(new Date(`${report.data.last}T00:00:00Z`));
  return (
    <div className="space-y-3">
      <p className="text-sm text-muted">{`${first} – ${last}`}</p>
      <div className="grid gap-3 md:grid-cols-2">
        {report.data.tvs.map((tv) => (
          <TvReport key={tv.tv_id} tv={tv} />
        ))}
      </div>
    </div>
  );
}
