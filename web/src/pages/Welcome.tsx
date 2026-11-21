import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useState, type FormEvent } from "react";
import { useTranslation } from "react-i18next";
import { Navigate, useNavigate } from "react-router-dom";

import { errorMessage } from "../api/errors";
import { keys, useAuthState, type Me } from "../api/hooks";
import { api, request, setCsrfToken } from "../api/http";
import { browserTimezone, RegionFields } from "../components/RegionFields";
import { Button } from "../components/ui/button";
import { Card } from "../components/ui/card";
import { Field, Input } from "../components/ui/field";
import i18n, { currentLanguage, type Language } from "../i18n";
import { schoolPreset } from "../presets";

const MIN_PASSWORD = 10;

type Step = "password" | "region" | "rules";
const STEPS: Step[] = ["password", "region", "rules"];

/** First run: create the admin, pick language and time zone, offer a first rule set. */
export function Welcome() {
  const { t } = useTranslation();
  const [step, setStep] = useState<Step>("password");
  const state = useAuthState();

  if (state.isPending) return <p role="status">{t("auth.loading")}</p>;
  // Someone who lands here after setup is done has nothing to do; mid-flow the step moves on.
  if (state.data && !state.data.setup_required && step === "password") {
    return <Navigate to="/" replace />;
  }
  return (
    <div className="mx-auto max-w-md space-y-4 px-4 py-8">
      <header className="space-y-1">
        <h1 className="text-2xl font-bold">{t("welcome.title")}</h1>
        <p className="text-muted">{t("welcome.intro")}</p>
        <p className="text-sm text-muted">
          {t("welcome.step", { current: STEPS.indexOf(step) + 1, total: STEPS.length })}
        </p>
      </header>
      <Card>
        {step === "password" && <PasswordStep onDone={() => setStep("region")} />}
        {step === "region" && <RegionStep onDone={() => setStep("rules")} />}
        {step === "rules" && <RulesStep />}
      </Card>
    </div>
  );
}

function PasswordStep({ onDone }: { onDone: () => void }) {
  const { t } = useTranslation();
  const queryClient = useQueryClient();
  const [password, setPassword] = useState("");
  const [confirm, setConfirm] = useState("");
  const [problem, setProblem] = useState<string | null>(null);

  const setup = useMutation({
    mutationFn: () => request<Me>("POST", "auth/setup", { body: { password }, session: false }),
    onSuccess: (me) => {
      setCsrfToken(me.csrf_token);
      queryClient.setQueryData(keys.me, me);
      queryClient.setQueryData(keys.state, { setup_required: false });
      onDone();
    },
    onError: (error) => setProblem(errorMessage(t, error)),
  });

  const submit = (event: FormEvent) => {
    event.preventDefault();
    if (password.length < MIN_PASSWORD) {
      setProblem(t("welcome.passwordShort", { min: MIN_PASSWORD }));
    } else if (password !== confirm) {
      setProblem(t("welcome.passwordMismatch"));
    } else {
      setProblem(null);
      setup.mutate();
    }
  };

  return (
    <form onSubmit={submit} className="space-y-4">
      <h2 className="text-lg font-semibold">{t("welcome.passwordTitle")}</h2>
      <p className="text-sm text-muted">{t("welcome.passwordHelp")}</p>
      <Field label={t("welcome.password")} hint={t("welcome.passwordHint", { min: MIN_PASSWORD })}>
        {(props) => (
          <Input
            {...props}
            type="password"
            autoComplete="new-password"
            value={password}
            onChange={(event) => setPassword(event.target.value)}
          />
        )}
      </Field>
      <Field label={t("welcome.confirm")} error={problem}>
        {(props) => (
          <Input
            {...props}
            type="password"
            autoComplete="new-password"
            value={confirm}
            onChange={(event) => setConfirm(event.target.value)}
          />
        )}
      </Field>
      <Button type="submit" className="w-full" disabled={setup.isPending}>
        {t("welcome.next")}
      </Button>
    </form>
  );
}

function RegionStep({ onDone }: { onDone: () => void }) {
  const { t } = useTranslation();
  const [language, setLanguage] = useState<Language>(currentLanguage());
  const [timezone, setTimezone] = useState(browserTimezone());
  const [problem, setProblem] = useState<string | null>(null);

  const save = useMutation({
    mutationFn: () => api.put("settings", { language, timezone }),
    onSuccess: onDone,
    onError: (error) => setProblem(errorMessage(t, error)),
  });

  return (
    <form
      onSubmit={(event) => {
        event.preventDefault();
        save.mutate();
      }}
      className="space-y-4"
    >
      <h2 className="text-lg font-semibold">{t("welcome.regionTitle")}</h2>
      <RegionFields
        language={language}
        timezone={timezone}
        onLanguage={(next) => {
          setLanguage(next);
          void i18n.changeLanguage(next);
        }}
        onTimezone={setTimezone}
      />
      {problem ? (
        <p role="alert" className="text-sm text-danger">
          {problem}
        </p>
      ) : null}
      <Button type="submit" className="w-full" disabled={save.isPending}>
        {t("welcome.next")}
      </Button>
    </form>
  );
}

function RulesStep() {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const [problem, setProblem] = useState<string | null>(null);

  const finish = () => {
    void queryClient.invalidateQueries({ queryKey: keys.policies });
    navigate("/", { replace: true });
  };
  const create = useMutation({
    mutationFn: () => api.post("policies", { name: t("presets.school"), policy: schoolPreset() }),
    onSuccess: finish,
    onError: (error) => setProblem(errorMessage(t, error)),
  });

  return (
    <div className="space-y-4">
      <h2 className="text-lg font-semibold">{t("welcome.rulesTitle")}</h2>
      <p className="text-sm text-muted">{t("welcome.rulesHelp")}</p>
      <div className="rounded-lg border border-line p-3">
        <p className="font-medium">{t("presets.school")}</p>
        <p className="text-sm text-muted">{t("presets.schoolSummary")}</p>
      </div>
      {problem ? (
        <p role="alert" className="text-sm text-danger">
          {problem}
        </p>
      ) : null}
      <Button className="w-full" onClick={() => create.mutate()} disabled={create.isPending}>
        {t("welcome.usePreset")}
      </Button>
      <Button variant="ghost" className="w-full" onClick={finish}>
        {t("welcome.skip")}
      </Button>
    </div>
  );
}
