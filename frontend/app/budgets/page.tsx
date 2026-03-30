"use client";

import Link from "next/link";
import useSWR from "swr";

import Card, { cx } from "@/app/components/Card";
import EmptyState from "@/app/components/EmptyState";
import PageHeader from "@/app/components/PageHeader";
import ProgressBar from "@/app/components/ProgressBar";
import { getBudgetPlan, listMonths } from "@/lib/api";

const primaryButtonClassName =
  "inline-flex items-center justify-center rounded-xl bg-[var(--gold-400)] px-4 py-2.5 text-sm font-medium text-black transition hover:bg-[var(--gold-500)]";

export default function BudgetsPage() {
  const { data: months } = useSWR("months", listMonths);
  const latestMonth = months?.months?.[0];
  const { data: budget } = useSWR(
    latestMonth ? ["budget", latestMonth] : null,
    ([, yearMonth]) => getBudgetPlan(yearMonth)
  );

  return (
    <div className="space-y-6">
      <PageHeader
        eyebrow="Budget Planner"
        title="预算规划"
        description="像翻阅一本年度预算册一样查看每个月的建议与执行进度，优先关注最新账期和已经逼近上限的分类。"
      >
        {latestMonth ? (
          <Link href={`/budgets/${latestMonth}`} className={primaryButtonClassName}>
            查看最新预算
          </Link>
        ) : null}
      </PageHeader>

      {!months ? (
        <div className="grid grid-cols-1 gap-4 md:grid-cols-3">
          <SkeletonCard />
          <SkeletonCard />
          <SkeletonCard />
        </div>
      ) : months.months.length === 0 ? (
        <EmptyState
          title="还没有可分析的账期"
          description="请先导入微信、支付宝或招商银行账单，系统会自动生成月度预算建议。"
          action={
            <Link href="/import" className={primaryButtonClassName}>
              去导入账单
            </Link>
          }
        />
      ) : (
        <div className="grid grid-cols-1 gap-6 xl:grid-cols-[1.45fr_1fr]">
          <Card variant="surface" className="p-6">
            <div className="mb-5 flex items-center justify-between gap-4">
              <div>
                <h2 className="text-2xl font-bold tracking-[-0.03em] text-[var(--text-primary)]">可用账期</h2>
                <p className="mt-2 text-sm leading-7 text-[var(--text-secondary)]">选择任一月份查看预算建议和执行情况。</p>
              </div>
              <span className="rounded-full bg-white/5 px-3 py-1 text-xs font-medium text-[var(--text-secondary)]">
                {months.months.length} 个账期
              </span>
            </div>
            <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
              {months.months.map((month) => {
                const isLatest = month === latestMonth;

                return (
                  <Link
                    key={month}
                    href={`/budgets/${month}`}
                    className={cx(
                      "rounded-[24px] border p-4 transition-all hover:-translate-y-0.5",
                      isLatest
                        ? "border-[rgba(212,168,67,0.24)] bg-[rgba(212,168,67,0.08)] shadow-[0_18px_40px_rgba(0,0,0,0.26)]"
                        : "border-[var(--border-subtle)] bg-[rgba(255,255,255,0.02)] hover:border-[rgba(212,168,67,0.18)]"
                    )}
                  >
                    <div className="flex items-center justify-between gap-3">
                      <div>
                        <p className="text-lg font-semibold text-[var(--text-primary)]">{month}</p>
                        <p className="mt-1 text-sm text-[var(--text-secondary)]">查看该月预算执行情况</p>
                      </div>
                      {isLatest ? (
                        <span className="rounded-full bg-[rgba(212,168,67,0.14)] px-2.5 py-1 text-xs font-medium text-[var(--gold-400)]">
                          最新
                        </span>
                      ) : null}
                    </div>
                  </Link>
                );
              })}
            </div>
          </Card>

          <Card variant="elevated" className="p-6">
            <p className="text-xs uppercase tracking-[0.24em] text-[var(--gold-400)]">Current Snapshot</p>
            <h2 className="mt-4 text-2xl font-bold tracking-[-0.03em] text-[var(--text-primary)]">本月预算概览</h2>
            {!latestMonth || !budget ? (
              <div className="mt-6 space-y-3">
                <SkeletonCard />
                <SkeletonCard />
              </div>
            ) : (
              <>
                <p className="mt-2 text-sm leading-7 text-[var(--text-secondary)]">{latestMonth} 自动生成预算摘要</p>
                <div className="mt-5 grid grid-cols-1 gap-3">
                  <Metric title="预算总额" value={budget.total_budget} tone="text-[var(--gold-400)]" />
                  <Metric title="已支出" value={budget.total_spent} tone="text-rose-300" />
                  <Metric title="剩余空间" value={budget.remaining} tone={budget.remaining >= 0 ? "text-emerald-300" : "text-rose-300"} />
                </div>
                <ProgressBar
                  className="mt-5"
                  label="使用率"
                  tone={budget.usage_percentage >= 100 ? "overspent" : budget.usage_percentage >= 80 ? "warning" : "gold"}
                  value={budget.usage_percentage}
                  valueLabel={`${budget.usage_percentage.toFixed(1)}%`}
                />
                <div className="mt-5 space-y-3">
                  {budget.categories.slice(0, 3).map((category) => (
                    <div key={category.id} className="rounded-[22px] border border-[var(--border-subtle)] bg-[rgba(255,255,255,0.03)] px-4 py-3">
                      <div className="flex items-center justify-between gap-3">
                        <p className="font-medium text-[var(--text-primary)]">{category.category_l1}</p>
                        <span className={statusClassName(category.status)}>{statusLabel(category.status)}</span>
                      </div>
                      <p className="mt-1 text-sm text-[var(--text-secondary)]">
                        ¥{category.spent.toLocaleString("zh-CN", { minimumFractionDigits: 2 })} / ¥{category.budget.toLocaleString("zh-CN", { minimumFractionDigits: 2 })}
                      </p>
                    </div>
                  ))}
                </div>
              </>
            )}
          </Card>
        </div>
      )}
    </div>
  );
}

function Metric({ title, value, tone }: { title: string; value: number; tone: string }) {
  return (
    <div className="rounded-[22px] border border-[var(--border-subtle)] bg-[rgba(255,255,255,0.03)] px-4 py-3">
      <p className="text-sm text-[var(--text-secondary)]">{title}</p>
      <p className={cx("tabular mt-2 text-2xl font-bold tracking-[-0.03em]", tone)}>
        ¥{value.toLocaleString("zh-CN", { minimumFractionDigits: 2 })}
      </p>
    </div>
  );
}

function SkeletonCard() {
  return <div className="h-24 animate-pulse rounded-[22px] bg-[rgba(255,255,255,0.04)]" />;
}

function statusClassName(status: "healthy" | "warning" | "overspent") {
  if (status === "overspent") return "rounded-full bg-rose-400/10 px-2.5 py-1 text-xs font-medium text-rose-300";
  if (status === "warning") return "rounded-full bg-amber-400/10 px-2.5 py-1 text-xs font-medium text-amber-300";
  return "rounded-full bg-emerald-400/10 px-2.5 py-1 text-xs font-medium text-emerald-300";
}

function statusLabel(status: "healthy" | "warning" | "overspent") {
  if (status === "overspent") return "超支";
  if (status === "warning") return "预警";
  return "健康";
}
