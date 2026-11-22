import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { App } from "../App";
import type { Policy, Tv } from "../api/hooks";
import { setCsrfToken } from "../api/http";
import i18n from "../i18n";
import { schoolPreset } from "../presets";
import { FakeSocket, json, stubApi } from "../test/fakes";

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
  plan_limited: false,
  policy_id: 1,
  created_at: "2026-01-01T00:00:00Z",
  status: null,
} as unknown as Tv;

const POLICY = {
  id: 1,
  name: "School days",
  policy: schoolPreset(),
  tv_ids: ["living"],
  updated_at: "2026-01-01T00:00:00Z",
} as unknown as Policy;

const ACTIVATION = {
  policy_id: 1,
  name: "School days",
  starts_at: "2026-01-01T10:00:00Z",
  ends_at: "2026-01-01T12:00:00Z",
  excluded_tv_ids: [],
  source: "manual",
};

const WEEKLY = {
  id: 7,
  kind: "weekly",
  policy_id: 1,
  weekdays: [5, 6],
  start: "08:00:00",
  end: "20:00:00",
  excluded_tv_ids: [],
};

function renderAt(hash: string, extra: Record<string, unknown> = {}) {
  window.location.hash = hash;
  const fetchMock = stubApi({
    "GET auth/state": { setup_required: false },
    "GET auth/me": ME,
    "GET tvs": [TV],
    "GET policies": [POLICY],
    "GET settings": { language: "en", timezone: null },
    "GET profiles/active": { effective: true, activation: null },
    "GET calendar": { effective: true, entries: [] },
    ...(extra as Record<string, object>),
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
  return { body: init.body ? JSON.parse(String(init.body)) : undefined };
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

describe("profiles", () => {
  it("shows the active profile on the dashboard and ends it", async () => {
    const user = userEvent.setup();
    const fetchMock = renderAt("#/", {
      "GET profiles/active": { effective: true, activation: ACTIVATION },
      "DELETE profiles/active": new Response(null, { status: 204 }),
    });
    const banner = await screen.findByLabelText("Active profile");
    expect(banner).toHaveTextContent("School days");
    await user.click(screen.getByRole("button", { name: "End profile" }));
    expect(await screen.findByText("Profile ended")).toBeInTheDocument();
    expect(lastCall(fetchMock, "profiles/active", "DELETE")).toBeDefined();
  });

  it("notes that the Free plan ignores a profile", async () => {
    renderAt("#/", { "GET profiles/active": { effective: false, activation: ACTIVATION } });
    expect(await screen.findByText(/need the Pro plan/)).toBeInTheDocument();
  });

  it("activates a rule set for a duration, leaving a TV out", async () => {
    const user = userEvent.setup();
    const fetchMock = renderAt("#/rules", { "POST profiles/active": json(ACTIVATION) });
    await user.click(await screen.findByRole("button", { name: "Activate School days as profile" }));
    await user.click(await screen.findByLabelText("Living room"));
    await user.selectOptions(screen.getByLabelText("For how long"), "120");
    await user.click(screen.getByRole("button", { name: "Activate" }));
    expect(await screen.findByText("Profile activated")).toBeInTheDocument();
    expect(lastCall(fetchMock, "profiles/active", "POST").body).toEqual({
      policy_id: 1,
      excluded_tv_ids: ["living"],
      minutes: 120,
      until_midnight: false,
    });
  });
});

describe("calendar", () => {
  it("lists entries", async () => {
    renderAt("#/calendar", { "GET calendar": { effective: true, entries: [WEEKLY] } });
    expect(await screen.findByText("Sat, Sun, 08:00–20:00")).toBeInTheDocument();
  });

  it("adds a weekly entry", async () => {
    const user = userEvent.setup();
    const fetchMock = renderAt("#/calendar", { "POST calendar": json({ ...WEEKLY, id: 1 }, { status: 201 }) });
    await user.click(await screen.findByRole("button", { name: "Add entry" }));
    await user.click(screen.getByRole("button", { name: "Save" }));
    expect(await screen.findByText("Entry saved")).toBeInTheDocument();
    expect(lastCall(fetchMock, "calendar", "POST").body).toEqual({
      kind: "weekly",
      policy_id: 1,
      excluded_tv_ids: [],
      weekdays: [5, 6],
      start: "08:00",
      end: "20:00",
    });
  });

  it("removes an entry", async () => {
    const user = userEvent.setup();
    const fetchMock = renderAt("#/calendar", {
      "GET calendar": { effective: true, entries: [WEEKLY] },
      "DELETE calendar/7": new Response(null, { status: 204 }),
    });
    await user.click(await screen.findByRole("button", { name: "Remove entry for School days" }));
    expect(await screen.findByText("Entry removed")).toBeInTheDocument();
    expect(lastCall(fetchMock, "calendar/7", "DELETE")).toBeDefined();
  });

  it("warns when the plan does not apply the calendar", async () => {
    renderAt("#/calendar", { "GET calendar": { effective: false, entries: [] } });
    expect(await screen.findByText(/need the Pro plan/)).toBeInTheDocument();
  });
});
