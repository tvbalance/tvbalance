import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { act, render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { App } from "../App";
import type { Tv } from "../api/hooks";
import { setCsrfToken } from "../api/http";
import i18n from "../i18n";
import { failure, FakeSocket, stubApi } from "../test/fakes";

const ME = {
  kind: "admin",
  name: "Admin",
  full_admin: true,
  scopes: ["read", "control", "admin"],
  session_id: "s",
  csrf_token: "csrf-1",
};

const STATUS: NonNullable<Tv["status"]> = {
  connected: true,
  pairing_required: false,
  power: "on",
  foreground_app: "youtube",
  watched_seconds: 1500,
  remaining_seconds: 2100,
  decision: { kind: "allow" },
  channel_id: null,
  input_id: null,
  program_title: null,
  updated_at: null,
};

function tv(overrides: Partial<Tv> = {}): Tv {
  return {
    id: "living",
    name: "Living room",
    adapter_id: "lg_webos",
    host: "203.0.113.50",
    enabled: true,
    needs_pairing: false,
    policy_id: 1,
    created_at: "2026-01-01T00:00:00Z",
    status: STATUS,
    ...overrides,
  };
}

function renderDashboard(tvs: Tv[], me: object = ME, extra: Record<string, object> = {}) {
  window.location.hash = "#/";
  const fetchMock = stubApi({
    "GET auth/state": { setup_required: false },
    "GET auth/me": me,
    "GET tvs": tvs,
    "GET settings": { language: "en", timezone: null },
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

function lastCall(fetchMock: ReturnType<typeof stubApi>, url: string) {
  const call = fetchMock.mock.calls.filter(([u]) => u === `api/v1/${url}`).at(-1)!;
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

describe("dashboard", () => {
  it("shows a card with the live status", async () => {
    renderDashboard([tv()]);
    const card = (await screen.findByRole("heading", { name: "Living room" })).closest("section")!;
    expect(within(card).getByText("On")).toBeInTheDocument();
    expect(within(card).getByText("Watching youtube")).toBeInTheDocument();
    expect(within(card).getByText("Allowed")).toBeInTheDocument();
    expect(within(card).getByText("25 min watched today · 35 min left")).toBeInTheDocument();
    expect(within(card).getByRole("progressbar")).toHaveAttribute("aria-valuenow", "25");
  });

  it("says why a TV is blocked and when time is running out", async () => {
    renderDashboard([
      tv({ status: { ...STATUS, decision: { kind: "block", reason: "budget_exhausted" } } }),
      tv({
        id: "kids",
        name: "Kids room",
        status: { ...STATUS, decision: { kind: "warn", limit: "budget", minutes_left: 5 } },
      }),
    ]);
    expect(await screen.findByText("Blocked: daily time used up")).toBeInTheDocument();
    expect(screen.getByText("5 min left before the daily time is used up")).toBeInTheDocument();
  });

  it("flags an unreachable, a pairing and a disabled TV and offers no actions", async () => {
    renderDashboard([
      tv({ id: "a", name: "A", status: { ...STATUS, connected: false } }),
      tv({ id: "b", name: "B", needs_pairing: true }),
      tv({ id: "c", name: "C", enabled: false }),
    ]);
    expect(await screen.findByText("Unreachable")).toBeInTheDocument();
    expect(screen.getByText("Needs pairing")).toBeInTheDocument();
    expect(screen.getByText("Not monitored")).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /Pause/ })).toBeNull();
  });

  it("explains the empty state and offers to add a TV", async () => {
    renderDashboard([]);
    expect(await screen.findByText(/No TV yet/)).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Add a TV" })).toHaveAttribute("href", "#/tvs/add");
  });

  it("keeps an Add a TV link in the header once there are TVs", async () => {
    renderDashboard([tv()]);
    expect(await screen.findByRole("link", { name: "Add a TV" })).toBeInTheDocument();
  });

  it("offers Pair again to an administrator when a TV needs pairing", async () => {
    renderDashboard([tv({ id: "b", name: "B", needs_pairing: true })]);
    expect(await screen.findByRole("link", { name: "Pair again" })).toHaveAttribute("href", "#/tvs/b/pair");
  });

  it("hides adding and pairing from a PIN session", async () => {
    const pin = { ...ME, kind: "pin", full_admin: false, scopes: ["read", "control"] };
    renderDashboard([tv({ id: "b", name: "B", needs_pairing: true })], pin);
    await screen.findByText("Needs pairing");
    expect(screen.queryByRole("link", { name: "Add a TV" })).toBeNull();
    expect(screen.queryByRole("link", { name: "Pair again" })).toBeNull();
  });

  it("pauses, adds time and clears with the CSRF header", async () => {
    const fetchMock = renderDashboard([tv()], ME, {
      "POST tvs/living/pause": {},
      "POST tvs/living/bonus": {},
      "DELETE tvs/living/override": new Response(null, { status: 204 }),
    });
    await userEvent.click(await screen.findByRole("button", { name: "Pause 30 min" }));
    expect(lastCall(fetchMock, "tvs/living/pause")).toEqual({
      method: "POST",
      body: { minutes: 30 },
      csrf: "csrf-1",
    });
    expect(await screen.findByText("Paused for 30 min")).toBeInTheDocument();

    await userEvent.click(screen.getByRole("button", { name: "+15 min" }));
    expect(lastCall(fetchMock, "tvs/living/bonus").body).toEqual({ minutes: 15 });

    await userEvent.click(screen.getByRole("button", { name: "Clear override" }));
    expect(await screen.findByText("Override cleared")).toBeInTheDocument();
    expect(lastCall(fetchMock, "tvs/living/override").method).toBe("DELETE");
  });

  it("blocks for a chosen time and allows until midnight", async () => {
    const fetchMock = renderDashboard([tv()], ME, { "POST tvs/living/override": {} });
    await userEvent.click(await screen.findByRole("button", { name: "Block…" }));
    const dialog = await screen.findByRole("dialog", { name: "Block the TV" });
    await userEvent.selectOptions(within(dialog).getByLabelText("For how long"), "60");
    await userEvent.click(within(dialog).getByRole("button", { name: "Apply" }));
    expect(lastCall(fetchMock, "tvs/living/override").body).toEqual({
      allow: false,
      minutes: 60,
      until_midnight: false,
    });

    await userEvent.click(screen.getByRole("button", { name: "Allow…" }));
    const second = await screen.findByRole("dialog", { name: "Allow the TV" });
    await userEvent.selectOptions(within(second).getByLabelText("For how long"), "midnight");
    await userEvent.click(within(second).getByRole("button", { name: "Apply" }));
    expect(lastCall(fetchMock, "tvs/living/override").body).toEqual({
      allow: true,
      until_midnight: true,
    });
  });

  it("reports a failed action", async () => {
    renderDashboard([tv()], ME, { "POST tvs/living/pause": failure(409, "tv_offline") });
    await userEvent.click(await screen.findByRole("button", { name: "Pause 30 min" }));
    expect(await screen.findByText("The TV is not reachable right now.")).toBeInTheDocument();
  });

  it("lets a PIN session control the TV", async () => {
    renderDashboard([tv()], { ...ME, kind: "pin", full_admin: false, scopes: ["read", "control"] });
    expect(await screen.findByRole("button", { name: "Pause 30 min" })).toBeInTheDocument();
  });

  it("gives a read-only caller the status without the actions", async () => {
    renderDashboard([tv()], { ...ME, kind: "token", full_admin: false, scopes: ["read"] });
    expect(await screen.findByText("Allowed")).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Pause 30 min" })).toBeNull();
  });

  it("follows live status pushed over the WebSocket", async () => {
    renderDashboard([tv()]);
    expect(await screen.findByText("Allowed")).toBeInTheDocument();
    act(() => {
      FakeSocket.instances[0].send({
        type: "status",
        tv_id: "living",
        at: "2026-01-01T10:00:00Z",
        payload: { ...STATUS, decision: { kind: "block", reason: "app_blocked" } },
      });
    });
    expect(await screen.findByText("Blocked: app not allowed")).toBeInTheDocument();
  });

});
