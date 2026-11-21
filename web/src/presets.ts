import type { components } from "./api/schema";

export type PolicyDoc = components["schemas"]["PolicyDoc"];

/** Weekday numbers follow Python's `date.weekday()`: 0 is Monday. */
const WEEKDAYS = [0, 1, 2, 3, 4];
const WEEKEND = [5, 6];

function windows(days: number[], start: string, end: string): Record<string, PolicyDoc["schedule"]["windows"][string]> {
  return Object.fromEntries(days.map((day) => [String(day), [{ start, end }]]));
}

export function emptyPolicy(): PolicyDoc {
  return {
    schedule: { windows: {}, special_days: {} },
    daily_budget_minutes: null,
    blocked_apps: [],
    blocked_inputs: [],
    blocked_channels: [],
    always_allowed_apps: [],
    always_allowed_inputs: [],
    always_allowed_channels: [],
    allow_list_apps: null,
    fallback: null,
    warn_at_minutes: [10, 5],
    escalation: { debounce: 3, grace: 15, power_off_cap: 3, cap_window: 300, cap_pause: 600, message_repeat: 60 },
  };
}

/** After-school viewing on weekdays, longer weekends, two hours a day. */
export function schoolPreset(): PolicyDoc {
  return {
    ...emptyPolicy(),
    schedule: {
      windows: { ...windows(WEEKDAYS, "16:00:00", "20:00:00"), ...windows(WEEKEND, "09:00:00", "21:00:00") },
      special_days: {},
    },
    daily_budget_minutes: 120,
  };
}
