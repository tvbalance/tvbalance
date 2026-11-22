import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useTranslation } from "react-i18next";

import { errorMessage } from "../api/errors";
import { keys, useActiveProfile } from "../api/hooks";
import { api } from "../api/http";
import { Button } from "./ui/button";
import { Card } from "./ui/card";
import { useToast } from "./ui/toast";

export function formatUntil(iso: string): string {
  return new Date(iso).toLocaleString([], { weekday: "short", hour: "2-digit", minute: "2-digit" });
}

/** The profile a person switched on, with a way to end it, and a note when the plan ignores it. */
export function ProfileBanner({ canControl }: { canControl: boolean }) {
  const { t } = useTranslation();
  const toast = useToast();
  const queryClient = useQueryClient();
  const profile = useActiveProfile();

  const stop = useMutation({
    mutationFn: () => api.delete("profiles/active"),
    onSuccess: () => {
      toast(t("profiles.stopped"));
      void queryClient.invalidateQueries({ queryKey: keys.profile });
      void queryClient.invalidateQueries({ queryKey: keys.tvs });
    },
    onError: (error) => toast(errorMessage(t, error), "error"),
  });

  const activation = profile.data?.activation;
  if (!activation) return null;
  return (
    <Card aria-label={t("profiles.banner")} className="space-y-2">
      <p className="font-medium">
        {t("profiles.active", { name: activation.name, until: formatUntil(activation.ends_at) })}
      </p>
      {profile.data?.effective ? null : <p className="text-sm text-muted">{t("profiles.requiresPro")}</p>}
      {canControl ? (
        <Button variant="secondary" disabled={stop.isPending} onClick={() => stop.mutate()}>
          {t("profiles.stop")}
        </Button>
      ) : null}
    </Card>
  );
}
