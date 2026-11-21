import { useTranslation } from "react-i18next";

import { useMe, useTvs } from "../api/hooks";
import { TvCard } from "../components/TvCard";

export function Dashboard() {
  const { t } = useTranslation();
  const tvs = useTvs();
  const me = useMe();
  const canControl = me.data?.scopes.includes("control") ?? false;

  return (
    <section aria-labelledby="dashboard-title" className="space-y-4">
      <h1 id="dashboard-title" className="text-2xl font-bold">
        {t("dashboard.title")}
      </h1>
      {tvs.isPending ? <p role="status">{t("auth.loading")}</p> : null}
      {tvs.error ? <p role="alert">{t("auth.error")}</p> : null}
      {tvs.data?.length === 0 ? <p className="text-muted">{t("dashboard.empty")}</p> : null}
      <div className="grid gap-4 lg:grid-cols-2">
        {tvs.data?.map((tv) => <TvCard key={tv.id} tv={tv} canControl={canControl} />)}
      </div>
    </section>
  );
}
