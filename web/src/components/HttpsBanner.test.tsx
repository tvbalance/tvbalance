import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import i18n from "../i18n";
import { stubApi } from "../test/fakes";
import { HttpsBanner } from "./HttpsBanner";

const PLAIN = {
  protocol: "http:",
  hostname: "tvbalance.local",
  pathname: "/",
  search: "",
  hash: "",
};

function renderBanner(info: object, where: typeof PLAIN = PLAIN) {
  stubApi({ "GET info": info });
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return render(
    <QueryClientProvider client={queryClient}>
      <HttpsBanner where={where} />
    </QueryClientProvider>,
  );
}

beforeEach(async () => {
  await i18n.changeLanguage("en");
  localStorage.clear();
});

afterEach(() => vi.unstubAllGlobals());

describe("HttpsBanner", () => {
  it("offers the secure address on a plain http page", async () => {
    renderBanner({ version: "1", api_version: "1", https_port: 8766 });
    const link = await screen.findByRole("link", { name: /secure address/i });
    expect(link).toHaveAttribute("href", "https://tvbalance.local:8766/");
  });

  it("says nothing when HTTPS is unavailable", async () => {
    renderBanner({ version: "1", api_version: "1", https_port: null });
    await vi.waitFor(() => expect(fetch).toHaveBeenCalled());
    expect(screen.queryByRole("link")).toBeNull();
  });

  it("says nothing on localhost or an https page", async () => {
    renderBanner(
      { version: "1", api_version: "1", https_port: 8766 },
      { ...PLAIN, hostname: "localhost" },
    );
    await vi.waitFor(() => expect(fetch).toHaveBeenCalled());
    expect(screen.queryByRole("link")).toBeNull();
  });

  it("stays dismissed", async () => {
    const user = userEvent.setup();
    const first = renderBanner({
      version: "1",
      api_version: "1",
      https_port: 8766,
    });
    await user.click(await screen.findByRole("button", { name: /dismiss/i }));
    expect(screen.queryByRole("link")).toBeNull();
    first.unmount();
    renderBanner({ version: "1", api_version: "1", https_port: 8766 });
    await vi.waitFor(() => expect(fetch).toHaveBeenCalled());
    expect(screen.queryByRole("link")).toBeNull();
  });

  it("still works when storage is unavailable", async () => {
    vi.spyOn(Storage.prototype, "getItem").mockImplementation(() => {
      throw new Error("blocked");
    });
    vi.spyOn(Storage.prototype, "setItem").mockImplementation(() => {
      throw new Error("blocked");
    });
    const user = userEvent.setup();
    renderBanner({ version: "1", api_version: "1", https_port: 8766 });
    await user.click(await screen.findByRole("button", { name: /dismiss/i }));
    expect(screen.queryByRole("link")).toBeNull();
    vi.restoreAllMocks();
  });
});
