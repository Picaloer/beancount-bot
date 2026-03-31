import { cx } from "@/app/components/Card";

const badgeBase =
  "inline-flex items-center gap-1.5 rounded-full px-2.5 py-1 text-xs font-medium ring-1 ring-inset";

const sourceStyles: Record<string, string> = {
  wechat: "bg-emerald-400/10 text-emerald-300 ring-emerald-400/20",
  alipay: "bg-sky-400/10 text-sky-300 ring-sky-400/20",
  cmb: "bg-rose-400/10 text-rose-300 ring-rose-400/20",
};

const sourceLabels: Record<string, string> = {
  wechat: "微信",
  alipay: "支付宝",
  cmb: "招商银行",
};

const statusStyles: Record<string, string> = {
  done: "bg-emerald-400/10 text-emerald-300 ring-emerald-400/20",
  pending: "bg-amber-400/10 text-amber-300 ring-amber-400/20",
  processing: "bg-sky-400/10 text-sky-300 ring-sky-400/20",
  reviewing_duplicates: "bg-amber-400/10 text-amber-300 ring-amber-400/20",
  classifying: "bg-sky-400/10 text-sky-300 ring-sky-400/20",
  failed: "bg-rose-400/10 text-rose-300 ring-rose-400/20",
};

const statusLabels: Record<string, string> = {
  done: "完成",
  pending: "等待中",
  processing: "处理中",
  reviewing_duplicates: "等待复核",
  classifying: "分类中",
  failed: "失败",
};

const categoryPalette = [
  "bg-[rgba(212,168,67,0.12)] text-[var(--gold-400)] ring-[rgba(212,168,67,0.22)]",
  "bg-emerald-400/10 text-emerald-300 ring-emerald-400/20",
  "bg-sky-400/10 text-sky-300 ring-sky-400/20",
  "bg-violet-400/10 text-violet-300 ring-violet-400/20",
  "bg-amber-400/10 text-amber-300 ring-amber-400/20",
  "bg-rose-400/10 text-rose-300 ring-rose-400/20",
  "bg-cyan-400/10 text-cyan-300 ring-cyan-400/20",
  "bg-orange-400/10 text-orange-300 ring-orange-400/20",
];

const categorySourceLabels: Record<string, string> = {
  user_rule: "用户规则",
  system_rule: "系统规则",
  llm: "AI 分类",
  manual: "手动调整",
  fallback: "兜底分类",
};

function hashCategory(value: string) {
  let hash = 0;
  for (let index = 0; index < value.length; index += 1) {
    hash = (hash * 33 + value.charCodeAt(index)) >>> 0;
  }
  return hash;
}

function getCategoryStyle(categoryL1: string) {
  if (!categoryL1.trim()) {
    return "bg-white/5 text-[var(--text-secondary)] ring-white/10";
  }
  return categoryPalette[hashCategory(categoryL1) % categoryPalette.length];
}

export function SourceBadge({ className, source }: { className?: string; source: string }) {
  return (
    <span className={cx(badgeBase, sourceStyles[source] ?? "bg-white/5 text-[var(--text-secondary)] ring-white/10", className)}>
      <span className="h-1.5 w-1.5 rounded-full bg-current opacity-80" />
      {sourceLabels[source] ?? source}
    </span>
  );
}

export function StatusBadge({ className, status }: { className?: string; status: string }) {
  return (
    <span className={cx(badgeBase, statusStyles[status] ?? "bg-white/5 text-[var(--text-secondary)] ring-white/10", className)}>
      {statusLabels[status] ?? status}
    </span>
  );
}

export function CategoryTag({
  categoryL1,
  categoryL2,
  className,
  source,
}: {
  categoryL1: string;
  categoryL2?: string | null;
  className?: string;
  source?: string;
}) {
  const sourceLabel = source ? categorySourceLabels[source] ?? source : undefined;
  const title = sourceLabel ? `${categoryL1}${categoryL2 ? ` · ${categoryL2}` : ""} · ${sourceLabel}` : undefined;

  return (
    <span className={cx(badgeBase, "max-w-full text-left", getCategoryStyle(categoryL1), className)} title={title}>
      <span className="truncate">
        {categoryL1}
        {categoryL2 ? ` · ${categoryL2}` : ""}
      </span>
    </span>
  );
}
