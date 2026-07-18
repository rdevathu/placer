import clsx from "clsx";
import type { ButtonHTMLAttributes, HTMLAttributes, ReactNode } from "react";
import { Loader2 } from "lucide-react";

// --- Badge --------------------------------------------------------------

export type BadgeVariant = "neutral" | "accent" | "success" | "warning" | "danger";

const badgeVariantClasses: Record<BadgeVariant, string> = {
  neutral: "bg-bg-inset text-text-secondary border-border",
  accent: "bg-accent-soft text-accent border-transparent",
  success: "bg-success-soft text-success border-transparent",
  warning: "bg-warning-soft text-warning border-transparent",
  danger: "bg-danger-soft text-danger border-transparent",
};

export function Badge({
  children,
  variant = "neutral",
  className,
}: {
  children: ReactNode;
  variant?: BadgeVariant;
  className?: string;
}) {
  return (
    <span
      className={clsx(
        "inline-flex items-center gap-1 rounded-md border px-1.5 py-0.5 text-[11px] font-medium leading-none whitespace-nowrap",
        badgeVariantClasses[variant],
        className,
      )}
    >
      {children}
    </span>
  );
}

// --- Button ---------------------------------------------------------------

type ButtonVariant = "primary" | "secondary" | "ghost" | "danger";
type ButtonSize = "sm" | "md";

const buttonVariantClasses: Record<ButtonVariant, string> = {
  primary: "bg-accent text-white hover:bg-accent-hover border-transparent",
  secondary: "bg-bg-elevated text-text hover:bg-bg-hover border-border-strong",
  ghost: "bg-transparent text-text-secondary hover:bg-bg-hover hover:text-text border-transparent",
  danger: "bg-transparent text-danger hover:bg-danger-soft border-transparent",
};

const buttonSizeClasses: Record<ButtonSize, string> = {
  sm: "h-6.5 px-2 text-[12px] gap-1",
  md: "h-8 px-3 text-[13px] gap-1.5",
};

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: ButtonVariant;
  size?: ButtonSize;
  loading?: boolean;
}

export function Button({
  variant = "secondary",
  size = "md",
  loading,
  disabled,
  className,
  children,
  ...rest
}: ButtonProps) {
  return (
    <button
      className={clsx(
        "inline-flex items-center justify-center rounded-md border font-medium transition-colors duration-100 disabled:opacity-50 disabled:cursor-not-allowed cursor-pointer",
        buttonVariantClasses[variant],
        buttonSizeClasses[size],
        className,
      )}
      disabled={disabled || loading}
      {...rest}
    >
      {loading && <Loader2 size={13} className="animate-spin" />}
      {children}
    </button>
  );
}

// --- Card -------------------------------------------------------------

export function Card({ children, className, ...rest }: HTMLAttributes<HTMLDivElement>) {
  return (
    <div
      className={clsx("rounded-lg border border-border bg-bg-elevated", className)}
      {...rest}
    >
      {children}
    </div>
  );
}

export function CardHeader({
  title,
  action,
  subtitle,
}: {
  title: ReactNode;
  action?: ReactNode;
  subtitle?: ReactNode;
}) {
  return (
    <div className="flex items-center justify-between border-b border-border px-4 py-2.5">
      <div>
        <h3 className="text-[12.5px] font-semibold text-text">{title}</h3>
        {subtitle && <p className="mt-0.5 text-[11.5px] text-text-tertiary">{subtitle}</p>}
      </div>
      {action}
    </div>
  );
}

// --- Empty / loading / error states -------------------------------------

export function Spinner({ size = 16 }: { size?: number }) {
  return <Loader2 size={size} className="animate-spin text-text-tertiary" />;
}

export function CenteredSpinner() {
  return (
    <div className="flex items-center justify-center py-14">
      <Spinner size={18} />
    </div>
  );
}

export function EmptyState({ icon, title, hint }: { icon?: ReactNode; title: string; hint?: string }) {
  return (
    <div className="flex flex-col items-center justify-center gap-2 py-12 text-center">
      {icon && <div className="text-text-tertiary">{icon}</div>}
      <p className="text-[12.5px] font-medium text-text-secondary">{title}</p>
      {hint && <p className="max-w-xs text-[11.5px] text-text-tertiary">{hint}</p>}
    </div>
  );
}

export function ErrorState({ message }: { message: string }) {
  return (
    <div className="flex flex-col items-center justify-center gap-2 py-12 text-center">
      <p className="text-[12.5px] font-medium text-danger">Failed to load</p>
      <p className="max-w-sm text-[11.5px] text-text-tertiary">{message}</p>
    </div>
  );
}

// --- Section label ---------------------------------------------------------

export function SectionLabel({ children }: { children: ReactNode }) {
  return (
    <div className="px-1 pb-1.5 text-[11px] font-semibold uppercase tracking-wide text-text-tertiary">
      {children}
    </div>
  );
}

// --- Page header --------------------------------------------------------

export function PageHeader({
  title,
  subtitle,
  action,
}: {
  title: ReactNode;
  subtitle?: ReactNode;
  action?: ReactNode;
}) {
  return (
    <div className="flex shrink-0 items-center justify-between border-b border-border px-5 py-3">
      <div>
        <h1 className="text-[14px] font-semibold text-text">{title}</h1>
        {subtitle && <p className="mt-0.5 text-[11.5px] text-text-tertiary">{subtitle}</p>}
      </div>
      {action}
    </div>
  );
}

// --- Table primitives -------------------------------------------------

export function Table({ children }: { children: ReactNode }) {
  return (
    <div className="overflow-x-auto">
      <table className="w-full border-collapse text-[12.5px]">{children}</table>
    </div>
  );
}

export function Th({ children, className }: { children?: ReactNode; className?: string }) {
  return (
    <th
      className={clsx(
        "border-b border-border px-3 py-2 text-left text-[11px] font-semibold uppercase tracking-wide text-text-tertiary",
        className,
      )}
    >
      {children}
    </th>
  );
}

export function Tr({
  children,
  onClick,
  className,
}: {
  children: ReactNode;
  onClick?: () => void;
  className?: string;
}) {
  return (
    <tr
      onClick={onClick}
      className={clsx(
        "border-b border-border last:border-0",
        onClick && "cursor-pointer hover:bg-bg-hover",
        className,
      )}
    >
      {children}
    </tr>
  );
}

export function Td({ children, className }: { children?: ReactNode; className?: string }) {
  return <td className={clsx("px-3 py-2 align-middle text-text", className)}>{children}</td>;
}

// --- Kv row (label/value pair) --------------------------------------------

export function Kv({ label, value }: { label: string; value: ReactNode }) {
  return (
    <div className="flex items-start justify-between gap-3 py-1.5">
      <span className="shrink-0 text-[11.5px] text-text-tertiary">{label}</span>
      <span className="text-right text-[12.5px] text-text">{value ?? "—"}</span>
    </div>
  );
}
