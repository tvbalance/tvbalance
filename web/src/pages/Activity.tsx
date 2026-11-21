import { useState } from "react";
import { useTranslation } from "react-i18next";

import { useEvents, useTvs, useUsage } from "../api/hooks";
import { EventList } from "../components/EventList";
import { UsageBars } from "../components/UsageBars";
import { Button } from "../components/ui/button";
import { Card } from "../components/ui/card";
import { Field, Select } from "../components/ui/field";

const PAGE = 50;

function TvUsage({ tvId, name }: { tvId: string; name: string }) {
  const { t } = useTranslation();
  const usage = useUsage(tvId, 7);
  return (
    <Card className="space-y-3">
      <h2 className="text-lg font-semibold">{name}</h2>
      {usage.isPending ? <p role="status">{t("auth.loading")}</p> : null}
      {usage.data ? <UsageBars usage={usage.data} /> : null}
    </Card>
  );
}

export function Activity() {
  const { t } = useTranslation();
  const tvs = useTvs();
  const [tvId, setTvId] = useState("");
  const [limit, setLimit] = useState(PAGE);
  const events = useEvents(tvId || null, limit);
  const shown = (tvs.data ?? []).filter((tv) => !tvId || tv.id === tvId);

  return (
    <section aria-labelledby="activity-title" className="space-y-4">
      <h1 id="activity-title" className="text-2xl font-bold">
        {t("activity.title")}
      </h1>
      {(tvs.data?.length ?? 0) > 1 ? (
        <Field label={t("activity.filter")}>
          {(props) => (
            <Select
              {...props}
              value={tvId}
              onChange={(event) => {
                setTvId(event.target.value);
                setLimit(PAGE);
              }}
            >
              <option value="">{t("activity.allTvs")}</option>
              {tvs.data?.map((tv) => (
                <option key={tv.id} value={tv.id}>
                  {tv.name}
                </option>
              ))}
            </Select>
          )}
        </Field>
      ) : null}
      <h2 className="text-lg font-semibold">{t("activity.usage")}</h2>
      {shown.length === 0 && tvs.data ? <p className="text-muted">{t("activity.noTvs")}</p> : null}
      <div className="grid gap-3 md:grid-cols-2">
        {shown.map((tv) => (
          <TvUsage key={tv.id} tvId={tv.id} name={tv.name} />
        ))}
      </div>
      <h2 className="text-lg font-semibold">{t("activity.log")}</h2>
      {events.isPending ? <p role="status">{t("auth.loading")}</p> : null}
      {events.error ? <p role="alert">{t("auth.error")}</p> : null}
      {events.data ? <EventList events={events.data} tvs={tvs.data ?? []} /> : null}
      {events.data && events.data.length >= limit ? (
        <Button variant="secondary" onClick={() => setLimit(limit + PAGE)}>
          {t("activity.more")}
        </Button>
      ) : null}
    </section>
  );
}
