import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { useTranslation } from "react-i18next";
import { Link, useNavigate, useParams } from "react-router-dom";

import { errorMessage } from "../api/errors";
import { keys, useEvents, useMe, usePolicies, useTvs, useUsage, type Tv } from "../api/hooks";
import { api } from "../api/http";
import { EventList } from "../components/EventList";
import { UsageBars } from "../components/UsageBars";
import { Button } from "../components/ui/button";
import { Card } from "../components/ui/card";
import { Dialog } from "../components/ui/dialog";
import { Field, Input, Select, Switch } from "../components/ui/field";
import { useToast } from "../components/ui/toast";

function Settings({ tv, canWrite }: { tv: Tv; canWrite: boolean }) {
  const { t } = useTranslation();
  const toast = useToast();
  const queryClient = useQueryClient();
  const policies = usePolicies();
  const [name, setName] = useState(tv.name);

  const update = useMutation({
    mutationFn: (patch: { name?: string; enabled?: boolean; policy_id?: number | null }) =>
      api.patch<Tv>(`tvs/${tv.id}`, patch),
    onSuccess: () => {
      toast(t("tvDetail.saved"));
      void queryClient.invalidateQueries({ queryKey: keys.tvs });
      void queryClient.invalidateQueries({ queryKey: keys.policies });
    },
    onError: (error) => toast(errorMessage(t, error), "error"),
  });

  return (
    <Card className="space-y-4">
      <div className="flex items-end gap-2">
        <div className="flex-1">
          <Field label={t("tvDetail.name")}>
            {(props) => (
              <Input {...props} value={name} disabled={!canWrite} onChange={(event) => setName(event.target.value)} />
            )}
          </Field>
        </div>
        {canWrite ? (
          <Button
            variant="secondary"
            disabled={name.trim() === "" || name.trim() === tv.name || update.isPending}
            onClick={() => update.mutate({ name: name.trim() })}
          >
            {t("tvDetail.rename")}
          </Button>
        ) : null}
      </div>
      <Field label={t("tvDetail.rules")} hint={t("tvDetail.rulesHelp")}>
        {(props) => (
          <Select
            {...props}
            value={tv.policy_id ?? ""}
            disabled={!canWrite}
            onChange={(event) => update.mutate({ policy_id: event.target.value ? Number(event.target.value) : null })}
          >
            <option value="">{t("tvDetail.noRules")}</option>
            {policies.data?.map((policy) => (
              <option key={policy.id} value={policy.id}>
                {policy.name}
              </option>
            ))}
          </Select>
        )}
      </Field>
      <div className="flex items-center justify-between gap-4">
        <div>
          <p className="font-medium">{t("tvDetail.enabled")}</p>
          <p className="text-sm text-muted">{t("tvDetail.enabledHelp")}</p>
        </div>
        <Switch
          label={t("tvDetail.enabled")}
          checked={tv.enabled}
          disabled={!canWrite || update.isPending}
          onChange={(enabled) => update.mutate({ enabled })}
        />
      </div>
    </Card>
  );
}

function RemoveTv({ tv }: { tv: Tv }) {
  const { t } = useTranslation();
  const toast = useToast();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const [open, setOpen] = useState(false);
  const remove = useMutation({
    mutationFn: () => api.delete(`tvs/${tv.id}`),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: keys.tvs });
      navigate("/");
    },
    onError: (error) => toast(errorMessage(t, error), "error"),
  });
  return (
    <>
      <Button variant="danger" onClick={() => setOpen(true)}>
        {t("tvDetail.remove")}
      </Button>
      <Dialog
        open={open}
        onOpenChange={setOpen}
        title={t("tvDetail.removeTitle", { name: tv.name })}
        description={t("tvDetail.removeHelp")}
      >
        <div className="flex justify-end gap-2">
          <Button variant="secondary" onClick={() => setOpen(false)}>
            {t("actions.cancel")}
          </Button>
          <Button variant="danger" disabled={remove.isPending} onClick={() => remove.mutate()}>
            {t("tvDetail.confirmRemove")}
          </Button>
        </div>
      </Dialog>
    </>
  );
}

export function TvDetail() {
  const { t } = useTranslation();
  const { id = "" } = useParams();
  const tvs = useTvs();
  const me = useMe();
  const usage = useUsage(id, 7);
  const events = useEvents(id, 10);
  const canWrite = me.data?.scopes.includes("admin") ?? false;
  const tv = tvs.data?.find((candidate) => candidate.id === id);

  if (tvs.isPending) return <p role="status">{t("auth.loading")}</p>;
  if (!tv) return <p role="alert">{t("errors.not_found")}</p>;
  return (
    <section aria-labelledby="tv-title" className="space-y-4">
      <p>
        <Link to="/" className="text-sm text-brand underline">
          {t("tvDetail.back")}
        </Link>
      </p>
      <h1 id="tv-title" className="text-2xl font-bold">
        {tv.name}
      </h1>
      {tv.needs_pairing || tv.status?.pairing_required ? (
        <p role="alert" className="space-y-1">
          <span className="block">{t("tvDetail.needsPairing")}</span>
          {canWrite ? (
            <Link to={`/tvs/${tv.id}/pair`} className="text-sm text-brand underline">
              {t("pairing.pairAgain")}
            </Link>
          ) : null}
        </p>
      ) : null}
      {tv.plan_limited ? <p role="status">{t("tvDetail.planLimited")}</p> : null}
      <Settings key={`${tv.id}-${tv.name}`} tv={tv} canWrite={canWrite} />
      <h2 className="text-lg font-semibold">{t("activity.usage")}</h2>
      {usage.data ? <UsageBars usage={usage.data} /> : null}
      <h2 className="text-lg font-semibold">{t("tvDetail.recent")}</h2>
      {events.data ? <EventList events={events.data} tvs={tvs.data ?? []} /> : null}
      <p>
        <Link to="/activity" className="text-sm text-brand underline">
          {t("tvDetail.allActivity")}
        </Link>
      </p>
      {canWrite ? <RemoveTv tv={tv} /> : null}
    </section>
  );
}
