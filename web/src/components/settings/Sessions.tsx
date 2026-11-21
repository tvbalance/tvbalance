import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useTranslation } from "react-i18next";

import { errorMessage } from "../../api/errors";
import { keys, useSessions } from "../../api/hooks";
import { api } from "../../api/http";
import { currentLanguage } from "../../i18n";
import { Button } from "../ui/button";
import { Badge, Card } from "../ui/card";
import { useToast } from "../ui/toast";

export function Sessions() {
  const { t } = useTranslation();
  const toast = useToast();
  const queryClient = useQueryClient();
  const sessions = useSessions();
  const format = new Intl.DateTimeFormat(currentLanguage(), { dateStyle: "short", timeStyle: "short" });

  const refresh = () => queryClient.invalidateQueries({ queryKey: keys.sessions });
  const revoke = useMutation({
    mutationFn: (id: string) => api.delete(`auth/sessions/${id}`),
    onSuccess: refresh,
    onError: (error) => toast(errorMessage(t, error), "error"),
  });
  const revokeOthers = useMutation({
    mutationFn: () => api.delete("auth/sessions"),
    onSuccess: () => {
      toast(t("settings.othersSignedOut"));
      return refresh();
    },
    onError: (error) => toast(errorMessage(t, error), "error"),
  });

  const others = (sessions.data ?? []).filter((s) => !s.current);
  return (
    <Card className="space-y-3">
      <h2 className="text-lg font-semibold">{t("settings.sessions")}</h2>
      <p className="text-sm text-muted">{t("settings.sessionsHelp")}</p>
      <ul className="divide-y divide-line">
        {sessions.data?.map((s) => (
          <li key={s.id} className="flex flex-wrap items-center justify-between gap-2 py-2">
            <div className="space-y-0.5 text-sm">
              <p className="flex items-center gap-2 font-medium">
                {t(`settings.sessionKind.${s.kind}`)}
                {s.current ? <Badge tone="ok">{t("settings.thisDevice")}</Badge> : null}
              </p>
              <p className="text-muted">
                {t("settings.lastSeen", { when: format.format(new Date(s.last_seen_at)) })}
              </p>
            </div>
            {s.current ? null : (
              <Button
                variant="secondary"
                aria-label={t("settings.signOutSession", { when: format.format(new Date(s.last_seen_at)) })}
                onClick={() => revoke.mutate(s.id)}
              >
                {t("settings.signOut")}
              </Button>
            )}
          </li>
        ))}
      </ul>
      {others.length > 0 ? (
        <Button variant="danger" disabled={revokeOthers.isPending} onClick={() => revokeOthers.mutate()}>
          {t("settings.signOutOthers")}
        </Button>
      ) : null}
    </Card>
  );
}
