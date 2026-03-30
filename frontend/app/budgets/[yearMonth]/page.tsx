"use client";

import { use } from "react";
import Link from "next/link";
import useSWR from "swr";
import { getBudgetPlan } from "@/lib/api";

export default function BudgetDetailPage({
  params,
}: {
  params: Promise<{ yearMonth: string }>;
}) {
  const { yearMonth } = use(params);
  const { data: budget, error, isLoading, mutate } = useSWR(["budget", yearMonth], ([, ym]) => getBudgetPlan(ym));

  return (
    <div className="space-y-8">
      <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
        <div>
          <Link href="/budgets" className="text-sm text-amber-700 hover:underline">
            ← 返回预算列表
          </Link>
          <h1 className="mt-2 text-3xl font-bold text-stone-900">{yearMonth} 预算规划</h1>
          <p className="mt-2 text-sm text-stone-500">按月查看预算总额、分类执行情况与超支预警。</p>
        </div>
        <button
          type="button"
          onClick={() => mutate(() => getBudgetPlan(yearMonth, true), { revalidate: false })}
          className="inline-flex items-center justify-center rounded-full border border-amber-300 px-5 py-2.5 text-sm font-medium text-amber-800 transition-colors hover:bg-amber-50"
        >
          重新生成预算
        </button>
      </div>

      {error ? (
        <div className="rounded-2xl border border-red-200 bg-red-50 px-5 py-4 text-sm text-red-700">
          预算加载失败：{error.message}
        </div>
      ) : null}

      {isLoading || !budget ? (
        <div className="grid grid-cols-1 gap-4 md:grid-cols-3">
          <SkeletonCard />
          <SkeletonCard />
          <SkeletonCard />
        </div>
      ) : (
        <>
          <div className="grid grid-cols-1 gap-4 md:grid-cols-4">
            <MetricCard title="预算总额" value={budget.total_budget} tone="text-amber-700" />
            <MetricCard title="已支出" value={budget.total_spent} tone="text-rose-600" />
            <MetricCard title="剩余金额" value={budget.remaining} tone={budget.remaining >= 0 ? "text-emerald-600" : "text-orange-600"} />
            <MetricCard title="总体使用率" value={budget.usage_percentage} suffix="%" tone={budget.usage_percentage >= 100 ? "text-red-600" : budget.usage_percentage >= 80 ? "text-amber-600" : "text-emerald-600"} />
          </div>

          <div className="rounded-2xl border border-stone-200 bg-white p-6 shadow-sm">
            <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
              <div>
                <h2 className="text-xl font-semibold text-stone-900">分类预算执行</h2>
                <p className="mt-1 text-sm text-stone-500">
                  {budget.generated ? "当前结果由最新账单趋势生成。" : "当前展示已缓存预算。"}
                </p>
              </div>
              <span className="rounded-full bg-stone-100 px-3 py-1 text-xs font-medium text-stone-600">
                {budget.categories.length} 个分类
              </span>
            </div>

            <div className="mt-6 overflow-hidden rounded-xl border border-stone-200">
              <table className="w-full text-sm">
                <thead className="bg-stone-50 text-xs uppercase text-stone-500">
                  <tr>
                    <th className="px-4 py-3 text-left">分类</th>
                    <th className="px-4 py-3 text-right">预算</th>
                    <th className="px-4 py-3 text-right">已支出</th>
                    <th className="px-4 py-3 text-right">剩余</th>
                    <th className="px-4 py-3 text-right">使用率</th>
                    <th className="px-4 py-3 text-left">状态</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-stone-100">
                  {budget.categories.map((category) => (
                    <tr key={category.id} className="align-top hover:bg-stone-50/80">
                      <td className="px-4 py-4">
                        <div>
                          <p className="font-medium text-stone-900">{category.category_l1}</p>
                          <p className="mt-1 text-xs text-stone-500">来源：{category.source === "ai" ? "AI 推荐" : category.source}</p>
                        </div>
                      </td>
                      <td className="px-4 py-4 text-right font-medium text-stone-900">
                        ¥{category.budget.toLocaleString("zh-CN", { minimumFractionDigits: 2 })}
                      </td>
                      <td className="px-4 py-4 text-right text-stone-700">
                        ¥{category.spent.toLocaleString("zh-CN", { minimumFractionDigits: 2 })}
                      </td>
                      <td className={`px-4 py-4 text-right font-medium ${category.remaining >= 0 ? "text-emerald-600" : "text-orange-600"}`}>
                        ¥{category.remaining.toLocaleString("zh-CN", { minimumFractionDigits: 2 })}
                      </td>
                      <td className="px-4 py-4 text-right text-stone-700">
                        <div className="ml-auto flex w-40 flex-col items-end gap-2">
                          <span>{category.usage_percentage.toFixed(1)}%</span>
                          <div className="h-2 w-full overflow-hidden rounded-full bg-stone-100">
                            <div
                              className={`h-full rounded-full ${category.status === "overspent" ? "bg-red-500" : category.status === "warning" ? "bg-amber-500" : "bg-emerald-500"}`}
                              style={{ width: `${Math.min(category.usage_percentage, 100)}%` }}
                            />
                          </div>
                        </div>
                      </td>
                      <td className="px-4 py-4">
                        <span className={`rounded-full px-2.5 py-1 text-xs font-medium ${statusClassName(category.status)}`}>
                          {statusLabel(category.status)}
                        </span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </>
      )}
    </div>
  );
}

function MetricCard({
  title,
  value,
  tone,
  suffix,
}: {
  title: string;
  value: number;
  tone: string;
  suffix?: string;
}) {
  return (
    <div className="rounded-2xl border border-stone-200 bg-white p-5 shadow-sm">
      <p className="text-sm text-stone-500">{title}</p>
      <p className={`mt-2 text-2xl font-semibold ${tone}`}>
        {suffix ? value.toFixed(1) : `¥${value.toLocaleString("zh-CN", { minimumFractionDigits: 2 })}`}
        {suffix ?? ""}
      </p>
    </div>
  );
}

function SkeletonCard() {
  return <div className="h-28 animate-pulse rounded-2xl bg-stone-100" />;
}

function statusClassName(status: "healthy" | "warning" | "overspent") {
  if (status === "overspent") return "bg-red-100 text-red-700";
  if (status === "warning") return "bg-amber-100 text-amber-700";
  return "bg-emerald-100 text-emerald-700";
}

function statusLabel(status: "healthy" | "warning" | "overspent") {
  if (status === "overspent") return "超支";
  if (status === "warning") return "预警";
  return "健康";
}
