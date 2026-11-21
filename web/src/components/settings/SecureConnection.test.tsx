import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { setCsrfToken } from "../../api/http";
import i18n from "../../i18n";
import { stubApi } from "../../test/fakes";
import { ToastProvider } from "../ui/toast";
import { SecureConnection } from "./SecureConnection";

const FINGERPRINT = "AA:BB:CC:DD";

function status(over: Record<string, unknown> = {}) {
  return {
    mode: "auto",
    active: true,
    https_port: 8766,
    names: ["tvbalance.local", "10.1.2.3"],
    skipped_names: [],
    urls: ["https://tvbalance.local:8766", "https://10.1.2.3:8766"],
    expires_at: "2027-12-24T10:00:00Z",
    ca_fingerprint: FINGERPRINT,
    error: null,
    ...over,
  };
}

function renderCard(routes: Record<string, object>) {
  const fetchMock = stubApi(routes);
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  render(
    <QueryClientProvider client={queryClient}>
      <ToastProvider>
        <SecureConnection />
      </ToastProvider>
    </QueryClientProvider>,
  );
  return fetchMock;
}

beforeEach(async () => {
  await i18n.changeLanguage("en");
  setCsrfToken("csrf-1");
});

afterEach(() => vi.unstubAllGlobals());

describe("SecureConnection", () => {
  it("shows the addresses, the fingerprint and the CA downloads", async () => {
    renderCard({ "GET tls": status({ skipped_names: ["example.com"] }) });
    expect(
      await screen.findByRole("link", { name: "https://tvbalance.local:8766" }),
    ).toHaveAttribute("href", "https://tvbalance.local:8766");
    expect(screen.getByText(FINGERPRINT)).toBeInTheDocument();
    expect(
      screen.getByRole("link", { name: /download the certificate/i }),
    ).toHaveAttribute("href", "api/v1/tls/ca.crt");
    expect(screen.getByRole("link", { name: /iphone/i })).toHaveAttribute(
      "href",
      "api/v1/tls/ca.mobileconfig",
    );
    expect(screen.getByText(/example\.com/)).toBeInTheDocument();
  });

  it("creates a new certificate only after confirmation", async () => {
    const user = userEvent.setup();
    const fetchMock = renderCard({
      "GET tls": status(),
      "POST tls/rotate": status({ ca_fingerprint: "11:22:33" }),
    });
    const posted = () =>
      fetchMock.mock.calls.some(([url]) => url === "api/v1/tls/rotate");
    await user.click(
      await screen.findByRole("button", { name: /new certificate/i }),
    );
    const dialog = await screen.findByRole("dialog");
    expect(posted()).toBe(false);
    await user.click(within(dialog).getByRole("button", { name: /create/i }));
    await vi.waitFor(() => expect(posted()).toBe(true));
    expect(await screen.findByText("11:22:33")).toBeInTheDocument();
  });

  it("explains a certificate the user provided and offers no CA", async () => {
    renderCard({ "GET tls": status({ mode: "custom", ca_fingerprint: null }) });
    expect(
      await screen.findByText(/your own certificate/i),
    ).toBeInTheDocument();
    expect(
      screen.queryByRole("link", { name: /download the certificate/i }),
    ).toBeNull();
    expect(
      screen.queryByRole("button", { name: /new certificate/i }),
    ).toBeNull();
  });

  it("says when HTTPS is off", async () => {
    renderCard({
      "GET tls": status({
        mode: "off",
        active: false,
        urls: [],
        names: [],
        ca_fingerprint: null,
      }),
    });
    expect(await screen.findByText(/HTTPS is turned off/i)).toBeInTheDocument();
  });

  it("shows why HTTPS is unavailable", async () => {
    renderCard({
      "GET tls": status({
        mode: "custom",
        active: false,
        urls: [],
        error: "The certificate has expired",
        ca_fingerprint: null,
      }),
    });
    expect(
      await screen.findByText("The certificate has expired"),
    ).toBeInTheDocument();
  });
});
