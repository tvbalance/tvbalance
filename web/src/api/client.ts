import type { components } from "./schema";

export type EngineInfo = components["schemas"]["InfoResponse"];

/**
 * Relative URL on purpose (no leading slash): under Home Assistant Ingress the page
 * lives at /api/hassio_ingress/<token>/, and absolute paths would escape it.
 */
export async function fetchInfo(signal?: AbortSignal): Promise<EngineInfo> {
  const resp = await fetch("api/v1/info", { signal });
  if (!resp.ok) {
    throw new Error(`HTTP ${resp.status}`);
  }
  return (await resp.json()) as EngineInfo;
}
