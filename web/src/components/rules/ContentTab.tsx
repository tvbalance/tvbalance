import { useState } from "react";
import { useTranslation } from "react-i18next";

import { useInventory, type Tv } from "../../api/hooks";
import type { PolicyDoc } from "../../presets";
import { Field, Input, Select, Switch } from "../ui/field";
import { IdList, type Choice } from "./IdList";

type Fallback = NonNullable<PolicyDoc["fallback"]>;
type Kind = Fallback["kind"] | "none";

function FallbackField({
  fallback,
  choices,
  onChange,
}: {
  fallback: PolicyDoc["fallback"];
  choices: Record<"app" | "input" | "channel", Choice[]>;
  onChange: (fallback: PolicyDoc["fallback"]) => void;
}) {
  const { t } = useTranslation();
  const kind: Kind = fallback?.kind ?? "none";
  const options = kind === "app" || kind === "input" || kind === "channel" ? choices[kind] : [];
  return (
    <div className="space-y-3">
      <Field label={t("rules.fallbackKind")} hint={t("rules.fallbackHelp")}>
        {(props) => (
          <Select
            {...props}
            value={kind}
            onChange={(event) => {
              const next = event.target.value as Kind;
              onChange(next === "none" ? null : { kind: next, id: null });
            }}
          >
            <option value="none">{t("rules.fallbackNone")}</option>
            <option value="home">{t("rules.fallbackHome")}</option>
            <option value="app">{t("rules.fallbackApp")}</option>
            <option value="input">{t("rules.fallbackInput")}</option>
            <option value="channel">{t("rules.fallbackChannel")}</option>
          </Select>
        )}
      </Field>
      {fallback && fallback.kind !== "home" ? (
        <Field label={t("rules.fallbackTarget")}>
          {(props) =>
            options.length > 0 ? (
              <Select
                {...props}
                value={fallback.id ?? ""}
                onChange={(event) => onChange({ ...fallback, id: event.target.value || null })}
              >
                <option value="">{t("rules.addPlaceholder")}</option>
                {fallback.id && !options.some((o) => o.id === fallback.id) ? (
                  <option value={fallback.id}>{fallback.id}</option>
                ) : null}
                {options.map((choice) => (
                  <option key={choice.id} value={choice.id}>
                    {choice.label}
                  </option>
                ))}
              </Select>
            ) : (
              <Input
                {...props}
                value={fallback.id ?? ""}
                onChange={(event) => onChange({ ...fallback, id: event.target.value || null })}
              />
            )
          }
        </Field>
      ) : null}
    </div>
  );
}

export function ContentTab({
  policy,
  tvs,
  onChange,
}: {
  policy: PolicyDoc;
  tvs: Tv[];
  onChange: (patch: Partial<PolicyDoc>) => void;
}) {
  const { t } = useTranslation();
  const [chosen, setChosen] = useState<string | null>(null);
  const tvId = chosen ?? tvs[0]?.id ?? null;
  const inventory = useInventory(tvId);

  const data = inventory.data;
  const choices = {
    app: (data?.apps ?? []).map((app) => ({
      id: app.id,
      label: app.name,
      icon: app.has_icon ? `api/v1/tvs/${tvId}/apps/${encodeURIComponent(app.id)}/icon` : undefined,
    })),
    input: (data?.inputs ?? []).map((input) => ({ id: input.id, label: input.label })),
    channel: (data?.channels ?? []).map((channel) => ({
      id: channel.id,
      label: channel.number ? `${channel.number} ${channel.name}` : channel.name,
    })),
  };
  const allowList = policy.allow_list_apps;

  return (
    <div className="space-y-6">
      {tvs.length > 0 ? (
        <section className="space-y-2">
          <Field label={t("rules.pickFrom")}>
            {(props) => (
              <Select {...props} value={tvId ?? ""} onChange={(event) => setChosen(event.target.value)}>
                {tvs.map((tv) => (
                  <option key={tv.id} value={tv.id}>
                    {tv.name}
                  </option>
                ))}
              </Select>
            )}
          </Field>
          {inventory.isPending ? <p role="status">{t("auth.loading")}</p> : null}
          {inventory.error ? (
            <p role="status" className="text-sm text-muted">
              {t("rules.inventoryOffline")}
            </p>
          ) : null}
        </section>
      ) : (
        <p className="text-sm text-muted">{t("rules.inventoryNoTv")}</p>
      )}

      <section className="space-y-4">
        <h3 className="font-semibold">{t("rules.blocked")}</h3>
        <IdList
          label={t("rules.apps")}
          value={policy.blocked_apps}
          choices={choices.app}
          onChange={(blocked_apps) => onChange({ blocked_apps })}
        />
        <IdList
          label={t("rules.inputs")}
          value={policy.blocked_inputs}
          choices={choices.input}
          onChange={(blocked_inputs) => onChange({ blocked_inputs })}
        />
        <IdList
          label={t("rules.channels")}
          value={policy.blocked_channels}
          choices={choices.channel}
          onChange={(blocked_channels) => onChange({ blocked_channels })}
        />
      </section>

      <section className="space-y-3">
        <div className="flex items-center justify-between gap-4">
          <div>
            <h3 className="font-semibold">{t("rules.allowListMode")}</h3>
            <p className="text-sm text-muted">{t("rules.allowListHelp")}</p>
          </div>
          <Switch
            label={t("rules.allowListMode")}
            checked={allowList !== null && allowList !== undefined}
            onChange={(on) => onChange({ allow_list_apps: on ? [] : null })}
          />
        </div>
        {allowList ? (
          <IdList
            label={t("rules.allowedApps")}
            value={allowList}
            choices={choices.app}
            onChange={(allow_list_apps) => onChange({ allow_list_apps })}
          />
        ) : null}
      </section>

      <section className="space-y-4">
        <div>
          <h3 className="font-semibold">{t("rules.alwaysAllowed")}</h3>
          <p className="text-sm text-muted">{t("rules.alwaysAllowedHelp")}</p>
        </div>
        <IdList
          label={t("rules.apps")}
          value={policy.always_allowed_apps}
          choices={choices.app}
          onChange={(always_allowed_apps) => onChange({ always_allowed_apps })}
        />
        <IdList
          label={t("rules.inputs")}
          value={policy.always_allowed_inputs}
          choices={choices.input}
          onChange={(always_allowed_inputs) => onChange({ always_allowed_inputs })}
        />
        <IdList
          label={t("rules.channels")}
          value={policy.always_allowed_channels}
          choices={choices.channel}
          onChange={(always_allowed_channels) => onChange({ always_allowed_channels })}
        />
      </section>

      <section className="space-y-3">
        <h3 className="font-semibold">{t("rules.fallback")}</h3>
        <FallbackField
          fallback={policy.fallback ?? null}
          choices={choices}
          onChange={(fallback) => onChange({ fallback })}
        />
      </section>
    </div>
  );
}
