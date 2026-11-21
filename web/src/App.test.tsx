import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { App } from "./App";
import "./i18n";

const INFO = { version: "0.0.1", api_version: "1" };

function renderApp() {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={client}>
      <App />
    </QueryClientProvider>,
  );
}

afterEach(() => vi.unstubAllGlobals());

describe("System page", () => {
  it("shows engine info using a relative API URL", async () => {
    const fetchMock = vi.fn().mockResolvedValue({ ok: true, json: async () => INFO });
    vi.stubGlobal("fetch", fetchMock);
    renderApp();
    expect(await screen.findByText("0.0.1")).toBeInTheDocument();
    const url = fetchMock.mock.calls[0][0] as string;
    expect(url).toBe("api/v1/info");
    expect(url.startsWith("/")).toBe(false);
  });

  it("reports an unreachable engine", async () => {
    vi.stubGlobal("fetch", vi.fn().mockRejectedValue(new Error("down")));
    renderApp();
    expect(await screen.findByRole("alert")).toBeInTheDocument();
  });
});
