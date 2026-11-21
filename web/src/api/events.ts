import type { QueryClient } from "@tanstack/react-query";
import { useEffect } from "react";

import { keys, type Tv, type TvStatus } from "./hooks";

const NOT_AUTHENTICATED = 4401;
const FORBIDDEN = 4403;
const FIRST_RETRY_MS = 1000;
const MAX_RETRY_MS = 30_000;

interface Message {
  type: string;
  tv_id: string | null;
  payload: unknown;
}

/** Relative to the page so it stays inside the Ingress prefix; ws or wss follows the page. */
export function eventsUrl(base: string = window.location.href): string {
  const url = new URL("api/v1/events/ws", base);
  url.protocol = url.protocol === "https:" ? "wss:" : "ws:";
  return url.toString();
}

function apply(queryClient: QueryClient, message: Message): void {
  if (message.type === "ping") return;
  if (message.type === "status" && message.tv_id) {
    queryClient.setQueryData<Tv[]>(keys.tvs, (tvs) =>
      tvs?.map((tv) =>
        tv.id === message.tv_id ? { ...tv, status: message.payload as TvStatus } : tv,
      ),
    );
    return;
  }
  // Any other message is a logged event: the TV's state moved, so refetch what shows it.
  void queryClient.invalidateQueries({ queryKey: keys.tvs });
  void queryClient.invalidateQueries({ queryKey: keys.eventsAll });
  void queryClient.invalidateQueries({ queryKey: ["usage"] });
}

/**
 * Keeps the TV cache live. Reconnects with a growing delay; a 4401 means the session is
 * gone, so `me` is refetched (which sends the user to sign in) instead of retrying.
 * Returns the function that stops it.
 */
export function connectEvents(queryClient: QueryClient): () => void {
  let socket: WebSocket | null = null;
  let timer: ReturnType<typeof setTimeout> | undefined;
  let delay = FIRST_RETRY_MS;
  let stopped = false;

  const open = () => {
    socket = new WebSocket(eventsUrl());
    socket.onopen = () => {
      delay = FIRST_RETRY_MS;
      // Whatever happened while we were away is not in the stream.
      void queryClient.invalidateQueries({ queryKey: keys.tvs });
    };
    socket.onmessage = (event) => {
      try {
        apply(queryClient, JSON.parse(String(event.data)) as Message);
      } catch {
        // A malformed frame is not worth dropping the connection for.
      }
    };
    socket.onclose = (event) => {
      socket = null;
      if (stopped) return;
      if (event.code === NOT_AUTHENTICATED) {
        void queryClient.invalidateQueries({ queryKey: keys.me });
        return;
      }
      if (event.code === FORBIDDEN) return;
      timer = setTimeout(open, delay);
      delay = Math.min(delay * 2, MAX_RETRY_MS);
    };
  };

  open();
  return () => {
    stopped = true;
    clearTimeout(timer);
    socket?.close();
  };
}

export function useLiveEvents(queryClient: QueryClient, enabled: boolean): void {
  useEffect(() => {
    if (!enabled) return;
    return connectEvents(queryClient);
  }, [queryClient, enabled]);
}
