import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useTranslation } from "react-i18next";

import { errorMessage } from "../../api/errors";
import { keys, useInfo, usePushDevices, type PushDevice, type PushEvent } from "../../api/hooks";
import { api } from "../../api/http";
import { secureAddress } from "../../https";
import { currentLanguage } from "../../i18n";
import {
  appUrl,
  currentSubscription,
  permission,
  PermissionDenied,
  pushSupport,
  subscribeBrowser,
} from "../../push-client";
import { Button } from "../ui/button";
import { Badge, Card } from "../ui/card";
import { useToast } from "../ui/toast";

const EVENTS: PushEvent[] = ["pairing_lost", "tv_unreachable", "blocked", "time_warning", "weekly_report"];

export function Notifications() {
  const { t } = useTranslation();
  const toast = useToast();
  const queryClient = useQueryClient();
  const support = pushSupport();
  const secure = secureAddress(window.location, useInfo().data?.https_port);
  const blocked = support === "ok" && permission() === "denied";
  const usable = support === "ok" && !blocked;

  const browser = useQuery({
    queryKey: [...keys.push, "browser"],
    queryFn: currentSubscription,
    enabled: usable,
  });
  const endpoint = browser.data?.endpoint ?? null;
  const devices = usePushDevices(endpoint, usable && browser.isSuccess);
  const here = devices.data?.find((d) => d.current);
  const others = (devices.data ?? []).filter((d) => !d.current);
  const format = new Intl.DateTimeFormat(currentLanguage(), { dateStyle: "short", timeStyle: "short" });

  const refresh = () => queryClient.invalidateQueries({ queryKey: keys.push });
  const fail = (error: unknown) => toast(errorMessage(t, error), "error");

  const enable = useMutation({
    mutationFn: async () => {
      const { public_key } = await api.get<{ public_key: string }>("push/key");
      const json = (await subscribeBrowser(public_key)).toJSON();
      return api.post("push/subscriptions", {
        endpoint: json.endpoint,
        keys: json.keys,
        language: currentLanguage(),
        app_url: appUrl(),
      });
    },
    onSuccess: () => {
      toast(t("push.on"));
      return refresh();
    },
    onError: (error) => (error instanceof PermissionDenied ? refresh() : fail(error)),
  });

  const remove = useMutation({
    mutationFn: async ({ device, unsubscribe }: { device: PushDevice; unsubscribe: boolean }) => {
      await api.delete(`push/subscriptions/${device.id}`);
      if (unsubscribe) await (await currentSubscription())?.unsubscribe();
    },
    onSuccess: (_, { unsubscribe }) => {
      toast(t(unsubscribe ? "push.off" : "push.removed"));
      return refresh();
    },
    onError: fail,
  });

  const setEvents = useMutation({
    mutationFn: ({ device, events }: { device: PushDevice; events: PushEvent[] }) =>
      api.patch(`push/subscriptions/${device.id}`, { events }),
    onSuccess: refresh,
    onError: fail,
  });

  const test = useMutation({
    mutationFn: (device: PushDevice) =>
      api.post<{ result: "delivered" | "gone" | "failed" }>(`push/subscriptions/${device.id}/test`),
    onSuccess: ({ result }) => {
      const key = { delivered: "testDelivered", gone: "testGone", failed: "testFailed" }[result];
      toast(t(`push.${key}`), result === "delivered" ? "info" : "error");
      return refresh();
    },
    onError: fail,
  });

  const toggle = (device: PushDevice, event: PushEvent) => {
    const events = device.events.includes(event)
      ? device.events.filter((e) => e !== event)
      : [...device.events, event];
    setEvents.mutate({ device, events });
  };

  const describe = (device: PushDevice) => device.user_agent || t("push.unknownDevice");

  return (
    <Card className="space-y-3">
      <h2 className="text-lg font-semibold">{t("push.title")}</h2>
      <p className="text-sm text-muted">{t("push.help")}</p>
      {support === "insecure" ? <p className="text-sm">{t("push.insecure")}</p> : null}
      {support === "insecure" && secure ? (
        <p className="text-sm">
          <a href={secure} className="text-brand underline">
            {t("push.secureAddress")}
          </a>
        </p>
      ) : null}
      {support === "unsupported" ? <p className="text-sm">{t("push.unsupported")}</p> : null}
      {blocked ? <p className="text-sm">{t("push.denied")}</p> : null}

      {usable && browser.isSuccess && !here ? (
        <Button disabled={enable.isPending} onClick={() => enable.mutate()}>
          {t("push.enable")}
        </Button>
      ) : null}

      {here ? (
        <div className="space-y-3">
          <p className="flex items-center gap-2 text-sm">
            <Badge tone="ok">{t("push.enabled")}</Badge>
          </p>
          <fieldset className="space-y-1">
            <legend className="text-sm font-medium">{t("push.events")}</legend>
            {EVENTS.map((event) => (
              <label key={event} className="flex items-center gap-2 text-sm">
                <input
                  type="checkbox"
                  checked={here.events.includes(event)}
                  onChange={() => toggle(here, event)}
                />
                {t(`push.event.${event}`)}
              </label>
            ))}
          </fieldset>
          <div className="flex flex-wrap gap-2">
            <Button variant="secondary" disabled={test.isPending} onClick={() => test.mutate(here)}>
              {t("push.test")}
            </Button>
            <Button
              variant="danger"
              disabled={remove.isPending}
              onClick={() => remove.mutate({ device: here, unsubscribe: true })}
            >
              {t("push.disable")}
            </Button>
          </div>
        </div>
      ) : null}

      {others.length > 0 ? (
        <div className="space-y-1">
          <h3 className="text-sm font-medium">{t("push.otherDevices")}</h3>
          <ul className="divide-y divide-line">
            {others.map((device) => (
              <li key={device.id} className="flex flex-wrap items-center justify-between gap-2 py-2">
                <div className="space-y-0.5 text-sm">
                  <p className="font-medium">{describe(device)}</p>
                  <p className="text-muted">
                    {device.last_sent_at
                      ? t("push.lastSent", { when: format.format(new Date(device.last_sent_at)) })
                      : t("push.neverSent")}
                  </p>
                </div>
                <Button
                  variant="secondary"
                  aria-label={t("push.removeDevice", { device: describe(device) })}
                  onClick={() => remove.mutate({ device, unsubscribe: false })}
                >
                  {t("push.remove")}
                </Button>
              </li>
            ))}
          </ul>
        </div>
      ) : null}
    </Card>
  );
}
