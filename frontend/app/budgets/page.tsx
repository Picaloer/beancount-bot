"use client";

import Link from "next/link";
import useSWR from "swr";
import { getBudgetPlan, listMonths } from "@/lib/api";

export default function BudgetsPage() {
  const { data: months } = useSWR("months", listMonths);
  const latestMonth = months?.months?.[0];
  const { data: budget } = useSWR(
    latestMonth ? ["budget", latestMonth] : null,
    ([, yearMonth]) => getBudgetPlan(yearMonth)
  );

  return (
    <div className="space-y-8">
      <div className="flex flex-col gap-3 md:flex-row md:items-end md:justify-between">
        <div>
          <p className="text-sm font-medium text-amber-700">Budget Planner</p>
          <h1 className="text-3xl font-bold text-stone-900">预算规划</h1>
          <p className="mt-2 text-sm text-stone-500">
            根据历史消费趋势，为每个账期自动生成预算建议与执行状态。
          </p>
        </div>
        {latestMonth ? (
          <Link
            href={`/budgets/${latestMonth}`}
            className="inline-flex items-center rounded-full bg-amber-600 px-5 py-2.5 text-sm font-medium text-white transition-colors hover:bg-amber-700"
          >
            查看最新预算
          </Link>
        ) : null}
      </div>

      {!months ? (
        <div className="grid grid-cols-1 gap-4 md:grid-cols-3">
          <SkeletonCard />
          <SkeletonCard />
          <SkeletonCard />
        </div>
      ) : months.months.length === 0 ? (
        <EmptyState />
      ) : (
        <div className="grid grid-cols-1 gap-6 xl:grid-cols-[1.4fr_1fr]">
          <div className="rounded-2xl border border-stone-200 bg-white p-6 shadow-sm">
            <div className="mb-5 flex items-center justify-between">
              <div>
                <h2 className="text-xl font-semibold text-stone-900">可用账期</h2>
                <p className="mt-1 text-sm text-stone-500">选择任一月份查看预算建议。</p>
              </div>
              <span className="rounded-full bg-stone-100 px-3 py-1 text-xs font-medium text-stone-600">
                {months.months.length} 个账期
              </span>
            </div>
            <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
              {months.months.map((month) => (
                <Link
                  key={month}
                  href={`/budgets/${month}`}
                  className={`rounded-xl border px-4 py-4 transition-all hover:-translate-y-0.5 hover:border-amber-300 hover:shadow-sm ${month === latestMonth ? "border-amber-300 bg-amber-50/70" : "border-stone-200 bg-stone-50/50"}`}
                >
                  <div className="flex items-center justify-between gap-3">
                    <div>
                      <p className="text-base font-semibold text-stone-900">{month}</p>
                      <p className="mt-1 text-sm text-stone-500">查看该月预算执行情况</p>
                    </div>
                    {month === latestMonth ? (
                      <span className="rounded-full bg-amber-100 px-2.5 py-1 text-xs font-medium text-amber-700">
                        最新
                      </span>
                    ) : null}
                  </div>
                </Link>
              ))}
            </div>
          </div>

          <div className="rounded-2xl border border-amber-200 bg-gradient-to-br from-amber-50 via-white to-orange-50 p-6 shadow-sm">
            <h2 className="text-xl font-semibold text-stone-900">本月预算概览</h2>
            {!latestMonth || !budget ? (
              <div className="mt-6 space-y-3">
                <SkeletonCard />
                <SkeletonCard />
              </div>
            ) : (
              <>
                <p className="mt-2 text-sm text-stone-500">{latestMonth} 自动生成预算摘要</p>
                <div className="mt-5 grid grid-cols-1 gap-3">
                  <Metric title="预算总额" value={budget.total_budget} tone="text-amber-700" />
                  <Metric title="已支出" value={budget.total_spent} tone="text-rose-600" />
                  <Metric title="剩余空间" value={budget.remaining} tone={budget.remaining >= 0 ? "text-emerald-600" : "text-orange-600"} />
                </div>
                <div className="mt-5">
                  <div className="mb-2 flex items-center justify-between text-sm text-stone-500">
                    <span>使用率</span>
                    <span>{budget.usage_percentage.toFixed(1)}%</span>
                  </div>
                  <div className="h-3 overflow-hidden rounded-full bg-white/80">
                    <div
                      className={`h-full rounded-full ${budget.usage_percentage >= 100 ? "bg-red-500" : budget.usage_percentage >= 80 ? "bg-amber-500" : "bg-emerald-500"}`}
                      style={{ width: `${Math.min(budget.usage_percentage, 100)}%` }}
                    />
                  </div>
                </div>
                <div className="mt-5 space-y-3">
                  {budget.categories.slice(0, 3).map((category) => (
                    <div key={category.id} className="rounded-xl bg-white/80 px-4 py-3">
                      <div className="flex items-center justify-between gap-3">
                        <p className="font-medium text-stone-900">{category.category_l1}</p>
                        <span className={`rounded-full px-2 py-0.5 text-xs ${statusClassName(category.status)}`}>
                          {statusLabel(category.status)}
                        </span>
                      </div>
                      <p className="mt-1 text-sm text-stone-500">
                        ¥{category.spent.toLocaleString("zh-CN", { minimumFractionDigits: 2 })} / ¥{category.budget.toLocaleString("zh-CN", { minimumFractionDigits: 2 })}
                      </p>
                    </div>
                  ))}
                </div>
              </>
            )}
          </div>
        </div>
      )}
    </div>
  );
}

function Metric({ title, value, tone }: { title: string; value: number; tone: string }) {
  return (
    <div className="rounded-xl bg-white/80 px-4 py-3">
      <p className="text-sm text-stone-500">{title}</p>
      <p className={`mt-1 text-2xl font-semibold ${tone}`}>
        ¥{value.toLocaleString("zh-CN", { minimumFractionDigits: 2 })}
      </p>
    </div>
  );
}

function EmptyState() {
  return (
    <div className="rounded-2xl border border-dashed border-stone-300 bg-white px-6 py-16 text-center">
      <p className="text-4xl">🧾</p>
      <h2 className="mt-4 text-xl font-semibold text-stone-900">还没有可分析的账期</h2>
      <p className="mt-2 text-sm text-stone-500">请先导入微信或支付宝账单，系统会自动生成月度预算建议。</p>
      <Link
        href="/import"
        className="mt-6 inline-flex items-center rounded-full bg-amber-600 px-5 py-2.5 text-sm font-medium text-white transition-colors hover:bg-amber-700"
      >
        去导入账单
      </Link>
    </div>
  );
}

function SkeletonCard() {
  return <div className="h-24 animate-pulse rounded-xl bg-stone-100" />;
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
