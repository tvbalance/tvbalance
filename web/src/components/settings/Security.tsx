import { useMutation } from "@tanstack/react-query";
import { useState, type FormEvent } from "react";
import { useTranslation } from "react-i18next";

import { errorMessage } from "../../api/errors";
import { api } from "../../api/http";
import { Button } from "../ui/button";
import { Card } from "../ui/card";
import { Field, Input } from "../ui/field";
import { useToast } from "../ui/toast";

const MIN_PASSWORD = 10;

function PasswordForm() {
  const { t } = useTranslation();
  const toast = useToast();
  const [current, setCurrent] = useState("");
  const [next, setNext] = useState("");
  const [confirm, setConfirm] = useState("");
  const mismatch = confirm !== "" && confirm !== next;

  const change = useMutation({
    mutationFn: () => api.put("auth/password", { current_password: current, new_password: next }),
    onSuccess: () => {
      toast(t("settings.passwordChanged"));
      setCurrent("");
      setNext("");
      setConfirm("");
    },
    onError: (error) => toast(errorMessage(t, error), "error"),
  });
  const ready = current !== "" && next.length >= MIN_PASSWORD && next === confirm;
  const submit = (event: FormEvent) => {
    event.preventDefault();
    if (ready) change.mutate();
  };

  return (
    <form onSubmit={submit} className="space-y-3">
      <h3 className="font-semibold">{t("settings.password")}</h3>
      <Field label={t("settings.currentPassword")}>
        {(props) => (
          <Input {...props} type="password" autoComplete="current-password" value={current} onChange={(e) => setCurrent(e.target.value)} />
        )}
      </Field>
      <Field label={t("settings.newPassword")} hint={t("settings.passwordHint", { count: MIN_PASSWORD })}>
        {(props) => (
          <Input {...props} type="password" autoComplete="new-password" value={next} onChange={(e) => setNext(e.target.value)} />
        )}
      </Field>
      <Field label={t("settings.confirmPassword")} error={mismatch ? t("settings.passwordMismatch") : undefined}>
        {(props) => (
          <Input {...props} type="password" autoComplete="new-password" value={confirm} onChange={(e) => setConfirm(e.target.value)} />
        )}
      </Field>
      <Button type="submit" disabled={!ready || change.isPending}>
        {t("settings.changePassword")}
      </Button>
    </form>
  );
}

function PinForm() {
  const { t } = useTranslation();
  const toast = useToast();
  const [pin, setPin] = useState("");

  const set = useMutation({
    mutationFn: () => api.put("auth/pin", { pin }),
    onSuccess: () => {
      toast(t("settings.pinSet"));
      setPin("");
    },
    onError: (error) => toast(errorMessage(t, error), "error"),
  });
  const clear = useMutation({
    mutationFn: () => api.delete("auth/pin"),
    onSuccess: () => toast(t("settings.pinCleared")),
    onError: (error) => toast(errorMessage(t, error), "error"),
  });

  return (
    <div className="space-y-3">
      <h3 className="font-semibold">{t("settings.pin")}</h3>
      <p className="text-sm text-muted">{t("settings.pinHelp")}</p>
      <Field label={t("settings.newPin")}>
        {(props) => (
          <Input {...props} type="password" inputMode="numeric" autoComplete="off" value={pin} onChange={(e) => setPin(e.target.value)} />
        )}
      </Field>
      <div className="flex gap-2">
        <Button disabled={pin.length < 4 || set.isPending} onClick={() => set.mutate()}>
          {t("settings.savePin")}
        </Button>
        <Button variant="secondary" disabled={clear.isPending} onClick={() => clear.mutate()}>
          {t("settings.removePin")}
        </Button>
      </div>
    </div>
  );
}

export function Security() {
  const { t } = useTranslation();
  return (
    <Card className="space-y-6">
      <h2 className="text-lg font-semibold">{t("settings.security")}</h2>
      <PasswordForm />
      <PinForm />
    </Card>
  );
}
