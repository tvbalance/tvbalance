import { useTranslation } from "react-i18next";
import { Link } from "react-router-dom";

import { useMe, useTvs } from "../api/hooks";
import { ProfileBanner } from "../components/ProfileBanner";
import { TvCard } from "../components/TvCard";

export function Dashboard() {
  const { t } = useTranslation();
  const tvs = useTvs();
  const me = useMe();
  const canControl = me.data?.scopes.includes("control") ?? false;
  const canAdmin = me.data?.scopes.includes("admin") ?? false;

  const addTv = (
    <Link
      to="/tvs/add"
      className="inline-flex min-h-11 items-center justify-center rounded-lg bg-brand px-4 text-sm font-medium text-brand-ink hover:opacity-90"
    >
      {t("dashboard.add")}
    </Link>
  );

  return (
    <section aria-labelledby="dashboard-title" className="space-y-4">
      <div className="flex items-center justify-between gap-2">
        <h1 id="dashboard-title" className="text-2xl font-bold">
          {t("dashboard.title")}
        </h1>
        {canAdmin && tvs.data && tvs.data.length > 0 ? addTv : null}
      </div>
      <ProfileBanner canControl={canControl} />
      {tvs.isPending ?<p role="status">{t("auth.loading")}</p> : null}
      {tvs.error ? <p role="alert">{t("auth.error")}</p> : null}
      {tvs.data?.length === 0 ? (
        <div className="space-y-3">
          <p className="text-muted">{t("dashboard.empty")}</p>
          {canAdmin ? addTv : null}
        </div>
      ) : null}
      <div className="grid gap-4 lg:grid-cols-2">
        {tvs.data?.map((tv) => <TvCard key={tv.id} tv={tv} canControl={canControl} canAdmin={canAdmin} />)}
      </div>
    </section>
  );
}
