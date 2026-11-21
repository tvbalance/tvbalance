import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { useTranslation } from "react-i18next";
import { Link, useNavigate } from "react-router-dom";

import { errorMessage } from "../api/errors";
import { keys, useMe, usePolicies, useTvs, type Policy } from "../api/hooks";
import { api } from "../api/http";
import { Button } from "../components/ui/button";
import { Card } from "../components/ui/card";
import { Dialog } from "../components/ui/dialog";
import { Field, Input, Select } from "../components/ui/field";
import { useToast } from "../components/ui/toast";
import { emptyPolicy, schoolPreset } from "../presets";

type Start = "school" | "empty";

function NewRuleDialog({ open, onClose }: { open: boolean; onClose: () => void }) {
  const { t } = useTranslation();
  const toast = useToast();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const [name, setName] = useState("");
  const [start, setStart] = useState<Start>("school");

  const create = useMutation({
    mutationFn: () =>
      api.post<Policy>("policies", {
        name: name.trim(),
        policy: start === "school" ? schoolPreset() : emptyPolicy(),
      }),
    onSuccess: (created) => {
      void queryClient.invalidateQueries({ queryKey: keys.policies });
      navigate(`/rules/${created.id}`);
    },
    onError: (error) => toast(errorMessage(t, error), "error"),
  });

  return (
    <Dialog
      open={open}
      onOpenChange={(next) => !next && onClose()}
      title={t("rules.newTitle")}
      description={t("rules.newHelp")}
    >
      <Field label={t("rules.name")}>
        {(props) => <Input {...props} value={name} onChange={(event) => setName(event.target.value)} />}
      </Field>
      <Field label={t("rules.startFrom")}>
        {(props) => (
          <Select {...props} value={start} onChange={(event) => setStart(event.target.value as Start)}>
            <option value="school">{t("presets.school")}</option>
            <option value="empty">{t("rules.empty")}</option>
          </Select>
        )}
      </Field>
      <div className="flex justify-end gap-2">
        <Button variant="secondary" onClick={onClose}>
          {t("actions.cancel")}
        </Button>
        <Button disabled={name.trim() === "" || create.isPending} onClick={() => create.mutate()}>
          {t("rules.create")}
        </Button>
      </div>
    </Dialog>
  );
}

export function Rules() {
  const { t } = useTranslation();
  const policies = usePolicies();
  const tvs = useTvs();
  const me = useMe();
  const [creating, setCreating] = useState(false);
  const canWrite = me.data?.scopes.includes("admin") ?? false;
  const tvName = (id: string) => tvs.data?.find((tv) => tv.id === id)?.name ?? id;

  return (
    <section aria-labelledby="rules-title" className="space-y-4">
      <div className="flex items-center justify-between gap-2">
        <h1 id="rules-title" className="text-2xl font-bold">
          {t("rules.title")}
        </h1>
        {canWrite ? <Button onClick={() => setCreating(true)}>{t("rules.new")}</Button> : null}
      </div>
      <p className="text-muted">{t("rules.intro")}</p>
      {policies.isPending ? <p role="status">{t("auth.loading")}</p> : null}
      {policies.error ? <p role="alert">{t("auth.error")}</p> : null}
      {policies.data?.length === 0 ? <p className="text-muted">{t("rules.none")}</p> : null}
      <ul className="space-y-3">
        {policies.data?.map((policy) => (
          <li key={policy.id}>
            <Card className="space-y-1">
              <h2 className="text-lg font-semibold">
                <Link to={`/rules/${policy.id}`} className="hover:underline">
                  {policy.name}
                </Link>
              </h2>
              <p className="text-sm text-muted">
                {policy.tv_ids.length > 0
                  ? t("rules.usedBy", { tvs: policy.tv_ids.map(tvName).join(", ") })
                  : t("rules.unused")}
              </p>
            </Card>
          </li>
        ))}
      </ul>
      <NewRuleDialog key={String(creating)} open={creating} onClose={() => setCreating(false)} />
    </section>
  );
}
