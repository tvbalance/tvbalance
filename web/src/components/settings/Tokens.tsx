import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { useTranslation } from "react-i18next";

import { errorMessage } from "../../api/errors";
import { keys, useTokens, type Token } from "../../api/hooks";
import { api } from "../../api/http";
import { Button } from "../ui/button";
import { Card } from "../ui/card";
import { Field, Input } from "../ui/field";
import { useToast } from "../ui/toast";

type Scope = Token["scopes"][number];
const SCOPES: Scope[] = ["read", "control", "admin"];

interface Created extends Token {
  token: string;
}

/** The secret is only in this response: show it once, with a copy button. */
function NewToken({ created, onDone }: { created: Created; onDone: () => void }) {
  const { t } = useTranslation();
  const toast = useToast();
  const copy = async () => {
    try {
      await navigator.clipboard.writeText(created.token);
      toast(t("settings.tokenCopied"));
    } catch {
      toast(t("settings.tokenCopyFailed"), "error");
    }
  };
  return (
    <div role="status" className="space-y-2 rounded-lg border border-brand p-3">
      <p className="font-medium">{t("settings.tokenShownOnce")}</p>
      <code className="block break-all rounded bg-page p-2 text-sm">{created.token}</code>
      <div className="flex gap-2">
        <Button variant="secondary" onClick={copy}>
          {t("settings.copy")}
        </Button>
        <Button variant="ghost" onClick={onDone}>
          {t("settings.done")}
        </Button>
      </div>
    </div>
  );
}

export function Tokens() {
  const { t } = useTranslation();
  const toast = useToast();
  const queryClient = useQueryClient();
  const tokens = useTokens();
  const [name, setName] = useState("");
  const [scopes, setScopes] = useState<Scope[]>(["read", "control"]);
  const [created, setCreated] = useState<Created | null>(null);

  const refresh = () => queryClient.invalidateQueries({ queryKey: keys.tokens });
  const create = useMutation({
    mutationFn: () => api.post<Created>("auth/tokens", { name: name.trim(), scopes }),
    onSuccess: (token) => {
      setCreated(token);
      setName("");
      return refresh();
    },
    onError: (error) => toast(errorMessage(t, error), "error"),
  });
  const revoke = useMutation({
    mutationFn: (id: string) => api.delete(`auth/tokens/${id}`),
    onSuccess: refresh,
    onError: (error) => toast(errorMessage(t, error), "error"),
  });
  const toggle = (scope: Scope) =>
    setScopes((current) => (current.includes(scope) ? current.filter((s) => s !== scope) : [...current, scope]));

  const active = (tokens.data ?? []).filter((token) => !token.revoked_at);
  return (
    <Card className="space-y-4">
      <h2 className="text-lg font-semibold">{t("settings.tokens")}</h2>
      <p className="text-sm text-muted">{t("settings.tokensHelp")}</p>
      {created ? <NewToken created={created} onDone={() => setCreated(null)} /> : null}
      <ul className="divide-y divide-line">
        {active.map((token) => (
          <li key={token.id} className="flex flex-wrap items-center justify-between gap-2 py-2">
            <div className="text-sm">
              <p className="font-medium">{token.name}</p>
              <p className="text-muted">{token.scopes.map((s) => t(`settings.scope.${s}`)).join(", ")}</p>
            </div>
            <Button
              variant="secondary"
              aria-label={t("settings.revokeToken", { name: token.name })}
              onClick={() => revoke.mutate(token.id)}
            >
              {t("settings.revoke")}
            </Button>
          </li>
        ))}
      </ul>
      <form
        className="space-y-3"
        onSubmit={(event) => {
          event.preventDefault();
          if (name.trim() && scopes.length > 0) create.mutate();
        }}
      >
        <Field label={t("settings.tokenName")}>
          {(props) => <Input {...props} value={name} onChange={(event) => setName(event.target.value)} />}
        </Field>
        <fieldset className="space-y-1">
          <legend className="text-sm font-medium">{t("settings.tokenScopes")}</legend>
          {SCOPES.map((scope) => (
            <label key={scope} className="flex min-h-11 items-center gap-2 text-sm">
              <input type="checkbox" checked={scopes.includes(scope)} onChange={() => toggle(scope)} />
              {t(`settings.scope.${scope}`)}
            </label>
          ))}
        </fieldset>
        <Button type="submit" disabled={!name.trim() || scopes.length === 0 || create.isPending}>
          {t("settings.createToken")}
        </Button>
      </form>
    </Card>
  );
}
