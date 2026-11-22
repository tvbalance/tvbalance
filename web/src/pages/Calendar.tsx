import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { useTranslation } from "react-i18next";
import { Link } from "react-router-dom";

import { errorMessage } from "../api/errors";
import {
  keys,
  useCalendar,
  useMe,
  usePolicies,
  type CalendarEntry,
  type Policy,
} from "../api/hooks";
import { api } from "../api/http";
import { TvPicker } from "../components/ActivateProfileDialog";
import { Button } from "../components/ui/button";
import { Card } from "../components/ui/card";
import { Dialog } from "../components/ui/dialog";
import { Field, Input, Select } from "../components/ui/field";
import { useToast } from "../components/ui/toast";

const WEEK = [0, 1, 2, 3, 4, 5, 6];

interface Draft {
  kind: "weekly" | "dated";
  policyId: string;
  weekdays: number[];
  start: string;
  end: string;
  startDate: string;
  endDate: string;
  excluded: string[];
}

function emptyDraft(policies: Policy[]): Draft {
  return {
    kind: "weekly",
    policyId: String(policies[0]?.id ?? ""),
    weekdays: [5, 6],
    start: "08:00",
    end: "20:00",
    startDate: "",
    endDate: "",
    excluded: [],
  };
}

function draftOf(entry: CalendarEntry): Draft {
  return {
    kind: entry.kind,
    policyId: String(entry.policy_id),
    weekdays: entry.kind === "weekly" ? entry.weekdays : [5, 6],
    start: entry.kind === "weekly" ? entry.start.slice(0, 5) : "08:00",
    end: entry.kind === "weekly" ? entry.end.slice(0, 5) : "20:00",
    startDate: entry.kind === "dated" ? entry.start_date : "",
    endDate: entry.kind === "dated" ? entry.end_date : "",
    excluded: entry.excluded_tv_ids ?? [],
  };
}

function body(draft: Draft) {
  const common = { policy_id: Number(draft.policyId), excluded_tv_ids: draft.excluded };
  return draft.kind === "weekly"
    ? { kind: "weekly", ...common, weekdays: draft.weekdays, start: draft.start, end: draft.end }
    : { kind: "dated", ...common, start_date: draft.startDate, end_date: draft.endDate };
}

function valid(draft: Draft): boolean {
  if (draft.policyId === "") return false;
  if (draft.kind === "weekly") return draft.weekdays.length > 0 && draft.start !== "" && draft.end !== "";
  return draft.startDate !== "" && draft.endDate !== "" && draft.endDate >= draft.startDate;
}

function EntryDialog({
  entry,
  policies,
  onClose,
}: {
  entry: CalendarEntry | "new";
  policies: Policy[];
  onClose: () => void;
}) {
  const { t } = useTranslation();
  const toast = useToast();
  const queryClient = useQueryClient();
  const [draft, setDraft] = useState<Draft>(entry === "new" ? emptyDraft(policies) : draftOf(entry));
  const set = (change: Partial<Draft>) => setDraft((old) => ({ ...old, ...change }));

  const save = useMutation({
    mutationFn: () =>
      entry === "new" ? api.post("calendar", body(draft)) : api.put(`calendar/${entry.id}`, body(draft)),
    onSuccess: () => {
      toast(t("calendar.saved"));
      void queryClient.invalidateQueries({ queryKey: keys.calendar });
      onClose();
    },
    onError: (error) => toast(errorMessage(t, error), "error"),
  });

  const toggleDay = (day: number) =>
    set({
      weekdays: draft.weekdays.includes(day)
        ? draft.weekdays.filter((other) => other !== day)
        : [...draft.weekdays, day].sort(),
    });

  return (
    <Dialog
      open
      onOpenChange={(next) => !next && onClose()}
      title={t(entry === "new" ? "calendar.newTitle" : "calendar.editTitle")}
      description={t("calendar.formHelp")}
    >
      <Field label={t("calendar.kind")}>
        {(props) => (
          <Select
            {...props}
            value={draft.kind}
            onChange={(event) => set({ kind: event.target.value as Draft["kind"] })}
          >
            <option value="weekly">{t("calendar.weekly")}</option>
            <option value="dated">{t("calendar.dated")}</option>
          </Select>
        )}
      </Field>
      <Field label={t("calendar.ruleSet")}>
        {(props) => (
          <Select {...props} value={draft.policyId} onChange={(event) => set({ policyId: event.target.value })}>
            {policies.map((policy) => (
              <option key={policy.id} value={policy.id}>
                {policy.name}
              </option>
            ))}
          </Select>
        )}
      </Field>
      {draft.kind === "weekly" ? (
        <>
          <fieldset className="space-y-1">
            <legend className="text-sm font-medium">{t("calendar.days")}</legend>
            <div className="flex flex-wrap gap-x-4">
              {WEEK.map((day) => (
                <label key={day} className="flex min-h-11 items-center gap-1">
                  <input
                    type="checkbox"
                    checked={draft.weekdays.includes(day)}
                    onChange={() => toggleDay(day)}
                  />
                  {t(`calendar.day.${day}`)}
                </label>
              ))}
            </div>
          </fieldset>
          <Field label={t("calendar.from")} hint={t("calendar.overnight")}>
            {(props) => (
              <Input {...props} type="time" value={draft.start} onChange={(event) => set({ start: event.target.value })} />
            )}
          </Field>
          <Field label={t("calendar.until")}>
            {(props) => (
              <Input {...props} type="time" value={draft.end} onChange={(event) => set({ end: event.target.value })} />
            )}
          </Field>
        </>
      ) : (
        <>
          <Field label={t("calendar.firstDay")}>
            {(props) => (
              <Input
                {...props}
                type="date"
                value={draft.startDate}
                onChange={(event) => set({ startDate: event.target.value })}
              />
            )}
          </Field>
          <Field label={t("calendar.lastDay")}>
            {(props) => (
              <Input
                {...props}
                type="date"
                value={draft.endDate}
                onChange={(event) => set({ endDate: event.target.value })}
              />
            )}
          </Field>
        </>
      )}
      <TvPicker legend={t("profiles.excluded")} selected={draft.excluded} onChange={(excluded) => set({ excluded })} />
      <div className="flex justify-end gap-2">
        <Button variant="secondary" onClick={onClose}>
          {t("actions.cancel")}
        </Button>
        <Button disabled={!valid(draft) || save.isPending} onClick={() => save.mutate()}>
          {t("rules.save")}
        </Button>
      </div>
    </Dialog>
  );
}

export function Calendar() {
  const { t } = useTranslation();
  const toast = useToast();
  const queryClient = useQueryClient();
  const calendar = useCalendar();
  const policies = usePolicies();
  const me = useMe();
  const canWrite = me.data?.scopes.includes("admin") ?? false;
  const [editing, setEditing] = useState<CalendarEntry | "new" | null>(null);
  const ruleName = (id: number) => policies.data?.find((policy) => policy.id === id)?.name ?? String(id);

  const remove = useMutation({
    mutationFn: (id: number) => api.delete(`calendar/${id}`),
    onSuccess: () => {
      toast(t("calendar.removed"));
      return queryClient.invalidateQueries({ queryKey: keys.calendar });
    },
    onError: (error) => toast(errorMessage(t, error), "error"),
  });

  const when = (entry: CalendarEntry) =>
    entry.kind === "weekly"
      ? t("calendar.weeklyWhen", {
          days: entry.weekdays.map((day) => t(`calendar.day.${day}`)).join(", "),
          start: entry.start.slice(0, 5),
          end: entry.end.slice(0, 5),
        })
      : t("calendar.datedWhen", { start: entry.start_date, end: entry.end_date });

  return (
    <section aria-labelledby="calendar-title" className="space-y-4">
      <div className="flex items-center justify-between gap-2">
        <h1 id="calendar-title" className="text-2xl font-bold">
          {t("calendar.title")}
        </h1>
        {canWrite && (policies.data?.length ?? 0) > 0 ? (
          <Button onClick={() => setEditing("new")}>{t("calendar.add")}</Button>
        ) : null}
      </div>
      <Link to="/rules" className="inline-block text-sm text-brand underline">
        {t("rules.back")}
      </Link>
      <p className="text-muted">{t("calendar.intro")}</p>
      {calendar.data && !calendar.data.effective ? (
        <p role="status" className="text-sm text-warn">
          {t("profiles.requiresPro")}
        </p>
      ) : null}
      {calendar.isPending ? <p role="status">{t("auth.loading")}</p> : null}
      {calendar.error ? <p role="alert">{t("auth.error")}</p> : null}
      {calendar.data?.entries.length === 0 ? <p className="text-muted">{t("calendar.none")}</p> : null}
      <ul className="space-y-3">
        {calendar.data?.entries.map((entry) => (
          <li key={entry.id}>
            <Card className="flex flex-wrap items-center justify-between gap-2">
              <div>
                <h2 className="font-semibold">{ruleName(entry.policy_id)}</h2>
                <p className="text-sm text-muted">{when(entry)}</p>
              </div>
              {canWrite ? (
                <div className="flex gap-2">
                  <Button variant="secondary" onClick={() => setEditing(entry)}>
                    {t("calendar.edit")}
                  </Button>
                  <Button
                    variant="secondary"
                    aria-label={t("calendar.removeEntry", { name: ruleName(entry.policy_id) })}
                    disabled={remove.isPending}
                    onClick={() => remove.mutate(entry.id)}
                  >
                    {t("calendar.remove")}
                  </Button>
                </div>
              ) : null}
            </Card>
          </li>
        ))}
      </ul>
      {editing !== null && policies.data ? (
        <EntryDialog
          key={editing === "new" ? "new" : editing.id}
          entry={editing}
          policies={policies.data}
          onClose={() => setEditing(null)}
        />
      ) : null}
    </section>
  );
}
