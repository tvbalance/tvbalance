import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { setCsrfToken } from "../../api/http";
import i18n from "../../i18n";
import { secureAddress } from "../../https";
import * as client from "../../push-client";
import { stubApi } from "../../test/fakes";
import { ToastProvider } from "../ui/toast";
import { Notifications } from "./Notifications";

vi.mock("../../push-client", async (original) => ({
  ...(await original<typeof import("../../push-client")>()),
  pushSupport: vi.fn(),
  permission: vi.fn(),
  currentSubscription: vi.fn(),
  subscribeBrowser: vi.fn(),
  appUrl: vi.fn(() => "https://ha.local/app/"),
}));

vi.mock("../../https", () => ({ secureAddress: vi.fn(() => null) }));

const ENDPOINT = "https://push.example.net/send/abc";
const ALL = ["blocked", "pairing_lost", "time_warning", "tv_unreachable"];

function device(over: Record<string, unknown> = {}) {
  return {
    id: "d1",
    events: ALL,
    language: "en",
    user_agent: "Firefox",
    created_at: "2026-03-01T10:00:00Z",
    last_sent_at: null,
    current: true,
    ...over,
  };
}

function renderCard(routes: Record<string, object> = {}) {
  const fetchMock = stubApi(routes);
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  render(
    <QueryClientProvider client={queryClient}>
      <ToastProvider>
        <Notifications />
      </ToastProvider>
    </QueryClientProvider>,
  );
  return fetchMock;
}

function bodyOf(fetchMock: ReturnType<typeof stubApi>, url: string, method: string) {
  const call = fetchMock.mock.calls
    .filter(([u, init]) => u === `api/v1/${url}` && ((init as RequestInit | undefined)?.method ?? "GET") === method)
    .at(-1);
  const init = call?.[1] as RequestInit | undefined;
  return init?.body ? JSON.parse(String(init.body)) : undefined;
}

beforeEach(async () => {
  await i18n.changeLanguage("en");
  setCsrfToken("csrf-1");
  vi.mocked(client.pushSupport).mockReturnValue("ok");
  vi.mocked(client.permission).mockReturnValue("default");
  vi.mocked(client.currentSubscription).mockResolvedValue(null);
});

afterEach(() => {
  vi.unstubAllGlobals();
  vi.clearAllMocks();
});

describe("Notifications", () => {
  it("explains that plain HTTP cannot receive notifications", async () => {
    vi.mocked(client.pushSupport).mockReturnValue("insecure");
    renderCard();
    expect(await screen.findByText(/secure \(HTTPS\) connection/)).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Turn on for this device" })).not.toBeInTheDocument();
  });

  it("links to the secure address when the Engine offers one", async () => {
    vi.mocked(client.pushSupport).mockReturnValue("insecure");
    vi.mocked(secureAddress).mockReturnValue("https://tvbalance.local:8766/settings");
    renderCard({ "GET info": { version: "1", api_version: "1", https_port: 8766 } });
    expect(await screen.findByRole("link", { name: /secure address/i })).toHaveAttribute(
      "href",
      "https://tvbalance.local:8766/settings",
    );
  });

  it("tells an unsupported browser apart", async () => {
    vi.mocked(client.pushSupport).mockReturnValue("unsupported");
    renderCard();
    expect(await screen.findByText(/can't show push notifications/)).toBeInTheDocument();
  });

  it("points at the browser settings when permission is denied", async () => {
    vi.mocked(client.permission).mockReturnValue("denied");
    renderCard();
    expect(await screen.findByText(/blocked for this site/)).toBeInTheDocument();
  });

  it("subscribes this browser with the Engine key and the current language", async () => {
    const subscription = { toJSON: () => ({ endpoint: ENDPOINT, keys: { p256dh: "P", auth: "A" } }) };
    vi.mocked(client.subscribeBrowser).mockResolvedValue(subscription as unknown as PushSubscription);
    const fetchMock = renderCard({
      "GET push/subscriptions": [],
      "GET push/key": { public_key: "PUBLIC" },
      "POST push/subscriptions": device(),
    });
    await userEvent.click(await screen.findByRole("button", { name: "Turn on for this device" }));
    await waitFor(() => expect(client.subscribeBrowser).toHaveBeenCalledWith("PUBLIC"));
    await waitFor(() => expect(bodyOf(fetchMock, "push/subscriptions", "POST")).toBeDefined());
    expect(bodyOf(fetchMock, "push/subscriptions", "POST")).toEqual({
      endpoint: ENDPOINT,
      keys: { p256dh: "P", auth: "A" },
      language: "en",
      app_url: "https://ha.local/app/",
    });
  });

  it("stays quiet when the user refuses the permission prompt", async () => {
    vi.mocked(client.subscribeBrowser).mockRejectedValue(new client.PermissionDenied());
    renderCard({ "GET push/subscriptions": [], "GET push/key": { public_key: "PUBLIC" } });
    await userEvent.click(await screen.findByRole("button", { name: "Turn on for this device" }));
    await waitFor(() => expect(client.subscribeBrowser).toHaveBeenCalled());
    expect(screen.queryByText("Something went wrong")).not.toBeInTheDocument();
  });

  describe("on a subscribed device", () => {
    const subscribed = { endpoint: ENDPOINT, unsubscribe: vi.fn().mockResolvedValue(true) };

    beforeEach(() => {
      vi.mocked(client.currentSubscription).mockResolvedValue(subscribed as unknown as PushSubscription);
    });

    it("switches events on and off", async () => {
      const fetchMock = renderCard({
        [`GET push/subscriptions?endpoint=${encodeURIComponent(ENDPOINT)}`]: [device()],
        "PATCH push/subscriptions/d1": device({ events: ["pairing_lost", "time_warning", "tv_unreachable"] }),
      });
      await userEvent.click(await screen.findByRole("checkbox", { name: "Content was blocked" }));
      await waitFor(() =>
        expect(bodyOf(fetchMock, "push/subscriptions/d1", "PATCH")).toEqual({
          events: ["pairing_lost", "time_warning", "tv_unreachable"],
        }),
      );
    });

    it("sends a test notification and reports it", async () => {
      renderCard({
        [`GET push/subscriptions?endpoint=${encodeURIComponent(ENDPOINT)}`]: [device()],
        "POST push/subscriptions/d1/test": { result: "delivered" },
      });
      await userEvent.click(await screen.findByRole("button", { name: "Send a test notification" }));
      expect(await screen.findByText("Test notification sent")).toBeInTheDocument();
    });

    it("warns when the push service forgot this device", async () => {
      renderCard({
        [`GET push/subscriptions?endpoint=${encodeURIComponent(ENDPOINT)}`]: [device()],
        "POST push/subscriptions/d1/test": { result: "gone" },
      });
      await userEvent.click(await screen.findByRole("button", { name: "Send a test notification" }));
      expect(await screen.findByText(/no longer registered/)).toBeInTheDocument();
    });

    it("turns off for this device and unsubscribes the browser", async () => {
      const fetchMock = renderCard({
        [`GET push/subscriptions?endpoint=${encodeURIComponent(ENDPOINT)}`]: [device()],
        "DELETE push/subscriptions/d1": new Response(null, { status: 204 }),
      });
      await userEvent.click(await screen.findByRole("button", { name: "Turn off for this device" }));
      await waitFor(() => expect(subscribed.unsubscribe).toHaveBeenCalled());
      expect(fetchMock).toHaveBeenCalledWith("api/v1/push/subscriptions/d1", expect.objectContaining({ method: "DELETE" }));
    });

    it("lists and removes the other devices", async () => {
      const fetchMock = renderCard({
        [`GET push/subscriptions?endpoint=${encodeURIComponent(ENDPOINT)}`]: [
          device(),
          device({ id: "d2", current: false, user_agent: "Chrome on tablet" }),
        ],
        "DELETE push/subscriptions/d2": new Response(null, { status: 204 }),
      });
      expect(await screen.findByText("Chrome on tablet")).toBeInTheDocument();
      expect(screen.getByText("Nothing sent yet")).toBeInTheDocument();
      await userEvent.click(screen.getByRole("button", { name: "Remove Chrome on tablet" }));
      await waitFor(() =>
        expect(fetchMock).toHaveBeenCalledWith("api/v1/push/subscriptions/d2", expect.objectContaining({ method: "DELETE" })),
      );
      expect(subscribed.unsubscribe).not.toHaveBeenCalled();
    });
  });
});
