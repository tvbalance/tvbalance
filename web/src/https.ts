// The HTTPS address of the page the user is on, when the Engine offers one.

const LOCAL_HOSTS = new Set(["localhost", "127.0.0.1", "[::1]", "::1"]);
const INGRESS = "/api/hassio_ingress/";

type Where = Pick<
  Location,
  "protocol" | "hostname" | "pathname" | "search" | "hash"
>;

/** `null` when the page is already secure, is local, goes through Ingress or HTTPS is unavailable. */
export function secureAddress(
  where: Where,
  httpsPort: number | null | undefined,
): string | null {
  if (!httpsPort || where.protocol !== "http:") return null;
  if (LOCAL_HOSTS.has(where.hostname) || where.pathname.includes(INGRESS))
    return null;
  const host =
    where.hostname.includes(":") && !where.hostname.startsWith("[")
      ? `[${where.hostname}]`
      : where.hostname;
  return `https://${host}:${httpsPort}${where.pathname}${where.search}${where.hash}`;
}
