import { useState } from "react";
import { useTranslation } from "react-i18next";

import { useInfo } from "../api/hooks";
import { secureAddress } from "../https";
import { Button } from "./ui/button";

const DISMISSED = "tvbalance.https-banner";

function wasDismissed(): boolean {
  try {
    return localStorage.getItem(DISMISSED) === "1";
  } catch {
    return false;
  }
}

function remember(): void {
  try {
    localStorage.setItem(DISMISSED, "1");
  } catch {
    // The banner just comes back next time.
  }
}

/** On a plain http page, points to the HTTPS address when the Engine has one. */
export function HttpsBanner({
  where = window.location,
}: {
  where?: Parameters<typeof secureAddress>[0];
}) {
  const { t } = useTranslation();
  const info = useInfo();
  const [hidden, setHidden] = useState(wasDismissed);
  const address = secureAddress(where, info.data?.https_port);
  if (hidden || !address) return null;
  return (
    <div
      role="status"
      className="mb-4 flex flex-wrap items-center gap-3 rounded-xl border border-line bg-card p-3 text-sm"
    >
      <p className="flex-1">{t("https.banner")}</p>
      <a href={address} className="font-medium text-brand underline">
        {t("https.open")}
      </a>
      <Button
        variant="ghost"
        onClick={() => {
          remember();
          setHidden(true);
        }}
      >
        {t("https.dismiss")}
      </Button>
    </div>
  );
}
