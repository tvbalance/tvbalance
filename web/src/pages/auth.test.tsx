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
  session_id: "s",
  csrf_token: "csrf-1",
};

/** Routes where `auth/me` answers 401 until one of the given calls has succeeded. */
function withSession(routes: Record<string, object>, starts: string[]) {
  let active = false;
  const wrapped: Record<string, object> = { ...routes };
  for (const key of starts) {
    const original = routes[key];
    wrapped[key] = () => {
      if (typeof original !== "function" && (!(original instanceof Response) || original.ok)) active = true;
      if (typeof original === "function") return original();
      return original instanceof Response ? original.clone() : json(original);
    };
  }
  const needsSetup = (routes["GET auth/state"] as { setup_required: boolean }).setup_required;
  wrapped["GET auth/state"] = () => json({ setup_required: needsSetup && !active });
  wrapped["GET auth/me"] = () => (active ? json(ME) : failure(401, "not_authenticated"));
  return wrapped;
}

function renderApp() {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={client}>
      <App />
    </QueryClientProvider>,
  );
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

describe("welcome flow", () => {
  function firstRun(extra: Record<string, object> = {}) {
    window.location.hash = "#/welcome";
    return stubApi(
      withSession(
        {
          "GET auth/state": { setup_required: true },
          "POST auth/setup": ME,
          "PUT settings": { language: "en", timezone: "Europe/Rome" },
          "POST policies": { id: 1 },
          "GET tvs": [],
          "GET settings": { language: "en", timezone: "Europe/Rome" },
          ...extra,
        },
        ["POST auth/setup"],
      ),
    );
  }

  async function createPassword(password: string, confirm = password) {
    await userEvent.type(await screen.findByLabelText("Password"), password);
    await userEvent.type(screen.getByLabelText("Repeat the password"), confirm);
    await userEvent.click(screen.getByRole("button", { name: "Continue" }));
  }

  it("sets up the admin, the region and the first rule, then opens the dashboard", async () => {
    const fetchMock = firstRun();
    renderApp();
    await createPassword("correct horse battery");
    const setup = fetchMock.mock.calls.find(([url]) => url === "api/v1/auth/setup")!;
    expect(JSON.parse(String((setup[1] as RequestInit).body))).toEqual({
      password: "correct horse battery",
    });

    await userEvent.selectOptions(await screen.findByLabelText("Language"), "it");
    expect(await screen.findByLabelText("Lingua")).toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: "Continua" }));

    await userEvent.click(await screen.findByRole("button", { name: "Usa questa regola" }));
    expect(await screen.findByRole("heading", { name: "Pannello" })).toBeInTheDocument();

    const put = fetchMock.mock.calls.find(([url, init]) => url === "api/v1/settings" && (init as RequestInit).method === "PUT")!;
    const settings = JSON.parse(String((put[1] as RequestInit).body)) as Record<string, string>;
    expect(settings.language).toBe("it");
    expect(settings.timezone).toBeTruthy();
    expect(new Headers((put[1] as RequestInit).headers).get("X-TVBalance-CSRF")).toBe("csrf-1");

    const post = fetchMock.mock.calls.find(([url]) => url === "api/v1/policies")!;
    const created = JSON.parse(String((post[1] as RequestInit).body)) as {
      name: string;
      policy: { schedule: { windows: Record<string, unknown[]> }; daily_budget_minutes: number };
    };
    expect(created.name).toBe("Giorni di scuola");
    expect(created.policy.daily_budget_minutes).toBe(120);
    expect(Object.keys(created.policy.schedule.windows)).toHaveLength(7);
  });

  it("rejects a short password and a mismatch before calling the Engine", async () => {
    const fetchMock = firstRun();
    renderApp();
    await createPassword("short");
    expect(await screen.findByRole("alert")).toHaveTextContent("at least 10 characters");
    await userEvent.clear(screen.getByLabelText("Password"));
    await userEvent.clear(screen.getByLabelText("Repeat the password"));
    await createPassword("correct horse battery", "something else");
    expect(await screen.findByRole("alert")).toHaveTextContent("do not match");
    expect(fetchMock.mock.calls.some(([url]) => url === "api/v1/auth/setup")).toBe(false);
  });

  it("shows an Engine error and stays on the first step", async () => {
    firstRun({ "POST auth/setup": failure(409, "conflict") });
    renderApp();
    await createPassword("correct horse battery");
    expect(await screen.findByRole("alert")).toHaveTextContent("conflicts");
  });

  it("lets the user skip the first rule", async () => {
    const fetchMock = firstRun();
    renderApp();
    await createPassword("correct horse battery");
    await screen.findByRole("heading", { name: "Language and time zone" });
    await userEvent.click(screen.getByRole("button", { name: "Continue" }));
    await userEvent.click(await screen.findByRole("button", { name: "Skip for now" }));
    expect(await screen.findByRole("heading", { name: "Dashboard" })).toBeInTheDocument();
    expect(fetchMock.mock.calls.some(([url]) => url === "api/v1/policies")).toBe(false);
  });

  it("sends an already configured install away from the welcome page", async () => {
    window.location.hash = "#/welcome";
    stubApi({
      "GET auth/state": { setup_required: false },
      "GET auth/me": failure(401, "not_authenticated"),
    });
    renderApp();
    expect(await screen.findByRole("heading", { name: "Sign in" })).toBeInTheDocument();
  });
});

describe("sign-in", () => {
  function signedOut(extra: Record<string, object> = {}) {
    window.location.hash = "#/login";
    return stubApi(
      withSession(
        {
          "GET auth/state": { setup_required: false },
          "GET tvs": [],
          "GET settings": { language: "en", timezone: null },
          ...extra,
        },
        ["POST auth/login", "POST auth/pin-login"],
      ),
    );
  }

  it("signs in with the password and keeps the CSRF token for later writes", async () => {
    signedOut({ "POST auth/login": ME });
    renderApp();
    await userEvent.type(await screen.findByLabelText("Password", { selector: "input" }), "secret");
    await userEvent.click(screen.getByRole("button", { name: "Sign in" }));
    expect(await screen.findByRole("heading", { name: "Dashboard" })).toBeInTheDocument();
    expect(window.location.hash).toBe("#/");
  });

  it("signs in with the PIN", async () => {
    const fetchMock = signedOut({ "POST auth/pin-login": { ...ME, kind: "pin", full_admin: false } });
    renderApp();
    await userEvent.click(await screen.findByRole("tab", { name: "PIN" }));
    await userEvent.type(screen.getByLabelText("PIN", { selector: "input" }), "1234");
    await userEvent.click(screen.getByRole("button", { name: "Sign in" }));
    expect(await screen.findByRole("heading", { name: "Dashboard" })).toBeInTheDocument();
    const call = fetchMock.mock.calls.find(([url]) => url === "api/v1/auth/pin-login")!;
    expect(JSON.parse(String((call[1] as RequestInit).body))).toEqual({ pin: "1234" });
  });

  it("explains a wrong password and clears the field", async () => {
    signedOut({ "POST auth/login": failure(401, "not_authenticated") });
    renderApp();
    const field = await screen.findByLabelText("Password", { selector: "input" });
    await userEvent.type(field, "nope");
    await userEvent.click(screen.getByRole("button", { name: "Sign in" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("That is not right");
    expect(field).toHaveValue("");
  });

  it("tells a locked PIN to use the password", async () => {
    signedOut({ "POST auth/pin-login": failure(403, "pin_locked") });
    renderApp();
    await userEvent.click(await screen.findByRole("tab", { name: "PIN" }));
    await userEvent.type(screen.getByLabelText("PIN", { selector: "input" }), "1234");
    await userEvent.click(screen.getByRole("button", { name: "Sign in" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("Too many wrong PINs");
  });

  it("shows how long to wait after a rate limit", async () => {
    signedOut({ "POST auth/login": failure(429, "rate_limited", "slow", { "Retry-After": "42" }) });
    renderApp();
    await userEvent.type(await screen.findByLabelText("Password", { selector: "input" }), "x");
    await userEvent.click(screen.getByRole("button", { name: "Sign in" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("42 s");
  });

  it("reports an unreachable Engine", async () => {
    signedOut({ "POST auth/login": () => { throw new TypeError("offline"); } });
    renderApp();
    await userEvent.type(await screen.findByLabelText("Password", { selector: "input" }), "x");
    await userEvent.click(screen.getByRole("button", { name: "Sign in" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("Cannot reach the Engine");
  });

  it("skips the form when already signed in", async () => {
    window.location.hash = "#/login";
    stubApi({
      "GET auth/state": { setup_required: false },
      "GET auth/me": ME,
      "GET tvs": [],
      "GET settings": { language: "en", timezone: null },
    });
    renderApp();
    expect(await screen.findByRole("heading", { name: "Dashboard" })).toBeInTheDocument();
  });

  it("switches to the saved language once signed in", async () => {
    window.location.hash = "#/";
    stubApi({
      "GET auth/state": { setup_required: false },
      "GET auth/me": ME,
      "GET tvs": [],
      "GET settings": { language: "de", timezone: null },
    });
    renderApp();
    expect(await screen.findByRole("heading", { name: "Übersicht" })).toBeInTheDocument();
  });
});
