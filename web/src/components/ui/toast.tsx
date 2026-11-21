import { createContext, useCallback, useContext, useRef, useState, type ReactNode } from "react";

import { cn } from "../../lib";

type Tone = "info" | "error";

interface Toast {
  id: number;
  message: string;
  tone: Tone;
}

const LIFETIME_MS = 5000;

const ToastContext = createContext<(message: string, tone?: Tone) => void>(() => {});

/** Short confirmations and failures, announced politely to screen readers. */
export function ToastProvider({ children }: { children: ReactNode }) {
  const [toasts, setToasts] = useState<Toast[]>([]);
  const next = useRef(0);
  const show = useCallback((message: string, tone: Tone = "info") => {
    const id = next.current++;
    setToasts((current) => [...current, { id, message, tone }]);
    setTimeout(() => setToasts((current) => current.filter((t) => t.id !== id)), LIFETIME_MS);
  }, []);
  return (
    <ToastContext.Provider value={show}>
      {children}
      <div
        role="status"
        aria-live="polite"
        className="fixed inset-x-4 bottom-20 z-50 space-y-2 md:bottom-4 md:left-auto md:w-80"
      >
        {toasts.map((toast) => (
          <p
            key={toast.id}
            className={cn(
              "rounded-lg border bg-card px-4 py-3 text-sm shadow-lg",
              toast.tone === "error" ? "border-danger text-danger" : "border-line text-ink",
            )}
          >
            {toast.message}
          </p>
        ))}
      </div>
    </ToastContext.Provider>
  );
}

export function useToast() {
  return useContext(ToastContext);
}
