import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { App } from "../App";
import type { Tv } from "../api/hooks";
import { setCsrfToken } from "../api/http";
import i18n from "../i18n";
import { FakeSocket, stubApi } from "../test/fakes";

const ME = {
  kind: "admin",
  name: "Admin",
  full_admin: true,
  scopes: ["read", "control", "admin"],
  session_id: "s",
  csrf_token: "csrf-1",
};

const TV = {
  id: "living",
  name: "Living room",
  adapter_id: "lg_webos",
  host: "203.0.113.50",
  enabled: true,
  needs_pairing: false,
  policy_id: 1,
  created_at: "2026-01-01T00:00:00Z",
  status: null,
} as unknown as Tv;

const USAGE = {
  tv_id: "living",
  days: [
    { day: "2026-03-02", watched_seconds: 3600, bonus_minutes: 0 },
    { day: "2026-03-03", watched_seconds: 1800, bonus_minutes: 0 },
  ],
};

const EVENTS = [
  { id: 2, tv_id: "living", occurred_at: "2026-03-03T18:00:00Z", type: "blocked", payload: { reason: "budget_exhausted" } },
  { id: 1, tv_id: "living", occurred_at: "2026-03-03T17:00:00Z", type: "mystery", payload: {} },
];

function renderAt(hash: string, extra: Record<string, object> = {}) {
  window.location.hash = hash;
  const fetchMock = stubApi({
    "GET auth/state": { setup_required: false },
    "GET auth/me": ME,
    "GET tvs": [TV],
    "GET policies": [{ id: 1, name: "School days", policy: {}, tv_ids: ["living"], updated_at: "x" }],
    "GET settings": { language: "en", timezone: null },
    "GET tvs/living/usage?days=7": USAGE,
    "GET events?limit=50": EVENTS,
    "GET events?limit=10&tv_id=living": EVENTS,
    ...extra,
  });
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  render(
    <QueryClientProvider client={client}>
      <App />
    </QueryClientProvider>,
  );
  return fetchMock;
}

function lastCall(fetchMock: ReturnType<typeof stubApi>, url: string, method: string) {
  const call = fetchMock.mock.calls
    .filter(([u, init]) => u === `api/v1/${url}` && ((init as RequestInit | undefined)?.method ?? "GET") === method)
    .at(-1)!;
  const init = call[1] as RequestInit;
  return {
    body: init.body ? JSON.parse(String(init.body)) : undefined,
    csrf: new Headers(init.headers).get("X-TVBalance-CSRF"),
  };
}

beforeEach(() => {
  void i18n.changeLanguage("en");
  FakeSocket.instances = [];
  vi.stubGlobal("WebSocket", FakeSocket);
});
afterEach(() => {
  vi.unstubAllGlobals();
  setCsrfToken(null);
});

describe("activity", () => {
  it("shows weekly usage and a translated event log", async () => {
    renderAt("#/activity");
    expect(await screen.findByRole("img", { name: "2026-03-02: 60 minutes" })).toBeInTheDocument();
    expect(screen.getByText("Blocked: daily time used up")).toBeInTheDocument();
    expect(screen.getByText("mystery")).toBeInTheDocument();
  });
});

describe("TV details", () => {
  it("changes the rule set and the monitoring switch", async () => {
    const user = userEvent.setup();
    const fetchMock = renderAt("#/tvs/living", { "PATCH tvs/living": TV });
    const select = await screen.findByLabelText("Rule set");
    await user.selectOptions(select, "");
    expect(lastCall(fetchMock, "tvs/living", "PATCH").body).toEqual({ policy_id: null });
    await user.click(screen.getByRole("switch", { name: "Monitor this TV" }));
    const call = lastCall(fetchMock, "tvs/living", "PATCH");
    expect(call.body).toEqual({ enabled: false });
    expect(call.csrf).toBe("csrf-1");
  });

  it("removes the TV after confirmation", async () => {
    const user = userEvent.setup();
    const fetchMock = renderAt("#/tvs/living", { "DELETE tvs/living": new Response(null, { status: 204 }) });
    await user.click(await screen.findByRole("button", { name: "Remove this TV" }));
    const dialog = await screen.findByRole("dialog");
    await user.click(within(dialog).getByRole("button", { name: "Remove TV" }));
    expect(await screen.findByRole("heading", { name: "Dashboard" })).toBeInTheDocument();
    expect(lastCall(fetchMock, "tvs/living", "DELETE").csrf).toBe("csrf-1");
  });

  it("is read-only without the admin scope", async () => {
    renderAt("#/tvs/living", { "GET auth/me": { ...ME, scopes: ["read", "control"] } });
    expect(await screen.findByLabelText("Rule set")).toBeDisabled();
    expect(screen.queryByRole("button", { name: "Remove this TV" })).toBeNull();
  });
});
