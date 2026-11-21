import { describe, expect, it } from "vitest";

import { secureAddress } from "./https";

const at = (over: Partial<Location> = {}) => ({
  protocol: "http:",
  hostname: "tvbalance.local",
  pathname: "/",
  search: "",
  hash: "#/settings",
  ...over,
});

describe("secureAddress", () => {
  it("points a plain http address at the HTTPS port, keeping the page", () => {
    expect(secureAddress(at(), 8766)).toBe(
      "https://tvbalance.local:8766/#/settings",
    );
  });

  it("brackets an IPv6 host", () => {
    expect(secureAddress(at({ hostname: "fd00::5" }), 8766)).toBe(
      "https://[fd00::5]:8766/#/settings",
    );
  });

  it.each([
    ["already https", at({ protocol: "https:" }), 8766],
    ["localhost", at({ hostname: "localhost" }), 8766],
    ["loopback", at({ hostname: "127.0.0.1" }), 8766],
    [
      "Home Assistant Ingress",
      at({ pathname: "/api/hassio_ingress/abc/" }),
      8766,
    ],
    ["no HTTPS port", at(), null],
    ["HTTPS port unknown", at(), undefined],
  ])("offers nothing when %s", (_name, location, port) => {
    expect(secureAddress(location, port)).toBeNull();
  });
});
