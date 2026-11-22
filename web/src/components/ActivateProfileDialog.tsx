import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { useTranslation } from "react-i18next";

import { errorMessage } from "../api/errors";
import { keys, useTvs, type Policy } from "../api/hooks";
import { api } from "../api/http";
import { Button } from "./ui/button";
import { Dialog } from "./ui/dialog";
import { Field, Select } from "./ui/field";
import { useToast } from "./ui/toast";

const DURATIONS = [30, 60, 120, 240];
const MIDNIGHT = "midnight";

/** Which TVs a profile skips: they keep following their own rule set. */
export function TvPicker({
  legend,
  selected,
  onChange,
}: {
  legend: string;
  selected: string[];
  onChange: (ids: string[]) => void;
}) {
  const tvs = useTvs();
  if (!tvs.data || tvs.data.length === 0) return null;
  const toggle = (id: string) =>
    onChange(selected.includes(id) ? selected.filter((other) => other !== id) : [...selected, id]);
  return (
    <fieldset className="space-y-1">
      <legend className="text-sm font-medium">{legend}</legend>
      {tvs.data.map((tv) => (
        <label key={tv.id} className="flex min-h-11 items-center gap-2">
          <input type="checkbox" checked={selected.includes(tv.id)} onChange={() => toggle(tv.id)} />
          {tv.name}
        </label>
      ))}
    </fieldset>
  );
}

/** Puts a rule set in force for the whole household, except the TVs the person leaves out. */
export function ActivateProfileDialog({
  policy,
  onClose,
}: {
  policy: Policy | null;
  onClose: () => void;
}) {
  const { t } = useTranslation();
  const toast = useToast();
  const queryClient = useQueryClient();
  const [length, setLength] = useState("60");
  const [excluded, setExcluded] = useState<string[]>([]);

  const activate = useMutation({
    mutationFn: (policyId: number) =>
      api.post("profiles/active", {
        policy_id: policyId,
        excluded_tv_ids: excluded,
        ...(length === MIDNIGHT
          ? { until_midnight: true }
          : { minutes: Number(length), until_midnight: false }),
      }),
    onSuccess: () => {
      toast(t("profiles.activated"));
      void queryClient.invalidateQueries({ queryKey: keys.profile });
      void queryClient.invalidateQueries({ queryKey: keys.tvs });
      onClose();
    },
    onError: (error) => toast(errorMessage(t, error), "error"),
  });

  return (
    <Dialog
      open={policy !== null}
      onOpenChange={(next) => !next && onClose()}
      title={t("profiles.activateTitle", { name: policy?.name ?? "" })}
      description={t("profiles.activateHelp")}
    >
      <Field label={t("actions.duration")}>
        {(props) => (
          <Select {...props} value={length} onChange={(event) => setLength(event.target.value)}>
            {DURATIONS.map((value) => (
              <option key={value} value={value}>
                {t("actions.minutes", { minutes: value })}
              </option>
            ))}
            <option value={MIDNIGHT}>{t("actions.untilMidnight")}</option>
          </Select>
        )}
      </Field>
      <TvPicker legend={t("profiles.excluded")} selected={excluded} onChange={setExcluded} />
      <div className="flex justify-end gap-2">
        <Button variant="secondary" onClick={onClose}>
          {t("actions.cancel")}
        </Button>
        <Button
          disabled={policy === null || activate.isPending}
          onClick={() => policy && activate.mutate(policy.id)}
        >
          {t("profiles.activate")}
        </Button>
      </div>
    </Dialog>
  );
}
