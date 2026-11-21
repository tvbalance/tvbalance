import type { TFunction } from "i18next";

import { ApiError } from "./http";

/** A translated, human message for a failed request; `overrides` map codes to special keys. */
export function errorMessage(
  t: TFunction,
  error: unknown,
  overrides: Record<string, string> = {},
): string {
  if (error instanceof ApiError) {
    if (error.code === "rate_limited") {
      return t("errors.rate_limited", { seconds: error.retryAfter ?? 60 });
    }
    const key = overrides[error.code] ?? `errors.${error.code}`;
    return t(key, { defaultValue: t("errors.unknown") });
  }
  return t("errors.network");
}
