// The browser side of Web Push: support detection, permission and subscription.

export type PushSupport = "ok" | "insecure" | "unsupported";

export function pushSupport(): PushSupport {
  if (!window.isSecureContext) return "insecure";
  const ready = "serviceWorker" in navigator && "PushManager" in window && "Notification" in window;
  return ready ? "ok" : "unsupported";
}

export function permission(): NotificationPermission {
  return "Notification" in window ? Notification.permission : "denied";
}

export class PermissionDenied extends Error {}

function keyBytes(key: string): Uint8Array<ArrayBuffer> {
  const padded = (key + "=".repeat((4 - (key.length % 4)) % 4)).replace(/-/g, "+").replace(/_/g, "/");
  return Uint8Array.from(atob(padded), (c) => c.charCodeAt(0));
}

export async function currentSubscription(): Promise<PushSubscription | null> {
  if (pushSupport() !== "ok") return null;
  const registration = await navigator.serviceWorker.ready;
  return registration.pushManager.getSubscription();
}

/** Asks for permission, then subscribes this browser with the Engine's VAPID key. */
export async function subscribeBrowser(publicKey: string): Promise<PushSubscription> {
  if ((await Notification.requestPermission()) !== "granted") throw new PermissionDenied();
  const registration = await navigator.serviceWorker.ready;
  return registration.pushManager.subscribe({
    userVisibleOnly: true,
    applicationServerKey: keyBytes(publicKey),
  });
}

/** The page a notification opens: Home Assistant's panel when embedded by Ingress, else this app. */
export function appUrl(): string {
  let url = window.location.href;
  try {
    if (window.top && window.top !== window) url = window.top.location.href;
  } catch {
    // A cross-origin parent: keep this frame's own address.
  }
  return url.split("#")[0];
}
