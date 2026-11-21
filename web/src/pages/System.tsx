import { useQuery } from "@tanstack/react-query";
import { useTranslation } from "react-i18next";

import { fetchInfo } from "../api/client";

export function System() {
  const { t } = useTranslation();
  const { data, error, isPending } = useQuery({
    queryKey: ["info"],
    queryFn: ({ signal }) => fetchInfo(signal),
  });

  if (isPending) return <p role="status">{t("system.loading")}</p>;
  if (error) return <p role="alert">{t("system.error")}</p>;

  return (
    <section aria-labelledby="system-title" className="space-y-4">
      <h2 id="system-title" className="text-xl font-semibold">
        {t("system.title")}
      </h2>
      <dl className="grid grid-cols-[max-content_1fr] gap-x-4 gap-y-1">
        <dt className="text-slate-500">{t("system.version")}</dt>
        <dd>{data.version}</dd>
        <dt className="text-slate-500">{t("system.apiVersion")}</dt>
        <dd>{data.api_version}</dd>
      </dl>
    </section>
  );
}
