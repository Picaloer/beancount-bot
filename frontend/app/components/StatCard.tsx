import Card, { cx } from "@/app/components/Card";

export type StatCardTone = "gold" | "rose" | "emerald" | "sky";

const toneStyles: Record<StatCardTone, { glow: string; value: string; chip: string }> = {
  gold: {
    glow: "before:bg-[radial-gradient(circle_at_top_right,rgba(212,168,67,0.18),transparent_40%)]",
    value: "text-[var(--gold-400)]",
    chip: "bg-[rgba(212,168,67,0.12)] text-[var(--gold-400)]",
  },
  rose: {
    glow: "before:bg-[radial-gradient(circle_at_top_right,rgba(248,113,113,0.16),transparent_40%)]",
    value: "text-rose-300",
    chip: "bg-rose-400/10 text-rose-300",
  },
  emerald: {
    glow: "before:bg-[radial-gradient(circle_at_top_right,rgba(52,211,153,0.18),transparent_40%)]",
    value: "text-emerald-300",
    chip: "bg-emerald-400/10 text-emerald-300",
  },
  sky: {
    glow: "before:bg-[radial-gradient(circle_at_top_right,rgba(56,189,248,0.18),transparent_40%)]",
    value: "text-sky-300",
    chip: "bg-sky-400/10 text-sky-300",
  },
};

export default function StatCard({
  label,
  value,
  hint,
  tone = "gold",
}: {
  hint?: string;
  label: string;
  tone?: StatCardTone;
  value: string;
}) {
  const styles = toneStyles[tone];

  return (
    <Card variant="surface" className={cx("min-h-[164px] p-5 before:opacity-100", styles.glow)}>
      <div className="flex h-full flex-col justify-between gap-8">
        <div className="space-y-3">
          <div className="inline-flex rounded-full bg-white/5 px-2.5 py-1 text-[11px] uppercase tracking-[0.24em] text-[var(--text-muted)]">
            {label}
          </div>
          <p className={cx("tabular text-4xl font-bold tracking-[-0.04em] sm:text-[2.5rem]", styles.value)}>{value}</p>
        </div>
        <div className="flex items-center justify-between gap-3">
          <div className="h-px flex-1 bg-[linear-gradient(90deg,rgba(212,168,67,0.26),transparent)]" />
          <span className={cx("rounded-full px-2.5 py-1 text-xs font-medium", styles.chip)}>
            {hint ?? "Ledger Metric"}
          </span>
        </div>
      </div>
    </Card>
  );
}
