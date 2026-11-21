import { useSyncExternalStore } from "react";

export type Theme = "system" | "light" | "dark";

const STORAGE_KEY = "tvbalance.theme";
const listeners = new Set<() => void>();

function stored(): Theme {
  try {
    const value = localStorage.getItem(STORAGE_KEY);
    if (value === "light" || value === "dark") return value;
  } catch {
    // Storage can be blocked (private windows): follow the system.
  }
  return "system";
}

function prefersDark(): boolean {
  return typeof matchMedia === "function" && matchMedia("(prefers-color-scheme: dark)").matches;
}

/** Puts the `dark` class on <html> according to the saved choice or the system. */
export function applyTheme(theme: Theme = stored()): void {
  const dark = theme === "dark" || (theme === "system" && prefersDark());
  document.documentElement.classList.toggle("dark", dark);
}

export function setTheme(theme: Theme): void {
  try {
    if (theme === "system") localStorage.removeItem(STORAGE_KEY);
    else localStorage.setItem(STORAGE_KEY, theme);
  } catch {
    // Not persisted, still applied for this visit.
  }
  applyTheme(theme);
  listeners.forEach((listener) => listener());
}

export function useTheme(): [Theme, (theme: Theme) => void] {
  const theme = useSyncExternalStore((listener) => {
    listeners.add(listener);
    return () => listeners.delete(listener);
  }, stored);
  return [theme, setTheme];
}
