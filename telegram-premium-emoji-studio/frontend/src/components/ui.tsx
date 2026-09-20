import { useEffect } from "react";
import { haptic } from "@/lib/telegram";

export function Skeleton({ className = "" }: { className?: string }) {
  return <div className={`skeleton ${className}`} />;
}

export function Spinner({ className = "" }: { className?: string }) {
  return (
    <svg className={`animate-spin ${className}`} viewBox="0 0 24 24" fill="none">
      <circle className="opacity-20" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
      <path className="opacity-90" d="M22 12a10 10 0 0 1-10 10" stroke="currentColor" strokeWidth="4" strokeLinecap="round" />
    </svg>
  );
}

export function EmptyState({ title, hint }: { title: string; hint?: string }) {
  return (
    <div className="flex flex-col items-center justify-center py-16 text-center animate-fade-in">
      <div className="text-5xl mb-3 opacity-60">🗂️</div>
      <p className="font-semibold text-tg-text">{title}</p>
      {hint && <p className="text-sm text-tg-hint mt-1">{hint}</p>}
    </div>
  );
}

export function ErrorState({ message, onRetry, retryLabel }: { message: string; onRetry?: () => void; retryLabel?: string }) {
  return (
    <div className="flex flex-col items-center justify-center py-14 text-center animate-fade-in">
      <div className="text-5xl mb-3">⚠️</div>
      <p className="font-semibold text-tg-text max-w-xs">{message}</p>
      {onRetry && (
        <button className="btn-ghost mt-4" onClick={onRetry}>
          {retryLabel || "Retry"}
        </button>
      )}
    </div>
  );
}

// Bottom sheet used for template galleries, color pickers, checkout, etc.
export function Sheet({
  open,
  onClose,
  title,
  children,
}: {
  open: boolean;
  onClose: () => void;
  title?: string;
  children: React.ReactNode;
}) {
  useEffect(() => {
    if (open) {
      haptic("light");
      document.body.style.overflow = "hidden";
    }
    return () => {
      document.body.style.overflow = "";
    };
  }, [open]);

  if (!open) return null;
  return (
    <div className="fixed inset-0 z-50 flex items-end sm:items-center sm:justify-center">
      <div className="absolute inset-0 bg-black/50 backdrop-blur-sm animate-fade-in" onClick={onClose} />
      <div className="relative w-full sm:max-w-lg bg-tg-card rounded-t-3xl sm:rounded-3xl border-t sm:border border-tg-border shadow-soft animate-sheet-up max-h-[88vh] flex flex-col">
        <div className="pt-3 flex justify-center">
          <div className="h-1.5 w-10 rounded-full bg-tg-hint/40" />
        </div>
        {title && (
          <div className="px-5 pt-2 pb-3 flex items-center justify-between">
            <h3 className="text-lg font-bold">{title}</h3>
            <button className="text-tg-hint text-xl leading-none px-2" onClick={onClose}>
              ✕
            </button>
          </div>
        )}
        <div className="px-5 pb-6 overflow-y-auto no-scrollbar">{children}</div>
      </div>
    </div>
  );
}

export function SectionTitle({ children, action }: { children: React.ReactNode; action?: React.ReactNode }) {
  return (
    <div className="flex items-center justify-between mb-3">
      <h2 className="text-base font-bold text-tg-text">{children}</h2>
      {action}
    </div>
  );
}

export function Badge({ children, tone = "brand" }: { children: React.ReactNode; tone?: "brand" | "gold" | "green" }) {
  const tones = {
    brand: "bg-brand-500/15 text-brand-400 border-brand-500/30",
    gold: "bg-gold/15 text-gold border-gold/30",
    green: "bg-emerald-500/15 text-emerald-400 border-emerald-500/30",
  };
  return <span className={`chip border ${tones[tone]}`}>{children}</span>;
}
