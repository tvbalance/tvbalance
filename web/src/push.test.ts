import { isSameApp, parsePush, safeTarget } from "./push";

describe("parsePush", () => {
  it("reads a complete message", () => {
    const text = JSON.stringify({ title: "TV", body: "Blocked", tag: "blocked:1", url: "https://a/b#/x" });
    expect(parsePush(text)).toEqual({ title: "TV", body: "Blocked", tag: "blocked:1", url: "https://a/b#/x" });
  });

  it("fills in a missing tag and url", () => {
    expect(parsePush('{"title":"TV","body":"x"}')).toEqual({ title: "TV", body: "x", tag: "", url: "" });
  });

  it.each([undefined, "", "not json", "null", "[]", '{"title":1,"body":"x"}', '{"title":"t"}'])(
    "rejects %s",
    (text) => {
      expect(parsePush(text)).toBeNull();
    },
  );
});

describe("safeTarget", () => {
  it("keeps http and https links only", () => {
    expect(safeTarget("https://ha.local/app/#/tvs/1")).toBe("https://ha.local/app/#/tvs/1");
    expect(safeTarget("http://localhost:8765/#/")).toBe("http://localhost:8765/#/");
    expect(safeTarget("javascript:alert(1)")).toBeNull();
    expect(safeTarget("/relative")).toBeNull();
    expect(safeTarget(42)).toBeNull();
  });
});

describe("isSameApp", () => {
  it("ignores the hash and the query", () => {
    expect(isSameApp("https://ha.local/app/#/tvs/1", "https://ha.local/app/#/tvs/2/pair")).toBe(true);
  });

  it("tells apps on another origin or path apart", () => {
    expect(isSameApp("https://other/app/", "https://ha.local/app/")).toBe(false);
    expect(isSameApp("https://ha.local/other/", "https://ha.local/app/")).toBe(false);
    expect(isSameApp("about:blank", "https://ha.local/app/")).toBe(false);
  });
});
