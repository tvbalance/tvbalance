import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { useTranslation } from "react-i18next";

import { errorMessage } from "../../api/errors";
import { keys, useTls, type TlsStatus } from "../../api/hooks";
import { api } from "../../api/http";
import { currentLanguage } from "../../i18n";
import { Button, buttonClasses } from "../ui/button";
import { Badge, Card } from "../ui/card";
import { Dialog } from "../ui/dialog";
import { useToast } from "../ui/toast";

const PLATFORMS = ["ios", "android", "windows", "mac"] as const;

function Install() {
  const { t } = useTranslation();
  return (
    <div className="space-y-3">
      <p className="text-sm text-muted">{t("secure.caHelp")}</p>
      <div className="flex flex-wrap gap-2">
        <a
          className={buttonClasses("secondary")}
          href="api/v1/tls/ca.crt"
          download
        >
          {t("secure.downloadCa")}
        </a>
        <a
          className={buttonClasses("secondary")}
          href="api/v1/tls/ca.mobileconfig"
        >
          {t("secure.downloadProfile")}
        </a>
      </div>
      <ul className="space-y-1 text-sm">
        {PLATFORMS.map((platform) => (
          <li key={platform}>
            <details>
              <summary className="cursor-pointer font-medium">
                {t(`secure.platform.${platform}.name`)}
              </summary>
              <p className="mt-1 text-muted">
                {t(`secure.platform.${platform}.steps`)}
              </p>
            </details>
          </li>
        ))}
      </ul>
    </div>
  );
}

function Rotate() {
  const { t } = useTranslation();
  const toast = useToast();
  const queryClient = useQueryClient();
  const [open, setOpen] = useState(false);
  const rotate = useMutation({
    mutationFn: () => api.post<TlsStatus>("tls/rotate"),
    onSuccess: (next) => {
      queryClient.setQueryData(keys.tls, next);
      setOpen(false);
      toast(t("secure.rotated"));
    },
    onError: (error) => toast(errorMessage(t, error), "error"),
  });
  return (
    <>
      <Button variant="secondary" onClick={() => setOpen(true)}>
        {t("secure.rotate")}
      </Button>
      <Dialog
        open={open}
        onOpenChange={setOpen}
        title={t("secure.rotateTitle")}
        description={t("secure.rotateHelp")}
      >
        <div className="flex justify-end gap-2">
          <Button variant="secondary" onClick={() => setOpen(false)}>
            {t("actions.cancel")}
          </Button>
          <Button
            variant="danger"
            disabled={rotate.isPending}
            onClick={() => rotate.mutate()}
          >
            {t("secure.rotateConfirm")}
          </Button>
        </div>
      </Dialog>
    </>
  );
}

/** Settings card: where HTTPS answers, and how to make devices trust the local certificate. */
export function SecureConnection() {
  const { t } = useTranslation();
  const tls = useTls();
  const status = tls.data;
  if (!status) return null;
  const date = new Intl.DateTimeFormat(currentLanguage(), {
    dateStyle: "medium",
  });
  return (
    <Card className="space-y-3">
      <h2 className="text-lg font-semibold">{t("secure.title")}</h2>
      <p className="text-sm text-muted">{t("secure.help")}</p>
      <p>
        <Badge tone={status.active ? "ok" : status.error ? "warn" : "neutral"}>
          {t(status.active ? "secure.on" : "secure.off")}
        </Badge>
      </p>
      {status.mode === "off" ? (
        <p className="text-sm">{t("secure.offNote")}</p>
      ) : null}
      {status.error ? <p className="text-sm">{status.error}</p> : null}
      {status.active ? (
        <div className="space-y-2 text-sm">
          <div>
            <h3 className="font-medium">{t("secure.addresses")}</h3>
            <ul>
              {status.urls.map((url) => (
                <li key={url}>
                  <a href={url} className="text-brand underline">
                    {url}
                  </a>
                </li>
              ))}
            </ul>
          </div>
          {status.expires_at ? (
            <p className="text-muted">
              {t("secure.expires", {
                date: date.format(new Date(status.expires_at)),
              })}
            </p>
          ) : null}
          {status.skipped_names.length > 0 ? (
            <p className="text-muted">
              {t("secure.skipped", { names: status.skipped_names.join(", ") })}
            </p>
          ) : null}
        </div>
      ) : null}
      {status.mode === "custom" ? (
        <p className="text-sm">{t("secure.customNote")}</p>
      ) : null}
      {status.mode === "auto" && status.active && status.ca_fingerprint ? (
        <>
          <div className="text-sm">
            <h3 className="font-medium">{t("secure.fingerprint")}</h3>
            <code className="break-all text-xs">{status.ca_fingerprint}</code>
          </div>
          <Install />
          <Rotate />
        </>
      ) : null}
    </Card>
  );
}
