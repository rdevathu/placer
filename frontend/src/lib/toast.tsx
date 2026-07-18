import { createContext, useCallback, useContext, useRef, useState, type ReactNode } from "react";
import { CheckCircle2, XCircle } from "lucide-react";

interface Toast {
  id: number;
  kind: "success" | "error";
  message: string;
}

const ToastContext = createContext<{
  success: (message: string) => void;
  error: (message: string) => void;
} | null>(null);

export function ToastProvider({ children }: { children: ReactNode }) {
  const [toasts, setToasts] = useState<Toast[]>([]);
  const counter = useRef(0);

  const push = useCallback((kind: Toast["kind"], message: string) => {
    const id = ++counter.current;
    setToasts((prev) => [...prev, { id, kind, message }]);
    window.setTimeout(() => {
      setToasts((prev) => prev.filter((t) => t.id !== id));
    }, 4000);
  }, []);

  const value = {
    success: (message: string) => push("success", message),
    error: (message: string) => push("error", message),
  };

  return (
    <ToastContext.Provider value={value}>
      {children}
      <div className="fixed bottom-4 right-4 z-50 flex flex-col gap-2">
        {toasts.map((t) => (
          <div
            key={t.id}
            className="animate-fade-in flex items-start gap-2 rounded-lg border border-border bg-bg-elevated px-3.5 py-2.5 text-[12.5px] shadow-lg shadow-black/10 max-w-sm"
          >
            {t.kind === "success" ? (
              <CheckCircle2 size={15} className="mt-0.5 shrink-0 text-success" />
            ) : (
              <XCircle size={15} className="mt-0.5 shrink-0 text-danger" />
            )}
            <span className="text-text leading-snug">{t.message}</span>
          </div>
        ))}
      </div>
    </ToastContext.Provider>
  );
}

export function useToast() {
  const ctx = useContext(ToastContext);
  if (!ctx) throw new Error("useToast must be used within ToastProvider");
  return ctx;
}

export function errorMessage(err: unknown): string {
  if (err instanceof Error) return err.message;
  return "Something went wrong";
}
