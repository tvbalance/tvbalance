import { useQuery } from "@tanstack/react-query";

import { api, ApiError, setCsrfToken } from "./http";
import type { components } from "./schema";

type Schemas = components["schemas"];

export type Me = Schemas["Me"];
export type Tv = Schemas["TvOut"];
export type TvStatus = Schemas["TvStatusOut"];
export type Policy = Schemas["PolicyOut"];
export type Usage = Schemas["UsageOut"];
export type EngineEvent = Schemas["EventOut"];
export type Settings = Schemas["SettingsOut"];
export type Session = Schemas["SessionOut"];
export type Token = Schemas["TokenOut"];
export type PushDevice = Schemas["PushSubscriptionOut"];
export type PushEvent = PushDevice["events"][number];
export type Inventory = Schemas["InventoryOut"];
export type Adapter = Schemas["AdapterOut"];
export type FoundTv = Schemas["FoundTvOut"];
export type Pairing = Schemas["PairingOut"];

export const keys = {
  state: ["auth", "state"] as const,
  me: ["auth", "me"] as const,
  tvs: ["tvs"] as const,
  policies: ["policies"] as const,
  usage: (tvId: string, days: number) => ["usage", tvId, days] as const,
  events: (tvId: string | null, limit: number) => ["events", tvId, limit] as const,
  eventsAll: ["events"] as const,
  settings: ["settings"] as const,
  sessions: ["auth", "sessions"] as const,
  tokens: ["auth", "tokens"] as const,
  push: ["push"] as const,
  pushDevices: (endpoint: string | null) => ["push", "devices", endpoint] as const,
  inventory: (tvId: string) => ["inventory", tvId] as const,
  adapters: ["adapters"] as const,
  discovery: ["discovery"] as const,
  pairing: (id: string) => ["pairing", id] as const,
};

export function useAuthState() {
  return useQuery({
    queryKey: keys.state,
    queryFn: ({ signal }) => api.get<Schemas["AuthState"]>("auth/state", signal),
  });
}

/** The signed-in caller, or `null` when there is no valid credential. */
export function useMe() {
  return useQuery({
    queryKey: keys.me,
    queryFn: async ({ signal }): Promise<Me | null> => {
      try {
        const me = await api.get<Me>("auth/me", signal);
        setCsrfToken(me.csrf_token);
        return me;
      } catch (error) {
        if (error instanceof ApiError && error.status === 401) {
          setCsrfToken(null);
          return null;
        }
        throw error;
      }
    },
  });
}

export function useTvs() {
  return useQuery({
    queryKey: keys.tvs,
    queryFn: ({ signal }) => api.get<Tv[]>("tvs", signal),
  });
}

export function usePolicies() {
  return useQuery({
    queryKey: keys.policies,
    queryFn: ({ signal }) => api.get<Policy[]>("policies", signal),
  });
}

export function useUsage(tvId: string, days = 7) {
  return useQuery({
    queryKey: keys.usage(tvId, days),
    queryFn: ({ signal }) => api.get<Usage>(`tvs/${tvId}/usage?days=${days}`, signal),
  });
}

export function useEvents(tvId: string | null, limit = 50) {
  const query = new URLSearchParams({ limit: String(limit) });
  if (tvId) query.set("tv_id", tvId);
  return useQuery({
    queryKey: keys.events(tvId, limit),
    queryFn: ({ signal }) => api.get<EngineEvent[]>(`events?${query}`, signal),
  });
}

export function useSettings() {
  return useQuery({
    queryKey: keys.settings,
    queryFn: ({ signal }) => api.get<Settings>("settings", signal),
  });
}

export function useSessions(enabled = true) {
  return useQuery({
    queryKey: keys.sessions,
    queryFn: ({ signal }) => api.get<Session[]>("auth/sessions", signal),
    enabled,
  });
}

export function useTokens(enabled = true) {
  return useQuery({
    queryKey: keys.tokens,
    queryFn: ({ signal }) => api.get<Token[]>("auth/tokens", signal),
    enabled,
  });
}

/** A TV's apps, inputs and channels; fails with `tv_offline` while the TV is unreachable. */
export function useInventory(tvId: string | null) {
  return useQuery({
    queryKey: keys.inventory(tvId ?? ""),
    queryFn: ({ signal }) => api.get<Inventory>(`tvs/${tvId}/inventory`, signal),
    enabled: tvId !== null,
    retry: false,
  });
}

/** TVs the Engine can see on the network. Runs once; `refetch()` searches again. */
export function useDiscovery() {
  return useQuery({
    queryKey: keys.discovery,
    queryFn: ({ signal }) => api.get<FoundTv[]>("discovery", signal),
    retry: false,
    staleTime: Infinity,
    gcTime: 0,
  });
}

/** A pairing, polled every second while the person has yet to accept on the TV. */
export function usePairing(id: string | null) {
  return useQuery({
    queryKey: keys.pairing(id ?? ""),
    queryFn: ({ signal }) => api.get<Pairing>(`pairings/${id}`, signal),
    enabled: id !== null,
    retry: false,
    refetchInterval: (query) => (query.state.data?.state === "waiting_for_user" ? 1000 : false),
  });
}

export function useAdapters() {
  return useQuery({
    queryKey: keys.adapters,
    queryFn: ({ signal }) => api.get<Adapter[]>("adapters", signal),
  });
}

export function usePushDevices(endpoint: string | null, enabled = true) {
  return useQuery({
    queryKey: keys.pushDevices(endpoint),
    queryFn: ({ signal }) =>
      api.get<PushDevice[]>(
        `push/subscriptions${endpoint ? `?endpoint=${encodeURIComponent(endpoint)}` : ""}`,
        signal,
      ),
    enabled,
  });
}
