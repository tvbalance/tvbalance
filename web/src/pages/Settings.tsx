import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { useTranslation } from "react-i18next";
import { useNavigate } from "react-router-dom";

import { errorMessage } from "../api/errors";
import { keys, useMe, useSettings, type Settings as SavedSettings } from "../api/hooks";
import { api, setCsrfToken } from "../api/http";
import { browserTimezone, RegionFields } from "../components/RegionFields";
import { Security } from "../components/settings/Security";
import { Sessions } from "../components/settings/Sessions";
import { Tokens } from "../components/settings/Tokens";
import { Button } from "../components/ui/button";
import { Card } from "../components/ui/card";
import { Field, Select } from "../components/ui/field";
import { useToast } from "../components/ui/toast";
import i18n, { type Language } from "../i18n";
import { useTheme, type Theme } from "../theme";

const THEMES: Theme[] = ["system", "light", "dark"];

function GeneralForm({ saved, canWrite }: { saved: SavedSettings; canWrite: boolean }) {
  const { t } = useTranslation();
  const toast = useToast();
  const queryClient = useQueryClient();
  const [theme, setTheme] = useTheme();
  const [language, setLanguage] = useState<Language>(saved.language);
  const [timezone, setTimezone] = useState(saved.timezone ?? browserTimezone());

  const save = useMutation({
    mutationFn: () => api.put("settings", { language, timezone }),
    onSuccess: () => {
      void i18n.changeLanguage(language);
      toast(t("settings.saved"));
      return queryClient.invalidateQueries({ queryKey: keys.settings });
    },
    onError: (error) => toast(errorMessage(t, error), "error"),
  });

  return (
    <Card className="space-y-4">
      <h2 className="text-lg font-semibold">{t("settings.general")}</h2>
      <RegionFields language={language} timezone={timezone} onLanguage={setLanguage} onTimezone={setTimezone} />
      {canWrite ? (
        <Button disabled={save.isPending} onClick={() => save.mutate()}>
          {t("settings.save")}
        </Button>
      ) : null}
      <Field label={t("settings.theme")}>
        {(props) => (
          <Select {...props} value={theme} onChange={(event) => setTheme(event.target.value as Theme)}>
            {THEMES.map((option) => (
              <option key={option} value={option}>
                {t(`settings.themes.${option}`)}
              </option>
            ))}
          </Select>
        )}
      </Field>
    </Card>
  );
}

function General({ canWrite }: { canWrite: boolean }) {
  const settings = useSettings();
  if (!settings.data) return null;
  return <GeneralForm key={`${settings.data.language}-${settings.data.timezone}`} saved={settings.data} canWrite={canWrite} />;
}

function SignOut() {
  const { t } = useTranslation();
  const toast = useToast();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const logout = useMutation({
    mutationFn: () => api.post("auth/logout"),
    onSuccess: () => {
      setCsrfToken(null);
      queryClient.setQueryData(keys.me, null);
      navigate("/login");
    },
    onError: (error) => toast(errorMessage(t, error), "error"),
  });
  return (
    <Button variant="secondary" disabled={logout.isPending} onClick={() => logout.mutate()}>
      {t("settings.logout")}
    </Button>
  );
}

export function Settings() {
  const { t } = useTranslation();
  const me = useMe();
  const canWrite = me.data?.scopes.includes("admin") ?? false;
  // Passwords, PINs, sessions and tokens are for the full admin only, never a PIN or a token.
  const fullAdmin = me.data?.full_admin ?? false;
  return (
    <section aria-labelledby="settings-title" className="space-y-4">
      <h1 id="settings-title" className="text-2xl font-bold">
        {t("settings.title")}
      </h1>
      <General canWrite={canWrite} />
      {fullAdmin ? (
        <>
          <Security />
          <Sessions />
          <Tokens />
        </>
      ) : null}
      {me.data?.kind === "admin" || me.data?.kind === "pin" ? <SignOut /> : null}
    </section>
  );
}
