import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useEffect, useRef, useState } from "react";
import { useTranslation } from "react-i18next";
import { Link, useNavigate, useParams } from "react-router-dom";

import { errorMessage } from "../api/errors";
import {
  keys,
  useAdapters,
  useDiscovery,
  useMe,
  usePairing,
  usePolicies,
  useTvs,
  type Adapter,
  type Pairing,
} from "../api/hooks";
import { api } from "../api/http";
import { Button } from "../components/ui/button";
import { Card } from "../components/ui/card";
import { Field, Input, Select } from "../components/ui/field";
import { useToast } from "../components/ui/toast";

/** What is being paired: a TV found or typed (new), or a stored TV (`tvId`) whose key was lost. */
interface Target {
  adapterId?: string;
  host?: string;
  name?: string;
  tvId?: string;
}

const PAIRING_ERRORS = { tv_exists: "errors.tv_exists", adapter_mismatch: "errors.adapter_mismatch" };

function Instructions({ adapterId }: { adapterId: string | undefined }) {
  const { t } = useTranslation();
  const key = `pairing.instructions.${adapterId}`;
  return <p>{t(key, { defaultValue: t("pairing.instructions.generic") })}</p>;
}

function Countdown({ until }: { until: string }) {
  const { t } = useTranslation();
  const [now, setNow] = useState(() => Date.now());
  useEffect(() => {
    const timer = setInterval(() => setNow(Date.now()), 1000);
    return () => clearInterval(timer);
  }, []);
  const seconds = Math.max(0, Math.round((new Date(until).getTime() - now) / 1000));
  return (
    <p className="text-sm text-muted">
      {t("pairing.timeLeft", { time: `${Math.floor(seconds / 60)}:${String(seconds % 60).padStart(2, "0")}` })}
    </p>
  );
}

function FindStep({ onChoose }: { onChoose: (target: Target) => void }) {
  const { t } = useTranslation();
  const discovery = useDiscovery();
  const adapters = useAdapters();
  const choices = adapters.data ?? [];
  const [adapterId, setAdapterId] = useState("");
  const [host, setHost] = useState("");
  const selected = adapterId || choices[0]?.id || "";

  return (
    <div className="space-y-6">
      <Card className="space-y-3">
        <div className="flex items-center justify-between gap-2">
          <h2 className="text-lg font-semibold">{t("pairing.foundTitle")}</h2>
          <Button variant="secondary" disabled={discovery.isFetching} onClick={() => void discovery.refetch()}>
            {t("pairing.searchAgain")}
          </Button>
        </div>
        {discovery.isFetching ? <p role="status">{t("pairing.searching")}</p> : null}
        {discovery.error ? <p role="alert">{errorMessage(t, discovery.error)}</p> : null}
        {!discovery.isFetching && discovery.data?.length === 0 ? (
          <p className="text-muted">{t("pairing.noneFound")}</p>
        ) : null}
        <ul className="divide-y divide-line">
          {(discovery.isFetching ? [] : (discovery.data ?? [])).map((found) => (
            <li key={`${found.adapter_id}/${found.host}`} className="flex items-center justify-between gap-3 py-2">
              <div>
                <p className="font-medium">{found.name}</p>
                <p className="text-sm text-muted">
                  {[found.adapter_name, found.model, found.host].filter(Boolean).join(" · ")}
                </p>
              </div>
              {found.already_added ? (
                <span className="text-sm text-muted">{t("pairing.alreadyAdded")}</span>
              ) : (
                <Button
                  aria-label={t("pairing.choose", { name: found.name })}
                  onClick={() => onChoose({ adapterId: found.adapter_id, host: found.host, name: found.name })}
                >
                  {t("pairing.pick")}
                </Button>
              )}
            </li>
          ))}
        </ul>
      </Card>

      <Card className="space-y-3">
        <h2 className="text-lg font-semibold">{t("pairing.manualTitle")}</h2>
        <p className="text-sm text-muted">{t("pairing.manualHelp")}</p>
        <Field label={t("pairing.brand")}>
          {(props) => (
            <Select {...props} value={selected} onChange={(event) => setAdapterId(event.target.value)}>
              {choices.map((adapter: Adapter) => (
                <option key={adapter.id} value={adapter.id}>
                  {adapter.display_name}
                </option>
              ))}
            </Select>
          )}
        </Field>
        <Field label={t("pairing.address")}>
          {(props) => (
            <Input
              {...props}
              value={host}
              placeholder="10.0.0.20"
              onChange={(event) => setHost(event.target.value)}
            />
          )}
        </Field>
        <Button disabled={selected === "" || host.trim() === ""} onClick={() => onChoose({ adapterId: selected, host: host.trim() })}>
          {t("pairing.continue")}
        </Button>
      </Card>
    </div>
  );
}

function PairStep({
  target,
  onDone,
  onBack,
}: {
  target: Target;
  onDone: (pairing: Pairing) => void;
  onBack: () => void;
}) {
  const { t } = useTranslation();
  const toast = useToast();
  const [pairingId, setPairingId] = useState<string | null>(null);
  const live = useRef<string | null>(null);
  const pairing = usePairing(pairingId);
  const state = pairing.data?.state;

  const start = useMutation({
    mutationFn: () =>
      api.post<Pairing>("pairings", {
        adapter_id: target.tvId ? undefined : target.adapterId,
        host: target.tvId ? undefined : target.host,
        name: target.tvId ? undefined : target.name,
        tv_id: target.tvId,
      }),
    onSuccess: (created) => {
      live.current = created.id;
      setPairingId(created.id);
    },
    onError: (error) => toast(errorMessage(t, error, PAIRING_ERRORS), "error"),
  });

  // Leaving the page while the TV still waits for an answer abandons the pairing.
  useEffect(
    () => () => {
      if (live.current) void api.delete(`pairings/${live.current}`).catch(() => undefined);
    },
    [],
  );

  useEffect(() => {
    if (pairing.data?.state === "completed") {
      live.current = null;
      onDone(pairing.data);
    }
  }, [pairing.data, onDone]);

  function retry() {
    if (live.current) void api.delete(`pairings/${live.current}`).catch(() => undefined);
    live.current = null;
    setPairingId(null);
    start.mutate();
  }

  const waiting = state === "waiting_for_user" || (pairingId !== null && pairing.isPending);

  return (
    <Card className="space-y-4">
      <h2 className="text-lg font-semibold">{t("pairing.pairTitle")}</h2>
      <p className="text-sm text-muted">
        {target.host ? t("pairing.target", { host: target.host }) : null}
      </p>
      <Instructions adapterId={target.adapterId} />
      {waiting ? (
        <div role="status" className="space-y-1">
          <p className="font-medium">{t("pairing.waiting")}</p>
          {pairing.data ? <Countdown until={pairing.data.expires_at} /> : null}
        </div>
      ) : null}
      {state === "failed" ? <p role="alert">{t("pairing.failed")}</p> : null}
      {state === "expired" ? <p role="alert">{t("pairing.expired")}</p> : null}
      {pairing.error ? <p role="alert">{errorMessage(t, pairing.error)}</p> : null}
      <div className="flex justify-end gap-2">
        <Button variant="secondary" onClick={onBack}>
          {t("actions.cancel")}
        </Button>
        {state === "failed" || state === "expired" ? (
          <Button onClick={retry}>{t("pairing.retry")}</Button>
        ) : (
          <Button disabled={start.isPending || waiting} onClick={() => start.mutate()}>
            {t("pairing.start")}
          </Button>
        )}
      </div>
    </Card>
  );
}

function FinishStep({ tvId, suggested }: { tvId: string; suggested: string }) {
  const { t } = useTranslation();
  const toast = useToast();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const policies = usePolicies();
  const adapters = useAdapters();
  const tvs = useTvs();
  const tv = tvs.data?.find((candidate) => candidate.id === tvId);
  const [name, setName] = useState(suggested);
  const [policyId, setPolicyId] = useState("");
  const capabilities = adapters.data?.find((a) => a.id === tv?.adapter_id)?.capabilities ?? [];

  const save = useMutation({
    mutationFn: () =>
      api.patch(`tvs/${tvId}`, {
        name: name.trim(),
        policy_id: policyId === "" ? null : Number(policyId),
      }),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: keys.tvs });
      void queryClient.invalidateQueries({ queryKey: keys.policies });
      toast(t("pairing.added"), "info");
      navigate("/");
    },
    onError: (error) => toast(errorMessage(t, error), "error"),
  });

  return (
    <Card className="space-y-4">
      <h2 className="text-lg font-semibold">{t("pairing.finishTitle")}</h2>
      <p className="text-sm text-muted">{t("pairing.finishHelp")}</p>
      <Field label={t("tvDetail.name")}>
        {(props) => <Input {...props} value={name} onChange={(event) => setName(event.target.value)} />}
      </Field>
      <Field label={t("tvDetail.rules")}>
        {(props) => (
          <Select {...props} value={policyId} onChange={(event) => setPolicyId(event.target.value)}>
            <option value="">{t("tvDetail.noRules")}</option>
            {policies.data?.map((policy) => (
              <option key={policy.id} value={String(policy.id)}>
                {policy.name}
              </option>
            ))}
          </Select>
        )}
      </Field>
      {capabilities.length > 0 ? (
        <div>
          <h3 className="text-sm font-semibold">{t("pairing.capabilities")}</h3>
          <ul className="mt-1 flex flex-wrap gap-2 text-sm text-muted">
            {capabilities.map((capability) => (
              <li key={capability}>{t(`pairing.capability.${capability}`, { defaultValue: capability })}</li>
            ))}
          </ul>
        </div>
      ) : null}
      <div className="flex justify-end">
        <Button disabled={name.trim() === "" || save.isPending} onClick={() => save.mutate()}>
          {t("pairing.finish")}
        </Button>
      </div>
    </Card>
  );
}

export function AddTv() {
  const { t } = useTranslation();
  const toast = useToast();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const { id: tvId } = useParams();
  const me = useMe();
  const tvs = useTvs();
  const stored = tvId ? tvs.data?.find((tv) => tv.id === tvId) : undefined;
  const [chosen, setChosen] = useState<Target | null>(null);
  const [added, setAdded] = useState<{ tvId: string; name: string } | null>(null);
  const canAdmin = me.data?.scopes.includes("admin") ?? false;

  const target: Target | null = tvId
    ? stored
      ? { tvId, adapterId: stored.adapter_id, host: stored.host, name: stored.name }
      : null
    : chosen;

  function done(pairing: Pairing) {
    void queryClient.invalidateQueries({ queryKey: keys.tvs });
    if (tvId) {
      toast(t("pairing.paired"), "info");
      navigate(`/tvs/${tvId}`);
    } else if (pairing.tv_id) {
      setAdded({ tvId: pairing.tv_id, name: chosen?.name ?? "" });
    }
  }

  let body;
  if (!canAdmin && me.data) body = <p role="alert">{t("errors.forbidden")}</p>;
  else if (added) body = <FinishStep tvId={added.tvId} suggested={added.name} />;
  else if (target) {
    body = (
      <PairStep
        target={target}
        onDone={done}
        onBack={() => (tvId ? navigate(`/tvs/${tvId}`) : setChosen(null))}
      />
    );
  } else if (tvId) body = <p role="status">{t("auth.loading")}</p>;
  else body = <FindStep onChoose={setChosen} />;

  return (
    <section aria-labelledby="add-tv-title" className="space-y-4">
      <Link to="/" className="text-sm text-muted hover:underline">
        {t("tvDetail.back")}
      </Link>
      <h1 id="add-tv-title" className="text-2xl font-bold">
        {tvId ? t("pairing.repairTitle") : t("pairing.title")}
      </h1>
      {body}
    </section>
  );
}
