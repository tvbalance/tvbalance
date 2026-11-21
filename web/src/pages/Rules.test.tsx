import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { App } from "../App";
import type { Policy, Tv } from "../api/hooks";
import { setCsrfToken } from "../api/http";
import i18n from "../i18n";
import { emptyPolicy, schoolPreset } from "../presets";
import { failure, FakeSocket, json, stubApi } from "../test/fakes";

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

const POLICY: Policy = {
  id: 1,
  name: "School days",
  policy: schoolPreset(),
  tv_ids: ["living"],
  updated_at: "2026-01-01T00:00:00Z",
} as unknown as Policy;

const INVENTORY = {
  apps: [{ id: "youtube", name: "YouTube", has_icon: true }],
  inputs: [{ id: "HDMI_1", label: "Console" }],
  channels: [],
};

function renderAt(hash: string, extra: Record<string, unknown> = {}) {
  window.location.hash = hash;
  const fetchMock = stubApi({
    "GET auth/state": { setup_required: false },
    "GET auth/me": ME,
    "GET tvs": [TV],
    "GET policies": [POLICY],
    "GET settings": { language: "en", timezone: null },
    "GET tvs/living/inventory": INVENTORY,
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

function lastCall(fetchMock: ReturnType<typeof stubApi>, url: string, method = "GET") {
  const call = fetchMock.mock.calls
    .filter(([u, init]) => u === `api/v1/${url}` && ((init as RequestInit | undefined)?.method ?? "GET") === method)
    .at(-1)!;
  const init = call[1] as RequestInit;
  return {
    method: init.method,
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

describe("rule sets", () => {
  it("lists sets with the TVs that use them", async () => {
    renderAt("#/rules");
    expect(await screen.findByRole("link", { name: "School days" })).toBeInTheDocument();
    expect(screen.getByText("Used by Living room")).toBeInTheDocument();
  });

  it("creates a set from the school preset and opens its editor", async () => {
    const user = userEvent.setup();
    const created = { ...POLICY, id: 2, name: "Weekend", tv_ids: [] };
    const fetchMock = renderAt("#/rules", { "POST policies": json(created, { status: 201 }) });
    await user.click(await screen.findByRole("button", { name: "New rule set" }));
    await user.type(screen.getByLabelText("Name"), "Weekend");
    await user.click(screen.getByRole("button", { name: "Create" }));
    expect(await screen.findByRole("heading", { name: "Edit rule set" })).toBeInTheDocument();
    const call = lastCall(fetchMock, "policies", "POST");
    expect(call.body.name).toBe("Weekend");
    expect(call.body.policy.daily_budget_minutes).toBe(120);
    expect(call.csrf).toBe("csrf-1");
  });
});

describe("rule editor", () => {
  it("saves edits with a PUT carrying the CSRF header", async () => {
    const user = userEvent.setup();
    const fetchMock = renderAt("#/rules/1", { "PUT policies/1": POLICY });
    await user.click(await screen.findByRole("tab", { name: "Time" }));
    const minutes = screen.getByLabelText("Minutes per day");
    await user.clear(minutes);
    await user.type(minutes, "90");
    await user.click(screen.getByRole("button", { name: "Save" }));
    expect(await screen.findByText("Rules saved")).toBeInTheDocument();
    const call = lastCall(fetchMock, "policies/1", "PUT");
    expect(call.method).toBe("PUT");
    expect(call.body.policy.daily_budget_minutes).toBe(90);
    expect(call.csrf).toBe("csrf-1");
  });

  it("turns the budget off", async () => {
    const user = userEvent.setup();
    const fetchMock = renderAt("#/rules/1", { "PUT policies/1": POLICY });
    await user.click(await screen.findByRole("tab", { name: "Time" }));
    await user.click(screen.getByRole("switch", { name: "Daily budget" }));
    await user.click(screen.getByRole("button", { name: "Save" }));
    await screen.findByText("Rules saved");
    expect(lastCall(fetchMock, "policies/1", "PUT").body.policy.daily_budget_minutes).toBeNull();
  });

  it("adds a time window on a day", async () => {
    const user = userEvent.setup();
    renderAt("#/rules/1", { "GET policies": [{ ...POLICY, policy: emptyPolicy() }] });
    await user.click(await screen.findByRole("button", { name: /Add a window on Monday/ }));
    expect(screen.getByLabelText(/Monday, window 1: from/)).toBeInTheDocument();
  });

  it("offers the TV's apps with a proxied icon", async () => {
    const user = userEvent.setup();
    renderAt("#/rules/1");
    await user.click(await screen.findByRole("tab", { name: "Content" }));
    const select = (await screen.findAllByLabelText("Add to Apps"))[0]!;
    await screen.findAllByRole("option", { name: "YouTube" });
    await user.selectOptions(select, "youtube");
    const icon = document.querySelector("img");
    expect(icon?.getAttribute("src")).toBe("api/v1/tvs/living/apps/youtube/icon");
  });

  it("falls back to typing ids when the TV is offline", async () => {
    const user = userEvent.setup();
    renderAt("#/rules/1", { "GET tvs/living/inventory": failure(409, "tv_offline") });
    await user.click(await screen.findByRole("tab", { name: "Content" }));
    expect(await screen.findByText(/can't be reached/)).toBeInTheDocument();
    expect(screen.getAllByLabelText("Add to Apps by id")).toHaveLength(2);
  });

  it("explains a 422 with the issue messages", async () => {
    const user = userEvent.setup();
    const rejected = json(
      {
        error: {
          code: "validation_failed",
          message: "invalid",
          details: [{ code: "negative_budget", detail: "-5" }],
        },
      },
      { status: 422 },
    );
    renderAt("#/rules/1", { "PUT policies/1": rejected });
    await user.click(await screen.findByRole("button", { name: "Save" }));
    expect(await screen.findByText("These rules can't be saved yet:")).toBeInTheDocument();
    expect(screen.getByText(/daily budget can't be negative/)).toBeInTheDocument();
  });
});
