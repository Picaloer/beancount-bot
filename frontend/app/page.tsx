"use client";

import Link from "next/link";
import useSWR from "swr";
import { getBudgetPlan, getTransactionSummary, listImports, listMonths } from "@/lib/api";

export default function Dashboard() {
  const { data: summary } = useSWR("summary", getTransactionSummary);
  const { data: imports } = useSWR("imports", listImports);
  const { data: months } = useSWR("months", listMonths);

  const latestMonth = months?.months?.[0];
  const { data: budget } = useSWR(
    latestMonth ? ["budget", latestMonth] : null,
    ([, yearMonth]) => getBudgetPlan(yearMonth)
  );

  const totalExpense = summary?.expense?.total ?? 0;
  const totalIncome = summary?.income?.total ?? 0;
  const net = totalIncome - totalExpense;

  return (
    <div className="space-y-8">
      <div>
        <h1 className="mt-1 text-2xl font-bold text-gray-900">财务看板</h1>
        <p className="text-sm text-gray-500">全账期汇总概览</p>
      </div>

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
        <SummaryCard
          label="累计支出"
          value={`¥${totalExpense.toLocaleString("zh-CN", { minimumFractionDigits: 2 })}`}
          color="text-red-600"
          bg="bg-red-50"
        />
        <SummaryCard
          label="累计收入"
          value={`¥${totalIncome.toLocaleString("zh-CN", { minimumFractionDigits: 2 })}`}
          color="text-green-600"
          bg="bg-green-50"
        />
        <SummaryCard
          label="净资产变化"
          value={`${net >= 0 ? "+" : ""}¥${net.toLocaleString("zh-CN", { minimumFractionDigits: 2 })}`}
          color={net >= 0 ? "text-indigo-600" : "text-orange-600"}
          bg={net >= 0 ? "bg-indigo-50" : "bg-orange-50"}
        />
      </div>

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-[1.4fr_1fr]">
        <BudgetOverviewCard latestMonth={latestMonth} budget={budget} />
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-1">
          <ActionCard
            title="导入账单"
            description="上传微信支付 XLSX/CSV 或支付宝 CSV 账单"
            href="/import"
            icon="📂"
          />
          {latestMonth ? (
            <ActionCard
              title={`查看 ${latestMonth} 报告`}
              description="查看最新月度财务分析报告"
              href={`/reports/${latestMonth}`}
              icon="📊"
            />
          ) : (
            <ActionCard
              title="财务报告"
              description="导入账单后生成月度报告"
              href="/reports"
              icon="📊"
            />
          )}
        </div>
      </div>

      <div>
        <div className="mb-3 flex items-center justify-between">
          <h2 className="text-lg font-semibold">最近导入</h2>
          <Link href="/import" className="text-sm text-indigo-600 hover:underline">
            查看全部
          </Link>
        </div>
        <div className="overflow-hidden rounded-xl border border-gray-200 bg-white">
          {!imports || imports.length === 0 ? (
            <div className="py-12 text-center text-gray-400">
              <p className="mb-2 text-3xl">📄</p>
              <p>
                暂无导入记录，
                <Link href="/import" className="text-indigo-600 hover:underline">
                  立即导入
                </Link>
              </p>
            </div>
          ) : (
            <table className="w-full text-sm">
              <thead className="bg-gray-50 text-xs uppercase text-gray-500">
                <tr>
                  <th className="px-4 py-3 text-left">文件</th>
                  <th className="px-4 py-3 text-left">来源</th>
                  <th className="px-4 py-3 text-right">条数</th>
                  <th className="px-4 py-3 text-left">状态</th>
                  <th className="px-4 py-3 text-left">时间</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100">
                {imports.slice(0, 5).map((imp) => (
                  <tr key={imp.import_id} className="hover:bg-gray-50">
                    <td className="max-w-xs truncate px-4 py-3">{imp.file_name}</td>
                    <td className="px-4 py-3">
                      <SourceBadge source={imp.source} />
                    </td>
                    <td className="px-4 py-3 text-right">{imp.row_count}</td>
                    <td className="px-4 py-3">
                      <StatusBadge status={imp.status} />
                    </td>
                    <td className="px-4 py-3 text-gray-500">
                      {new Date(imp.imported_at).toLocaleDateString("zh-CN")}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      </div>
    </div>
  );
}

function SummaryCard({
  label,
  value,
  color,
  bg,
}: {
  label: string;
  value: string;
  color: string;
  bg: string;
}) {
  return (
    <div className={`${bg} rounded-xl p-5`}>
      <p className="mb-1 text-sm text-gray-500">{label}</p>
      <p className={`text-2xl font-bold ${color}`}>{value}</p>
    </div>
  );
}

function BudgetOverviewCard({
  latestMonth,
  budget,
}: {
  latestMonth?: string;
  budget?: {
    total_budget: number;
    total_spent: number;
    remaining: number;
    usage_percentage: number;
    generated: boolean;
    categories: {
      category_l1: string;
      budget: number;
      spent: number;
      usage_percentage: number;
      status: "healthy" | "warning" | "overspent";
    }[];
  };
}) {
  return (
    <div className="rounded-2xl border border-amber-200/80 bg-white/90 p-6 shadow-[0_16px_50px_rgba(120,98,63,0.08)]">
      <div className="flex flex-col gap-2 sm:flex-row sm:items-start sm:justify-between">
        <div>
          <p className="text-sm font-medium text-amber-700">预算规划</p>
          <h2 className="mt-1 text-xl font-semibold text-stone-900">
            {latestMonth ? `${latestMonth} 智能预算` : "智能预算"}
          </h2>
          <p className="mt-1 text-sm text-stone-500">
            {latestMonth ? "基于近 6 个月消费趋势自动推荐预算。" : "导入账单后自动生成预算建议。"}
          </p>
        </div>
        <Link
          href={latestMonth ? `/budgets/${latestMonth}` : "/budgets"}
          className="inline-flex items-center rounded-full border border-amber-300 px-4 py-2 text-sm font-medium text-amber-800 transition-colors hover:bg-amber-50"
        >
          查看预算详情
        </Link>
      </div>

      {!latestMonth ? (
        <div className="mt-6 rounded-xl border border-dashed border-stone-300 px-4 py-8 text-center text-sm text-stone-500">
          暂无可用账期，请先导入账单生成预算。
        </div>
      ) : !budget ? (
        <div className="mt-6 grid grid-cols-1 gap-4 sm:grid-cols-3">
          <SkeletonStat />
          <SkeletonStat />
          <SkeletonStat />
        </div>
      ) : (
        <>
          <div className="mt-6 grid grid-cols-1 gap-4 sm:grid-cols-3">
            <BudgetStat label="预算总额" value={budget.total_budget} accent="text-amber-700" />
            <BudgetStat label="已支出" value={budget.total_spent} accent="text-rose-600" />
            <BudgetStat label="剩余可用" value={budget.remaining} accent={budget.remaining >= 0 ? "text-emerald-600" : "text-orange-600"} />
          </div>

          <div className="mt-5">
            <div className="mb-2 flex items-center justify-between text-sm text-stone-500">
              <span>整体使用率</span>
              <span>{budget.usage_percentage.toFixed(1)}%</span>
            </div>
            <div className="h-3 overflow-hidden rounded-full bg-stone-100">
              <div
                className={`h-full rounded-full ${budget.usage_percentage >= 100 ? "bg-red-500" : budget.usage_percentage >= 80 ? "bg-amber-500" : "bg-emerald-500"}`}
                style={{ width: `${Math.min(budget.usage_percentage, 100)}%` }}
              />
            </div>
            <p className="mt-2 text-xs text-stone-500">
              {budget.generated ? "已按最新流水重新生成预算建议。" : "当前展示已缓存的月度预算。"}
            </p>
          </div>

          <div className="mt-6 space-y-3">
            {budget.categories.slice(0, 4).map((category) => (
              <div key={category.category_l1} className="rounded-xl border border-stone-200 px-4 py-3">
                <div className="flex items-center justify-between gap-4">
                  <div>
                    <p className="font-medium text-stone-900">{category.category_l1}</p>
                    <p className="text-sm text-stone-500">
                      已支出 ¥{category.spent.toLocaleString("zh-CN", { minimumFractionDigits: 2 })} / 预算 ¥{category.budget.toLocaleString("zh-CN", { minimumFractionDigits: 2 })}
                    </p>
                  </div>
                  <span className={`rounded-full px-2.5 py-1 text-xs font-medium ${statusClassName(category.status)}`}>
                    {statusLabel(category.status)}
                  </span>
                </div>
                <div className="mt-3 h-2 overflow-hidden rounded-full bg-stone-100">
                  <div
                    className={`h-full rounded-full ${category.status === "overspent" ? "bg-red-500" : category.status === "warning" ? "bg-amber-500" : "bg-emerald-500"}`}
                    style={{ width: `${Math.min(category.usage_percentage, 100)}%` }}
                  />
                </div>
              </div>
            ))}
          </div>
        </>
      )}
    </div>
  );
}

function BudgetStat({
  label,
  value,
  accent,
}: {
  label: string;
  value: number;
  accent: string;
}) {
  return (
    <div className="rounded-xl bg-amber-50/70 p-4">
      <p className="text-sm text-stone-500">{label}</p>
      <p className={`mt-1 text-2xl font-semibold ${accent}`}>
        ¥{value.toLocaleString("zh-CN", { minimumFractionDigits: 2 })}
      </p>
    </div>
  );
}

function SkeletonStat() {
  return <div className="h-24 animate-pulse rounded-xl bg-stone-100" />;
}

function ActionCard({
  title,
  description,
  href,
  icon,
}: {
  title: string;
  description: string;
  href: string;
  icon: string;
}) {
  return (
    <Link
      href={href}
      className="flex items-start gap-4 rounded-xl border border-gray-200 bg-white p-5 transition-all hover:border-indigo-400 hover:shadow-sm"
    >
      <span className="text-3xl">{icon}</span>
      <div>
        <p className="font-semibold text-gray-900">{title}</p>
        <p className="mt-0.5 text-sm text-gray-500">{description}</p>
      </div>
    </Link>
  );
}

function SourceBadge({ source }: { source: string }) {
  const map: Record<string, string> = { wechat: "微信", alipay: "支付宝" };
  return <span className="rounded-full bg-blue-100 px-2 py-0.5 text-xs text-blue-700">{map[source] ?? source}</span>;
}

function StatusBadge({ status }: { status: string }) {
  const map: Record<string, { label: string; cls: string }> = {
    done: { label: "完成", cls: "bg-green-100 text-green-700" },
    pending: { label: "等待中", cls: "bg-yellow-100 text-yellow-700" },
    processing: { label: "处理中", cls: "bg-blue-100 text-blue-700" },
    classifying: { label: "分类中", cls: "bg-purple-100 text-purple-700" },
    failed: { label: "失败", cls: "bg-red-100 text-red-700" },
  };
  const { label, cls } = map[status] ?? { label: status, cls: "bg-gray-100 text-gray-700" };
  return <span className={`rounded-full px-2 py-0.5 text-xs ${cls}`}>{label}</span>;
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
