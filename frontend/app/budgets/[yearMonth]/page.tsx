"use client";

import { use } from "react";
import Link from "next/link";
import useSWR from "swr";

import Card, { cx } from "@/app/components/Card";
import EmptyState from "@/app/components/EmptyState";
import PageHeader from "@/app/components/PageHeader";
import ProgressBar from "@/app/components/ProgressBar";
import StatCard from "@/app/components/StatCard";
import { getBudgetPlan } from "@/lib/api";

const primaryButtonClassName =
  "inline-flex items-center justify-center rounded-xl bg-[var(--gold-400)] px-4 py-2.5 text-sm font-medium text-black transition hover:bg-[var(--gold-500)]";

const secondaryButtonClassName =
  "inline-flex items-center justify-center rounded-xl border border-[rgba(212,168,67,0.28)] px-4 py-2.5 text-sm font-medium text-[var(--gold-400)] transition hover:bg-[rgba(212,168,67,0.08)]";

export default function BudgetDetailPage({
  params,
}: {
  params: Promise<{ yearMonth: string }>;
}) {
  const { yearMonth } = use(params);
  const { data: budget, error, isLoading, mutate } = useSWR(["budget", yearMonth], ([, ym]) => getBudgetPlan(ym));

  return (
    <div className="space-y-6">
      <PageHeader
        eyebrow="Budget Execution"
        title={`${yearMonth} 预算规划`}
        description="按月查看预算总额、分类执行情况与超支预警，确认哪些预算已经靠近边界。"
      >
        <Link href="/budgets" className={secondaryButtonClassName}>
          返回预算列表
        </Link>
        <button
          type="button"
          onClick={() => mutate(() => getBudgetPlan(yearMonth, true), { revalidate: false })}
          className={primaryButtonClassName}
        >
          重新生成预算
        </button>
      </PageHeader>

      {error ? (
        <div className="rounded-[24px] border border-rose-400/20 bg-rose-400/8 px-5 py-4 text-sm text-rose-200">
          预算加载失败：{error.message}
        </div>
      ) : null}

      {isLoading || !budget ? (
        <div className="grid grid-cols-1 gap-4 md:grid-cols-4">
          <SkeletonCard />
          <SkeletonCard />
          <SkeletonCard />
          <SkeletonCard />
        </div>
      ) : budget.categories.length === 0 ? (
        <EmptyState title="当前账期还没有预算分类" description="继续导入流水后，这里会展示每个分类的预算、已支出和执行进度。" />
      ) : (
        <>
          <div className="grid grid-cols-1 gap-4 md:grid-cols-4">
            <StatCard label="预算总额" value={formatCurrency(budget.total_budget)} tone="gold" hint="本月预算" />
            <StatCard label="已支出" value={formatCurrency(budget.total_spent)} tone="rose" hint="当前支出" />
            <StatCard
              label="剩余金额"
              value={formatCurrency(budget.remaining)}
              tone={budget.remaining >= 0 ? "emerald" : "rose"}
              hint={budget.remaining >= 0 ? "仍有余量" : "已经超支"}
            />
            <StatCard
              label="总体使用率"
              value={`${budget.usage_percentage.toFixed(1)}%`}
              tone={budget.usage_percentage >= 100 ? "rose" : budget.usage_percentage >= 80 ? "gold" : "emerald"}
              hint={budget.generated ? "最新生成" : "缓存预算"}
            />
          </div>

          <Card variant="surface" className="p-6">
            <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
              <div>
                <h2 className="text-xl font-semibold text-[var(--text-primary)]">分类预算执行</h2>
                <p className="mt-1 text-sm text-[var(--text-secondary)]">
                  {budget.generated ? "当前结果由最新账单趋势生成。" : "当前展示已缓存预算。"}
                </p>
              </div>
              <span className="rounded-full bg-white/5 px-3 py-1 text-xs font-medium text-[var(--text-secondary)]">
                {budget.categories.length} 个分类
              </span>
            </div>

            <div className="mt-6 overflow-hidden rounded-[24px] border border-[var(--border-subtle)]">
              <table className="w-full text-sm">
                <thead className="bg-[var(--bg-elevated)] text-xs uppercase tracking-[0.18em] text-[var(--text-muted)]">
                  <tr>
                    <th className="px-4 py-3 text-left">分类</th>
                    <th className="px-4 py-3 text-right">预算</th>
                    <th className="px-4 py-3 text-right">已支出</th>
                    <th className="px-4 py-3 text-right">剩余</th>
                    <th className="px-4 py-3 text-right">使用率</th>
                    <th className="px-4 py-3 text-left">状态</th>
                  </tr>
                </thead>
                <tbody>
                  {budget.categories.map((category, index) => (
                    <tr
                      key={category.id}
                      className={cx(
                        "border-t border-white/6 align-top hover:bg-[var(--bg-elevated)]",
                        index % 2 === 0 ? "bg-[rgba(20,15,11,0.5)]" : "bg-transparent"
                      )}
                    >
                      <td className="px-4 py-4">
                        <div>
                          <p className="font-medium text-[var(--text-primary)]">{category.category_l1}</p>
                          <p className="mt-1 text-xs text-[var(--text-muted)]">来源：{category.source === "ai" ? "AI 推荐" : category.source}</p>
                        </div>
                      </td>
                      <td className="tabular px-4 py-4 text-right font-medium text-[var(--text-primary)]">
                        {formatCurrency(category.budget)}
                      </td>
                      <td className="tabular px-4 py-4 text-right text-[var(--text-secondary)]">
                        {formatCurrency(category.spent)}
                      </td>
                      <td
                        className={cx(
                          "tabular px-4 py-4 text-right font-medium",
                          category.remaining >= 0 ? "text-emerald-300" : "text-rose-300"
                        )}
                      >
                        {formatCurrency(category.remaining)}
                      </td>
                      <td className="px-4 py-4 text-right text-[var(--text-secondary)]">
                        <div className="ml-auto flex w-44 flex-col items-end gap-2">
                          <span className="tabular">{category.usage_percentage.toFixed(1)}%</span>
                          <ProgressBar
                            className="w-full"
                            size="sm"
                            tone={category.status === "overspent" ? "overspent" : category.status === "warning" ? "warning" : "healthy"}
                            value={category.usage_percentage}
                          />
                        </div>
                      </td>
                      <td className="px-4 py-4">
                        <span className={statusClassName(category.status)}>{statusLabel(category.status)}</span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </Card>
        </>
      )}
    </div>
  );
}

function SkeletonCard() {
  return <div className="h-28 animate-pulse rounded-[24px] bg-[rgba(255,255,255,0.04)]" />;
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

function formatCurrency(value: number) {
  return `¥${value.toLocaleString("zh-CN", { minimumFractionDigits: 2 })}`;
}
