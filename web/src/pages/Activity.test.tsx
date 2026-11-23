import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { App } from "../App";
import type { Tv } from "../api/hooks";
import { setCsrfToken } from "../api/http";
import i18n from "../i18n";
import { FakeSocket, failure, stubApi } from "../test/fakes";

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

const USAGE = {
  tv_id: "living",
  days: [
    { day: "2026-03-02", watched_seconds: 3600, bonus_minutes: 0 },
    { day: "2026-03-03", watched_seconds: 1800, bonus_minutes: 0 },
  ],
};

const EVENTS = [
  {
    id: 2,
    tv_id: "living",
    occurred_at: "2026-03-03T18:00:00Z",
    type: "blocked",
    payload: { reason: "budget_exhausted" },
  },
  {
    id: 1,
    tv_id: "living",
    occurred_at: "2026-03-03T17:00:00Z",
    type: "mystery",
    payload: {},
  },
];

const CONTENT = {
  tv_id: "living",
  first: "2026-03-04",
  last: "2026-03-10",
  limited: false,
  items: [
    { kind: "app", id: "netflix", seconds: 2700 },
    { kind: "app", id: "unknown.app", seconds: 300 },
  ],
};

const INVENTORY = {
  apps: [{ id: "netflix", name: "Netflix", has_icon: false }],
  inputs: [],
  channels: [],
};

const REPORT = {
  first: "2026-03-02",
  last: "2026-03-08",
  tvs: [
    {
      tv_id: "living",
      tv_name: "Living room",
      total_seconds: 7500,
      days: [2, 3, 4, 5, 6, 7, 8].map((d) => ({
        day: `2026-03-0${d}`,
        seconds: 600,
      })),
      top_content: [{ kind: "app", id: "netflix", seconds: 6000 }],
      blocks: 3,
    },
  ],
};

function renderAt(hash: string, extra: Record<string, object> = {}) {
  window.location.hash = hash;
  const fetchMock = stubApi({
    "GET auth/state": { setup_required: false },
    "GET auth/me": ME,
    "GET tvs": [TV],
    "GET policies": [
      {
        id: 1,
        name: "School days",
        policy: {},
        tv_ids: ["living"],
        updated_at: "x",
      },
    ],
    "GET settings": { language: "en", timezone: null },
    "GET tvs/living/usage?days=7": USAGE,
    "GET events?limit=50": EVENTS,
    "GET events?limit=10&tv_id=living": EVENTS,
    ...extra,
  });
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  render(
    <QueryClientProvider client={client}>
      <App />
    </QueryClientProvider>,
  );
  return fetchMock;
}

function lastCall(
  fetchMock: ReturnType<typeof stubApi>,
  url: string,
  method: string,
) {
  const call = fetchMock.mock.calls
    .filter(
      ([u, init]) =>
        u === `api/v1/${url}` &&
        ((init as RequestInit | undefined)?.method ?? "GET") === method,
    )
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
  vi.useRealTimers();
});

describe("activity", () => {
  it("shows weekly usage and a translated event log", async () => {
    renderAt("#/activity");
    expect(
      await screen.findByRole("img", { name: "2026-03-02: 60 minutes" }),
    ).toBeInTheDocument();
    expect(screen.getByText("Blocked: daily time used up")).toBeInTheDocument();
    expect(screen.getByText("mystery")).toBeInTheDocument();
  });

  it("shows the most watched content by the names the TV gives it", async () => {
    vi.setSystemTime(new Date("2026-03-10T12:00:00"));
    renderAt("#/activity", {
      "GET tvs/living/usage/content?from=2026-03-04": CONTENT,
      "GET tvs/living/inventory": INVENTORY,
    });
    expect(
      await screen.findByRole("img", { name: "Netflix: 45 minutes" }),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("img", { name: "unknown.app: 5 minutes" }),
    ).toBeInTheDocument();
  });

  it("asks for a longer range and says when the plan cuts it short", async () => {
    vi.setSystemTime(new Date("2026-03-10T12:00:00"));
    const user = userEvent.setup();
    const fetchMock = renderAt("#/activity", {
      "GET tvs/living/usage?days=30": { ...USAGE, limited: true },
    });
    await user.selectOptions(await screen.findByLabelText("Period"), "30");
    expect(
      await screen.findByText(
        "A longer history needs the Pro plan. Showing the last 7 days.",
      ),
    ).toBeInTheDocument();
    expect(fetchMock).toHaveBeenCalledWith(
      "api/v1/tvs/living/usage/content?from=2026-02-09",
      expect.anything(),
    );
  });

  it("shows last week's report with Pro", async () => {
    renderAt("#/activity", {
      "GET reports/weekly": REPORT,
      "GET tvs/living/inventory": INVENTORY,
    });
    expect(
      await screen.findByText("2 h 5 min watched · Times blocked: 3"),
    ).toBeInTheDocument();
    expect(screen.getByText("Netflix")).toBeInTheDocument();
  });

  it("explains that the weekly report needs Pro on the Free plan", async () => {
    renderAt("#/activity", {
      "GET reports/weekly": failure(403, "requires_pro"),
    });
    expect(
      await screen.findByText("The weekly report needs the Pro plan."),
    ).toBeInTheDocument();
  });
});

describe("TV details", () => {
  it("changes the rule set and the monitoring switch", async () => {
    const user = userEvent.setup();
    const fetchMock = renderAt("#/tvs/living", { "PATCH tvs/living": TV });
    const select = await screen.findByLabelText("Rule set");
    await user.selectOptions(select, "");
    expect(lastCall(fetchMock, "tvs/living", "PATCH").body).toEqual({
      policy_id: null,
    });
    await user.click(screen.getByRole("switch", { name: "Monitor this TV" }));
    const call = lastCall(fetchMock, "tvs/living", "PATCH");
    expect(call.body).toEqual({ enabled: false });
    expect(call.csrf).toBe("csrf-1");
  });

  it("removes the TV after confirmation", async () => {
    const user = userEvent.setup();
    const fetchMock = renderAt("#/tvs/living", {
      "DELETE tvs/living": new Response(null, { status: 204 }),
    });
    await user.click(
      await screen.findByRole("button", { name: "Remove this TV" }),
    );
    const dialog = await screen.findByRole("dialog");
    await user.click(within(dialog).getByRole("button", { name: "Remove TV" }));
    expect(
      await screen.findByRole("heading", { name: "Dashboard" }),
    ).toBeInTheDocument();
    expect(lastCall(fetchMock, "tvs/living", "DELETE").csrf).toBe("csrf-1");
  });

  it("is read-only without the admin scope", async () => {
    renderAt("#/tvs/living", {
      "GET auth/me": { ...ME, scopes: ["read", "control"] },
    });
    expect(await screen.findByLabelText("Rule set")).toBeDisabled();
    expect(screen.queryByRole("button", { name: "Remove this TV" })).toBeNull();
  });
});
