import { useQuery } from "@tanstack/react-query";
import { useTranslation } from "react-i18next";

import { fetchInfo } from "../api/client";
import { useAdapters } from "../api/hooks";
import { Badge } from "../components/ui/card";

export function System() {
  const { t } = useTranslation();
  const adapters = useAdapters();
  const { data, error, isPending } = useQuery({
    queryKey: ["info"],
    queryFn: ({ signal }) => fetchInfo(signal),
  });

  if (isPending) return <p role="status">{t("system.loading")}</p>;
  if (error) return <p role="alert">{t("system.error")}</p>;

  return (
    <section aria-labelledby="system-title" className="space-y-4">
      <h1 id="system-title" className="text-2xl font-bold">
        {t("system.title")}
      </h1>
      <dl className="grid grid-cols-[max-content_1fr] gap-x-4 gap-y-1">
        <dt className="text-muted">{t("system.version")}</dt>
        <dd>{data.version}</dd>
        <dt className="text-muted">{t("system.apiVersion")}</dt>
        <dd>{data.api_version}</dd>
      </dl>
      {adapters.data ? (
        <>
          <h2 className="text-lg font-semibold">{t("system.adapters")}</h2>
          <ul className="divide-y divide-line">
            {adapters.data.map((adapter) => (
              <li key={adapter.id} className="flex items-center justify-between gap-2 py-2">
                <span>{adapter.display_name}</span>
                <Badge tone={adapter.maturity === "stable" ? "ok" : "warn"}>{t(`system.maturity.${adapter.maturity}`)}</Badge>
              </li>
            ))}
          </ul>
        </>
      ) : null}
    </section>
  );
}
