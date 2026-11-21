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
      <h1 id="system-title" className="text-2xl font-bold">
        {t("system.title")}
      </h1>
      <dl className="grid grid-cols-[max-content_1fr] gap-x-4 gap-y-1">
        <dt className="text-muted">{t("system.version")}</dt>
        <dd>{data.version}</dd>
        <dt className="text-muted">{t("system.apiVersion")}</dt>
        <dd>{data.api_version}</dd>
      </dl>
    </section>
  );
}
