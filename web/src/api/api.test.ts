import { QueryClient } from "@tanstack/react-query";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { failure, FakeSocket, json, stubApi } from "../test/fakes";
import { connectEvents, eventsUrl } from "./events";
import { keys, type Tv } from "./hooks";
import { api, ApiError, setCsrfToken, setUnauthorizedHandler } from "./http";

afterEach(() => {
  vi.unstubAllGlobals();
  vi.useRealTimers();
  setCsrfToken(null);
  setUnauthorizedHandler(null);
});

describe("http client", () => {
  it("uses relative URLs and sends no CSRF header on reads", async () => {
    const fetchMock = stubApi({ "GET tvs": [] });
    await api.get("tvs");
    const [url, init] = fetchMock.mock.calls[0] as [string, RequestInit];
    expect(url).toBe("api/v1/tvs");
    expect(init.credentials).toBe("same-origin");
    expect(new Headers(init.headers).has("X-TVBalance-CSRF")).toBe(false);
  });

  it("sends the CSRF token on unsafe methods only once it is known", async () => {
    const seen: (string | null)[] = [];
    stubApi({
      "POST tvs/a/pause": ({ headers }) => {
        seen.push(headers.get("X-TVBalance-CSRF"));
        return json({});
      },
    });
    await api.post("tvs/a/pause", { minutes: 5 });
    setCsrfToken("tok");
    await api.post("tvs/a/pause", { minutes: 5 });
    expect(seen).toEqual([null, "tok"]);
  });

  it("turns the error envelope into an ApiError", async () => {
    stubApi({ "GET policies/9": failure(404, "not_found", "No such policy") });
    await expect(api.get("policies/9")).rejects.toMatchObject({
      status: 404,
      code: "not_found",
      message: "No such policy",
    });
  });

  it("keeps Retry-After on a rate limit", async () => {
    stubApi({ "POST auth/login": failure(429, "rate_limited", "slow", { "Retry-After": "42" }) });
    const error = (await api.post("auth/login", {}).catch((e: unknown) => e)) as ApiError;
    expect(error.retryAfter).toBe(42);
  });

  it("copes with a non-JSON error body", async () => {
    stubApi({ "GET tvs": new Response("<html>", { status: 502 }) });
    await expect(api.get("tvs")).rejects.toMatchObject({ status: 502, code: "http_error" });
  });

  it("returns undefined for 204", async () => {
    stubApi({ "DELETE auth/pin": new Response(null, { status: 204 }) });
    await expect(api.delete("auth/pin")).resolves.toBeUndefined();
  });

  it("calls the unauthorized handler on 401", async () => {
    const handler = vi.fn();
    setUnauthorizedHandler(handler);
    stubApi({ "GET tvs": failure(401, "not_authenticated") });
    await expect(api.get("tvs")).rejects.toBeInstanceOf(ApiError);
    expect(handler).toHaveBeenCalledOnce();
  });
});

const TV = (id: string): Tv => ({
  id,
  name: id,
  adapter_id: "fake",
  host: "tv.local",
  enabled: true,
  needs_pairing: false,
  plan_limited: false,
  policy_id: null,
  created_at: "2026-01-01T00:00:00Z",
  status: null,
});

describe("live events", () => {
  let queryClient: QueryClient;

  beforeEach(() => {
    FakeSocket.instances = [];
    vi.stubGlobal("WebSocket", FakeSocket);
    queryClient = new QueryClient();
    queryClient.setQueryData(keys.tvs, [TV("a"), TV("b")]);
  });

  it("derives a relative ws URL from the page", () => {
    expect(eventsUrl("http://host:8099/#/x")).toBe("ws://host:8099/api/v1/events/ws");
    expect(eventsUrl("https://h/api/hassio_ingress/t/")).toBe(
      "wss://h/api/hassio_ingress/t/api/v1/events/ws",
    );
  });

  it("patches the TV a status message names", () => {
    connectEvents(queryClient);
    FakeSocket.instances[0].send({
      type: "status",
      tv_id: "b",
      payload: { connected: true, watched_seconds: 60 },
    });
    const tvs = queryClient.getQueryData<Tv[]>(keys.tvs)!;
    expect(tvs[0].status).toBeNull();
    expect(tvs[1].status).toMatchObject({ connected: true });
  });

  it("refetches on an event and ignores pings and junk", () => {
    const invalidate = vi.spyOn(queryClient, "invalidateQueries");
    connectEvents(queryClient);
    const socket = FakeSocket.instances[0];
    socket.send({ type: "ping", tv_id: null, payload: {} });
    socket.onmessage?.({ data: "not json" });
    expect(invalidate).not.toHaveBeenCalled();
    socket.send({ type: "blocked", tv_id: "a", payload: {} });
    expect(invalidate).toHaveBeenCalledWith({ queryKey: keys.tvs });
  });

  it("reconnects with a growing delay and resets it once open", () => {
    vi.useFakeTimers();
    connectEvents(queryClient);
    FakeSocket.instances[0].drop(1006);
    vi.advanceTimersByTime(999);
    expect(FakeSocket.instances).toHaveLength(1);
    vi.advanceTimersByTime(1);
    expect(FakeSocket.instances).toHaveLength(2);
    FakeSocket.instances[1].drop(1006);
    vi.advanceTimersByTime(2000);
    expect(FakeSocket.instances).toHaveLength(3);
    FakeSocket.instances[2].open();
    FakeSocket.instances[2].drop(1006);
    vi.advanceTimersByTime(1000);
    expect(FakeSocket.instances).toHaveLength(4);
  });

  it("refetches me on 4401 and does not reconnect", () => {
    vi.useFakeTimers();
    const invalidate = vi.spyOn(queryClient, "invalidateQueries");
    connectEvents(queryClient);
    FakeSocket.instances[0].drop(4401);
    expect(invalidate).toHaveBeenCalledWith({ queryKey: keys.me });
    vi.advanceTimersByTime(60_000);
    expect(FakeSocket.instances).toHaveLength(1);
  });

  it("does not reconnect on 4403", () => {
    vi.useFakeTimers();
    connectEvents(queryClient);
    FakeSocket.instances[0].drop(4403);
    vi.advanceTimersByTime(60_000);
    expect(FakeSocket.instances).toHaveLength(1);
  });

  it("stops for good when closed", () => {
    vi.useFakeTimers();
    const stop = connectEvents(queryClient);
    const socket = FakeSocket.instances[0];
    stop();
    expect(socket.closed).toBe(true);
    socket.drop(1006);
    vi.advanceTimersByTime(60_000);
    expect(FakeSocket.instances).toHaveLength(1);
  });
});
