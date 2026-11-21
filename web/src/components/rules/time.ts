/** The API sends times as HH:MM:SS, `<input type="time">` works with HH:MM. */
export function toInput(value: string): string {
  return value.slice(0, 5);
}

export function fromInput(value: string): string {
  return value.length === 5 ? `${value}:00` : value;
}

/** Day 0 is Monday, as in the Engine. 2024-01-01 was a Monday. */
export function weekdayName(day: number, language: string): string {
  return new Date(2024, 0, 1 + day).toLocaleDateString(language, { weekday: "long" });
}
