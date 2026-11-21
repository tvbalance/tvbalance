import { useId, useState, type ReactNode } from "react";

import { cn } from "../../lib";

export interface TabSpec {
  id: string;
  label: string;
  content: ReactNode;
}

/** Tabs with arrow-key navigation (WAI-ARIA tabs pattern, automatic activation). */
export function Tabs({ tabs, label }: { tabs: TabSpec[]; label: string }) {
  const base = useId();
  const [active, setActive] = useState(tabs[0]?.id);
  const move = (from: number, step: number) => {
    const next = tabs[(from + step + tabs.length) % tabs.length];
    setActive(next.id);
    document.getElementById(`${base}-tab-${next.id}`)?.focus();
  };
  return (
    <div>
      <div
        role="tablist"
        aria-label={label}
        className="flex gap-1 overflow-x-auto border-b border-line"
      >
        {tabs.map((tab, index) => (
          <button
            key={tab.id}
            id={`${base}-tab-${tab.id}`}
            role="tab"
            type="button"
            aria-selected={tab.id === active}
            aria-controls={`${base}-panel-${tab.id}`}
            tabIndex={tab.id === active ? 0 : -1}
            onClick={() => setActive(tab.id)}
            onKeyDown={(event) => {
              if (event.key === "ArrowRight") move(index, 1);
              if (event.key === "ArrowLeft") move(index, -1);
            }}
            className={cn(
              "min-h-11 whitespace-nowrap border-b-2 px-3 text-sm font-medium",
              tab.id === active ? "border-brand text-brand" : "border-transparent text-muted",
            )}
          >
            {tab.label}
          </button>
        ))}
      </div>
      {tabs.map((tab) => (
        <div
          key={tab.id}
          id={`${base}-panel-${tab.id}`}
          role="tabpanel"
          aria-labelledby={`${base}-tab-${tab.id}`}
          hidden={tab.id !== active}
          className="pt-4"
        >
          {tab.id === active ? tab.content : null}
        </div>
      ))}
    </div>
  );
}
