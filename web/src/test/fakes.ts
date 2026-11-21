import { vi } from "vitest";

type Handler = (request: { method: string; headers: Headers; body: unknown }) => Response;

export function json(body: unknown, init: ResponseInit = {}): Response {
  return new Response(JSON.stringify(body), {
    status: 200,
    headers: { "Content-Type": "application/json" },
    ...init,
  });
}

export function failure(status: number, code: string, message = code, headers = {}): Response {
  return json({ error: { code, message } }, { status, headers });
}

/** Stubs `fetch` with handlers keyed by "METHOD path" (path relative to `api/v1/`). */
export function stubApi(routes: Record<string, Handler | Response | object>) {
  const mock = vi.fn(async (url: string, init: RequestInit = {}) => {
    const method = init.method ?? "GET";
    const key = `${method} ${url.replace(/^api\/v1\//, "")}`;
    const route = routes[key];
    if (route === undefined) return failure(404, "not_found", `no stub for ${key}`);
    if (route instanceof Response) return route.clone();
    if (typeof route === "function") {
      return (route as Handler)({
        method,
        headers: new Headers(init.headers),
        body: init.body ? JSON.parse(String(init.body)) : undefined,
      });
    }
    return json(route);
  });
  vi.stubGlobal("fetch", mock);
  return mock;
}

export class FakeSocket {
  static instances: FakeSocket[] = [];
  onopen: (() => void) | null = null;
  onmessage: ((event: { data: string }) => void) | null = null;
  onclose: ((event: { code: number }) => void) | null = null;
  closed = false;

  constructor(readonly url: string) {
    FakeSocket.instances.push(this);
  }

  close() {
    this.closed = true;
  }
  open() {
    this.onopen?.();
  }
  send(message: unknown) {
    this.onmessage?.({ data: JSON.stringify(message) });
  }
  drop(code: number) {
    this.onclose?.({ code });
  }
}
