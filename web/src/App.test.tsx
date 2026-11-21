import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { App } from "./App";
import "./i18n";
import { failure, FakeSocket, stubApi } from "./test/fakes";

const INFO = { version: "0.0.1", api_version: "1" };
const ME = {
  kind: "admin",
  name: "Admin",
  full_admin: true,
  scopes: ["read", "control", "admin"],
  session_id: "s",
  csrf_token: "csrf",
};

function renderApp() {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={client}>
      <App />
    </QueryClientProvider>,
  );
}

beforeEach(() => {
  window.location.hash = "";
  FakeSocket.instances = [];
  vi.stubGlobal("WebSocket", FakeSocket);
});
afterEach(() => vi.unstubAllGlobals());

describe("auth gate", () => {
  it("shows the app to a signed-in caller using relative API URLs", async () => {
    window.location.hash = "#/system";
    const fetchMock = stubApi({
      "GET auth/state": { setup_required: false },
      "GET auth/me": ME,
      "GET info": INFO,
    });
    renderApp();
    expect(await screen.findByText("0.0.1")).toBeInTheDocument();
    for (const [url] of fetchMock.mock.calls as [string][]) {
      expect(url.startsWith("/")).toBe(false);
    }
    expect(FakeSocket.instances).toHaveLength(1);
    expect(FakeSocket.instances[0].url).toMatch(/^ws:\/\/.*\/api\/v1\/events\/ws$/);
  });

  it("sends first-run visitors to the welcome flow", async () => {
    stubApi({
      "GET auth/state": { setup_required: true },
      "GET auth/me": failure(401, "setup_required"),
    });
    renderApp();
    expect(await screen.findByRole("heading", { name: "Welcome" })).toBeInTheDocument();
    expect(window.location.hash).toBe("#/welcome");
    expect(FakeSocket.instances).toHaveLength(0);
  });

  it("sends anonymous visitors to sign-in", async () => {
    stubApi({
      "GET auth/state": { setup_required: false },
      "GET auth/me": failure(401, "not_authenticated"),
    });
    renderApp();
    expect(await screen.findByRole("heading", { name: "Sign in" })).toBeInTheDocument();
    expect(window.location.hash).toBe("#/login");
  });

  it("reports an unreachable engine", async () => {
    vi.stubGlobal("fetch", vi.fn().mockRejectedValue(new Error("down")));
    renderApp();
    expect(await screen.findByRole("alert")).toBeInTheDocument();
  });
});

describe("navigation", () => {
  it("links the pages of the signed-in app", async () => {
    stubApi({
      "GET auth/state": { setup_required: false },
      "GET auth/me": ME,
      "GET tvs": [],
      "GET info": INFO,
    });
    renderApp();
    const nav = await screen.findByRole("navigation", { name: "Main" });
    expect(within(nav).getByRole("link", { name: "Dashboard" })).toHaveAttribute("aria-current", "page");
    expect(await screen.findByText(/No TV yet/)).toBeInTheDocument();
    await userEvent.click(within(nav).getByRole("link", { name: "System" }));
    expect(await screen.findByText("0.0.1")).toBeInTheDocument();
  });
});
