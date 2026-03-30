import type { HTMLAttributes, ReactNode } from "react";

export type CardVariant = "surface" | "elevated" | "bordered";

export function cx(...parts: Array<string | false | null | undefined>) {
  return parts.filter(Boolean).join(" ");
}

const VARIANT_CLASS_NAMES: Record<CardVariant, string> = {
  surface:
    "bg-[var(--bg-surface)] border border-[var(--border-default)] shadow-[0_20px_50px_rgba(0,0,0,0.26)]",
  elevated:
    "bg-[linear-gradient(145deg,rgba(34,30,23,0.98),rgba(26,22,16,0.98))] border border-[var(--border-subtle)] shadow-[0_26px_70px_rgba(0,0,0,0.34)]",
  bordered:
    "bg-transparent border border-[rgba(212,168,67,0.3)] shadow-[0_18px_40px_rgba(0,0,0,0.18)]",
};

export function cardClassName(variant: CardVariant = "surface", className?: string) {
  return cx(
    "relative isolate overflow-hidden rounded-[28px] transition-all before:pointer-events-none before:absolute before:inset-0 before:bg-[radial-gradient(circle_at_top_right,rgba(212,168,67,0.12),transparent_42%)]",
    VARIANT_CLASS_NAMES[variant],
    className
  );
}

export default function Card({
  children,
  className,
  variant = "surface",
  ...props
}: {
  children: ReactNode;
  className?: string;
  variant?: CardVariant;
} & HTMLAttributes<HTMLDivElement>) {
  return (
    <div className={cardClassName(variant, className)} {...props}>
      {children}
    </div>
  );
}
