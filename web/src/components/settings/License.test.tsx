import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { setCsrfToken } from "../../api/http";
import i18n from "../../i18n";
import { failure, json, stubApi } from "../../test/fakes";
import { ToastProvider } from "../ui/toast";
import { License } from "./License";

function license(over: Record<string, unknown> = {}) {
  return {
    status: "none",
    tier: "free",
    licensee: null,
    expires_at: null,
    max_tvs: 1,
    checkout_url: "",
    ...over,
  };
}

const PRO = {
  status: "active",
  tier: "pro",
  licensee: "Rossi",
  max_tvs: null,
};

function renderCard(routes: Record<string, object>) {
  const fetchMock = stubApi(routes);
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  render(
    <QueryClientProvider client={queryClient}>
      <ToastProvider>
        <License />
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

describe("License", () => {
  it("shows the Free plan with its limit and no remove button", async () => {
    renderCard({ "GET license": license() });
    expect(await screen.findByText("Free plan")).toBeInTheDocument();
    expect(screen.getByText("TVs supervised: 1")).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /remove license/i })).toBeNull();
  });

  it("offers the purchase link only when one is configured", async () => {
    renderCard({
      "GET license": license({ checkout_url: "https://shop.example/pro" }),
    });
    expect(await screen.findByRole("link", { name: "Buy Pro" })).toHaveAttribute(
      "href",
      "https://shop.example/pro",
    );
  });

  it("shows the licensee and that a Pro license never expires", async () => {
    renderCard({ "GET license": license(PRO) });
    expect(await screen.findByText("Licensed to Rossi")).toBeInTheDocument();
    expect(screen.getByText("No expiry date")).toBeInTheDocument();
    expect(screen.getByText("TVs supervised: unlimited")).toBeInTheDocument();
    expect(screen.queryByRole("link", { name: "Buy Pro" })).toBeNull();
  });

  it("explains an expired license", async () => {
    renderCard({
      "GET license": license({ status: "expired", licensee: "Rossi" }),
    });
    expect(await screen.findByText(/has expired/i)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /remove license/i })).toBeInTheDocument();
  });

  it("activates a pasted key", async () => {
    const user = userEvent.setup();
    const sent: unknown[] = [];
    renderCard({
      "GET license": license(),
      "PUT license": ({ body }: { body: unknown }) => {
        sent.push(body);
        return json(license(PRO));
      },
    });
    await user.type(await screen.findByLabelText("License key"), " abc.def ");
    await user.click(screen.getByRole("button", { name: "Activate" }));
    expect(await screen.findByText("Licensed to Rossi")).toBeInTheDocument();
    expect(sent).toEqual([{ key: "abc.def" }]);
  });

  it("shows why a key was refused", async () => {
    const user = userEvent.setup();
    renderCard({
      "GET license": license(),
      "PUT license": failure(422, "invalid_license", "bad signature"),
    });
    await user.type(await screen.findByLabelText("License key"), "nope");
    await user.click(screen.getByRole("button", { name: "Activate" }));
    expect(
      await screen.findByText("This license key is not valid."),
    ).toBeInTheDocument();
  });

  it("removes the license only after confirmation", async () => {
    const user = userEvent.setup();
    const fetchMock = renderCard({
      "GET license": license(PRO),
      "DELETE license": license(),
    });
    const deleted = () =>
      fetchMock.mock.calls.some(
        ([, init]) => (init as RequestInit | undefined)?.method === "DELETE",
      );
    await user.click(
      await screen.findByRole("button", { name: /remove license/i }),
    );
    const dialog = await screen.findByRole("dialog");
    expect(deleted()).toBe(false);
    await user.click(within(dialog).getByRole("button", { name: "Remove" }));
    await vi.waitFor(() => expect(deleted()).toBe(true));
    expect(await screen.findByText("Free plan")).toBeInTheDocument();
  });
});
