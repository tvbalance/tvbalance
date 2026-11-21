import { useTranslation } from "react-i18next";

import { useTvs } from "../api/hooks";

export function Dashboard() {
  const { t } = useTranslation();
  const tvs = useTvs();
  return (
    <section aria-labelledby="dashboard-title" className="space-y-4">
      <h1 id="dashboard-title" className="text-2xl font-bold">
        {t("dashboard.title")}
      </h1>
      {tvs.data?.length === 0 ? <p className="text-muted">{t("dashboard.empty")}</p> : null}
    </section>
  );
}
