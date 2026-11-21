import { useQueryClient } from "@tanstack/react-query";
import { useEffect, type ReactNode } from "react";
import { useTranslation } from "react-i18next";
import { Navigate } from "react-router-dom";

import { useLiveEvents } from "../api/events";
import { keys, useAuthState, useMe } from "../api/hooks";
import { setUnauthorizedHandler } from "../api/http";

/**
 * Lets the signed-in caller through and keeps the live event stream open for them.
 * First run goes to the welcome flow, everyone else without a credential to sign-in.
 * Under Home Assistant Ingress `auth/me` already succeeds, so nobody ever sees a form.
 */
export function AuthGate({ children }: { children: ReactNode }) {
  const { t } = useTranslation();
  const queryClient = useQueryClient();
  const state = useAuthState();
  const me = useMe();
  const signedIn = !!me.data;

  useEffect(() => {
    setUnauthorizedHandler(() => void queryClient.invalidateQueries({ queryKey: keys.me }));
    return () => setUnauthorizedHandler(null);
  }, [queryClient]);
  useLiveEvents(queryClient, signedIn);

  if (state.isPending || me.isPending) {
    return <p role="status">{t("auth.loading")}</p>;
  }
  if (state.error || me.error) {
    return <p role="alert">{t("auth.error")}</p>;
  }
  if (state.data.setup_required) {
    return <Navigate to="/welcome" replace />;
  }
  if (!me.data) {
    return <Navigate to="/login" replace />;
  }
  return <>{children}</>;
}
