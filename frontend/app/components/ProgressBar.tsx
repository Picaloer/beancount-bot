import { cx } from "@/app/components/Card";

export type ProgressTone =
  | "gold"
  | "healthy"
  | "warning"
  | "overspent"
  | "income"
  | "expense"
  | "info";

const toneStyles: Record<ProgressTone, string> = {
  gold: "bg-[linear-gradient(90deg,#d4a843,#b8882a)]",
  healthy: "bg-[linear-gradient(90deg,#34d399,#10b981)]",
  warning: "bg-[linear-gradient(90deg,#fbbf24,#f59e0b)]",
  overspent: "bg-[linear-gradient(90deg,#fb7185,#ef4444)]",
  income: "bg-[linear-gradient(90deg,#34d399,#059669)]",
  expense: "bg-[linear-gradient(90deg,#fb7185,#f87171)]",
  info: "bg-[linear-gradient(90deg,#38bdf8,#0ea5e9)]",
};

export default function ProgressBar({
  className,
  label,
  size = "md",
  tone = "gold",
  value,
  valueLabel,
}: {
  className?: string;
  label?: string;
  size?: "sm" | "md";
  tone?: ProgressTone;
  value: number;
  valueLabel?: string;
}) {
  const clamped = Math.max(0, Math.min(value, 100));
  const heightClassName = size === "sm" ? "h-2" : "h-3";

  return (
    <div className={cx("space-y-2", className)}>
      {label || valueLabel ? (
        <div className="flex items-center justify-between gap-3 text-sm text-[var(--text-secondary)]">
          <span>{label}</span>
          <span className="tabular text-[var(--text-muted)]">{valueLabel ?? `${clamped.toFixed(1)}%`}</span>
        </div>
      ) : null}
      <div
        aria-valuemax={100}
        aria-valuemin={0}
        aria-valuenow={Number(clamped.toFixed(1))}
        className={cx(
          "overflow-hidden rounded-full bg-[var(--bg-muted)] ring-1 ring-inset ring-white/8",
          heightClassName
        )}
        role="progressbar"
      >
        <div
          className={cx(
            "h-full rounded-full shadow-[0_0_18px_rgba(212,168,67,0.2)] transition-[width] duration-500",
            toneStyles[tone]
          )}
          style={{ width: `${clamped}%` }}
        />
      </div>
    </div>
  );
}
