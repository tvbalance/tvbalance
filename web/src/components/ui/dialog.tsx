import * as Radix from "@radix-ui/react-dialog";
import type { ReactNode } from "react";

/** A modal dialog; Radix provides the focus trap and Escape handling. */
export function Dialog({
  open,
  onOpenChange,
  title,
  description,
  children,
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  title: string;
  description: string;
  children: ReactNode;
}) {
  return (
    <Radix.Root open={open} onOpenChange={onOpenChange}>
      <Radix.Portal>
        <Radix.Overlay className="fixed inset-0 z-40 bg-black/50" />
        <Radix.Content className="fixed left-1/2 top-1/2 z-50 w-[calc(100%-2rem)] max-w-md -translate-x-1/2 -translate-y-1/2 space-y-4 rounded-xl border border-line bg-card p-5 text-ink shadow-xl">
          <Radix.Title className="text-lg font-semibold">{title}</Radix.Title>
          <Radix.Description className="text-sm text-muted">{description}</Radix.Description>
          {children}
        </Radix.Content>
      </Radix.Portal>
    </Radix.Root>
  );
}
