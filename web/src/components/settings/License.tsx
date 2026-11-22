import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useState, type FormEvent } from "react";
import { useTranslation } from "react-i18next";

import { errorMessage } from "../../api/errors";
import { keys, useLicense, type License as LicenseInfo } from "../../api/hooks";
import { api } from "../../api/http";
import { currentLanguage } from "../../i18n";
import { Button, buttonClasses } from "../ui/button";
import { Badge, Card } from "../ui/card";
import { Dialog } from "../ui/dialog";
import { Field, Input } from "../ui/field";
import { useToast } from "../ui/toast";

function Activate() {
  const { t } = useTranslation();
  const toast = useToast();
  const queryClient = useQueryClient();
  const [key, setKey] = useState("");
  const activate = useMutation({
    mutationFn: (value: string) =>
      api.put<LicenseInfo>("license", { key: value }),
    onSuccess: (next) => {
      queryClient.setQueryData(keys.license, next);
      void queryClient.invalidateQueries({ queryKey: keys.tvs });
      setKey("");
      toast(t("license.activated"));
    },
  });
  const submit = (event: FormEvent) => {
    event.preventDefault();
    if (key.trim()) activate.mutate(key.trim());
  };
  return (
    <form onSubmit={submit} className="space-y-2">
      <Field
        label={t("license.keyLabel")}
        error={activate.error ? errorMessage(t, activate.error) : null}
      >
        {(props) => (
          <Input
            {...props}
            value={key}
            autoComplete="off"
            spellCheck={false}
            onChange={(event) => setKey(event.target.value)}
          />
        )}
      </Field>
      <Button type="submit" disabled={activate.isPending || !key.trim()}>
        {t("license.activate")}
      </Button>
    </form>
  );
}

function Remove() {
  const { t } = useTranslation();
  const toast = useToast();
  const queryClient = useQueryClient();
  const [open, setOpen] = useState(false);
  const remove = useMutation({
    mutationFn: () => api.delete<LicenseInfo>("license"),
    onSuccess: (next) => {
      queryClient.setQueryData(keys.license, next);
      void queryClient.invalidateQueries({ queryKey: keys.tvs });
      setOpen(false);
      toast(t("license.removed"));
    },
    onError: (error) => toast(errorMessage(t, error), "error"),
  });
  return (
    <>
      <Button variant="secondary" onClick={() => setOpen(true)}>
        {t("license.remove")}
      </Button>
      <Dialog
        open={open}
        onOpenChange={setOpen}
        title={t("license.removeTitle")}
        description={t("license.removeHelp")}
      >
        <div className="flex justify-end gap-2">
          <Button variant="secondary" onClick={() => setOpen(false)}>
            {t("actions.cancel")}
          </Button>
          <Button
            variant="danger"
            disabled={remove.isPending}
            onClick={() => remove.mutate()}
          >
            {t("license.removeConfirm")}
          </Button>
        </div>
      </Dialog>
    </>
  );
}

/** Settings card: the current plan, and where to paste or remove a Pro license key. */
export function License() {
  const { t } = useTranslation();
  const license = useLicense();
  const info = license.data;
  if (!info) return null;
  const date = new Intl.DateTimeFormat(currentLanguage(), {
    dateStyle: "medium",
  });
  const pro = info.tier === "pro";
  return (
    <Card className="space-y-3">
      <h2 className="text-lg font-semibold">{t("license.title")}</h2>
      <p className="text-sm text-muted">{t("license.help")}</p>
      <p>
        <Badge tone={pro ? "ok" : "neutral"}>
          {t(pro ? "license.plan.pro" : "license.plan.free")}
        </Badge>
      </p>
      <p className="text-sm">{t(`license.status.${info.status}`)}</p>
      {pro ? (
        <div className="space-y-1 text-sm text-muted">
          {info.licensee ? (
            <p>{t("license.licensee", { name: info.licensee })}</p>
          ) : null}
          <p>
            {info.expires_at
              ? t("license.expires", {
                  date: date.format(new Date(info.expires_at)),
                })
              : t("license.perpetual")}
          </p>
        </div>
      ) : null}
      <p className="text-sm text-muted">
        {info.max_tvs === null
          ? t("license.tvUnlimited")
          : t("license.tvLimit", { count: info.max_tvs })}
      </p>
      {info.checkout_url && !pro ? (
        <a
          className={buttonClasses("secondary")}
          href={info.checkout_url}
          target="_blank"
          rel="noopener noreferrer"
        >
          {t("license.buy")}
        </a>
      ) : null}
      <Activate />
      {info.status !== "none" ? <Remove /> : null}
    </Card>
  );
}
