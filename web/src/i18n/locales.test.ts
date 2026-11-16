import { describe, expect, it } from "vitest";

import de from "./locales/de.json";
import en from "./locales/en.json";
import es from "./locales/es.json";
import fr from "./locales/fr.json";
import it_ from "./locales/it.json";

function keys(obj: Record<string, unknown>, prefix = ""): string[] {
  return Object.entries(obj).flatMap(([k, v]) =>
    typeof v === "object" && v !== null
      ? keys(v as Record<string, unknown>, `${prefix}${k}.`)
      : [`${prefix}${k}`],
  );
}

describe("locales", () => {
  const reference = keys(en).sort();
  it.each([
    ["it", it_],
    ["de", de],
    ["fr", fr],
    ["es", es],
  ])("%s has exactly the same keys as en", (_name, locale) => {
    expect(keys(locale).sort()).toEqual(reference);
  });
});
