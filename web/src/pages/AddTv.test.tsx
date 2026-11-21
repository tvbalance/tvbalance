import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { App } from "../App";
import type { Tv } from "../api/hooks";
import { setCsrfToken } from "../api/http";
import i18n from "../i18n";
import { failure, FakeSocket, json, stubApi } from "../test/fakes";

const ME = {
  kind: "admin",
  name: "Admin",
  full_admin: true,
  scopes: ["read", "control", "admin"],
  session_id: "s",
  csrf_token: "csrf-1",
};

const ADAPTERS = [
  {
    id: "lg_webos",
    brand: "LG",
    display_name: "LG webOS",
    maturity: "stable",
    capabilities: ["list_apps", "power_off"],
  },
];

const FOUND = [
  { adapter_id: "lg_webos", adapter_name: "LG webOS", host: "198.51.100.7", name: "Living room TV", model: "OLED", already_added: false },
  { adapter_id: "lg_webos", adapter_name: "LG webOS", host: "198.51.100.8", name: "Bedroom TV", model: null, already_added: true },
];

const PAIRING = {
  id: "p1",
  state: "waiting_for_user",
  adapter_id: "lg_webos",
  host: "198.51.100.7",
  tv_id: null,
  expires_at: new Date(Date.now() + 180_000).toISOString(),
};

const NEW_TV = {
  id: "tv-1",
  name: "Living room TV",
  adapter_id: "lg_webos",
  host: "198.51.100.7",
  enabled: true,
  needs_pairing: false,
  policy_id: null,
  created_at: "2026-01-01T00:00:00Z",
  status: null,
} as unknown as Tv;

function renderAt(hash: string, extra: Record<string, unknown> = {}) {
  window.location.hash = hash;
  const fetchMock = stubApi({
    "GET auth/state": { setup_required: false },
    "GET auth/me": ME,
    "GET tvs": [],
    "GET policies": [{ id: 1, name: "School days", tv_ids: [], policy: {}, updated_at: "2026-01-01T00:00:00Z" }],
    "GET settings": { language: "en", timezone: null },
    "GET adapters": ADAPTERS,
    "GET discovery": FOUND,
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

function calls(fetchMock: ReturnType<typeof stubApi>, url: string, method: string) {
  return fetchMock.mock.calls.filter(
    ([u, init]) => u === `api/v1/${url}` && ((init as RequestInit | undefined)?.method ?? "GET") === method,
  );
}

function body(call: unknown[]) {
  const init = call[1] as RequestInit;
  return JSON.parse(String(init.body));
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

describe("add a TV", () => {
  it("lists the TVs found and disables the ones already added", async () => {
    renderAt("#/tvs/add");
    expect(await screen.findByText("Living room TV")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Add Living room TV" })).toBeEnabled();
    expect(screen.getByText("Already added")).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Add Bedroom TV" })).not.toBeInTheDocument();
  });

  it("searches again on request", async () => {
    const user = userEvent.setup();
    const fetchMock = renderAt("#/tvs/add");
    await screen.findByText("Living room TV");
    await user.click(screen.getByRole("button", { name: "Search again" }));
    await waitFor(() => expect(calls(fetchMock, "discovery", "GET")).toHaveLength(2));
  });

  it("offers the manual address when nothing is found", async () => {
    const user = userEvent.setup();
    const fetchMock = renderAt("#/tvs/add", {
      "GET discovery": [],
      "POST pairings": json({ ...PAIRING, host: "10.0.0.20" }, { status: 201 }),
      "GET pairings/p1": { ...PAIRING, host: "10.0.0.20" },
      "DELETE pairings/p1": new Response(null, { status: 204 }),
    });
    expect(await screen.findByText("No TV found. Enter its address below.")).toBeInTheDocument();
    await user.type(screen.getByLabelText("Address"), "10.0.0.20");
    await user.click(screen.getByRole("button", { name: "Continue" }));
    await user.click(await screen.findByRole("button", { name: "Start pairing" }));
    await screen.findByText("Waiting for you to accept on the TV…");
    expect(body(calls(fetchMock, "pairings", "POST")[0])).toMatchObject({
      adapter_id: "lg_webos",
      host: "10.0.0.20",
    });
  });

  it("walks through pairing, naming and rules", async () => {
    const user = userEvent.setup();
    let polls = 0;
    const fetchMock = renderAt("#/tvs/add", {
      "POST pairings": json(PAIRING, { status: 201 }),
      "GET pairings/p1": () => {
        polls += 1;
        return json(polls < 2 ? PAIRING : { ...PAIRING, state: "completed", tv_id: "tv-1" });
      },
      "GET tvs": [NEW_TV],
      "PATCH tvs/tv-1": json(NEW_TV),
    });
    await user.click(await screen.findByRole("button", { name: "Add Living room TV" }));
    expect(screen.getByText(/choose Yes with the remote/)).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Start pairing" }));
    expect(await screen.findByText("Waiting for you to accept on the TV…")).toBeInTheDocument();

    expect(await screen.findByRole("heading", { name: "Almost done" }, { timeout: 4000 })).toBeInTheDocument();
    expect(screen.getByText("Switch off")).toBeInTheDocument();
    const name = screen.getByLabelText("Name");
    await user.clear(name);
    await user.type(name, "Den");
    await user.selectOptions(screen.getByLabelText("Rule set"), "1");
    await user.click(screen.getByRole("button", { name: "Finish" }));
    await waitFor(() => expect(calls(fetchMock, "tvs/tv-1", "PATCH")).toHaveLength(1));
    expect(body(calls(fetchMock, "tvs/tv-1", "PATCH")[0])).toEqual({ name: "Den", policy_id: 1 });
  });

  it("lets the person retry after a failure", async () => {
    const user = userEvent.setup();
    const fetchMock = renderAt("#/tvs/add", {
      "POST pairings": json(PAIRING, { status: 201 }),
      "GET pairings/p1": { ...PAIRING, state: "failed" },
      "DELETE pairings/p1": new Response(null, { status: 204 }),
    });
    await user.click(await screen.findByRole("button", { name: "Add Living room TV" }));
    await user.click(screen.getByRole("button", { name: "Start pairing" }));
    expect(await screen.findByText(/Pairing did not work/)).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Try again" }));
    await waitFor(() => expect(calls(fetchMock, "pairings", "POST")).toHaveLength(2));
    await waitFor(() => expect(calls(fetchMock, "pairings/p1", "DELETE")).toHaveLength(1));
  });

  it("abandons a pending pairing when the person leaves", async () => {
    const user = userEvent.setup();
    const fetchMock = renderAt("#/tvs/add", {
      "POST pairings": json(PAIRING, { status: 201 }),
      "GET pairings/p1": PAIRING,
      "DELETE pairings/p1": new Response(null, { status: 204 }),
    });
    await user.click(await screen.findByRole("button", { name: "Add Living room TV" }));
    await user.click(screen.getByRole("button", { name: "Start pairing" }));
    await screen.findByText("Waiting for you to accept on the TV…");
    window.location.hash = "#/rules";
    await waitFor(() => expect(calls(fetchMock, "pairings/p1", "DELETE")).toHaveLength(1));
    const init = calls(fetchMock, "pairings/p1", "DELETE")[0]![1] as RequestInit;
    expect(new Headers(init.headers).get("X-TVBalance-CSRF")).toBe("csrf-1");
  });

  it("says when the TV is already added", async () => {
    const user = userEvent.setup();
    renderAt("#/tvs/add", { "POST pairings": failure(409, "tv_exists") });
    await user.click(await screen.findByRole("button", { name: "Add Living room TV" }));
    await user.click(screen.getByRole("button", { name: "Start pairing" }));
    expect(await screen.findByText("This TV is already added.")).toBeInTheDocument();
  });

  it("pairs a stored TV again with its id", async () => {
    const user = userEvent.setup();
    const stored = { ...NEW_TV, needs_pairing: true };
    const fetchMock = renderAt("#/tvs/tv-1/pair", {
      "GET tvs": [stored],
      "POST pairings": json({ ...PAIRING, tv_id: "tv-1" }, { status: 201 }),
      "GET pairings/p1": { ...PAIRING, state: "completed", tv_id: "tv-1" },
      "GET tvs/tv-1": stored,
    });
    expect(await screen.findByRole("heading", { name: "Pair the TV again" })).toBeInTheDocument();
    await user.click(await screen.findByRole("button", { name: "Start pairing" }));
    await waitFor(() => expect(calls(fetchMock, "pairings", "POST")).toHaveLength(1));
    expect(body(calls(fetchMock, "pairings", "POST")[0])).toEqual({ tv_id: "tv-1" });
    await waitFor(() => expect(window.location.hash).toBe("#/tvs/tv-1"));
  });
});
