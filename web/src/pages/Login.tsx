import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useState, type FormEvent } from "react";
import { useTranslation } from "react-i18next";
import { Navigate, useNavigate } from "react-router-dom";

import { errorMessage } from "../api/errors";
import { keys, useAuthState, useMe, type Me } from "../api/hooks";
import { request, setCsrfToken } from "../api/http";
import { Button } from "../components/ui/button";
import { Card } from "../components/ui/card";
import { Field, Input } from "../components/ui/field";
import { Tabs } from "../components/ui/tabs";

const OVERRIDES = { not_authenticated: "login.wrong", pin_locked: "login.pinLocked" };

/** One credential form; `path` is the login endpoint and `field` the body key. */
function CredentialForm({
  path,
  field,
  label,
  inputMode,
  autoComplete,
}: {
  path: string;
  field: "password" | "pin";
  label: string;
  inputMode?: "numeric";
  autoComplete: string;
}) {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const [secret, setSecret] = useState("");
  const [problem, setProblem] = useState<string | null>(null);

  const signIn = useMutation({
    mutationFn: () => request<Me>("POST", path, { body: { [field]: secret }, session: false }),
    onSuccess: (me) => {
      setCsrfToken(me.csrf_token);
      queryClient.setQueryData(keys.me, me);
      navigate("/", { replace: true });
    },
    onError: (error) => {
      setSecret("");
      setProblem(errorMessage(t, error, OVERRIDES));
    },
  });

  const submit = (event: FormEvent) => {
    event.preventDefault();
    setProblem(null);
    signIn.mutate();
  };

  return (
    <form onSubmit={submit} className="space-y-4">
      <Field label={label} error={problem}>
        {(props) => (
          <Input
            {...props}
            type="password"
            inputMode={inputMode}
            autoComplete={autoComplete}
            value={secret}
            onChange={(event) => setSecret(event.target.value)}
          />
        )}
      </Field>
      <Button type="submit" className="w-full" disabled={signIn.isPending || secret === ""}>
        {t("login.submit")}
      </Button>
    </form>
  );
}

export function Login() {
  const { t } = useTranslation();
  const state = useAuthState();
  const me = useMe();

  if (state.isPending || me.isPending) return <p role="status">{t("auth.loading")}</p>;
  if (state.data?.setup_required) return <Navigate to="/welcome" replace />;
  if (me.data) return <Navigate to="/" replace />;
  return (
    <div className="mx-auto max-w-md space-y-4 px-4 py-8">
      <header className="space-y-1">
        <h1 className="text-2xl font-bold">{t("login.title")}</h1>
        <p className="text-muted">{t("login.intro")}</p>
      </header>
      <Card>
        <Tabs
          label={t("login.methods")}
          tabs={[
            {
              id: "password",
              label: t("login.password"),
              content: (
                <CredentialForm
                  path="auth/login"
                  field="password"
                  label={t("login.password")}
                  autoComplete="current-password"
                />
              ),
            },
            {
              id: "pin",
              label: t("login.pin"),
              content: (
                <CredentialForm
                  path="auth/pin-login"
                  field="pin"
                  label={t("login.pin")}
                  inputMode="numeric"
                  autoComplete="off"
                />
              ),
            },
          ]}
        />
      </Card>
    </div>
  );
}
