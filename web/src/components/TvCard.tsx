import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { useTranslation } from "react-i18next";
import { Link } from "react-router-dom";

import { errorMessage } from "../api/errors";
import { keys, type Tv } from "../api/hooks";
import { api } from "../api/http";
import { Button } from "./ui/button";
import { Badge, Card } from "./ui/card";
import { Dialog } from "./ui/dialog";
import { Field, Select } from "./ui/field";
import { useToast } from "./ui/toast";

const PAUSE_MINUTES = 30;
const BONUS_MINUTES = [15, 30];
const DURATIONS = [15, 30, 60, 120];
const MIDNIGHT = "midnight";

type Tone = "neutral" | "ok" | "warn" | "danger";

interface Job {
  call: () => Promise<unknown>;
  done: string;
}

function minutes(seconds: number): number {
  return Math.ceil(seconds / 60);
}

/** Who the TV is right now, in words: power, reachability and pairing. */
function presence(tv: Tv): { key: string; tone: Tone } {
  if (!tv.enabled) return { key: "tv.power.disabled", tone: "neutral" };
  const status = tv.status;
  if (tv.needs_pairing || status?.pairing_required) return { key: "tv.power.pairing", tone: "warn" };
  if (!status?.connected) return { key: "tv.power.offline", tone: "danger" };
  return { key: `tv.power.${status.power ?? "on"}`, tone: status.power === "on" ? "ok" : "neutral" };
}

function Verdict({ tv }: { tv: Tv }) {
  const { t } = useTranslation();
  const decision = tv.status?.decision;
  if (!decision) return null;
  if (decision.kind === "block") {
    return (
      <Badge tone="danger">
        {t("tv.decision.block")}
        {decision.reason ? `: ${t(`tv.reason.${decision.reason}`, { defaultValue: decision.reason })}` : ""}
      </Badge>
    );
  }
  if (decision.kind === "warn") {
    return (
      <Badge tone="warn">
        {t("tv.warn", {
          minutes: decision.minutes_left ?? 0,
          limit: t(`tv.limit.${decision.limit}`, { defaultValue: "" }),
        })}
      </Badge>
    );
  }
  return <Badge tone="ok">{t("tv.decision.allow")}</Badge>;
}

function Usage({ tv }: { tv: Tv }) {
  const { t } = useTranslation();
  const status = tv.status;
  if (!status) return null;
  const watched = minutes(status.watched_seconds);
  const left = status.remaining_seconds === null ? null : minutes(status.remaining_seconds);
  const total = left === null ? 0 : watched + left;
  return (
    <div className="space-y-1">
      <p className="text-sm">
        {t("tv.watched", { minutes: watched })}
        {left === null ? ` · ${t("tv.noLimit")}` : ` · ${t("tv.left", { minutes: left })}`}
      </p>
      {total > 0 ? (
        <div
          role="progressbar"
          aria-label={t("tv.usageBar")}
          aria-valuemin={0}
          aria-valuemax={total}
          aria-valuenow={watched}
          className="h-2 overflow-hidden rounded-full bg-page ring-1 ring-line"
        >
          <div className="h-full bg-brand" style={{ width: `${Math.min(100, (watched / total) * 100)}%` }} />
        </div>
      ) : null}
    </div>
  );
}

function OverrideDialog({
  open,
  allow,
  onClose,
  onApply,
}: {
  open: boolean;
  allow: boolean;
  onClose: () => void;
  onApply: (length: string) => void;
}) {
  const { t } = useTranslation();
  const [length, setLength] = useState("30");
  return (
    <Dialog
      open={open}
      onOpenChange={(next) => !next && onClose()}
      title={t(allow ? "actions.allowTitle" : "actions.blockTitle")}
      description={t(allow ? "actions.allowHelp" : "actions.blockHelp")}
    >
      <Field label={t("actions.duration")}>
        {(props) => (
          <Select {...props} value={length} onChange={(event) => setLength(event.target.value)}>
            {DURATIONS.map((value) => (
              <option key={value} value={value}>
                {t("actions.minutes", { minutes: value })}
              </option>
            ))}
            <option value={MIDNIGHT}>{t("actions.untilMidnight")}</option>
          </Select>
        )}
      </Field>
      <div className="flex justify-end gap-2">
        <Button variant="secondary" onClick={onClose}>
          {t("actions.cancel")}
        </Button>
        <Button onClick={() => onApply(length)}>{t("actions.apply")}</Button>
      </div>
    </Dialog>
  );
}

/** One TV: live status and, for callers with the control scope, the parent actions. */
export function TvCard({
  tv,
  canControl,
  canAdmin = false,
}: {
  tv: Tv;
  canControl: boolean;
  canAdmin?: boolean;
}) {
  const { t } = useTranslation();
  const toast = useToast();
  const queryClient = useQueryClient();
  const [dialog, setDialog] = useState<"allow" | "block" | null>(null);

  const run = useMutation({
    mutationFn: (job: Job) => job.call(),
    onSuccess: (_, job) => {
      toast(job.done);
      void queryClient.invalidateQueries({ queryKey: keys.tvs });
    },
    onError: (error) => toast(errorMessage(t, error), "error"),
  });

  const base = `tvs/${tv.id}`;
  const apply = (allow: boolean) => (length: string) => {
    setDialog(null);
    const body =
      length === MIDNIGHT
        ? { allow, until_midnight: true }
        : { allow, minutes: Number(length), until_midnight: false };
    run.mutate({ call: () => api.post(`${base}/override`, body), done: t("actions.overrideSet") });
  };

  const where = presence(tv);
  const watching = tv.status?.foreground_app;
  const active = tv.enabled && !tv.needs_pairing && tv.status?.connected;

  return (
    <Card aria-labelledby={`tv-${tv.id}`} className="space-y-3">
      <div className="flex items-start justify-between gap-2">
        <h2 id={`tv-${tv.id}`} className="text-lg font-semibold">
          <Link to={`/tvs/${tv.id}`} className="hover:underline">
            {tv.name}
          </Link>
        </h2>
        <Badge tone={where.tone}>{t(where.key)}</Badge>
      </div>
      <div aria-live="polite" className="space-y-2">
        {watching ? <p className="text-sm text-muted">{t("tv.watching", { app: watching })}</p> : null}
        <Verdict tv={tv} />
        <Usage tv={tv} />
      </div>
      {canAdmin && where.key === "tv.power.pairing" ? (
        <Link to={`/tvs/${tv.id}/pair`} className="inline-block text-sm text-brand underline">
          {t("pairing.pairAgain")}
        </Link>
      ) : null}
      {canControl && active ? (
        <div className="flex flex-wrap gap-2">
          <Button
            variant="secondary"
            disabled={run.isPending}
            onClick={() =>
              run.mutate({
                call: () => api.post(`${base}/pause`, { minutes: PAUSE_MINUTES }),
                done: t("actions.paused", { minutes: PAUSE_MINUTES }),
              })
            }
          >
            {t("actions.pause", { minutes: PAUSE_MINUTES })}
          </Button>
          {BONUS_MINUTES.map((value) => (
            <Button
              key={value}
              variant="secondary"
              disabled={run.isPending}
              onClick={() =>
                run.mutate({
                  call: () => api.post(`${base}/bonus`, { minutes: value }),
                  done: t("actions.bonusAdded", { minutes: value }),
                })
              }
            >
              {t("actions.bonus", { minutes: value })}
            </Button>
          ))}
          <Button variant="secondary" disabled={run.isPending} onClick={() => setDialog("allow")}>
            {t("actions.allow")}
          </Button>
          <Button variant="secondary" disabled={run.isPending} onClick={() => setDialog("block")}>
            {t("actions.block")}
          </Button>
          <Button
            variant="ghost"
            disabled={run.isPending}
            onClick={() =>
              run.mutate({
                call: () => api.delete(`${base}/override`),
                done: t("actions.overrideCleared"),
              })
            }
          >
            {t("actions.clear")}
          </Button>
        </div>
      ) : null}
      <OverrideDialog
        key={dialog ?? "closed"}
        open={dialog !== null}
        allow={dialog === "allow"}
        onClose={() => setDialog(null)}
        onApply={apply(dialog === "allow")}
      />
    </Card>
  );
}
