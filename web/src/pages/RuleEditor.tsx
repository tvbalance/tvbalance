import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { useTranslation } from "react-i18next";
import { Link, useParams } from "react-router-dom";

import { errorMessage } from "../api/errors";
import { keys, usePolicies, useTvs, type Policy } from "../api/hooks";
import { api, ApiError } from "../api/http";
import { AdvancedTab } from "../components/rules/AdvancedTab";
import { ContentTab } from "../components/rules/ContentTab";
import { ScheduleTab } from "../components/rules/ScheduleTab";
import { TimeTab } from "../components/rules/TimeTab";
import { Button } from "../components/ui/button";
import { Field, Input } from "../components/ui/field";
import { Tabs } from "../components/ui/tabs";
import { useToast } from "../components/ui/toast";
import type { PolicyDoc } from "../presets";

interface Issue {
  code: string;
  detail: string;
}

/** The domain's issue codes arrive in `details`; anything else is shown as a plain message. */
function issuesOf(error: unknown): Issue[] {
  if (!(error instanceof ApiError) || error.status !== 422) return [];
  return (error.details ?? [])
    .filter((d): d is { code: string; detail: string } => typeof d.code === "string")
    .map((d) => ({ code: d.code, detail: typeof d.detail === "string" ? d.detail : "" }));
}

function Editor({ saved }: { saved: Policy }) {
  const { t } = useTranslation();
  const toast = useToast();
  const queryClient = useQueryClient();
  const tvs = useTvs();
  const [name, setName] = useState(saved.name);
  const [policy, setPolicy] = useState<PolicyDoc>(saved.policy);
  const [failure, setFailure] = useState<unknown>(null);
  const edit = (patch: Partial<PolicyDoc>) => setPolicy((current) => ({ ...current, ...patch }));

  const save = useMutation({
    mutationFn: () => api.put(`policies/${saved.id}`, { name, policy }),
    onSuccess: () => {
      setFailure(null);
      toast(t("rules.saved"));
      void queryClient.invalidateQueries({ queryKey: keys.policies });
    },
    onError: setFailure,
  });

  const issues = issuesOf(failure);
  const plain = failure && issues.length === 0 ? errorMessage(t, failure) : null;

  return (
    <div className="space-y-4">
      <Field label={t("rules.name")}>
        {(props) => <Input {...props} value={name} onChange={(event) => setName(event.target.value)} />}
      </Field>
      {issues.length > 0 || plain ? (
        <div role="alert" className="rounded-lg border border-danger p-3 text-sm text-danger">
          <p className="font-medium">{t("rules.cannotSave")}</p>
          <ul className="list-disc pl-5">
            {issues.map((issue, index) => (
              <li key={index}>
                {t(`rules.issue.${issue.code}`, { defaultValue: issue.code })}
                {issue.detail ? ` (${issue.detail})` : ""}
              </li>
            ))}
            {plain ? <li>{plain}</li> : null}
          </ul>
        </div>
      ) : null}
      <Tabs
        label={t("rules.sections")}
        tabs={[
          {
            id: "schedule",
            label: t("rules.tabSchedule"),
            content: (
              <ScheduleTab schedule={policy.schedule} onChange={(schedule) => edit({ schedule })} />
            ),
          },
          { id: "time", label: t("rules.tabTime"), content: <TimeTab policy={policy} onChange={edit} /> },
          {
            id: "content",
            label: t("rules.tabContent"),
            content: <ContentTab policy={policy} tvs={tvs.data ?? []} onChange={edit} />,
          },
          {
            id: "advanced",
            label: t("rules.tabAdvanced"),
            content: (
              <AdvancedTab escalation={policy.escalation} onChange={(escalation) => edit({ escalation })} />
            ),
          },
        ]}
      />
      <div className="sticky bottom-16 flex justify-end md:bottom-0">
        <Button disabled={save.isPending || name.trim() === ""} onClick={() => save.mutate()}>
          {t("rules.save")}
        </Button>
      </div>
    </div>
  );
}

export function RuleEditor() {
  const { t } = useTranslation();
  const { id } = useParams();
  const policies = usePolicies();
  if (policies.isPending) return <p role="status">{t("auth.loading")}</p>;
  if (policies.error) return <p role="alert">{t("auth.error")}</p>;
  const saved = policies.data.find((policy) => String(policy.id) === id);
  return (
    <section aria-labelledby="rule-title" className="space-y-4">
      <p>
        <Link to="/rules" className="text-sm text-brand underline">
          {t("rules.back")}
        </Link>
      </p>
      <h1 id="rule-title" className="text-2xl font-bold">
        {t("rules.editTitle")}
      </h1>
      {saved ? <Editor key={`${saved.id}-${saved.updated_at}`} saved={saved} /> : <p role="alert">{t("errors.not_found")}</p>}
    </section>
  );
}
