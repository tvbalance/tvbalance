import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { App } from "../App";
import { setCsrfToken } from "../api/http";
import i18n from "../i18n";
import { failure, FakeSocket, json, stubApi } from "../test/fakes";

const ME = {
  kind: "admin",
  name: "Admin",
  full_admin: true,
  scopes: ["read", "control", "admin"],
  session_id: "s1",
  csrf_token: "csrf-1",
};

const SESSIONS = [
  { id: "s1", kind: "admin", current: true, created_at: "2026-03-01T10:00:00Z", expires_at: "2026-04-01T10:00:00Z", last_seen_at: "2026-03-03T10:00:00Z" },
  { id: "s2", kind: "pin", current: false, created_at: "2026-03-01T10:00:00Z", expires_at: "2026-04-01T10:00:00Z", last_seen_at: "2026-03-02T09:00:00Z" },
];

const TOKEN = {
  id: "t1",
  name: "Home Assistant",
  scopes: ["read", "control"],
  created_at: "2026-03-01T10:00:00Z",
  last_used_at: null,
  revoked_at: null,
};

function renderSettings(extra: Record<string, object> = {}) {
  window.location.hash = "#/settings";
  const fetchMock = stubApi({
    "GET auth/state": { setup_required: false },
    "GET auth/me": ME,
    "GET tvs": [],
    "GET settings": { language: "en", timezone: "Europe/Rome" },
    "GET auth/sessions": SESSIONS,
    "GET auth/tokens": [TOKEN],
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

describe("settings", () => {
  it("shows a new API token once, with the secret", async () => {
    const user = userEvent.setup();
    const created = { ...TOKEN, id: "t2", name: "Backup", token: "tvb_secret123" };
    const fetchMock = renderSettings({ "POST auth/tokens": json(created, { status: 201 }) });
    await user.type(await screen.findByLabelText("What is it for?"), "Backup");
    await user.click(screen.getByRole("button", { name: "Create token" }));
    expect(await screen.findByText("tvb_secret123")).toBeInTheDocument();
    const call = lastCall(fetchMock, "auth/tokens", "POST");
    expect(call.body).toEqual({ name: "Backup", scopes: ["read", "control"] });
    expect(call.csrf).toBe("csrf-1");
    await user.click(screen.getByRole("button", { name: "Done" }));
    expect(screen.queryByText("tvb_secret123")).toBeNull();
  });

  it("revokes a token", async () => {
    const user = userEvent.setup();
    const fetchMock = renderSettings({ "DELETE auth/tokens/t1": new Response(null, { status: 204 }) });
    await user.click(await screen.findByRole("button", { name: "Revoke the token Home Assistant" }));
    expect(lastCall(fetchMock, "auth/tokens/t1", "DELETE").csrf).toBe("csrf-1");
  });

  it("signs out the other devices", async () => {
    const user = userEvent.setup();
    const fetchMock = renderSettings({ "DELETE auth/sessions": new Response(null, { status: 204 }) });
    expect(await screen.findByText("This device")).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Sign out all other devices" }));
    expect(lastCall(fetchMock, "auth/sessions", "DELETE").csrf).toBe("csrf-1");
  });

  it("changes the password only when the new one is long enough and repeated", async () => {
    const user = userEvent.setup();
    const fetchMock = renderSettings({ "PUT auth/password": new Response(null, { status: 204 }) });
    await user.type(await screen.findByLabelText("Current password"), "old-password");
    await user.type(screen.getByLabelText("New password"), "a-new-password");
    const button = screen.getByRole("button", { name: "Change password" });
    expect(button).toBeDisabled();
    await user.type(screen.getByLabelText("Repeat the new password"), "a-new-password");
    await user.click(button);
    expect(await screen.findByText("Password changed")).toBeInTheDocument();
    expect(lastCall(fetchMock, "auth/password", "PUT").body).toEqual({
      current_password: "old-password",
      new_password: "a-new-password",
    });
  });

  it("reports a wrong current password", async () => {
    const user = userEvent.setup();
    renderSettings({ "PUT auth/password": failure(401, "not_authenticated") });
    await user.type(await screen.findByLabelText("Current password"), "nope-nope-nope");
    await user.type(screen.getByLabelText("New password"), "a-new-password");
    await user.type(screen.getByLabelText("Repeat the new password"), "a-new-password");
    await user.click(screen.getByRole("button", { name: "Change password" }));
    expect(await screen.findByRole("status")).toBeInTheDocument();
  });

  it("saves the language and time zone", async () => {
    const user = userEvent.setup();
    const fetchMock = renderSettings({ "PUT settings": { language: "it", timezone: "Europe/Rome" } });
    await user.selectOptions(await screen.findByLabelText("Language"), "it");
    await user.click(screen.getByRole("button", { name: "Save" }));
    expect(lastCall(fetchMock, "settings", "PUT").body).toEqual({ language: "it", timezone: "Europe/Rome" });
  });

  it("hides security sections from a PIN session", async () => {
    renderSettings({ "GET auth/me": { ...ME, kind: "pin", full_admin: false, scopes: ["read", "control"] } });
    expect(await screen.findByRole("heading", { name: "General" })).toBeInTheDocument();
    expect(screen.queryByRole("heading", { name: "API tokens" })).toBeNull();
    expect(screen.queryByRole("heading", { name: "Security" })).toBeNull();
    expect(screen.queryByRole("button", { name: "Save" })).toBeNull();
  });

  it("signs out and returns to the login page", async () => {
    const user = userEvent.setup();
    let signedOut = false;
    const fetchMock = renderSettings({
      "GET auth/me": () => (signedOut ? failure(401, "not_authenticated") : json(ME)),
      "POST auth/logout": () => {
        signedOut = true;
        return new Response(null, { status: 204 });
      },
    });
    await user.click(await screen.findByRole("button", { name: "Sign out" }));
    expect(await screen.findByRole("heading", { name: /sign in/i })).toBeInTheDocument();
    expect(lastCall(fetchMock, "auth/logout", "POST").csrf).toBe("csrf-1");
  });
});
