// Service worker: offline precache of the app shell, plus Web Push notifications.
import { clientsClaim } from "workbox-core";
import { cleanupOutdatedCaches, createHandlerBoundToURL, precacheAndRoute } from "workbox-precaching";
import { NavigationRoute, registerRoute } from "workbox-routing";
import { isSameApp, parsePush, safeTarget } from "./push";

interface WorkerWindow {
  url: string;
  focus(): Promise<unknown>;
  navigate?(url: string): Promise<unknown>;
}

interface WorkerScope {
  __WB_MANIFEST: Array<string | { url: string; revision: string | null }>;
  registration: {
    showNotification(title: string, options: { body: string; tag?: string; data?: unknown }): Promise<void>;
  };
  clients: {
    matchAll(options: { type: "window"; includeUncontrolled: boolean }): Promise<WorkerWindow[]>;
    openWindow(url: string): Promise<unknown>;
  };
  skipWaiting(): Promise<void>;
  addEventListener(type: "push", listener: (event: PushEvent) => void): void;
  addEventListener(type: "notificationclick", listener: (event: ClickEvent) => void): void;
  addEventListener(type: "message", listener: (event: { data?: { type?: string } }) => void): void;
}

interface Waitable {
  waitUntil(work: Promise<unknown>): void;
}
interface PushEvent extends Waitable {
  data: { text(): string } | null;
}
interface ClickEvent extends Waitable {
  notification: { close(): void; data?: { url?: unknown } };
}

declare const self: WorkerScope;

cleanupOutdatedCaches();
precacheAndRoute(self.__WB_MANIFEST);
registerRoute(new NavigationRoute(createHandlerBoundToURL("index.html")));

void self.skipWaiting();
clientsClaim();

self.addEventListener("push", (event) => {
  const message = parsePush(event.data?.text());
  if (!message) return;
  event.waitUntil(
    self.registration.showNotification(message.title, {
      body: message.body,
      tag: message.tag || undefined,
      data: { url: message.url },
    }),
  );
});

self.addEventListener("notificationclick", (event) => {
  event.notification.close();
  const target = safeTarget(event.notification.data?.url);
  if (!target) return;
  event.waitUntil(
    self.clients.matchAll({ type: "window", includeUncontrolled: true }).then(async (windows) => {
      const open = windows.find((w) => isSameApp(w.url, target));
      if (!open) return self.clients.openWindow(target);
      await open.focus();
      return open.navigate?.(target);
    }),
  );
});
