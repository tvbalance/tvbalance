import type { HTMLAttributes } from "react";

import { cn } from "../../lib";

export function Card({ className, ...props }: HTMLAttributes<HTMLElement>) {
  return (
    <section
      className={cn("rounded-xl border border-line bg-card p-4 shadow-sm", className)}
      {...props}
    />
  );
}

const TONES = {
  neutral: "border-line text-muted",
  ok: "border-ok text-ok",
  warn: "border-warn text-warn",
  danger: "border-danger text-danger",
};

export function Badge({
  tone = "neutral",
  className,
  ...props
}: HTMLAttributes<HTMLSpanElement> & { tone?: keyof typeof TONES }) {
  return (
    <span
      className={cn(
        "inline-flex items-center rounded-full border px-2 py-0.5 text-xs font-medium",
        TONES[tone],
        className,
      )}
      {...props}
    />
  );
}
