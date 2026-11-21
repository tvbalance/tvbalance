// Pure helpers for the service worker's push and notification-click handlers.

export interface PushMessage {
  title: string;
  body: string;
  tag: string;
  url: string;
}

export function parsePush(text: string | undefined): PushMessage | null {
  if (!text) return null;
  try {
    const raw: unknown = JSON.parse(text);
    if (typeof raw !== "object" || raw === null) return null;
    const { title, body, tag, url } = raw as Record<string, unknown>;
    if (typeof title !== "string" || typeof body !== "string") return null;
    return {
      title,
      body,
      tag: typeof tag === "string" ? tag : "",
      url: typeof url === "string" ? url : "",
    };
  } catch {
    return null;
  }
}

function webUrl(value: string): URL | null {
  try {
    const url = new URL(value);
    return url.protocol === "http:" || url.protocol === "https:" ? url : null;
  } catch {
    return null;
  }
}

/** The link a notification opens: only http(s) links are followed, anything else is dropped. */
export function safeTarget(value: unknown): string | null {
  return typeof value === "string" && webUrl(value) ? value : null;
}

/** True when `candidate` is a page of the same app as `target` (same origin and path). */
export function isSameApp(candidate: string, target: string): boolean {
  const a = webUrl(candidate);
  const b = webUrl(target);
  return a !== null && b !== null && a.origin === b.origin && a.pathname === b.pathname;
}
