import { useId, type InputHTMLAttributes, type ReactNode, type SelectHTMLAttributes } from "react";

import { cn } from "../../lib";

const CONTROL =
  "min-h-11 w-full rounded-lg border border-line bg-card px-3 text-ink placeholder:text-muted disabled:opacity-50";

interface ControlProps {
  id: string;
  "aria-describedby"?: string;
  "aria-invalid"?: true;
}

/** A labelled control; an error, when given, is announced and tied to the control. */
export function Field({
  label,
  error,
  hint,
  children,
}: {
  label: string;
  error?: string | null;
  hint?: string;
  children: (props: ControlProps) => ReactNode;
}) {
  const id = useId();
  const note = error ? `${id}-error` : hint ? `${id}-hint` : undefined;
  const props: ControlProps = { id, "aria-describedby": note };
  if (error) props["aria-invalid"] = true;
  return (
    <div className="space-y-1">
      <label htmlFor={id} className="block text-sm font-medium">
        {label}
      </label>
      {children(props)}
      {error ? (
        <p id={`${id}-error`} role="alert" className="text-sm text-danger">
          {error}
        </p>
      ) : hint ? (
        <p id={`${id}-hint`} className="text-sm text-muted">
          {hint}
        </p>
      ) : null}
    </div>
  );
}

export function Input({ className, ...props }: InputHTMLAttributes<HTMLInputElement>) {
  return <input className={cn(CONTROL, className)} {...props} />;
}

/** A native select: the best mobile picker and fully accessible. */
export function Select({ className, ...props }: SelectHTMLAttributes<HTMLSelectElement>) {
  return <select className={cn(CONTROL, className)} {...props} />;
}

export function Switch({
  checked,
  onChange,
  label,
  disabled,
}: {
  checked: boolean;
  onChange: (checked: boolean) => void;
  label: string;
  disabled?: boolean;
}) {
  return (
    <button
      type="button"
      role="switch"
      aria-checked={checked}
      aria-label={label}
      disabled={disabled}
      onClick={() => onChange(!checked)}
      className={cn(
        "relative inline-flex h-7 w-12 shrink-0 items-center rounded-full border border-line transition-colors",
        "disabled:opacity-50",
        checked ? "bg-brand" : "bg-page",
      )}
    >
      <span
        className={cn(
          "inline-block size-5 rounded-full bg-card shadow ring-1 ring-line transition-transform",
          checked ? "translate-x-6" : "translate-x-1",
        )}
      />
    </button>
  );
}
