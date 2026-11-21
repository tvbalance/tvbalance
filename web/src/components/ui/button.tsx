import type { ButtonHTMLAttributes } from "react";

import { cn } from "../../lib";

type Variant = "primary" | "secondary" | "danger" | "ghost";

const VARIANTS: Record<Variant, string> = {
  primary: "bg-brand text-brand-ink hover:opacity-90",
  secondary: "border border-line bg-card text-ink hover:bg-page",
  danger: "bg-danger text-white hover:opacity-90",
  ghost: "text-ink hover:bg-page",
};

export function Button({
  variant = "primary",
  className,
  type = "button",
  ...props
}: ButtonHTMLAttributes<HTMLButtonElement> & { variant?: Variant }) {
  return (
    <button
      type={type}
      className={cn(
        "inline-flex min-h-11 items-center justify-center gap-2 rounded-lg px-4 text-sm font-medium",
        "disabled:cursor-not-allowed disabled:opacity-50",
        VARIANTS[variant],
        className,
      )}
      {...props}
    />
  );
}
